"""Live mitlesen, was ein Sender spricht (RAD-129): aus dem Mitschnitt des Empfangs wird Stück für Stück Text, wahlweise
übersetzt. Beides rechnet die Leitstelle (Hördienst, Sprachmodell); der Pi liefert nur den Ton.

Es hängt am laufenden Empfang, hält ihn aber nicht am Leben: endet das Radio, endet das Mitlesen. Es läuft nur, solange jemand
liest (jede Abfrage der Oberfläche verlängert), und hört ganz auf, wenn man es ausschaltet.

Geschnitten wird im Ton an der leisesten Stelle zwischen `STUECK_VON_S` und `STUECK_BIS_S` (die Pegel misst der Empfang schon),
so trennt der Schnitt selten ein Wort. Gesammelt wird im Text: ein Absatz geht erst hinaus, wenn er mit einem ganzen Satz endet
und lang genug ist; der Rest wartet auf das nächste Stück. Werbung, die übersprungen wird, wird nicht mitgeschrieben.
"""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from appkern.leitstelle import GehoertesSegment, Leitstelle, LeitstellenFehler, Nachricht, gerade, halten, hoeren
from pydantic import BaseModel

if TYPE_CHECKING:
    from .empfang import Empfang

logger = logging.getLogger("radiohub.mitlesen")

STUECK_VON_S, STUECK_BIS_S = 15.0, 30.0      # so lang ist ein Stück Ton
EINSTIEG_S = 90.0                            # so weit zurück beginnt es im Puffer
RUECKSTAND_S = 300.0                         # weiter als so viel hinkt es nie hinterher, dann springt es nach vorn
ABSATZ_ZEICHEN = 160                         # ein Absatz ist mindestens so lang und endet mit einem Satz
ABSATZ_HOECHSTENS_S = 60.0                   # so lange wartet Text höchstens auf ein Satzende
LESER_WEG_S = 60.0                           # fragt so lange niemand, hört es auf
HALTEN_S = 120                               # es kommt gleich mehr: so lange bleiben die Modelle geladen
TAKT_S = 1.0
NACH_FEHLER_S = 15.0
ABSAETZE_HOECHSTENS = 2000
SATZENDE = re.compile(r"[.!?。！？…][\"')\]»]*\s*$")
ENDUNG = {"mp3": ".mp3", "aac": ".aac", "ogg": ".ogg", "flac": ".flac"}

Zustand = Literal["aus", "sammelt", "hoert", "uebersetzt", "gestoert"]

ANWEISUNG = """Du übersetzt fortlaufend, was in einem Radioprogramm gesprochen wird, ins {ziel}. Du bekommst den nächsten Absatz der
Abschrift; sie kann Hörfehler enthalten. Gib nur die Übersetzung dieses Absatzes aus, vollständig, flüssig und ohne Zusätze."""


class Absatz(BaseModel):
    nr: int
    #: Sekunden des Empfangs
    von: float
    bis: float
    #: Uhrzeit, zu der es gesendet wurde
    zeit: str
    text: str
    uebersetzung: str = ""


class Stand(BaseModel):
    laeuft: bool = False
    zustand: Zustand = "aus"
    grund: str = ""
    uuid: str = ""
    name: str = ""
    sprache: str = ""
    ziel: str = ""
    uebersetzen: bool = False
    #: was ab `ab` dazukam oder sich änderte (eine Übersetzung kommt nach ihrem Absatz)
    absaetze: list[Absatz] = []
    fassung: int = 0


def schnitt(pegel: list[tuple[float, float]], von: float, gehoert_bis: float) -> float | None:
    """Wo das Stück ab `von` endet: an der leisesten Stelle des erlaubten Bereichs. None: es ist noch nicht genug gesendet."""
    if gehoert_bis < von + STUECK_BIS_S:
        return None
    bereich = [(t, m) for t, m in pegel if von + STUECK_VON_S <= t <= von + STUECK_BIS_S]
    if not bereich:
        return von + STUECK_BIS_S
    # über drei Messungen (0,3 s) gemittelt: ein einzelnes Loch ist keine Pause
    glatt = [(bereich[i][0], sum(m for _, m in bereich[max(0, i - 1):i + 2]) / len(bereich[max(0, i - 1):i + 2])) for i in range(len(bereich))]
    return round(min(glatt, key=lambda x: (x[1], x[0]))[0], 2)


