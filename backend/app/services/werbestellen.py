"""Werbestellen in Podcast-Folgen (RAD-32): eine Stelle für die Frage "welche Abschnitte einer Folge sind Werbung".
Die Wiedergabe springt darüber, die Datei bleibt immer vollständig; wer will, speichert eine Fassung ohne Werbung als
neue Datei daneben. Vorbild ist TubeVault (services/ad_segments.py), nur gibt es für Podcasts keinen Dienst der
Gemeinschaft: die Stellen kommen aus eigenen Quellen.

Herkunft einer Stelle:
    kapitel      Kapitel im Feed (podcast:chapters), deren Titel nach Werbung klingt
    hand         von Hand gesetzt (Folgendetail oder Schnitt)
    vergleich    Vergleich zweier Fassungen derselben Folge (eingefügte Werbung unterscheidet sich)
    transkript   aus dem Transkript (sobald es Transkripte gibt, RAD-22)

"Keine Werbung" verwirft eine Stelle nur (verworfen = 1): eine neue Suche legt eine Stelle, die eine verworfene
überdeckt, nicht wieder an. Eine neue Suche ersetzt die Stellen ihrer Quelle, die von Hand bleiben.
"""
from __future__ import annotations

import logging
import re
import shutil
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Literal

import httpx
from pydantic import BaseModel

from ..ablage import ablage
from ..config import get_arbeit_dir
from ..database import db_session
from . import propagandafilter
from .segment_splitter import _ffmpeg

logger = logging.getLogger("radiohub.werbestellen")

Herkunft = Literal["kapitel", "hand", "vergleich", "transkript"]
Fortschritt = Callable[[int, int, str], None]

# Titel von Kapiteln, die Werbung meinen (deutsch und englisch, wie sie in Feeds vorkommen)
WERBETITEL = re.compile(r"\b(werbung|werbepause|anzeige|sponsor\w*|unterst[üu]tzt von|präsentiert von|ad|ads|ad break|"
                        r"advert\w*|commercial)\b", re.IGNORECASE)
# kürzer als das ist keine Stelle (Rundungen der Kapitel, Klicks)
KUERZESTE_S = 2.0


class Werbestelle(BaseModel):
    id: int
    folge_id: int
    von: float
    bis: float
    herkunft: Herkunft
    text: str
    verworfen: bool


class Neu(BaseModel):
    von: float
    bis: float
    text: str = ""


def _zeile(r) -> Werbestelle:
    return Werbestelle(id=r["id"], folge_id=r["folge_id"], von=r["von"], bis=r["bis"], herkunft=r["herkunft"],
                       text=r["text"], verworfen=bool(r["verworfen"]))


def stellen(folge_id: int, mit_verworfenen: bool = False) -> list[Werbestelle]:
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM werbestellen WHERE folge_id = ?" + ("" if mit_verworfenen else " AND verworfen = 0")
                            + " ORDER BY von", (folge_id,)).fetchall()
    return [_zeile(r) for r in rows]


