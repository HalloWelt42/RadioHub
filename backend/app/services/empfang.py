"""Empfang eines Senders (RAD-46): eine Verbindung, eine Zeitachse, eine Wahrheit der Sendedaten.

Der Empfang hält den Stromleser (Ton und Sendedaten aus einer Verbindung), das Titelbuch, die Werbestellen, den
Stillenwächter (Stille und Pegel) und einen Mitschnitt der Rohdaten über die Länge des Puffers. Alle Zeiten sind
Sekunden des Tons seit dem Verbinden (Bytes durch Bytes je Sekunde, wie beim Stromleser).

Abnehmer sind der Puffer (Zeitversatz) und die Aufnahme. Ein Abnehmer meldet sich an, ab jetzt oder ab einer Stelle
in der Vergangenheit: dann spielt der Empfang ihm den Mitschnitt mit den Angaben an ihren Stellen nach und hängt ihn
danach nahtlos an den laufenden Ton. Mit einem Ende bekommt er nur den Abschnitt bis dahin. Angaben bekommt jeder
Abnehmer auf seine eigene Zeit (ab seinem Beginn); zuerst die Angabe, die bei seinem Beginn galt.

Der Empfang lebt, solange ein Abnehmer an ihm hängt: endet der Puffer (Radio aus), läuft eine Aufnahme weiter.
"""

from __future__ import annotations

import asyncio
import bisect
import itertools
import logging
import shutil
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from ..sendewerbung import spots as werbespots
from ..sendewerbung.sitzung import Sitzungswerbung, Werbestelle
from . import feinschnitt
from .stillenwaechter import Stillenwaechter
from .stromleser import Angabe, Kopf, Stromleser
from .titelbuch import Titelbuch

logger = logging.getLogger("radiohub.empfang")

#: Größe eines Blocks des Mitschnitts auf dem Datenträger
BLOCK_BYTES = 1 << 20
#: so viel wird beim Nachspielen auf einmal gelesen
NACHSPIEL_BYTES = 64 << 10
#: so viel Rand bleibt im Mitschnitt über die Länge des Puffers hinaus (für den Titel, der am Rand begann)
RAND_S = 600


@dataclass
class Abnehmer:
    """Wer den Ton eines Empfangs bekommt. `ton` und `angabe` werden der Reihe nach gerufen, `ende`, wenn der Strom
    endet oder das Ende des Abschnitts erreicht ist."""

    name: str
    ton: Callable[[bytes], Awaitable[None]]
    angabe: Optional[Callable[[Angabe], Awaitable[None]]] = None
    ende: Optional[Callable[[], Awaitable[None]]] = None
    #: Beginn und Ende auf der Zeitachse des Empfangs (Bytes); gesetzt beim Anmelden
    ab: int = 0
    bis: Optional[int] = None
    position: int = 0
    _nachspiel: Optional[asyncio.Task] = field(default=None, repr=False)
    _beendet: bool = field(default=False, repr=False)

    @property
    def bekommen(self) -> int:
        """So viele Bytes Ton hat er bekommen."""
        return self.position - self.ab


class Mitschnitt:
    """Die Rohdaten des Stroms in Blöcken auf dem Datenträger, die ältesten fallen weg."""

    def __init__(self, ordner: Path, hoechstens_bytes: int):
        self.ordner = ordner
        self.hoechstens = hoechstens_bytes
        self.ende = 0
        self._bloecke: deque[tuple[int, Path]] = deque()
        self._datei = None
        ordner.mkdir(parents=True, exist_ok=True)

    @property
    def anfang(self) -> int:
        return self._bloecke[0][0] if self._bloecke else self.ende

    def schreiben(self, daten: bytes) -> None:
        while daten:
            if self._datei is None or self.ende - self._bloecke[-1][0] >= BLOCK_BYTES:
                if self._datei:
                    self._datei.close()
                pfad = self.ordner / f"{self.ende:012d}.bin"
                self._datei = open(pfad, "ab")
                self._bloecke.append((self.ende, pfad))
                self._vergessen()
            platz = BLOCK_BYTES - (self.ende - self._bloecke[-1][0])
            teil, daten = daten[:platz], daten[platz:]
            self._datei.write(teil)
            self.ende += len(teil)
        self._datei.flush()

    def _vergessen(self) -> None:
        while len(self._bloecke) > 2 and self.ende - self._bloecke[1][0] > self.hoechstens:
            _, pfad = self._bloecke.popleft()
            pfad.unlink(missing_ok=True)

    def lesen(self, von: int, hoechstens: int) -> bytes:
        """Bis zu `hoechstens` Bytes ab `von` (innerhalb eines Blocks)."""
        von = max(von, self.anfang)
        starts = [b[0] for b in self._bloecke]
        i = bisect.bisect_right(starts, von) - 1
        if i < 0 or von >= self.ende:
            return b""
        beginn, pfad = self._bloecke[i]
        with open(pfad, "rb") as f:
            f.seek(von - beginn)
            return f.read(min(hoechstens, self.ende - von))

    def schliessen(self) -> None:
        if self._datei:
            self._datei.close()
            self._datei = None
        shutil.rmtree(self.ordner, ignore_errors=True)