class Absatzsammler:
    """Sammelt gehörte Segmente zu Absätzen, die mit einem Satz enden."""

    def __init__(self) -> None:
        self._offen: list[GehoertesSegment] = []

    def nehmen(self, segmente: list[GehoertesSegment]) -> list[tuple[float, float, str]]:
        """(von, bis, Text) je fertigem Absatz."""
        aus: list[tuple[float, float, str]] = []
        for s in segmente:
            self._offen.append(s)
            laenge = sum(len(x.text) + 1 for x in self._offen)
            zu_lang = self._offen[-1].ende - self._offen[0].start > ABSATZ_HOECHSTENS_S
            if (laenge >= ABSATZ_ZEICHEN and SATZENDE.search(s.text)) or zu_lang:
                aus += self.rest()
        return aus

    def rest(self) -> list[tuple[float, float, str]]:
        """Was noch offen ist, als Absatz (eine Lücke im Ton oder das Ende)."""
        if not self._offen:
            return []
        text = " ".join(s.text.strip() for s in self._offen if s.text.strip())
        von, bis = self._offen[0].start, self._offen[-1].ende
        self._offen = []
        return [(von, bis, gerade(text))] if text else []


@dataclass
class Wahl:
    """Was die Oberfläche beim Start sagt."""

    sprache: str = ""               # Kürzel laut Sprachlabel des Senders, leer: erkennen
    ziel: str = "de"
    uebersetzen: bool = False


