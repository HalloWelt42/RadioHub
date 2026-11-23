"""Wie lange ein Sender je Tag lief (HELF-256). Nur dafür da, dass der Lernlauf nachts das hört, was man selbst hört."""

from __future__ import annotations

from ..database import db_session

#: so lange bleibt der Verlauf
TAGE = 60


def merken(uuid: str, sekunden: int) -> None:
    if not uuid or sekunden <= 0:
        return
    with db_session() as conn:
        conn.execute("INSERT INTO hoerverlauf (uuid, tag, sekunden) VALUES (?, date('now', 'localtime'), ?) "
                     "ON CONFLICT(uuid, tag) DO UPDATE SET sekunden = sekunden + excluded.sekunden", (uuid, int(sekunden)))
        conn.execute("DELETE FROM hoerverlauf WHERE tag < date('now', 'localtime', ?)", (f"-{TAGE} days",))


def stunden(tage: int = 30) -> dict[str, float]:
    """Gehörte Stunden je Sender in den letzten Tagen, das jüngste Drittel zählt doppelt."""
    with db_session() as conn:
        zeilen = conn.execute("SELECT uuid, SUM(sekunden * CASE WHEN tag >= date('now', 'localtime', ?) THEN 2 ELSE 1 END) AS s "
                              "FROM hoerverlauf WHERE tag >= date('now', 'localtime', ?) GROUP BY uuid",
                              (f"-{tage // 3} days", f"-{tage} days")).fetchall()
    return {z["uuid"]: z["s"] / 3600 for z in zeilen}
