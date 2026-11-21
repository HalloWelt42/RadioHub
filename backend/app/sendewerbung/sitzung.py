"""Werbestellen einer laufenden Sitzung (RAD-33): aus den Angaben des Stromlesers (roh, Stelle im Ton) werden Stellen
mit von und bis in Sekunden des Tons, also auf der Zeitachse des Zeitversatzes. Die genaue Grenze kommt aus der
Stille, die ffmpeg mitmeldet; ohne Stille bleibt die Grenze der Angabe.

- Eine Werbeangabe beginnt eine Stelle. Kam vorher noch keine Angabe, begann der Spot mit der Verbindung (Stelle ab 0):
  der Sender schickt die erste Angabe erst nach dem ersten Block Ton.
- Ende "dauer": die Stelle endet nach der angekündigten Länge. Ende "wechsel": sie endet mit der ersten Angabe, die
  nicht mehr zu ihr gehört (andere Kennung oder keine Werbung); bis dahin ist sie offen.
- Stille (von, bis): liegt eine Grenze höchstens `fenster_s` neben einer Stille, gehört die Stille zur Stelle (der
  Anfang rückt an den Beginn der Stille davor, das Ende an das Ende der Stille danach).

Ohne Ein- und Ausgabe; ffmpeg und der Stromleser rufen nur `angabe` und `stille`."""

from __future__ import annotations

import re
from typing import Callable, Literal, Optional

from pydantic import BaseModel

from .angaben import Regeln, Werbeangabe, lesen, regeln

Herkunft = Literal["angabe", "stille", "verbinden", "dauer"]

#: so viele Stillen bleiben gemerkt (eine Stelle braucht nur die in ihrer Nähe)
STILLEN_HOECHSTENS = 400

STILLE_BEGINN = re.compile(r"silence_start:\s*(-?[\d.]+)")
STILLE_ENDE = re.compile(r"silence_end:\s*(-?[\d.]+)")


class Werbestelle(BaseModel):
    von: float
    bis: Optional[float] = None          # None: läuft noch (Ende kommt mit dem nächsten Wechsel)
    von_aus: Herkunft
    bis_aus: Optional[Herkunft] = None
    format: str
    kennung: str
    werbender: str = ""
    titel: str = ""
    angekuendigt_ms: Optional[int] = None
    beim_verbinden: bool = False


class Sitzungswerbung:
    def __init__(self, r: Optional[Regeln] = None, bei_ende: Optional[Callable[[Werbestelle], None]] = None):
        """`bei_ende`: wird einmal je Stelle gerufen, sobald ihr Ende feststeht (etwa um den Spot zu zählen)."""
        self._regeln = r or regeln()
        self._bei_ende = bei_ende
        self.stellen: list[Werbestelle] = []
        self._stillen: list[tuple[float, float]] = []
        self._stille_beginn: Optional[float] = None
        self._angaben = 0
        self._offen: Optional[Werbestelle] = None

    def angabe(self, roh: str, sekunde: float) -> Optional[Werbestelle]:
        """Eine Angabe an ihrer Stelle im Ton; gibt die neu begonnene Stelle zurück, falls eine beginnt."""
        erste = self._angaben == 0
        self._angaben += 1
        w = lesen(roh)
        offen = self._offen
        if offen and w and w.kennung == offen.kennung:
            return None                                       # derselbe Spot, die Angabe wiederholt sich
        if offen:
            offen.bis, offen.bis_aus = sekunde, "angabe"
            self._offen = None
            self._an_stille(offen)
            self._geendet(offen)
        if not w:
            return None
        neu = self._beginnen(w, 0.0 if erste else sekunde, "verbinden" if erste else "angabe")
        return neu

    def _beginnen(self, w: Werbeangabe, von: float, von_aus: Herkunft) -> Werbestelle:
        s = Werbestelle(von=von, von_aus=von_aus, format=w.format, kennung=w.kennung, werbender=w.werbender,
                        titel=w.titel, angekuendigt_ms=w.dauer_ms, beim_verbinden=w.beim_verbinden or von_aus == "verbinden")
        if w.ende == "dauer" and w.dauer_ms:
            s.bis, s.bis_aus = von + w.dauer_ms / 1000, "dauer"
        else:
            self._offen = s
        self.stellen.append(s)
        self._an_stille(s)
        if s.bis is not None:
            self._geendet(s)
        return s

    def _geendet(self, s: Werbestelle) -> None:
        if self._bei_ende:
            self._bei_ende(s)

    def stille_zeile(self, zeile: str) -> None:
        """Eine Zeile von ffmpeg (silencedetect): silence_start und silence_end ergeben eine Stille."""
        if (t := STILLE_BEGINN.search(zeile)):
            self._stille_beginn = float(t.group(1))
        elif (t := STILLE_ENDE.search(zeile)) and self._stille_beginn is not None:
            self.stille(self._stille_beginn, float(t.group(1)))
            self._stille_beginn = None

    def stille(self, von: float, bis: float) -> None:
        self._stillen.append((max(0.0, von), bis))
        del self._stillen[:-STILLEN_HOECHSTENS]
        for s in self.stellen[-20:]:
            self._an_stille(s)

    def _an_stille(self, s: Werbestelle) -> None:
        fenster = self._regeln.grenze.fenster_s
        if s.von_aus not in ("stille", "verbinden"):
            nah = self._naechste(s.von, fenster)
            if nah:
                s.von, s.von_aus = nah[0], "stille"
        if s.bis is not None and s.bis_aus != "stille":
            nah = self._naechste(s.bis, fenster)
            if nah:
                s.bis, s.bis_aus = nah[1], "stille"

    def _naechste(self, t: float, fenster: float) -> Optional[tuple[float, float]]:
        """Die Stille, die t am nächsten liegt (Abstand zur Stille, 0 wenn t in ihr liegt), höchstens fenster weit."""
        abstand = lambda st: 0.0 if st[0] <= t <= st[1] else min(abs(st[0] - t), abs(st[1] - t))
        kandidaten = [st for st in self._stillen if abstand(st) <= fenster]
        return min(kandidaten, key=abstand) if kandidaten else None

    def im_fenster(self, ab: float) -> list[Werbestelle]:
        """Die Stellen, die noch im Puffer liegen (enden nach `ab` oder laufen noch)."""
        return [s for s in self.stellen if s.bis is None or s.bis >= ab]