@dataclass
class Mitleser:
    """Höchstens ein Mitlesen zugleich; ein neues ersetzt das alte."""

    leitstelle: Callable[[], Leitstelle | None] = lambda: None
    hoerdienst: Callable[[], str] = lambda: "klangwerk-hoeren"
    modell: Callable[[], str] = lambda: ""
    ziel_name: Callable[[str], str] = lambda k: k
    uhr: Callable[[], float] = time.monotonic

    _empfang: Empfang | None = field(default=None, repr=False)
    _wahl: Wahl = field(default_factory=Wahl)
    _aufgaben: list[asyncio.Task[None]] = field(default_factory=list, repr=False)
    _absaetze: list[Absatz] = field(default_factory=list, repr=False)
    _geaendert: dict[int, int] = field(default_factory=dict, repr=False)      # Absatz -> Fassung seiner letzten Änderung
    _fassung: int = 0
    _nr: int = 0
    _zustand: Zustand = "aus"
    _grund: str = ""
    _gelesen: float = 0.0
    _erkannt: str = ""
    _zu_uebersetzen: asyncio.Queue[int] = field(default_factory=asyncio.Queue, repr=False)

    @property
    def eingerichtet(self) -> bool:
        return self.leitstelle() is not None

    @property
    def laeuft(self) -> bool:
        return self._empfang is not None

    @property
    def sprache(self) -> str:
        return self._wahl.sprache or self._erkannt

    @property
    def fremd(self) -> bool:
        """Spricht der Sender eine andere Sprache als die der Oberfläche?"""
        return bool(self.sprache) and self.sprache != self._wahl.ziel

    async def starten(self, empfang: Empfang, wahl: Wahl) -> Stand:
        await self.beenden()
        self._empfang, self._wahl, self._zustand, self._grund, self._erkannt = empfang, wahl, "sammelt", "", ""
        self._absaetze, self._geaendert, self._zu_uebersetzen = [], {}, asyncio.Queue()
        self._gelesen = self.uhr()
        ab = max(empfang.anfang_s, empfang.jetzt_s - EINSTIEG_S)
        self._aufgaben = [asyncio.create_task(self._mithoeren(empfang, ab)), asyncio.create_task(self._uebersetzen())]
        return self.stand(0)

    async def beenden(self, grund: str = "") -> None:
        """Aus heißt aus: nichts wird mehr gehört und nichts mehr übersetzt. Der Text bleibt bis zum nächsten Start."""
        aufgaben, self._aufgaben = [a for a in self._aufgaben if a is not asyncio.current_task()], []
        for a in aufgaben:
            a.cancel()
        self._empfang, self._zustand, self._grund = None, "aus", grund
        await asyncio.gather(*aufgaben, return_exceptions=True)

    def stellen(self, uebersetzen: bool) -> None:
        """Übersetzen an oder aus; an holt die letzten Absätze nach."""
        self._wahl.uebersetzen = uebersetzen
        if uebersetzen:
            for a in self._absaetze[-3:]:
                if not a.uebersetzung:
                    self._zu_uebersetzen.put_nowait(a.nr)

    def stand(self, ab: int) -> Stand:
        """Der Stand und alle Absätze, die nach der Fassung `ab` kamen oder sich änderten. Wer fragt, liest."""
        self._gelesen = self.uhr()
        e = self._empfang
        return Stand(laeuft=e is not None, zustand=self._zustand, grund=self._grund, uuid=e.uuid if e else "", name=e.name if e else "",
                     sprache=self.sprache, ziel=self._wahl.ziel, uebersetzen=self._wahl.uebersetzen, fassung=self._fassung,
                     absaetze=[a for a in self._absaetze if self._geaendert[a.nr] > ab])

    # ----- Ablauf

    async def _mithoeren(self, e: Empfang, von: float) -> None:
        sammler = Absatzsammler()
        try:
            while not e.beendet:
                if self.uhr() - self._gelesen > LESER_WEG_S:
                    return await self.beenden("niemand liest")
                if e.jetzt_s - von > RUECKSTAND_S:
                    self._hinzu(e, sammler.rest())
                    von = e.jetzt_s - EINSTIEG_S
                nach_werbung = self._nach_werbung(e, von)
                if nach_werbung > von:
                    self._hinzu(e, sammler.rest())
                    von = nach_werbung
                bis = schnitt(e.pegel, von, min(e.jetzt_s, e.pegel[-1][0] if e.pegel else e.jetzt_s))
                if bis is None:
                    self._zustand = "sammelt" if self._zustand != "gestoert" else "gestoert"
                    await asyncio.sleep(TAKT_S)
                    continue
                try:
                    self._hinzu(e, sammler.nehmen(await self._hoeren(e, von, bis)))
                    self._zustand, self._grund, von = "sammelt", "", bis
                except LeitstellenFehler as f:
                    self._zustand, self._grund = "gestoert", f.meldung
                    await asyncio.sleep(NACH_FEHLER_S)
            self._hinzu(e, sammler.rest())
            await self.beenden()
        except asyncio.CancelledError:
            raise
        except Exception as f:  # noqa: BLE001 - das Radio hängt nicht am Mitlesen
            logger.exception("Mitlesen %s", e.name)
            await self.beenden(type(f).__name__)

    @staticmethod
    def _nach_werbung(e: Empfang, von: float) -> float:
        """Beginnt hier eine Werbestelle, geht es an ihrem Ende weiter."""
        for s in e.werbung.stellen:
            if s.bis is not None and s.von - 1.0 <= von < s.bis and s.bis <= e.jetzt_s:
                return s.bis
        return von

    async def _hoeren(self, e: Empfang, von: float, bis: float) -> list[GehoertesSegment]:
        ls, daten = self.leitstelle(), e.ton_zwischen(von, bis)
        if ls is None or not daten:
            return []
        self._zustand = "hoert"
        with tempfile.TemporaryDirectory(prefix="mitlesen-") as ordner:
            datei = Path(ordner) / f"stueck{ENDUNG.get(e.kopf.format if e.kopf else '', '.mp3') if e.kopf and e.kopf.format else '.mp3'}"
            datei.write_bytes(daten)
            with halten(HALTEN_S):
                erg = await hoeren(ls, self.hoerdienst(), datei, self._wahl.sprache or "auto", versatz=von, titel="Live mitlesen")
        if not self._wahl.sprache and erg.sprache:
            self._erkannt = erg.sprache
        return erg.segmente

    def _hinzu(self, e: Empfang, absaetze: list[tuple[float, float, str]]) -> None:
        for von, bis, text in absaetze:
            self._nr += 1
            zeit = datetime.now().astimezone() - timedelta(seconds=max(0.0, e.jetzt_s - von))
            self._absaetze.append(Absatz(nr=self._nr, von=round(von, 1), bis=round(bis, 1), zeit=zeit.isoformat(timespec="seconds"), text=text))
            self._merken(self._nr)
            if self._wahl.uebersetzen:
                self._zu_uebersetzen.put_nowait(self._nr)
        for a in self._absaetze[:-ABSAETZE_HOECHSTENS]:
            self._geaendert.pop(a.nr, None)
        del self._absaetze[:-ABSAETZE_HOECHSTENS]

    def _merken(self, nr: int) -> None:
        self._fassung += 1
        self._geaendert[nr] = self._fassung

    async def _uebersetzen(self) -> None:
        """Absatz für Absatz, mit dem vorigen als Zusammenhang."""
        while True:
            nr = await self._zu_uebersetzen.get()
            a = next((x for x in self._absaetze if x.nr == nr), None)
            ls, modell = self.leitstelle(), self.modell()
            if a is None or a.uebersetzung or not self._wahl.uebersetzen or not self.fremd or ls is None or not modell:
                continue
            vorher = next((x for x in reversed(self._absaetze) if x.nr < nr and x.uebersetzung), None)
            nachrichten = [Nachricht.system(ANWEISUNG.format(ziel=self.ziel_name(self._wahl.ziel)))]
            if vorher:
                nachrichten += [Nachricht.nutzer(vorher.text), Nachricht.assistent(vorher.uebersetzung)]
            try:
                with halten(HALTEN_S):
                    antwort = await ls.chat([*nachrichten, Nachricht.nutzer(a.text)], modell=modell, titel="Live mitlesen: übersetzen", temperature=0.2)
                a.uebersetzung = gerade(antwort.text.strip())
                self._merken(nr)
            except LeitstellenFehler as f:
                self._grund = f.meldung
                logger.info("Übersetzung fehlt: %s", f)


mitleser = Mitleser()
