"""Podcast-Folgen in einer anderen Sprache (RAD-26): Auf Knopfdruck wird eine Folge gespeichert, transkribiert (wenn noch kein
gehörtes Transkript da ist) und von der Vertonung übersetzt und zeitgenau neu gesprochen. Ton und Text der Fassung liegen danach als
Begleitdateien neben der Folge (`X.mp3`: `X.de.sprache.m4a`, `X.de.transkript.json`), beim Original und seinem Transkript; der
Papierkorb nimmt sie zusammen. Der Auftrag merkt sich den der Vertonung und verfolgt ihn nach einem Neustart weiter."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from appkern.auftraege import Art, AuftragAbgebrochen, AuftragFehler, Kontext, Phase
from appkern.verbund import VerbundFehler
from appkern.vorlesen import stimmwahl
from pydantic import BaseModel

from ..ablage import AblageFehler, ablage
from ..config import get_arbeit_dir
from ..database import db_session
from ..einstellungen import stand as einstellungen_stand
from .folgentranskript import ROLLE as ROLLE_TRANSKRIPT
from .folgentranskript import Folgentranskripte, Segment, folgentranskripte
from .uebersetzerstimme import stimme_aus
from .vertonungsdienst import Auftragsstand, Spurtext, Texte, Textspur, Vertonungsdienst, voruebergehend

ART = "folge_vertonen"
ORIGINAL = "original"                 # Wert der Stimme: je Sprecher seine eigene aus der Folge
TAKT_S = 10.0
UNBEKANNT = ("", "auto", "und")


class Eingabe(BaseModel):
    folge_id: int
    sprache: str
    stimme: str = ""                  # leer: die Einstellung


class Ergebnis(BaseModel):
    pfad: str
    absaetze: int


class Fassung(BaseModel):
    sprache: str
    pfad: str
    stimme: str = ""


def rolle_ton(sprache: str) -> str:
    return f"sprache_{sprache}"


def rolle_text(sprache: str) -> str:
    return f"{ROLLE_TRANSKRIPT}_{sprache}"


def stimme_der_folgen() -> str:
    e = einstellungen_stand()
    return e.podcast_stimme.strip() or stimme_aus(e)


def transkript_json(name: str, spur: Textspur, dienst: str) -> bytes:
    """Eine Textspur im Format der Transkription (`transkript/1`)."""
    namen = list(dict.fromkeys(s.sprecher for s in spur.segmente if s.sprecher))
    kennung = {n: f"s{i}" for i, n in enumerate(namen, 1)}
    jetzt = datetime.now(UTC).isoformat()
    return json.dumps({
        "format": "transkript/1", "name": name[:200], "sprache": spur.sprache or "und",
        "dauer_s": max((s.ende for s in spur.segmente), default=0.0), "erstellt_am": jetzt, "geaendert_am": jetzt,
        "sprecher": [{"kennung": kennung[n], "name": n} for n in namen],
        "segmente": [{"start": s.start, "ende": s.ende, "text": s.text, **({"sprecher": kennung[s.sprecher]} if s.sprecher else {})}
                     for s in spur.segmente if s.text.strip()],
        "erzeugt_mit": {"dienst": dienst},
    }, ensure_ascii=False, indent=1).encode()


# ----- Was es gibt (Verzeichnis in der Datenbank)

def fassungen(folge_id: int) -> list[Fassung]:
    with db_session() as conn:
        return [Fassung(sprache=z["sprache"], pfad=z["pfad"], stimme=z["stimme"]) for z in
                conn.execute("SELECT sprache, pfad, stimme FROM podcast_fassungen WHERE folge_id = ? ORDER BY sprache", (folge_id,))]


def fassung(folge_id: int, sprache: str) -> Fassung | None:
    return next((f for f in fassungen(folge_id) if f.sprache == sprache), None)


def merken(folge_id: int, f: Fassung) -> None:
    """Neue oder neu gesprochene Fassung; ab jetzt hört man sie."""
    with db_session() as conn:
        conn.execute("INSERT OR REPLACE INTO podcast_fassungen (folge_id, sprache, pfad, stimme) VALUES (?, ?, ?, ?)",
                     (folge_id, f.sprache, f.pfad, f.stimme))
        conn.execute("UPDATE podcast_episodes SET fassung = ? WHERE id = ?", (f.sprache, folge_id))


def waehlen(folge_id: int, sprache: str) -> None:
    """Welche Fassung man hört, auf allen Geräten (leer: das Original)."""
    with db_session() as conn:
        conn.execute("UPDATE podcast_episodes SET fassung = ? WHERE id = ?", (sprache, folge_id))


# ----- Auftrag

class Folgenvertonung:
    """`dienst`: die Vertonung nach den jetzigen Einstellungen (None: nicht eingerichtet)."""

    def __init__(self, transkripte: Folgentranskripte) -> None:
        self.transkripte = transkripte
        self.dienst: Callable[[], Vertonungsdienst | None] = lambda: None

    def kann(self) -> bool:
        return self.dienst() is not None and bool(stimme_der_folgen()) and self.transkripte.kann()

    async def _vertonen(self, k: Kontext) -> Ergebnis:
        e: Eingabe = k.eingabe
        dienst = self.dienst()
        wahl = (e.stimme or stimme_der_folgen()).strip()
        ersatz = stimmwahl(stimme_aus(einstellungen_stand()) if wahl == ORIGINAL else wahl)
        if dienst is None or ersatz is None:
            raise AuftragFehler("Vertonung oder Stimme fehlt (Einstellungen)")
        folge = await self.transkripte.gespeichert(k, e.folge_id)
        pfad, name = folge.pfad, folge.titel
        if "vertonung" not in k.zwischenstand:
            await self._abgeben(k, e, dienst, ersatz, wahl == ORIGINAL, pfad, name)
        stand = await self._abwarten(k, dienst, k.zwischenstand["vertonung"])
        return await self._ablegen(k, e, dienst, stand, pfad, name, wahl)

    async def _abgeben(self, k: Kontext, e: Eingabe, dienst: Vertonungsdienst, stimme: dict[str, str], original: bool, pfad: str,
                       name: str) -> None:
        ausgang, segmente = None, None
        if not original:                 # Originalstimmen: die Vertonung hört selbst, mit getrennten Sprechern
            gehoert = await self.transkripte.gehoert_sichern(k, e.folge_id, pfad)
            ausgang = gehoert.sprache if gehoert.sprache not in UNBEKANNT else None
            if ausgang == e.sprache:
                raise AuftragFehler(f"Die Folge ist schon in dieser Sprache ({ausgang})")
            segmente = [_spurtext(s) for s in gehoert.segmente]
            if not segmente:
                raise AuftragFehler("Das Transkript ist leer, es gibt nichts zu sprechen")
        await k.fortschritt(None, "An die Vertonung", phase="vertonen")
        ton = get_arbeit_dir("vertonung") / f"{e.folge_id}{PurePosixPath(pfad).suffix.lower()}"
        try:
            await ablage().herunterladen(pfad, ton)
            await k.pruefen()
            auftrag = await dienst.abgeben(ton, name, ausgang, e.sprache, stimme, original=original, segmente=segmente)
        except (AblageFehler, VerbundFehler) as f:
            raise AuftragFehler(f"Vertonung: {f}") from f
        finally:
            ton.unlink(missing_ok=True)
        await k.merken(vertonung=auftrag)

    async def _abwarten(self, k: Kontext, dienst: Vertonungsdienst, auftrag: str) -> Auftragsstand:
        await k.fortschritt(None, "Vertonung", phase="vertonen")
        while True:
            try:
                await k.pruefen()
            except AuftragAbgebrochen:
                await self._loslassen(k, dienst, auftrag, abbrechen=True)
                raise
            try:
                s = await dienst.stand(auftrag)
            except VerbundFehler as f:
                if not voruebergehend(f):
                    await k.merken(vertonung=None)
                    k.zwischenstand.pop("vertonung", None)
                    raise AuftragFehler(f"Vertonung: {f.meldung}") from f
                await k.fortschritt(None, f"Vertonung: {f.meldung}")
            else:
                if s.zustand == "fertig":
                    return s
                if not s.laeuft:
                    await self._loslassen(k, dienst, auftrag, abbrechen=False)
                    raise AuftragFehler(f"Vertonung: {(s.fehler or s.zustand).strip().splitlines()[0]}")
                await k.fortschritt(s.fortschritt, s.schritt or "wartet")
            await asyncio.sleep(TAKT_S)

    @staticmethod
    async def _loslassen(k: Kontext, dienst: Vertonungsdienst, auftrag: str, *, abbrechen: bool) -> None:
        """Wiederholen fragt neu an; die Vertonung räumt ihre Kopie weg (sonst tut sie es nach ihrer Frist)."""
        await k.merken(vertonung=None)
        k.zwischenstand.pop("vertonung", None)
        try:
            await (dienst.abbrechen(auftrag) if abbrechen else dienst.abgeholt(auftrag))
        except VerbundFehler:
            pass

    async def _ablegen(self, k: Kontext, e: Eingabe, dienst: Vertonungsdienst, stand: Auftragsstand, pfad: str, name: str,
                       wahl: str) -> Ergebnis:
        auftrag = k.zwischenstand["vertonung"]
        await k.fortschritt(None, "Ton und Text ablegen", phase="ablegen")
        ton: Path = get_arbeit_dir("vertonung") / f"{e.folge_id}.{e.sprache}.m4a"
        try:
            texte: Texte = await dienst.texte(auftrag)
            if texte.uebersetzung is None or not texte.uebersetzung.segmente:
                raise AuftragFehler("Die Vertonung ist fertig, liefert aber keinen Text")
            await dienst.ton(str((stand.ergebnis or {})["plan_id"]), ton)
            a = ablage()
            if texte.transkript is not None and texte.transkript.segmente and await a.begleiter_lesen(pfad, ROLLE_TRANSKRIPT) is None:
                await a.begleiten(pfad, ROLLE_TRANSKRIPT, ".transkript.json", transkript_json(name, texte.transkript, "Vertonung"),
                                  "application/json")
            await a.begleiten(pfad, rolle_text(e.sprache), f".{e.sprache}.transkript.json",
                              transkript_json(name, texte.uebersetzung, "Vertonung"), "application/json")
            abgelegt = await a.begleiten(pfad, rolle_ton(e.sprache), f".{e.sprache}.sprache.m4a", ton, "audio/mp4")
        except (AblageFehler, VerbundFehler, KeyError) as f:
            raise AuftragFehler(f"Fassung nicht abgelegt: {f}") from f
        finally:
            ton.unlink(missing_ok=True)
        merken(e.folge_id, Fassung(sprache=e.sprache, pfad=abgelegt.pfad, stimme=wahl))
        self.transkripte.vergessen(e.folge_id)
        try:
            await dienst.abgeholt(auftrag)
        except VerbundFehler:            # sie räumt nach ihrer Frist selbst auf
            pass
        return Ergebnis(pfad=abgelegt.pfad, absaetze=len(texte.uebersetzung.segmente))

    def art(self) -> Art:
        return Art(name=ART, titel="Folge vertonen", arbeit=self._vertonen, eingabe=Eingabe, fortsetzbar=True,
                   nach_neustart="fortsetzen", hoechstens=1, gegenstand=lambda e: f"fassung:{e.get('folge_id')}:{e.get('sprache')}",
                   phasen=[Phase(schluessel="speichern", titel="Folge speichern", symbol="cloud-arrow-up"),
                           Phase(schluessel="hoeren", titel="Transkribieren", symbol="closed-captioning"),
                           Phase(schluessel="vertonen", titel="Übersetzen und sprechen", symbol="language"),
                           Phase(schluessel="ablegen", titel="Ablegen", symbol="cloud-arrow-up")])


def _spurtext(s: Segment) -> Spurtext:
    return Spurtext(start=s.start, ende=max(s.ende, s.start), text=s.text, sprecher=s.sprecher or None)


folgenvertonung = Folgenvertonung(folgentranskripte)
