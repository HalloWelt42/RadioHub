"""Weitere Titel an eine Aufnahme anhängen (RAD-145): aufgenommen wird wie immer als eigene Aufnahme mit `ziel_id`; ist sie fertig und
fein geschnitten, kommen ihre Stücke hinten an das Ziel. So bleibt die vorhandene Aufnahme unberührt, bis die neue vollständig ist.

Die Stücke ziehen in den Ordner des Ziels um; der Rest der neuen (grobe Stücke, Analyse, Titelliste) liegt danach darunter in
`Angehängt/<Zeit>`, ihr Eintrag heißt "angehaengt" und steht in keiner Liste. Zeiten, Werbestellen, Titelliste und Analyse gelten auf der
Zeitachse des Ziels weiter. Das Anhängen ist ein Schritt: zurückgenommen wird wieder eine eigene Aufnahme daraus, mit ihren eigenen
Schritten. Bricht es mittendrin ab, zeigt jede Zeile auf eine Datei, die es gibt, und ein neuer Lauf macht weiter.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import PurePosixPath
from typing import Any

from ..ablage import AblageFehler, ablage, orte
from ..database import db_session
from . import feinschnitt_lauf
from .aufnahmen import AufnahmeFehler, aufnahmen
from .schnitt import SitzungGegenstand, schritt_fortschreiben, schritt_zum_anhaengen

logger = logging.getLogger("radiohub.anhaengen")

ANGEHAENGT = "angehaengt"
_sperre = asyncio.Lock()


def ziel_pruefen(ziel_id: str | None, station_uuid: str) -> dict | None:
    """Das Ziel einer neuen Aufnahme; AufnahmeFehler, wenn nichts angehängt werden kann."""
    if not ziel_id:
        return None
    ziel = aufnahmen.sitzung(ziel_id)
    if not ziel or ziel["status"] == ANGEHAENGT:
        raise AufnahmeFehler("Die Aufnahme, an die angehängt werden soll, gibt es nicht mehr", 404)
    if ziel["station_uuid"] != station_uuid:
        raise AufnahmeFehler("Die Aufnahme ist von einem anderen Sender", 409)
    if aufnahmen.laeuft(ziel_id):
        raise AufnahmeFehler("Die Aufnahme, an die angehängt werden soll, wird gerade geschnitten", 409)
    return ziel


async def anhaengen(quelle_id: str, status: str = "") -> int:
    """Die fertige Aufnahme an ihr Ziel hängen; liefert die Zahl der Stücke. Geht es nicht, bleibt sie eine eigene. `status`: der, den
    sie nach dem Feinschnitt hätte (bis zum Anhängen gilt sie noch als in Arbeit)."""
    async with _sperre:
        quelle = aufnahmen.sitzung(quelle_id)
        ziel = aufnahmen.sitzung(quelle["ziel_id"]) if quelle and quelle.get("ziel_id") else None
        if not quelle or quelle["status"] == ANGEHAENGT or (not status and aufnahmen.laeuft(quelle_id)):
            return 0
        quelle["status"] = status or quelle["status"]
        if ziel is None or ziel["status"] == ANGEHAENGT or aufnahmen.laeuft(ziel["id"]):
            raise AufnahmeFehler("Die Aufnahme, an die angehängt werden soll, ist gerade nicht frei", 409)
        stuecke, vorhandene = aufnahmen.segmente(quelle_id), aufnahmen.segmente(ziel["id"])
        if vorhandene and stuecke and PurePosixPath(vorhandene[-1]["file_path"]).suffix.lower() != PurePosixPath(stuecke[0]["file_path"]).suffix.lower():
            raise AufnahmeFehler("Der Sender sendet jetzt in einem anderen Format: die neuen Titel bleiben eine eigene Aufnahme", 409)
        feinschnitt_lauf.status_setzen(ziel["id"], "feinschnitt")
        try:
            return await _umziehen(quelle, ziel, stuecke, vorhandene)
        finally:
            feinschnitt_lauf.status_setzen(ziel["id"], ziel["status"], nur_wenn="feinschnitt")


async def _umziehen(quelle: dict, ziel: dict, stuecke: list[dict], vorhandene: list[dict]) -> int:
    schluessel = SitzungGegenstand(ziel["id"]).schluessel
    schritt, daten = schritt_zum_anhaengen(schluessel, quelle["id"])
    if schritt is None:
        ab = max((z["end_ms"] or 0 for z in vorhandene), default=0)
        daten = {"angehaengt": quelle["id"], "zeiten_bleiben": True, "ab_ms": ab, "zeilen": [], "werbung": [], "analysen": [],
                 "quelle": {f: quelle[f] for f in ("file_path", "status", "duration", "file_size")}, "ziel_ende": ziel["end_time"]}
    ab = daten["ab_ms"]
    anzahl = len(daten["zeilen"]) + len(stuecke)
    beschriftung = f"Angehängt: {anzahl} {'Stück' if anzahl == 1 else 'Stücke'} vom {quelle['start_time'][8:10]}.{quelle['start_time'][5:7]}."
    schritt = schritt_fortschreiben(schluessel, schritt, beschriftung, daten)
    for z in stuecke:
        index = len(aufnahmen.segmente(ziel["id"]))
        neu = await ablage().freier_pfad(orte.stueck(ziel["file_path"], index, z["title"], PurePosixPath(z["file_path"]).suffix))
        await ablage().verschieben(z["file_path"], neu)
        with db_session() as conn:
            conn.execute("UPDATE segments SET session_id = ?, segment_index = ?, start_ms = ?, end_ms = ?, file_path = ? WHERE id = ?",
                         (ziel["id"], index, (z["start_ms"] or 0) + ab, (z["end_ms"] or 0) + ab, neu, z["id"]))
        daten["zeilen"].append({"neu": neu, "alt": z["file_path"], "index": z["segment_index"], "start_ms": z["start_ms"], "end_ms": z["end_ms"]})
        schritt_fortschreiben(schluessel, schritt, beschriftung, daten)
    liste = await aufnahmen.titelliste(ziel)
    daten.setdefault("ziel_bytes", liste.get("total_audio_bytes", 0) if isinstance(liste, dict) else 0)
    daten["werbung"] += _werbung_umziehen(quelle["id"], ziel["id"], ab / 1000)
    daten["analysen"] += await _analyse_uebernehmen(quelle, ziel, ab / 1000)
    await _titelliste_uebernehmen(quelle, ziel, ab)
    ordner = await ablage().freier_pfad(f"{ziel['file_path']}/Angehängt/{orte.zeitpunkt(quelle['start_time'])}")
    if await ablage().eintrag(quelle["file_path"]) is not None:
        await ablage().verschieben(quelle["file_path"], ordner)
        aufnahmen.pfade_umziehen(quelle["id"], quelle["file_path"], ordner)
    with db_session() as conn:
        conn.execute("UPDATE sessions SET status = ?, folder_id = ? WHERE id = ?", (ANGEHAENGT, ziel["folder_id"], quelle["id"]))
        conn.execute("UPDATE sessions SET end_time = ? WHERE id = ?", (quelle["end_time"], ziel["id"]))
    _groesse_und_dauer(ziel["id"])
    schritt_fortschreiben(schluessel, schritt, beschriftung, daten)
    await aufnahmen._veraendert(ziel)
    logger.info(f"{len(daten['zeilen'])} Stücke von {quelle['id']} an {ziel['id']} angehängt")
    return len(daten["zeilen"])


async def abtrennen(ziel_id: str, daten: dict[str, Any]) -> None:
    """Das Anhängen zurücknehmen: die Stücke werden wieder eine eigene Aufnahme."""
    quelle, ziel = aufnahmen.sitzung(daten["angehaengt"]), aufnahmen.sitzung(ziel_id)
    if not quelle or not ziel:
        raise AufnahmeFehler("Die angehängte Aufnahme gibt es nicht mehr", 404)
    heim = await ablage().freier_pfad(daten["quelle"]["file_path"])
    if await ablage().eintrag(quelle["file_path"]) is not None and quelle["file_path"] != heim:
        await ablage().verschieben(quelle["file_path"], heim)
    aufnahmen.pfade_umziehen(quelle["id"], quelle["file_path"], heim)
    da = {z["file_path"]: z for z in aufnahmen.segmente(ziel_id)}
    for z in daten["zeilen"]:
        zeile = da.get(z["neu"])
        if zeile is None:                                  # inzwischen gelöscht
            continue
        pfad = await ablage().freier_pfad(f"{heim}/{PurePosixPath(z['alt']).name}")
        await ablage().verschieben(z["neu"], pfad)
        with db_session() as conn:
            conn.execute("UPDATE segments SET session_id = ?, segment_index = ?, start_ms = ?, end_ms = ?, file_path = ? WHERE id = ?",
                         (quelle["id"], z["index"], z["start_ms"], z["end_ms"], pfad, zeile["id"]))
    ab = daten["ab_ms"]
    with db_session() as conn:
        for i in daten["werbung"]:
            conn.execute("UPDATE werbestellen SET aufnahme_id = ?, von = von - ?, bis = bis - ? WHERE id = ?", (quelle["id"], ab / 1000, ab / 1000, i))
        conn.execute("UPDATE sessions SET status = ?, ziel_id = NULL WHERE id = ?", (daten["quelle"]["status"], quelle["id"]))
        conn.execute("UPDATE sessions SET end_time = ? WHERE id = ?", (daten["ziel_ende"], ziel_id))
    for pfad in daten["analysen"]:
        await ablage().loeschen(pfad)
    liste = await aufnahmen.titelliste(ziel)
    if isinstance(liste, dict):
        eigene = [e for e in liste.get("entries", []) if e.get("t", 0) < ab]
        await aufnahmen.titelliste_schreiben(ziel, {**liste, "entries": eigene, "total_audio_bytes": daten["ziel_bytes"]})
    aufnahmen._neu_nummerieren(ziel_id)
    for sid in (ziel_id, quelle["id"]):
        _groesse_und_dauer(sid)
    await aufnahmen._veraendert(ziel)


def _groesse_und_dauer(session_id: str) -> None:
    with db_session() as conn:
        conn.execute("""UPDATE sessions SET (file_size, duration) = (SELECT COALESCE(SUM(file_size), 0), COALESCE(SUM(duration_ms), 0) / 1000.0
                        FROM segments WHERE session_id = ?) WHERE id = ?""", (session_id, session_id))


def _werbung_umziehen(quelle_id: str, ziel_id: str, ab_s: float) -> list[int]:
    with db_session() as conn:
        ids = [r[0] for r in conn.execute("SELECT id FROM werbestellen WHERE aufnahme_id = ?", (quelle_id,))]
        conn.execute("UPDATE werbestellen SET aufnahme_id = ?, von = von + ?, bis = bis + ? WHERE aufnahme_id = ?", (ziel_id, ab_s, ab_s, quelle_id))
    return ids


async def _analyse_uebernehmen(quelle: dict, ziel: dict, ab_s: float) -> list[str]:
    """Die Messwerte der neuen neben die des Ziels, auf seiner Zeitachse (Neurechnen des Feinschnitts gilt fürs Ganze)."""
    a = await feinschnitt_lauf.analyse_lesen(quelle["id"])
    if a is None:
        return []
    nummer = 1
    while await ablage().eintrag(orte.analyse(ziel["file_path"], nummer)) is not None:
        nummer += 1
    pfad = await feinschnitt_lauf.analyse_ablegen(ziel["id"], a.model_copy(update={"ab": a.ab + ab_s}), nummer)
    return [pfad] if pfad else []


async def _titelliste_uebernehmen(quelle: dict, ziel: dict, ab_ms: int) -> None:
    neu, alt = await aufnahmen.titelliste(quelle), await aufnahmen.titelliste(ziel)
    if not isinstance(neu, dict) or not isinstance(alt, dict | None):
        return
    alt = alt or {"entries": [], "total_audio_bytes": 0}
    b = alt.get("total_audio_bytes", 0)
    eintraege = [{**e, "t": e.get("t", 0) + ab_ms, "b": e.get("b", 0) + b} for e in neu.get("entries", [])]
    await aufnahmen.titelliste_schreiben(ziel, {**alt, "entries": [*alt.get("entries", []), *eintraege], "total_audio_bytes": b + neu.get("total_audio_bytes", 0)})


async def nachholen() -> int:
    """Beim Start: fertige Aufnahmen, die noch an ihr Ziel gehören (ein Neustart kam dazwischen)."""
    with db_session() as conn:
        offen = [r[0] for r in conn.execute("SELECT id FROM sessions WHERE ziel_id IS NOT NULL AND status NOT IN (?, 'recording', 'feinschnitt')", (ANGEHAENGT,))]
    zahl = 0
    for kennung in offen:
        if not aufnahmen.segmente(kennung):
            continue
        try:
            zahl += bool(await anhaengen(kennung))
        except (AufnahmeFehler, AblageFehler) as f:
            logger.warning(f"{kennung} bleibt eine eigene Aufnahme: {f}")
    return zahl
