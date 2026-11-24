"""Ablauf des Feinschnitts einer Aufnahme (RAD-45): Analyse festhalten, Stücke planen, als Schritt des Schnitts ausführen,
später aus der gespeicherten Analyse neu rechnen.

Die Analyse (Wechsel der Sendedaten, Stillen, Pegel, Werbestellen) entsteht beim Aufnehmen und liegt als Analyse.json
neben den Stücken in der Ablage. So lässt sich der Feinschnitt nach einer Verbesserung der Regeln erneut rechnen, ohne
neu aufzunehmen: der vorige Feinschnitt wird zurückgenommen (Rückgängig des Schnitts), der neue angewendet. Die
Rechnung selbst steht in feinschnitt.py.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel

from ..ablage import ablage, orte
from ..database import db_session
from . import feinschnitt
from .aufnahmen import aufnahmen

logger = logging.getLogger("radiohub.feinschnitt")

#: so beginnt der Name des Schritts (zum Wiedererkennen beim Neurechnen)
SCHRITT = "Feinschnitt"


class Analyse(BaseModel):
    fassung: int = 1
    #: Beginn dieses Abschnitts in der Aufnahme (lange Aufnahmen werden in Abschnitten geschnitten, RAD-139)
    ab: float = 0.0
    dauer: float
    #: (Sekunde, Titel, gesperrt), auch Wechsel zu einem leeren Titel
    wechsel: list[tuple[float, str, bool]] = []
    stillen: list[tuple[float, float]] = []
    #: (Sekunde, Momentanlautheit LUFS) etwa alle 100 ms
    pegel: list[tuple[float, float]] = []
    #: (von, bis, wer)
    werbung: list[tuple[float, float, str]] = []


def planen(a: Analyse, stuecke_bisher: int = 0) -> Optional[list[feinschnitt.Stueck]]:
    """Die Stücke nach dem Feinschnitt; None, wenn es nichts zu verbessern gibt (ein Stück bleibt ein Stück). Mit
    `stuecke_bisher` > 1 gilt auch ein Plan mit einem Stück: dann fallen Splitter des groben Schnitts weg."""
    if a.dauer <= 0 or not (a.wechsel or a.werbung):
        return None
    stuecke = feinschnitt.stuecke(a.dauer, [feinschnitt.Angabe(t, x, g) for t, x, g in a.wechsel], a.stillen,
                                  [feinschnitt.Werbung(v, b, w) for v, b, w in a.werbung], pegel=a.pegel)
    return stuecke if len(stuecke) > 1 or a.werbung or stuecke_bisher > 1 else None


#: so weit um einen Wechsel braucht die Rechnung den Pegel; was dazwischen liegt, wird nicht abgelegt
PEGEL_RAND_S = 20.0


def schlank(a: Analyse) -> Analyse:
    """Nur der Pegel um die Wechsel und Werbestellen (je Stunde sonst 36000 Werte)."""
    stellen = sorted([t for t, _, _ in a.wechsel] + [x for v, b, _ in a.werbung for x in (v, b)])
    behalten, i = [], 0
    for t, wert in a.pegel:
        while i < len(stellen) and stellen[i] + PEGEL_RAND_S < t:
            i += 1
        if i < len(stellen) and stellen[i] - PEGEL_RAND_S <= t:
            behalten.append((t, wert))
    return a.model_copy(update={"pegel": behalten})


def zusammen(teile: list[Analyse]) -> Analyse:
    """Die Abschnitte einer Aufnahme als eine Analyse, auf die Zeit der Aufnahme."""
    alle = sorted(teile, key=lambda x: x.ab)
    r = lambda t, x: round(t + x.ab, 3)                                              # noqa: E731
    wechsel = [(r(t, x), titel, g) for x in alle for t, titel, g in x.wechsel]
    return Analyse(dauer=max(x.ab + x.dauer for x in alle),
                   wechsel=[w for i, w in enumerate(wechsel) if i == 0 or w[1] != wechsel[i - 1][1]],
                   stillen=[(r(v, x), r(b, x)) for x in alle for v, b in x.stillen], pegel=[(r(t, x), m) for x in alle for t, m in x.pegel],
                   werbung=[(r(v, x), r(b, x), w) for x in alle for v, b, w in x.werbung])


async def analyse_ablegen(session_id: str, a: Analyse, abschnitt: int = 0) -> Optional[str]:
    sitzung = aufnahmen.sitzung(session_id)
    if not sitzung:
        return None
    pfad = orte.analyse(sitzung["file_path"], abschnitt)
    await ablage().schreiben(pfad, a.model_dump_json().encode())
    return pfad


async def analyse_lesen(session_id: str) -> Optional[Analyse]:
    sitzung = aufnahmen.sitzung(session_id)
    if not sitzung:
        return None
    try:
        teile = [e for e in await ablage().liste(sitzung["file_path"]) if orte.ist_analyse(e.name)]
        gelesen = [Analyse.model_validate_json(await ablage().lesen_ganz(e.pfad)) for e in teile]
        return zusammen(gelesen) if gelesen else None
    except Exception:
        return None


def status_setzen(session_id: str, status: str, nur_wenn: Optional[str] = None) -> None:
    with db_session() as conn:
        if nur_wenn:
            conn.execute("UPDATE sessions SET status = ? WHERE id = ? AND status = ?", (status, session_id, nur_wenn))
        else:
            conn.execute("UPDATE sessions SET status = ? WHERE id = ?", (status, session_id))


#: Stand eines laufenden Feinschnitts je Aufnahme: (fertige, alle Stücke)
FORTSCHRITT: dict[str, tuple[int, int]] = {}


async def ausfuehren(session_id: str, stuecke: list[feinschnitt.Stueck]) -> int:
    """Als Schritt des Schnitts anwenden (ein voriger Feinschnitt als letzter Schritt wird erst zurückgenommen).
    Solange heißt die Aufnahme "feinschnitt" (die Oberfläche sperrt die Wiedergabe). Liefert die Zahl der Stücke."""
    from .schnitt import StueckWahl, gegenstand, schritte

    status_setzen(session_id, "feinschnitt")
    g = gegenstand("sitzung", session_id)
    try:
        bisher = schritte(g.schluessel)
        if bisher and bisher[-1]["was"].startswith(SCHRITT):
            await g.rueckgaengig()
        wahl = [StueckWahl(von=s.von, bis=s.bis, name=s.name) for s in stuecke]
        anzahl = await g.schneiden(wahl, lambda fertig, alle, _was: FORTSCHRITT.__setitem__(session_id, (fertig, alle)),
                                   was=f"{SCHRITT}: {len(wahl)} Stücke an den Pausen, Werbung für sich")
        logger.info(f"Feinschnitt {session_id}: {anzahl} Stücke")
        return anzahl
    finally:
        FORTSCHRITT.pop(session_id, None)
        status_setzen(session_id, "completed", nur_wenn="feinschnitt")


async def neu(session_id: str) -> int:
    """Aus der gespeicherten Analyse neu rechnen und anwenden."""
    a = await analyse_lesen(session_id)
    if a is None:
        raise LookupError("Zu dieser Aufnahme gibt es keine Analyse")
    stuecke = planen(a, len(aufnahmen.segmente(session_id)))
    if not stuecke:
        return 0
    return await ausfuehren(session_id, stuecke)


def zusammenfassung(stuecke: list[feinschnitt.Stueck]) -> str:
    return json.dumps([(round(s.von, 2), round(s.bis, 2), s.art, s.name) for s in stuecke], ensure_ascii=False)