class Empfang:
    def __init__(self, uuid: str, name: str, adresse: str, bitrate: int, puffer_s: int, ordner: Path):
        self.uuid, self.name, self.adresse = uuid, name, adresse
        self.puffer_s = puffer_s
        self.titelbuch = Titelbuch()
        self.werbung = Sitzungswerbung(bei_ende=self._spot_zaehlen, stillen_hoechstens=None)
        #: (Sekunde, Momentanlautheit LUFS) je 100 ms
        self.pegel: list[tuple[float, float]] = []
        self.stromleser = Stromleser(adresse, self._ton, self._angabe, bitrate=bitrate)
        self.kopf: Optional[Kopf] = None
        self.stillen: Optional[Stillenwaechter] = None
        self.mitschnitt: Optional[Mitschnitt] = None
        self._ordner = ordner
        self._angaben: list[Angabe] = []
        #: alle Angemeldeten; am laufenden Ton hängen davon die in `_abnehmer` (die übrigen werden nachgespielt)
        self._angemeldet: list[Abnehmer] = []
        self._abnehmer: list[Abnehmer] = []
        self._lauf: Optional[asyncio.Task] = None
        self._bei_ende_des_empfangs: Optional[Callable[["Empfang"], None]] = None
        self.beendet = False

    # --- Zeitachse ---------------------------------------------------------------------------------------------

    @property
    def bytes_je_sekunde(self) -> float:
        return self.stromleser.bytes_je_sekunde

    def sekunde(self, ton_bytes: int) -> float:
        return ton_bytes / self.bytes_je_sekunde

    def bytes_bei(self, sekunde: float) -> int:
        return int(round(sekunde * self.bytes_je_sekunde))

    @property
    def jetzt_s(self) -> float:
        return self.sekunde(self.stromleser.ton_bytes)

    @property
    def anfang_s(self) -> float:
        """Der älteste Ton, der noch im Mitschnitt liegt."""
        return self.sekunde(self.mitschnitt.anfang) if self.mitschnitt else self.jetzt_s

    # --- Lauf --------------------------------------------------------------------------------------------------

    async def verbinden(self) -> Kopf:
        """Verbindet und startet Stillenwächter und Mitschnitt; wirft StromFehler (auch Wiedergabeliste). Gelesen wird
        erst ab dem ersten Abnehmer: der bekommt den Ton ab dem Verbinden (mit einem Vorlauf beim Verbinden)."""
        self.kopf = await self.stromleser.verbinden()
        self.titelbuch.metaint = self.kopf.metaint
        self.werbung.sendername = self.kopf.name
        bytes_je_s = self.bytes_je_sekunde
        self.mitschnitt = Mitschnitt(self._ordner, int((self.puffer_s + RAND_S) * bytes_je_s))
        self.stillen = Stillenwaechter(self.kopf.format, self.werbung.stille_zeile, self._pegel)
        await self.stillen.starten()
        return self.kopf

    async def _laufen(self) -> None:
        try:
            await self.stromleser.laufen()
        finally:
            self.titelbuch.abschliessen(self.stromleser.ton_bytes)
            self.beendet = True
            for a in list(self._angemeldet):
                await self._beenden(a)
            await self._aufraeumen()

    async def _ton(self, daten: bytes) -> None:
        """Ziel des Stromlesers: ins Mitschnitt, zum Stillenwächter, an die Abnehmer."""
        ende = self.stromleser.ton_bytes
        if self.mitschnitt:
            self.mitschnitt.schreiben(daten)
        if self.stillen:
            await self.stillen.ton(daten)
        for a in list(self._abnehmer):
            await self._liefern(a, daten, ende - len(daten))

    async def _angabe(self, a: Angabe) -> None:
        self._angaben.append(a)
        await self.titelbuch.angabe(a)
        if (neu := self.werbung.angabe(a.roh, a.sekunde)):
            logger.info(f"Werbung ab {neu.von:.2f} s: {neu.name} ({neu.format}) bei {self.name}")
        for ab in list(self._abnehmer):
            if ab.angabe and (ab.bis is None or a.ton_bytes < ab.bis):      # am Ende beginnt nichts mehr
                await ab.angabe(self._fuer(ab, a))

    def _pegel(self, t: float, m: float) -> None:
        self.pegel.append((round(t, 2), round(m, 1)))
        self.werbung.ton_bis(t)
        if len(self.pegel) % 600 == 0:              # etwa jede Minute: was vor dem Mitschnitt liegt, vergessen
            self._vergessen()

    def _vergessen(self) -> None:
        grenze = self.anfang_s
        self.pegel = self.pegel[bisect.bisect_left(self.pegel, (grenze,)):]
        self.werbung.vergessen_vor(grenze)
        if self.mitschnitt:
            alt = bisect.bisect_left([a.ton_bytes for a in self._angaben], self.mitschnitt.anfang)
            del self._angaben[:max(0, alt - 1)]       # die Angabe, die am Anfang galt, bleibt

    def _spot_zaehlen(self, stelle: Werbestelle) -> None:
        try:
            werbespots.merken(self.uuid, stelle)
        except Exception as f:            # der Empfang hängt nicht an der Zählung
            logger.warning(f"Spot nicht gezählt: {f}")

    # --- Abnehmer ----------------------------------------------------------------------------------------------

    def _fuer(self, ab: Abnehmer, a: Angabe) -> Angabe:
        """Eine Angabe auf die Zeit des Abnehmers (ab seinem Beginn)."""
        return replace(a, ton_bytes=max(0, a.ton_bytes - ab.ab), sekunde=max(0.0, a.sekunde - self.sekunde(ab.ab)))

    async def _liefern(self, ab: Abnehmer, daten: bytes, von: int) -> None:
        """Ton ab der Stelle `von` an einen Abnehmer, gekappt an seinem Ende."""
        if ab._beendet:
            return
        if ab.bis is not None and von + len(daten) > ab.bis:
            daten = daten[:max(0, ab.bis - von)]
        if daten:
            await ab.ton(daten)
            ab.position = von + len(daten)
        if ab.bis is not None and ab.position >= ab.bis:
            await self._beenden(ab)

    async def anmelden(self, ab: Abnehmer, von_s: Optional[float] = None, bis_s: Optional[float] = None) -> None:
        """Ab jetzt oder ab `von_s` (Sekunden des Empfangs, höchstens so alt wie der Mitschnitt), bis `bis_s` oder
        bis zur Abmeldung."""
        jetzt = self.stromleser.ton_bytes
        anfang = self.mitschnitt.anfang if self.mitschnitt else jetzt
        ab.ab = jetzt if von_s is None else min(jetzt, max(anfang, self.bytes_bei(von_s)))
        ab.bis = None if bis_s is None else max(ab.ab, self.bytes_bei(bis_s))
        ab.position = ab.ab
        self._angemeldet.append(ab)
        if ab.angabe:                                # zuerst die Angabe, die beim Beginn galt
            galt = [a for a in self._angaben if a.ton_bytes <= ab.ab and "StreamTitle=" in a.roh][-1:]
            for a in galt:
                await ab.angabe(replace(a, ton_bytes=0, sekunde=0.0))
        if ab.ab >= jetzt:
            self._abnehmer.append(ab)
            if self._lauf is None:
                self._lauf = asyncio.create_task(self._laufen())
        else:
            ab._nachspiel = asyncio.create_task(self._nachspielen(ab))
        logger.info(f"Empfang {self.name}: {ab.name} ab {self.sekunde(ab.ab):.1f} s"
                    + (f" bis {self.sekunde(ab.bis):.1f} s" if ab.bis is not None else ""))

    async def _nachspielen(self, ab: Abnehmer) -> None:
        """Den Mitschnitt ab dem Beginn des Abnehmers nachliefern, mit den Angaben an ihren Stellen; ist er bei der
        Stelle des laufenden Tons angekommen, hängt er ohne Lücke am laufenden Ton (kein await dazwischen)."""
        try:
            while not ab._beendet:
                ende = self.stromleser.ton_bytes
                if ab.position >= ende:
                    if not self.beendet:
                        self._abnehmer.append(ab)
                    else:
                        await self._beenden(ab)
                    return
                naechste = next((a for a in self._angaben if a.ton_bytes > ab.position), None)
                grenze = min(ende, naechste.ton_bytes if naechste else ende, ab.position + NACHSPIEL_BYTES)
                daten = self.mitschnitt.lesen(ab.position, grenze - ab.position) if self.mitschnitt else b""
                if not daten:                       # nicht mehr im Mitschnitt: weiter am laufenden Ton
                    ab.position = ende
                    continue
                await self._liefern(ab, daten, ab.position)
                if naechste and ab.position >= naechste.ton_bytes and ab.angabe and not ab._beendet \
                        and (ab.bis is None or naechste.ton_bytes < ab.bis):
                    await ab.angabe(self._fuer(ab, naechste))
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass

    async def _beenden(self, ab: Abnehmer) -> None:
        if ab._beendet:
            return
        ab._beendet = True
        self._entfernen(ab)
        if ab.ende:
            await ab.ende()

    def _entfernen(self, ab: Abnehmer) -> None:
        for liste in (self._abnehmer, self._angemeldet):
            if ab in liste:
                liste.remove(ab)

    async def abmelden(self, ab: Abnehmer) -> None:
        """Der Abnehmer will nichts mehr; ohne Abnehmer endet der Empfang."""
        ab._beendet = True
        if ab._nachspiel and not ab._nachspiel.done():
            ab._nachspiel.cancel()
        self._entfernen(ab)
        if not self._angemeldet:
            await self.beenden()

    async def beenden(self) -> None:
        self.stromleser.stop()
        if self._lauf and not self._lauf.done():
            self._lauf.cancel()
            try:
                await self._lauf
            except asyncio.CancelledError:
                pass
        await self._aufraeumen()

    async def _aufraeumen(self) -> None:
        if self.stillen:
            await self.stillen.beenden()
            self.stillen = None
        if self.mitschnitt:
            self.mitschnitt.schliessen()
            self.mitschnitt = None
        if self._bei_ende_des_empfangs:
            self._bei_ende_des_empfangs(self)
            self._bei_ende_des_empfangs = None

    @property
    def hat_abnehmer(self) -> bool:
        return bool(self._angemeldet)

    # --- Sendedaten eines Abschnitts --------------------------------------------------------------------------

    def abschnitt(self, von_s: float, dauer: float) -> "Abschnitt":
        """Die Sendedaten von `von_s` an für `dauer` Sekunden, auf die Zeit ab `von_s` (Ränder gekappt)."""
        bis = von_s + dauer
        rel = lambda t: round(t - von_s, 3)
        stillen = [(round(max(0.0, v - von_s), 3), round(min(dauer, b - von_s), 3)) for v, b in self.werbung.stillen
                   if b > von_s and v < bis]
        pegel = [(rel(t), m) for t, m in self.pegel if von_s <= t <= bis]
        werbung = [(round(max(0.0, s.von - von_s), 3), round(min(dauer, (s.bis if s.bis is not None else bis) - von_s), 3), s)
                   for s in self.werbung.stellen if (s.bis is None or s.bis > von_s) and s.von < bis]
        vorher = [w for w in self.titelbuch.wechsel if w[0] <= von_s]
        wechsel = ([(0.0, vorher[-1][1], vorher[-1][2])] if vorher else []) + \
                  [(rel(t), x, g) for t, x, g in self.titelbuch.wechsel if von_s < t < bis]
        return Abschnitt(dauer=dauer, wechsel=wechsel, stillen=stillen, pegel=pegel, werbung=werbung)

    def stuecke(self, von_s: Optional[float] = None) -> list[feinschnitt.Stueck]:
        """Die Stücke (Titel, Werbung, Einschübe) ab `von_s` bis jetzt, nach der Regel des Feinschnitts, auf der
        Zeitachse des Empfangs. Das letzte ist das laufende."""
        von = self.anfang_s if von_s is None else max(self.anfang_s, von_s)
        a = self.abschnitt(von, max(0.0, self.jetzt_s - von))
        if a.dauer <= 0:
            return []
        liste = feinschnitt.stuecke(a.dauer, [feinschnitt.Angabe(t, x, g) for t, x, g in a.wechsel], a.stillen,
                                    [feinschnitt.Werbung(v, b, s.name) for v, b, s in a.werbung], pegel=a.pegel)
        for s in liste:
            s.von, s.bis = round(s.von + von, 3), round(s.bis + von, 3)
        return liste

    def titelanfang(self) -> tuple[float, Optional[Werbestelle]]:
        """Wo eine Aufnahme beginnt, die "am Anfang des laufenden Titels" beginnen soll: an der Grenze vor dem
        laufenden Stück. Läuft gerade Werbung, die laufende Stelle (die Aufnahme beginnt nach ihr)."""
        jetzt = self.jetzt_s
        laufend = next((s for s in reversed(self.werbung.stellen) if s.von <= jetzt and (s.bis is None or s.bis > jetzt)), None)
        if laufend:
            return jetzt, laufend
        liste = self.stuecke(max(self.anfang_s, jetzt - 1800))
        return (liste[-1].von if liste else jetzt), None


