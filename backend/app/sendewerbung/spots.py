"""Bekannte Spots und der Schalter je Sender (RAD-33).

Jede abgeschlossene Werbestelle aus den Sendedaten zählt ihren Spot (je Sender, Format und Kennung eine Zeile, mit
Anzahl und wann zuerst und zuletzt). Ein Sender mit mindestens einem Spot gilt als werbend; schon ein Fund reicht.
Ob angekündigte Werbung übersprungen wird, sagt die Einstellung für alle Sender (`werbung_ueberspringen`) und, wo
eine Zeile in `sender_werbung` steht, die Ausnahme des Senders."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .. import einstellungen
from ..database import db_session
from .sitzung import Werbestelle


class Spot(BaseModel):
    format: str
    kennung: str
    werbender: str
    titel: str
    dauer_ms: Optional[int]
    beim_verbinden: bool
    anzahl: int
    zuerst: str
    zuletzt: str


class SenderWerbung(BaseModel):
    uuid: str
    name: str = ""
    spots: int
    zuletzt: Optional[str] = None
    #: gilt für diesen Sender (Einstellung für alle und Ausnahme des Senders zusammen)
    ueberspringen: bool
    #: der Sender ist ausgenommen (eigene Zeile mit aus)
    ausgenommen: bool = False


class Steckbrief(SenderWerbung):
    liste: list[Spot]


def merken(uuid: str, s: Werbestelle) -> None:
    """Eine abgeschlossene Werbestelle zählt ihren Spot; die Länge ist die angekündigte, sonst die gemessene."""
    if not uuid:
        return
    dauer = s.angekuendigt_ms or (int(round((s.bis - s.von) * 1000)) if s.bis is not None else None)
    with db_session() as conn:
        conn.execute(
            "INSERT INTO werbespots (sender_uuid, format, kennung, werbender, titel, dauer_ms, beim_verbinden) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(sender_uuid, format, kennung) DO UPDATE SET "
            "anzahl = anzahl + 1, zuletzt = CURRENT_TIMESTAMP, werbender = excluded.werbender, titel = excluded.titel, "
            "dauer_ms = COALESCE(excluded.dauer_ms, dauer_ms), beim_verbinden = MAX(beim_verbinden, excluded.beim_verbinden)",
            (uuid, s.format, s.kennung, s.werbender, s.titel, dauer, int(s.beim_verbinden)))


def _alle_an() -> bool:
    return einstellungen.stand().werbung_ueberspringen


def ueberspringt(uuid: str) -> bool:
    """Gilt das Überspringen für diesen Sender?"""
    if not _alle_an():
        return False
    with db_session() as conn:
        zeile = conn.execute("SELECT ueberspringen FROM sender_werbung WHERE uuid = ?", (uuid,)).fetchone()
    return True if zeile is None else bool(zeile[0])


def setzen(uuid: str, ueberspringen: bool) -> None:
    """Ausnahme je Sender: aus nimmt ihn aus; an löscht die Ausnahme (dann gilt die Einstellung für alle)."""
    with db_session() as conn:
        if ueberspringen:
            conn.execute("DELETE FROM sender_werbung WHERE uuid = ?", (uuid,))
        else:
            conn.execute("INSERT INTO sender_werbung (uuid, ueberspringen) VALUES (?, 0) "
                         "ON CONFLICT(uuid) DO UPDATE SET ueberspringen = 0", (uuid,))


SENDER_SQL = """
SELECT w.sender_uuid, COALESCE(MAX(st.name), MAX(f.name), '') AS name, COUNT(*) AS spots, MAX(w.zuletzt) AS zuletzt,
       MAX(CASE WHEN sw.ueberspringen = 0 THEN 1 ELSE 0 END) AS ausgenommen
FROM werbespots w
LEFT JOIN stations st ON st.uuid = w.sender_uuid
LEFT JOIN favorites f ON f.uuid = w.sender_uuid
LEFT JOIN sender_werbung sw ON sw.uuid = w.sender_uuid
"""


def _sender(z, alle_an: bool) -> SenderWerbung:
    return SenderWerbung(uuid=z[0], name=(z[1] or "").strip(), spots=z[2], zuletzt=z[3], ausgenommen=bool(z[4]),
                         ueberspringen=alle_an and not z[4])


def werbende() -> list[SenderWerbung]:
    """Alle Sender mit bekannten Spots, zuletzt gehörte zuerst."""
    alle_an = _alle_an()
    with db_session() as conn:
        return [_sender(z, alle_an) for z in conn.execute(SENDER_SQL + " GROUP BY w.sender_uuid ORDER BY zuletzt DESC")]


def steckbrief(uuid: str) -> Steckbrief:
    alle_an = _alle_an()
    with db_session() as conn:
        z = conn.execute(SENDER_SQL + " WHERE w.sender_uuid = ? GROUP BY w.sender_uuid", (uuid,)).fetchone()
        liste = [Spot(format=r[0], kennung=r[1], werbender=r[2], titel=r[3], dauer_ms=r[4], beim_verbinden=bool(r[5]),
                      anzahl=r[6], zuerst=r[7], zuletzt=r[8])
                 for r in conn.execute("SELECT format, kennung, werbender, titel, dauer_ms, beim_verbinden, anzahl, zuerst, "
                                       "zuletzt FROM werbespots WHERE sender_uuid = ? ORDER BY zuletzt DESC", (uuid,))]
        ausnahme = conn.execute("SELECT ueberspringen FROM sender_werbung WHERE uuid = ?", (uuid,)).fetchone()
    ausgenommen = bool(ausnahme is not None and not ausnahme[0])
    if z is None:
        return Steckbrief(uuid=uuid, spots=0, ueberspringen=alle_an and not ausgenommen, ausgenommen=ausgenommen, liste=[])
    return Steckbrief(**_sender(z, alle_an).model_dump(), liste=liste)
