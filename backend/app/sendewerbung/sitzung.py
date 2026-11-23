"""Werbestellen einer laufenden Sitzung (RAD-33): aus den Angaben des Stromlesers (roh, Stelle im Ton) werden Stellen
mit von und bis in Sekunden des Tons, also auf der Zeitachse des Zeitversatzes. Die genaue Grenze kommt aus der
Stille, die ffmpeg mitmeldet; ohne Stille bleibt die Grenze der Angabe.

- Eine Werbeangabe beginnt eine Stelle. Kam vorher noch keine Angabe, begann der Spot mit der Verbindung (Stelle ab 0):
  der Sender schickt die erste Angabe erst nach dem ersten Block Ton.
- Ende "dauer": die Stelle endet nach der angekündigten Länge. Ende "wechsel": sie endet mit der ersten Angabe, die
  nicht mehr zu ihr gehört (andere Kennung oder keine Werbung); bis dahin ist sie offen.
- Stille (von, bis): liegt eine Grenze höchstens `fenster_s` neben einer Stille, gehört die Stille zur Stelle (der
  Anfang rückt an den Beginn der Stille davor, das Ende an das Ende der Stille danach). Maßgeblich ist immer die
  Stille, die der Grenze laut Angabe am nächsten liegt: ffmpeg meldet Stille etwas später, als die Angabe kommt, darum
  wird jede neue Stille gegen die Grenze laut Angabe geprüft, nicht gegen die schon gerückte.
- Gemeldet (`bei_ende`) wird eine Stelle, wenn der Ton das Fenster hinter ihrem Ende laut Angabe passiert hat; dann
  steht auch die Stille fest.
- Ein Format mit bestaetigen "stille" (Vorlauf beim Verbinden, RAD-47): endet die Stelle laut Angabe, bleibt sie offen,
  bis höchstens `fenster_s` neben diesem Ende eine Stille gemeldet ist; dann endet sie dort. Hat der geprüfte Ton
  (`ton_bis`) das Fenster passiert ohne Stille, wird sie verworfen: dann war es kein Vorlauf, nur ein später Titel.
  Bleibt die Angabe aus (der Name steht minutenlang), endet die Stelle an der ersten Stille zwischen mindestens_s und
  hoechstens_s nach ihrem Anfang; kommt bis hoechstens_s keine, wird sie verworfen.

Ohne Ein- und Ausgabe; ffmpeg und der Stromleser rufen nur `angabe` und `stille`."""

from __future__ import annotations

import re
from typing import Callable, Literal, Optional

from pydantic import BaseModel, PrivateAttr

from ..services.feinschnitt import grenze as wechsel_grenze
from .angaben import Regeln, Werbeangabe, lesen, regeln

Herkunft = Literal["angabe", "stille", "verbinden", "dauer", "klang"]

#: Format einer Stelle, die am Klang erkannt wurde (Propaganda-Filter, HELF-256)
KLANG = "klang"

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
    # Grenzen laut Angabe (vor dem Rücken an die Stille); nicht Teil der Antwort
    _von_angabe: Optional[float] = PrivateAttr(None)
    _bis_angabe: Optional[float] = PrivateAttr(None)

    _bis_quelle: Optional[Herkunft] = PrivateAttr(None)
    #: endet erst mit einer Stille am Ende laut Angabe (bestaetigen "stille")
    _bestaetigen: bool = PrivateAttr(False)
    _mindestens_s: Optional[float] = PrivateAttr(None)
    _hoechstens_s: Optional[float] = PrivateAttr(None)

    @property
    def name(self) -> str:
        """Wer wirbt, so genau die Angabe es sagt."""
        return self.werbender or self.titel or ("" if self.format == KLANG else self.kennung)

    def ende_setzen(self, bis: float, aus: Herkunft) -> None:
        self.bis, self.bis_aus, self._bis_angabe, self._bis_quelle = bis, aus, bis, aus