@dataclass
class Abschnitt:
    dauer: float
    wechsel: list[tuple[float, str, bool]]
    stillen: list[tuple[float, float]]
    pegel: list[tuple[float, float]]
    #: (von, bis, Stelle) auf die Zeit des Abschnitts
    werbung: list[tuple[float, float, Werbestelle]]


class Empfangsstelle:
    """Die laufenden Empfänge, einer je Adresse."""

    def __init__(self, ordner: Callable[[str], Path]):
        self._ordner = ordner
        self._laufend: dict[str, Empfang] = {}
        self._sperre = asyncio.Lock()
        self._zaehler = itertools.count(1)

    def zu(self, adresse: str) -> Optional[Empfang]:
        e = self._laufend.get(adresse)
        return e if e and not e.beendet else None

    async def holen(self, uuid: str, name: str, adresse: str, bitrate: int, puffer_s: int) -> Empfang:
        """Der laufende Empfang dieser Adresse oder ein neuer (verbindet; wirft StromFehler)."""
        async with self._sperre:
            if (e := self.zu(adresse)):
                return e
            e = Empfang(uuid, name, adresse, bitrate, puffer_s, self._ordner(f"{uuid[:8] or 'sender'}-{next(self._zaehler)}"))
            await e.verbinden()
            e._bei_ende_des_empfangs = lambda x: self._laufend.pop(x.adresse, None) if self._laufend.get(x.adresse) is x else None
            self._laufend[adresse] = e
            return e

    async def alle_beenden(self) -> None:
        for e in list(self._laufend.values()):
            await e.beenden()


def _ordner(name: str) -> Path:
    from ..config import get_arbeit_dir
    return get_arbeit_dir("empfang") / f"{time.strftime('%Y%m%d-%H%M%S')}-{name}"


def mitschnitte_raeumen() -> None:
    """Beim Start: Mitschnitte eines vorigen Laufs sind ohne ihren Empfang wertlos (keine Nutzerdaten)."""
    from ..config import get_arbeit_dir
    for alt in get_arbeit_dir("empfang").iterdir():
        shutil.rmtree(alt, ignore_errors=True)


empfaenge = Empfangsstelle(_ordner)