def anlegen(folge_id: int, neu: Neu, herkunft: Herkunft = "hand") -> Werbestelle:
    if neu.bis - neu.von < KUERZESTE_S:
        raise ValueError(f"Eine Werbestelle dauert mindestens {KUERZESTE_S:g} Sekunden")
    with db_session() as conn:
        if not conn.execute("SELECT 1 FROM podcast_episodes WHERE id = ?", (folge_id,)).fetchone():
            raise LookupError("Folge nicht gefunden")
        cur = conn.execute("INSERT INTO werbestellen (folge_id, von, bis, herkunft, text) VALUES (?, ?, ?, ?, ?)",
                           (folge_id, max(0.0, neu.von), neu.bis, herkunft, neu.text[:300]))
        r = conn.execute("SELECT * FROM werbestellen WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _zeile(r)


def verwerfen(stelle_id: int, an: bool) -> Werbestelle:
    """Keine Werbung (an) oder doch Werbung (aus, Rückgängig)."""
    with db_session() as conn:
        conn.execute("UPDATE werbestellen SET verworfen = ? WHERE id = ?", (1 if an else 0, stelle_id))
        r = conn.execute("SELECT * FROM werbestellen WHERE id = ?", (stelle_id,)).fetchone()
    if not r:
        raise LookupError("Werbestelle nicht gefunden")
    return _zeile(r)


def _ueberdeckt(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """mehr als die Hälfte der kürzeren überlappt"""
    ueber = min(a[1], b[1]) - max(a[0], b[0])
    return ueber > 0.5 * min(a[1] - a[0], b[1] - b[0])


def ersetzen(folge_id: int, herkunft: Herkunft, neue: list[Neu]) -> int:
    """Die Stellen einer Quelle neu setzen; verworfene bleiben verworfen (auch für überdeckende neue). Liefert die Zahl."""
    with db_session() as conn:
        verworfen = [(r["von"], r["bis"]) for r in conn.execute(
            "SELECT von, bis FROM werbestellen WHERE folge_id = ? AND verworfen = 1", (folge_id,)).fetchall()]
        conn.execute("DELETE FROM werbestellen WHERE folge_id = ? AND herkunft = ? AND verworfen = 0", (folge_id, herkunft))
        zahl = 0
        for n in neue:
            if n.bis - n.von < KUERZESTE_S or any(_ueberdeckt((n.von, n.bis), v) for v in verworfen):
                continue
            conn.execute("INSERT INTO werbestellen (folge_id, von, bis, herkunft, text) VALUES (?, ?, ?, ?, ?)",
                         (folge_id, max(0.0, n.von), n.bis, herkunft, n.text[:300]))
            zahl += 1
    return zahl


def uebersicht(folge_ids: list[int]) -> dict[int, tuple[int, float]]:
    """je Folge Zahl und Dauer der Werbestellen (für Zeilen und Abo-Kopf)"""
    if not folge_ids:
        return {}
    platz = ",".join("?" * len(folge_ids))
    with db_session() as conn:
        rows = conn.execute(f"SELECT folge_id, COUNT(*) n, SUM(bis - von) d FROM werbestellen WHERE verworfen = 0 "
                            f"AND folge_id IN ({platz}) GROUP BY folge_id", folge_ids).fetchall()
    return {r["folge_id"]: (r["n"], r["d"] or 0.0) for r in rows}


# ----- Quellen --------------------------------------------------------------------------------------------------

def kapitel_werbung(kapitel: list[dict], dauer: float) -> list[Neu]:
    """Kapitel im Format podcast:chapters (startTime, endTime, title): die nach Werbung klingenden als Stellen. Ohne
    endTime endet ein Kapitel beim nächsten oder am Ende der Folge."""
    reihe = sorted((k for k in kapitel if isinstance(k.get("startTime"), (int, float))), key=lambda k: k["startTime"])
    neue: list[Neu] = []
    for i, k in enumerate(reihe):
        titel = str(k.get("title") or "")
        if not WERBETITEL.search(titel):
            continue
        ende = k.get("endTime") if isinstance(k.get("endTime"), (int, float)) else (
            reihe[i + 1]["startTime"] if i + 1 < len(reihe) else dauer)
        if ende and ende > k["startTime"]:
            neue.append(Neu(von=float(k["startTime"]), bis=float(ende), text=f'Kapitel "{titel[:80]}"'))
    return neue


async def kapitel_lesen(adresse: str, dauer: float, client: httpx.AsyncClient | None = None) -> list[Neu]:
    eigen = client is None
    client = client or httpx.AsyncClient(timeout=20, follow_redirects=True)
    try:
        antwort = await client.get(adresse)
        antwort.raise_for_status()
        daten = antwort.json()
    finally:
        if eigen:
            await client.aclose()
    return kapitel_werbung(daten.get("chapters") or [], dauer)


def gespeichert(folge: dict) -> bool:
    return bool(folge.get("is_downloaded") and folge.get("local_path"))


def quellen(folge: dict) -> list[Herkunft]:
    """Welche Quellen für diese Folge gehen (nur die zeigt die Oberfläche). Der Vergleich braucht die gespeicherte
    Datei: nur für sie gelten die Zeiten, die er findet."""
    was: list[Herkunft] = []
    if folge.get("chapters_url"):
        was.append("kapitel")
    if gespeichert(folge) and folge.get("audio_url") and propagandafilter.FilterEinstellungen.jetzt().eingerichtet:
        was.append("vergleich")
    return was


NAMEN: dict[str, str] = {"kapitel": "Kapitel im Feed", "vergleich": "Vergleich zweier Fassungen"}


async def vergleich_suchen(folge: dict, melden: propagandafilter.Melden) -> list[Neu]:
    """Die gespeicherte Datei mit einer frisch geholten Fassung derselben Folge vergleichen lassen (Propaganda-Filter);
    was nur in der gespeicherten vorkommt, ist beim Abruf eingesetzte Werbung."""
    titel = str(folge.get("title") or "")
    ergebnis = await propagandafilter.vergleichen(propagandafilter.FilterEinstellungen.jetzt(),
                                                  ablage().lesen(folge["local_path"]), folge["audio_url"],
                                                  f"Podcast: {titel}"[:300], melden)
    if ergebnis.gleich or not ergebnis.verwertbar:
        if ergebnis.hinweis:
            logger.info("Vergleich Folge %s: %s", folge["id"], ergebnis.hinweis)
        return []
    return [Neu(von=s.von, bis=s.bis, text="Nur in dieser Fassung (Vergleich)") for s in ergebnis.nur_in_a]


async def suchen(folge: dict, fortschritt: Fortschritt) -> dict[str, int]:
    """Alle möglichen Quellen nacheinander; liefert je Quelle die Zahl der gefundenen Stellen."""
    was = quellen(folge)
    ergebnis: dict[str, int] = {}
    for i, q in enumerate(was):
        name = NAMEN.get(q, q)
        fortschritt(i + 1, len(was), name)
        if q == "kapitel":
            neue = await kapitel_lesen(folge["chapters_url"], float(folge.get("duration") or 0))
        elif q == "vergleich":
            def melden(anteil: float, schritt: str, i: int = i) -> None:
                fortschritt(i + 1, len(was), f"{name}: {schritt} ({anteil:.0%})")
            neue = await vergleich_suchen(folge, melden)
        else:
            continue
        ergebnis[q] = ersetzen(folge["id"], q, neue)
    return ergebnis


# ----- Fassung ohne Werbung -------------------------------------------------------------------------------------

def _filter_ohne(stellen_: list[Werbestelle]) -> str:
    """ffmpeg-Filter: die Werbestellen weglassen, die Zeit danach lückenlos"""
    weg = "+".join(f"between(t,{s.von:.3f},{s.bis:.3f})" for s in stellen_)
    return f"aselect='not({weg})',asetpts=N/SR/TB"


KODIERUNG = {".mp3": ["-c:a", "libmp3lame", "-q:a", "2"], ".m4a": ["-c:a", "aac", "-b:a", "128k"],
             ".aac": ["-c:a", "aac", "-b:a", "128k"], ".ogg": ["-c:a", "libvorbis", "-q:a", "5"],
             ".opus": ["-c:a", "libopus", "-b:a", "96k"]}


async def ohne_werbung(folge: dict, fortschritt: Fortschritt) -> str:
    """Neue Datei ohne die Werbestellen neben die gespeicherte Folge legen (das Original bleibt); liefert ihren Pfad."""
    pfad = folge.get("local_path") or ""
    if not (folge.get("is_downloaded") and pfad):
        raise ValueError("Die Folge ist nicht in der Kellerwolke gespeichert")
    weg = stellen(folge["id"])
    if not weg:
        raise ValueError("Keine Werbestellen in dieser Folge")
    endung = PurePosixPath(pfad).suffix.lower() or ".mp3"
    arbeit = get_arbeit_dir("werbung", str(folge["id"]))
    try:
        fortschritt(1, 3, "Folge holen")
        quelle = await ablage().herunterladen(pfad, arbeit / f"quelle{endung}")
        fortschritt(2, 3, "Werbung herausschneiden")
        ziel = arbeit / f"ohne{endung}"
        ok, fehler = await _ffmpeg(["ffmpeg", "-y", "-v", "error", "-i", str(quelle), "-af", _filter_ohne(weg), "-vn",
                                    *KODIERUNG.get(endung, ["-c:a", "libmp3lame", "-q:a", "2"]), str(ziel)], 1800)
        if not ok or not Path(ziel).exists():
            raise RuntimeError(f"Herausschneiden fehlgeschlagen: {fehler[-200:]}")
        fortschritt(3, 3, "Ablegen")
        stamm = PurePosixPath(pfad)
        neu = await ablage().freier_pfad(str(stamm.with_name(f"{stamm.stem} (ohne Werbung){endung}")))
        await ablage().ablegen(neu, ziel)
        return neu
    finally:
        shutil.rmtree(arbeit, ignore_errors=True)