class Sitzungswerbung:
    def __init__(self, r: Optional[Regeln] = None, bei_ende: Optional[Callable[[Werbestelle], None]] = None,
                 stillen_hoechstens: Optional[int] = STILLEN_HOECHSTENS):
        """`bei_ende`: wird einmal je Stelle gerufen, sobald ihr Ende feststeht (etwa um den Spot zu zählen): mit der
        Stille daran, oder wenn der Ton das Fenster der Stille hinter dem Ende hat und keine kam.
        `stillen_hoechstens`: so viele Stillen bleiben gemerkt; None: alle (eine Aufnahme braucht sie für den
        Feinschnitt, der rollende Puffer nur die jüngsten)."""
        self._stillen_hoechstens = stillen_hoechstens
        self._regeln = r or regeln()
        self._bei_ende = bei_ende
        self._wartet: list[Werbestelle] = []
        self.stellen: list[Werbestelle] = []
        self._stillen: list[tuple[float, float]] = []
        self._stille_beginn: Optional[float] = None
        self._angaben = 0
        self._offen: Optional[Werbestelle] = None
        self._unbestaetigt: list[Werbestelle] = []
        #: verworfene Stellen (Vorlauf ohne Stille am Ende), nur zur Auskunft
        self.verworfen: list[Werbestelle] = []
        #: Name des Senders aus dem Kopf des Stroms (icy-name); erst nach dem Verbinden bekannt
        self.sendername = ""

    def angabe(self, roh: str, sekunde: float) -> Optional[Werbestelle]:
        """Eine Angabe an ihrer Stelle im Ton; gibt die neu begonnene Stelle zurück, falls eine beginnt."""
        self._melden(sekunde)
        erste = self._angaben == 0
        self._angaben += 1
        w = lesen(roh, self.sendername, erste)
        offen = self._offen
        if offen and w and w.kennung == offen.kennung:
            return None                                       # derselbe Spot, die Angabe wiederholt sich
        if offen:
            self._offen = None
            if offen._bestaetigen:
                offen._bis_angabe = sekunde
                self._unbestaetigt.append(offen)
                self._bestaetigen()
            else:
                offen.ende_setzen(sekunde, "angabe")
                self._an_stille(offen)
                self._geendet(offen)
        if not w:
            return None
        neu = self._beginnen(w, 0.0 if erste else sekunde, "verbinden" if erste else "angabe")
        return neu

    def _beginnen(self, w: Werbeangabe, von: float, von_aus: Herkunft) -> Werbestelle:
        s = Werbestelle(von=von, von_aus=von_aus, format=w.format, kennung=w.kennung, werbender=w.werbender,
                        titel=w.titel, angekuendigt_ms=w.dauer_ms, beim_verbinden=w.beim_verbinden or von_aus == "verbinden")
        s._bestaetigen = w.bestaetigen == "stille"
        s._mindestens_s, s._hoechstens_s = w.mindestens_s, w.hoechstens_s
        if von_aus != "verbinden":
            s._von_angabe = von
        if w.ende == "dauer" and w.dauer_ms:
            s.ende_setzen(von + w.dauer_ms / 1000, "dauer")
        else:
            self._offen = s
        self.stellen.append(s)
        self._an_stille(s)
        if s.bis is not None:
            self._geendet(s)
        return s

    def erkannt(self, kennung: str, von: float, bis: float, werbender: str) -> None:
        """Am Klang erkannte Werbung. Was der Sender selbst ankündigt, gilt vor; dieselbe Stelle noch einmal rückt nur ihr Ende."""
        for s in self.stellen:
            if s.format == KLANG and s.kennung == kennung and abs(s.von - von) < 1.0:
                s.bis = bis
                return
            if s.format != KLANG and von < (s.bis if s.bis is not None else von + 1) and bis > s.von:
                return
        neu = Werbestelle(von=von, von_aus="klang", bis=bis, bis_aus="klang", format=KLANG, kennung=kennung, werbender=werbender)
        self.stellen.append(neu)
        self.stellen.sort(key=lambda s: s.von)
        self._geendet(neu)

    def _bestaetigen(self, jetzt: Optional[float] = None) -> None:
        """Offene Stellen, die eine Stille an ihrem Ende brauchen: mit Stille enden sie, ohne (der geprüfte Ton `jetzt`
        hat das Fenster passiert) fallen sie weg."""
        fenster = self._regeln.grenze.fenster_s
        for s in list(self._unbestaetigt):
            ende = s._bis_angabe or 0.0
            if self._naechste(ende, fenster):
                self._unbestaetigt.remove(s)
                s.ende_setzen(ende, "angabe")
                self._an_stille(s)
                self._geendet(s)
            elif jetzt is not None and jetzt > ende + fenster:
                self._unbestaetigt.remove(s)
                self.stellen.remove(s)
                self.verworfen.append(s)

    def _ohne_angabe(self, jetzt: Optional[float] = None) -> None:
        """Eine offene Stelle, die eine Stille braucht, ohne dass ihre Angabe endet: an der ersten Stille zwischen
        mindestens_s und hoechstens_s nach ihrem Anfang endet sie; hat der geprüfte Ton `jetzt` hoechstens_s passiert,
        wird sie verworfen."""
        s = self._offen
        if not s or not s._bestaetigen or s._hoechstens_s is None:
            return
        frueh, spaet = s.von + (s._mindestens_s or 0.0), s.von + s._hoechstens_s
        stille = next((st for st in self._stillen if frueh <= st[1] <= spaet), None)
        if stille:
            self._offen = None
            s.ende_setzen(stille[1], "stille")
            self._geendet(s)
        elif jetzt is not None and jetzt > spaet + self._regeln.grenze.fenster_s:
            self._offen = None
            self.stellen.remove(s)
            self.verworfen.append(s)

    def ton_bis(self, sekunde: float) -> None:
        """Der FFmpeg, der die Stille meldet, hat den Ton bis `sekunde` geprüft (sein Takt, nicht der des Lesers: der
        liest beim Verbinden einen Schwall Ton weit voraus). Bis hier ist jede Stille gemeldet."""
        self._ohne_angabe(sekunde)
        self._bestaetigen(sekunde)
        self._melden(sekunde)

    def _geendet(self, s: Werbestelle) -> None:
        if self._bei_ende:
            self._wartet.append(s)

    def _melden(self, jetzt: Optional[float] = None) -> None:
        """Wartende Stellen melden: mit Stille an ihrem Ende, oder wenn `jetzt` das Fenster hinter dem Ende passiert hat."""
        fenster = self._regeln.grenze.fenster_s
        fertig = [s for s in self._wartet if jetzt is not None and jetzt > (s._bis_angabe or s.bis or 0) + fenster]
        for s in fertig:
            self._wartet.remove(s)
            self._bei_ende(s)

    def stille_zeile(self, zeile: str) -> None:
        """Eine Zeile von ffmpeg (silencedetect): silence_start und silence_end ergeben eine Stille. Der ffmpeg prüft
        den ganzen Ton von Anfang an (Zeitversatz, Stillenwächter der Aufnahme), seine Zeiten sind die des Tons."""
        if (t := STILLE_BEGINN.search(zeile)):
            self._stille_beginn = float(t.group(1))
        elif (t := STILLE_ENDE.search(zeile)) and self._stille_beginn is not None:
            self.stille(self._stille_beginn, float(t.group(1)))
            self._stille_beginn = None

    def stille(self, von: float, bis: float) -> None:
        self._stillen.append((max(0.0, von), bis))
        if self._stillen_hoechstens is not None:
            del self._stillen[:-self._stillen_hoechstens]
        for s in self.stellen[-20:]:
            self._an_stille(s)
        self._ohne_angabe()
        self._bestaetigen()
        self._melden(bis)

    def _an_stille(self, s: Werbestelle) -> None:
        """Grenzen an die Stille. Kommt eine Grenze aus einer Angabe (Anfang, Ende durch die nächste Angabe), gilt die
        Regel des Feinschnitts: die Angabe kommt etwas nach dem echten Wechsel, maßgeblich ist das Ende der passenden
        Pause davor (vorher: die nächste Stille, das war bei Mangoradio ein 30-ms-Loch im Spot statt der Pause 0,8 s
        davor). Ein Ende aus der angekündigten Länge liegt genau: dort zählt die nächste Stille."""
        if s._von_angabe is not None:
            g = wechsel_grenze(s._von_angabe, self._stillen)
            if g != s._von_angabe:
                s.von, s.von_aus = g, "stille"
        if s._bis_angabe is None or s._bis_quelle is None:      # noch kein Ende, oder es wartet auf die Bestätigung
            return
        if s._bis_quelle == "angabe":
            g = wechsel_grenze(s._bis_angabe, self._stillen, nach=s.von)
            if g != s._bis_angabe:
                s.bis, s.bis_aus = g, "stille"
        else:
            nah = self._naechste(s._bis_angabe, self._regeln.grenze.fenster_s)
            if nah:
                s.bis, s.bis_aus = nah[1], "stille"

    def _naechste(self, t: float, fenster: float) -> Optional[tuple[float, float]]:
        """Die Stille, die t am nächsten liegt (Abstand zur Stille, 0 wenn t in ihr liegt), höchstens fenster weit."""
        abstand = lambda st: 0.0 if st[0] <= t <= st[1] else min(abs(st[0] - t), abs(st[1] - t))
        kandidaten = [st for st in self._stillen if abstand(st) <= fenster]
        return min(kandidaten, key=abstand) if kandidaten else None

    def vergessen_vor(self, sekunde: float) -> None:
        """Stillen und abgeschlossene Stellen, die vor `sekunde` enden, vergessen (der Empfang hält nur, was noch im
        Mitschnitt liegt)."""
        self._stillen = [st for st in self._stillen if st[1] >= sekunde]
        self.stellen = [s for s in self.stellen if s.bis is None or s.bis >= sekunde or s in self._unbestaetigt]

    @property
    def stillen(self) -> list[tuple[float, float]]:
        """Die gemerkten Stillen (von, bis) in Sekunden des Tons."""
        return list(self._stillen)

    def im_fenster(self, ab: float) -> list[Werbestelle]:
        """Die Stellen, die noch im Puffer liegen (enden nach `ab` oder laufen noch)."""
        return [s for s in self.stellen if s.bis is None or s.bis >= ab]
