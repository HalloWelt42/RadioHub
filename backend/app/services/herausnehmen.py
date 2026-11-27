"""Stücke aus einer fertigen Aufnahme herausnehmen, als hätte es sie nie gegeben (RAD-150: beim Aufnehmen abgewählte Titel).

Fällt ein Stück weg, rückt alles danach um seine Länge nach vorn: die übrigen Stücke, die Werbestellen, die Titelliste
und die Messwerte des Feinschnitts (sonst säße ein späteres Neurechnen oder eine Werbemarke neben dem Ton). Was im
herausgenommenen Bereich lag, fällt mit weg. Ein Schritt zum Rückgängigmachen entsteht nicht: Abwählen geht nur,
solange die Aufnahme läuft, und dort lässt es sich zurücknehmen.
"""

from __future__ import annotations

import bisect
import logging
from dataclasses import dataclass, field

from ..ablage import ablage, orte
from ..database import db_session
from .aufnahmen import aufnahmen
from .feinschnitt_lauf import Analyse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Zeitachse:
    """Bereiche (von, bis) in Millisekunden der alten Achse, die wegfallen; rechnet Zeiten auf die neue Achse um."""

    bereiche: list[tuple[int, int]]
    _anfaenge: list[int] = field(init=False, repr=False)
    _davor: list[int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        zusammen: list[tuple[int, int]] = []
        for von, bis in sorted(b for b in self.bereiche if b[1] > b[0]):
            if zusammen and von <= zusammen[-1][1]:
                zusammen[-1] = (zusammen[-1][0], max(bis, zusammen[-1][1]))
            else:
                zusammen.append((von, bis))
        object.__setattr__(self, "bereiche", zusammen)
        object.__setattr__(self, "_anfaenge", [von for von, _ in zusammen])
        summe, davor = 0, []
        for von, bis in zusammen:
            davor.append(summe)
            summe += bis - von
        object.__setattr__(self, "_davor", davor)

    def weg(self, t: float) -> bool:
        """Liegt die Stelle in einem Bereich, der wegfällt?"""
        i = bisect.bisect_right(self._anfaenge, t) - 1
        return i >= 0 and t < self.bereiche[i][1]

    def neu(self, t: float) -> float:
        """Die Stelle auf der neuen Achse; eine Stelle in einem wegfallenden Bereich landet an seinem Anfang."""
        i = bisect.bisect_right(self._anfaenge, t) - 1
        if i < 0:
            return t
        von, bis = self.bereiche[i]
        return von - self._davor[i] if t < bis else t - self._davor[i] - (bis - von)

    def neu_s(self, t: float) -> float:
        """Wie `neu`, für Sekunden."""
        return round(self.neu(t * 1000) / 1000, 3)

    def weg_s(self, t: float) -> bool:
        return self.weg(t * 1000)


async def stuecke_herausnehmen(session_id: str, segmente: list[dict]) -> int:
    """Die Stücke in den Papierkorb und alles danach nach vorn; liefert die Zahl der herausgenommenen."""
    sitzung = aufnahmen.sitzung(session_id)
    if not sitzung or not segmente:
        return 0
    achse = Zeitachse([(z["start_ms"] or 0, z["end_ms"] or 0) for z in segmente])
    for z in segmente:
        try:
            await ablage().loeschen(z["file_path"])
        except Exception as f:  # noqa: BLE001 - die Zeile geht trotzdem, sonst stünde der Titel noch da
            logger.warning(f"Herausgenommenes Stück {z['file_path']} nicht entfernt: {f}")
    with db_session() as conn:
        conn.executemany("DELETE FROM segments WHERE id = ?", [(z["id"],) for z in segmente])
    _stuecke_ruecken(session_id, achse)
    _werbung_ruecken(session_id, achse)
    await _titelliste_ruecken(sitzung, achse, sum(z["file_size"] or 0 for z in segmente), segmente)
    await _analysen_ruecken(sitzung, achse)
    with db_session() as conn:
        conn.execute("""UPDATE sessions SET (file_size, duration) = (SELECT COALESCE(SUM(file_size), 0), COALESCE(SUM(duration_ms), 0) / 1000.0
                        FROM segments WHERE session_id = ?) WHERE id = ?""", (session_id, session_id))
    return len(segmente)


def _stuecke_ruecken(session_id: str, achse: Zeitachse) -> None:
    with db_session() as conn:
        for index, z in enumerate(aufnahmen.segmente(session_id)):
            conn.execute("UPDATE segments SET segment_index = ?, start_ms = ?, end_ms = ? WHERE id = ?",
                         (index, int(achse.neu(z["start_ms"] or 0)), int(achse.neu(z["end_ms"] or 0)), z["id"]))


def _werbung_ruecken(session_id: str, achse: Zeitachse) -> None:
    with db_session() as conn:
        for wid, von, bis in conn.execute("SELECT id, von, bis FROM werbestellen WHERE aufnahme_id = ?", (session_id,)).fetchall():
            if achse.weg_s(von) and (bis is None or achse.weg_s(bis) or achse.neu_s(bis) == achse.neu_s(von)):
                conn.execute("DELETE FROM werbestellen WHERE id = ?", (wid,))
            else:
                conn.execute("UPDATE werbestellen SET von = ?, bis = ? WHERE id = ?",
                             (achse.neu_s(von), None if bis is None else achse.neu_s(bis), wid))


async def _titelliste_ruecken(sitzung: dict, achse: Zeitachse, bytes_weg: int, segmente: list[dict]) -> None:
    liste = await aufnahmen.titelliste(sitzung)
    if not isinstance(liste, dict):
        return
    vorher = sorted(((z["end_ms"] or 0), z["file_size"] or 0) for z in segmente)

    def bytes_davor(t: float) -> int:
        return sum(groesse for ende, groesse in vorher if ende <= t)

    eintraege = [{**e, "t": int(achse.neu(e.get("t", 0))), "b": max(0, e.get("b", 0) - bytes_davor(e.get("t", 0)))}
                 for e in liste.get("entries", []) if not achse.weg(e.get("t", 0))]
    await aufnahmen.titelliste_schreiben(sitzung, {**liste, "entries": eintraege,
                                                   "total_audio_bytes": max(0, liste.get("total_audio_bytes", 0) - bytes_weg)})


def analyse_ruecken(a: Analyse, achse: Zeitachse) -> Analyse:
    """Die Messwerte eines Abschnitts auf die neue Achse (ihre Zeiten zählen ab `a.ab`)."""
    ab = achse.neu_s(a.ab)
    alt = lambda t: a.ab + t                                                        # noqa: E731
    neu = lambda t: round(achse.neu_s(alt(t)) - ab, 3)                              # noqa: E731
    return a.model_copy(update={
        "ab": ab, "dauer": neu(a.dauer),
        "wechsel": [(neu(t), x, g) for t, x, g in a.wechsel if not achse.weg_s(alt(t))],
        "stillen": [(neu(v), neu(b)) for v, b in a.stillen if neu(b) > neu(v)],
        "pegel": [(neu(t), m) for t, m in a.pegel if not achse.weg_s(alt(t))],
        "werbung": [(neu(v), neu(b), w) for v, b, w in a.werbung if neu(b) > neu(v)],
    })


async def _analysen_ruecken(sitzung: dict, achse: Zeitachse) -> None:
    try:
        teile = [e for e in await ablage().liste(sitzung["file_path"]) if orte.ist_analyse(e.name)]
    except Exception:  # noqa: BLE001 - ohne Analyse gibt es nichts zu rücken
        return
    for e in teile:
        try:
            a = Analyse.model_validate_json(await ablage().lesen_ganz(e.pfad))
        except Exception as f:  # noqa: BLE001
            logger.warning(f"Analyse {e.pfad} nicht lesbar, bleibt: {f}")
            continue
        await ablage().schreiben(e.pfad, analyse_ruecken(a, achse).model_dump_json().encode())
