"""Feinschnitt einer laufenden Aufnahme in Abschnitten (RAD-139), damit sie beliebig lang werden kann.

Live wird grob geteilt, wenn die Angabe eintrifft (recorder.py). Früher schnitt der Feinschnitt erst nach dem Stopp und die ganze
Aufnahme auf einmal: sie war so lange gesperrt, und Pausen und Pegel vom Anfang waren da schon vergessen (der Empfang hält sie nur über
die Länge des Puffers). Jetzt folgt er der Aufnahme: alle Viertelstunde plant er die groben Stücke seit der letzten feinen Grenze,
schneidet, was feststeht, legt es ab und nimmt die groben dafür heraus. Offen bleibt immer der letzte Titel samt einem Nachlauf (spätere
Angaben können ihn noch ändern); sein Rest wartet als ein grobes Stück auf den nächsten Durchgang, beim Stopp auf den letzten.

Gehalten wird nur der laufende Abschnitt: lokal seine groben Stücke, im Arbeitsspeicher nichts, was mit der Länge wächst. Die groben
Stücke wandern in den Unterordner `Schritte/<Nr>` der Aufnahme; der Schritt "Feinschnitt" wächst mit und lässt sich wie jeder Schnitt
zurücknehmen. Ein Abbruch mittendrin verliert nichts: jede Zeile zeigt zu jeder Zeit auf eine Datei, die es gibt.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from ..ablage import AblageFehler, ablage, orte
from ..config import get_arbeit_dir
from ..database import db_session
from . import feinschnitt, feinschnitt_lauf, werbestellen
from .audio_utils import probe_duration
from .aufnahmen import aufnahmen
from .messung import messung
from .schnitt import SitzungGegenstand, schritt_fortschreiben, schritte
from .segment_splitter import Stueck, splitter

if TYPE_CHECKING:
    from .empfang import Abschnitt

logger = logging.getLogger("radiohub.laufschnitt")

#: so viel grob Geteiltes sammelt sich, bevor ein Durchgang lohnt
ABSCHNITT_S = 900.0
#: so lange nach einer Grenze können Angaben sie noch ändern (Einstreuungen dauern höchstens anderthalb Minuten)
NACHLAUF_S = 180.0
#: ein Titel, der länger nicht endet, wird in Teilen abgelegt (lange Sendung, Sender ohne Titelwechsel)
LANG_S = 3600.0
#: so viel lokal Gehaltenes höchstens; was älter ist, holt ein Durchgang aus der Ablage
LOKAL_HOECHSTENS = 400 << 20


@dataclass
class Laufschnitt:
    """`abschnitt` liefert Pausen, Pegel und Werbung (Sekunden der Aufnahme, Dauer), `wechsel` die Titelwechsel der Aufnahme, `sperre`
    schützt die Zeilen der Stücke gegen das Ablegen."""

    sitzung_id: str
    abschnitt: Callable[[float, float], Abschnitt]
    wechsel: Callable[[], list[tuple[float, str, bool]]]
    sperre: asyncio.Lock
    #: so viele Stücke vorn sind fein; alles dahinter ist grob
    fertig: int = 0
    werbung: list[werbestellen.Neu] = field(default_factory=list)
    _lokal: dict[str, Path] = field(default_factory=dict)
    _ab_wechsel_s: float = 0.0
    _rest: str = ""
    _teil: tuple[str, int] = ("", 1)
    _nr: int = 0
    _schritt: int | None = None
    _archiv: str = ""
    _vorher: list[dict] = field(default_factory=list)
    _neu: list[str] = field(default_factory=list)
    _laeuft: asyncio.Lock = field(default_factory=asyncio.Lock)

    # ----- Lokal gehaltene grobe Stücke

    @property
    def _ordner(self) -> Path:
        return get_arbeit_dir("schnitt", f"{self.sitzung_id}_lauf")

    def platz_fuer(self, nummer: int, endung: str) -> Path | None:
        """Wohin ein eben abgelegtes Stück lokal kommt; None, wenn schon genug gehalten wird."""
        if sum(p.stat().st_size for p in self._lokal.values() if p.exists()) > LOKAL_HOECHSTENS:
            return None
        return self._ordner / f"grob_{nummer:05d}{endung}"

    def gehalten(self, pfad: str, lokal: Path) -> None:
        self._lokal[pfad] = lokal

    async def _datei(self, zeile: dict, nummer: int) -> Path:
        lokal = self._lokal.get(zeile["file_path"])
        if lokal and lokal.exists():
            return lokal
        return await ablage().herunterladen(zeile["file_path"], self._ordner / f"geholt_{nummer:05d}{PurePosixPath(zeile['file_path']).suffix}")

    # ----- Planen

    def _grob(self) -> list[dict]:
        return aufnahmen.segmente(self.sitzung_id)[self.fertig:]

    def faellig(self) -> bool:
        grob = self._grob()
        return bool(grob) and (grob[-1]["end_ms"] - grob[0]["start_ms"]) / 1000 >= ABSCHNITT_S + NACHLAUF_S

    def _analyse(self, von: float, dauer: float) -> feinschnitt_lauf.Analyse:
        teil = self.abschnitt(von, dauer)
        alle = self.wechsel()
        vorher = [w for w in alle if w[0] <= max(von, self._ab_wechsel_s)]
        wechsel = [(0.0, vorher[-1][1], vorher[-1][2])] if vorher and von > 0 else []
        ab = max(von, self._ab_wechsel_s) if von > 0 else -1.0
        wechsel += [(round(t - von, 3), x, g) for t, x, g in alle if ab < t < von + dauer]
        return feinschnitt_lauf.Analyse(ab=von, dauer=dauer, wechsel=wechsel, stillen=teil.stillen, pegel=teil.pegel,
                                        werbung=[(v, b, w.name) for v, b, w in teil.werbung])

    def _behalten(self, plan: list[feinschnitt.Stueck], grob: list[dict], dauer: float, abschluss: bool) -> list[feinschnitt.Stueck]:
        """Was feststeht: beim Abschluss alles, sonst bis zum Nachlauf; ein sehr langer Titel endet dort, wo ein grobes Stück endet."""
        if abschluss:
            return plan
        fest = [s for s in plan[:-1] if s.bis <= dauer - NACHLAUF_S]
        if fest or dauer < LANG_S:
            return fest
        anfang = grob[0]["start_ms"]
        enden = [(g["end_ms"] - anfang) / 1000 for g in grob if (g["end_ms"] - anfang) / 1000 <= dauer - NACHLAUF_S]
        return [feinschnitt.Stueck(0.0, enden[-1], plan[0].name, plan[0].art)] if enden else []

    def _benennen(self, namen: list[str], weiter: bool) -> list[str]:
        """Ein Titel, der über mehrere Durchgänge geht, heißt ab dem zweiten "... (Teil 2)"."""
        aus = []
        for i, name in enumerate(namen):
            if i == 0 and weiter and name == self._teil[0]:
                self._teil = (name, self._teil[1] + 1)
                aus.append(f"{name} (Teil {self._teil[1]})")
            else:
                self._teil = (name, 1)
                aus.append(name)
        return aus

    # ----- Ein Durchgang

    async def durchgang(self, abschluss: bool = False) -> int:
        """Schneidet, was feststeht; liefert die Zahl der neuen feinen Stücke."""
        async with self._laeuft:
            beginn = time.monotonic()
            try:
                anzahl = await self._durchgang(abschluss)
                messung.merken("feinschnitt", sitzung=self.sitzung_id, stuecke=anzahl, fertig=self.fertig, abschluss=abschluss,
                               dauer_s=round(time.monotonic() - beginn, 2), lokal_mb=round(sum(p.stat().st_size for p in self._lokal.values() if p.exists()) / 1e6, 1))
                return anzahl
            finally:
                if abschluss:
                    shutil.rmtree(self._ordner, ignore_errors=True)
                    self._lokal.clear()

    async def _durchgang(self, abschluss: bool) -> int:
        grob = self._grob()
        if not grob:
            return 0
        von, bis = grob[0]["start_ms"] / 1000, grob[-1]["end_ms"] / 1000
        analyse = self._analyse(von, bis - von)
        plan = feinschnitt_lauf.planen(analyse, len(grob))
        behalten = self._behalten(plan, grob, bis - von, abschluss) if plan else []
        if not behalten:
            return 0
        ende = behalten[-1].bis
        offen = not abschluss and ende < bis - von - 0.05
        beteiligt = [g for g in grob if (g["start_ms"] / 1000 - von) < ende - 0.001] if offen else grob
        angabe = feinschnitt.angabe_der_grenze(ende, [feinschnitt.Angabe(*w) for w in analyse.wechsel], analyse.stillen, pegel=analyse.pegel)
        ordner, teil = self._ordner / "neu", self._teil
        try:
            stuecke, rest = await self._schneiden(beteiligt, behalten, von,
                                                  (plan[len(behalten)].name if len(plan) > len(behalten) else beteiligt[-1]["title"]) if offen else "", ordner)
            namen = self._benennen([s.titel for s in stuecke], von > 0)
            for s, name in zip(stuecke, namen):
                s.titel = name
            await self._uebernehmen(beteiligt, stuecke, rest)
        except BaseException:
            self._teil = teil                        # der nächste Durchgang rechnet denselben Abschnitt neu
            raise
        finally:
            shutil.rmtree(ordner, ignore_errors=True)
        self._messen(analyse, behalten, von)
        self._ab_wechsel_s = von + (max(ende, angabe.t) if angabe else ende)
        self.werbung += [werbestellen.Neu(von=von + v, bis=von + b, text=w.name + (" (beim Verbinden)" if w.beim_verbinden else ""))
                         for v, b, w in self.abschnitt(von, ende).werbung if b - v > 0.5]
        await self._analyse_ablegen(analyse, ende, abschluss)
        logger.info(f"Feinschnitt {self.sitzung_id}: {len(stuecke)} Stücke bis {(von + ende) / 60:.0f} min")
        return len(stuecke)

    def _messen(self, analyse: feinschnitt_lauf.Analyse, behalten: list[feinschnitt.Stueck], von: float) -> None:
        """Je Grenze ihr Grund und der Abstand zur Angabe (Messmodus): daran lässt sich die Regel prüfen und verbessern."""
        if not messung.aktiv:
            return
        angaben = [feinschnitt.Angabe(*w) for w in analyse.wechsel]
        for s in behalten:
            a = feinschnitt.angabe_der_grenze(s.bis, angaben, analyse.stillen, pegel=analyse.pegel)
            pausen = [(round(v, 2), round(b, 2)) for v, b in analyse.stillen if abs(b - s.bis) <= 8]
            grund = "werbung" if a is None else "pause" if any(v - 0.05 <= s.bis <= b + 0.05 for v, b in pausen) else \
                    "angabe" if abs(a.t - s.bis) < 0.01 else "tal"
            messung.merken("grenze", sitzung=self.sitzung_id, bei_s=round(von + s.bis, 2), davor=s.name, grund=grund,
                           angabe_s=round(von + a.t, 2) if a else None, abstand_s=round(s.bis - a.t, 2) if a else None,
                           pausen=[(round(von + v, 2), round(von + b, 2)) for v, b in pausen],
                           pegel=[(round(von + t, 1), m) for t, m in analyse.pegel if abs(t - s.bis) <= 6])

    async def _schneiden(self, beteiligt: list[dict], behalten: list[feinschnitt.Stueck], von: float, rest_name: str,
                         ordner: Path) -> tuple[list[Stueck], Stueck | None]:
        """Die beteiligten groben Stücke als eine Datei an den feinen Grenzen teilen; was dahinter bleibt, ist der Rest
        (`rest_name` leer: es bleibt keiner)."""
        ordner.mkdir(parents=True, exist_ok=True)
        dateien = [await self._datei(z, i) for i, z in enumerate(beteiligt)]
        ganz = dateien[0]
        if len(dateien) > 1:
            ganz = ordner / f"ganz{dateien[0].suffix}"
            if await splitter.zusammenfuegen(dateien, ganz) is None:
                raise AblageFehler("Grobe Stücke nicht zusammengefügt")
        dauer = await probe_duration(ganz) or (beteiligt[-1]["end_ms"] - beteiligt[0]["start_ms"]) / 1000
        zeiten = [s.bis for s in (behalten if rest_name else behalten[:-1]) if s.bis < dauer - 0.05]
        if zeiten:
            teile = await splitter.an_zeiten(ganz, zeiten, dauer, ganz.suffix, ordner / "teile")
        else:
            einzeln = ordner / f"einzeln{ganz.suffix}"
            shutil.copyfile(ganz, einzeln)
            teile = [Stueck("", 0, int(dauer * 1000), einzeln)]
        if len(teile) < len(behalten):
            raise AblageFehler(f"Schnitt ergab {len(teile)} von {len(behalten)} Stücken")
        fein, rest = teile[:len(behalten)], (teile[len(behalten)] if len(teile) > len(behalten) else None)
        beginn = int(von * 1000)
        for t, s in zip(fein, behalten):
            t.titel = s.name
        for t in teile:
            t.start_ms, t.end_ms = t.start_ms + beginn, t.end_ms + beginn
        fein[-1].end_ms = rest.start_ms if rest else beteiligt[-1]["end_ms"]
        if rest:
            rest.titel, rest.end_ms = rest_name, beteiligt[-1]["end_ms"]
        return fein, rest

    async def _uebernehmen(self, beteiligt: list[dict], stuecke: list[Stueck], rest: Stueck | None) -> None:
        """Erst die groben ins Archiv (jede Zeile zeigt dabei immer auf ihre Datei), dann die feinen ablegen, dann die Zeilen tauschen."""
        sitzung = aufnahmen.sitzung(self.sitzung_id)
        if not sitzung:
            raise AblageFehler("Die Aufnahme gibt es nicht mehr")
        gegenstand = SitzungGegenstand(self.sitzung_id)
        if not self._archiv:
            self._archiv = await ablage().freier_pfad(f"{sitzung['file_path']}/Schritte/{len(schritte(gegenstand.schluessel)) + 1:03d}")
        alter_rest = self._rest
        for z in beteiligt:
            if z["file_path"] != alter_rest and not z["file_path"].startswith(f"{self._archiv}/"):
                await self._archivieren(z)
        neue: list[tuple[Stueck, str, int]] = []
        feinschnitt_lauf.FORTSCHRITT[self.sitzung_id] = (0, len(stuecke))
        try:
            for i, s in enumerate([*stuecke, *([rest] if rest else [])]):
                pfad = await ablage().freier_pfad(orte.stueck(sitzung["file_path"], self.fertig + i, s.titel, s.datei.suffix))
                eintrag = await ablage().ablegen(pfad, s.datei)
                neue.append((s, pfad, eintrag.groesse))
                feinschnitt_lauf.FORTSCHRITT[self.sitzung_id] = (min(i + 1, len(stuecke)), len(stuecke))
        except Exception:
            for _, pfad, _ in neue:                  # halb Abgelegtes wieder weg; die groben Stücke gelten weiter
                try:
                    await ablage().loeschen(pfad)
                except AblageFehler:
                    pass
            raise
        async with self.sperre:
            self._tauschen([z["id"] for z in beteiligt], neue)
        self.fertig += len(stuecke)
        self._neu += [pfad for _, pfad, _ in neue[:len(stuecke)]]
        for datei in [d for z in beteiligt if (d := self._lokal.pop(z["file_path"], None))] + list(self._ordner.glob("geholt_*")):
            datei.unlink(missing_ok=True)
        self._rest = ""
        if rest:
            self._rest = neue[-1][1]
            ziel = self._ordner / f"rest_{self._nr:05d}{rest.datei.suffix}"
            rest.datei.replace(ziel)
            self._lokal[self._rest] = ziel
        was = f"{feinschnitt_lauf.SCHRITT}: {self.fertig} Stücke an den Pausen, Werbung für sich"
        self._schritt = schritt_fortschreiben(gegenstand.schluessel, self._schritt, was, {
            "archiv": self._archiv, "vorher": self._vorher, "neu": self._neu, "zeiten_bleiben": True})
        if alter_rest:
            try:
                await ablage().loeschen(alter_rest)      # in den Papierkorb: sein Ton steckt in den archivierten groben Stücken
            except AblageFehler as f:
                logger.warning(f"Rest {alter_rest} nicht entfernt: {f}")

    async def _archivieren(self, zeile: dict) -> None:
        alt = zeile["file_path"]
        neu = f"{self._archiv}/{PurePosixPath(alt).name}"
        await ablage().verschieben(alt, neu)
        with db_session() as conn:
            conn.execute("UPDATE segments SET file_path = ? WHERE id = ?", (neu, zeile["id"]))
        if alt in self._lokal:
            self._lokal[neu] = self._lokal.pop(alt)
        self._vorher.append({f: zeile.get(f) for f in ("title", "start_ms", "end_ms", "duration_ms", "file_path", "file_size")}
                            | {"segment_index": len(self._vorher)})
        zeile["file_path"] = neu

    def _tauschen(self, alte: list[int], neue: list[tuple[Stueck, str, int]]) -> None:
        with db_session() as conn:
            conn.executemany("DELETE FROM segments WHERE id = ?", [(i,) for i in alte])
            conn.execute("UPDATE segments SET segment_index = segment_index + ? WHERE session_id = ? AND segment_index >= ?",
                         (len(neue) - len(alte), self.sitzung_id, self.fertig))
            for i, (s, pfad, groesse) in enumerate(neue):
                conn.execute("""INSERT INTO segments (session_id, segment_index, title, start_ms, end_ms, duration_ms, file_path, file_size)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                             (self.sitzung_id, self.fertig + i, s.titel, s.start_ms, s.end_ms, s.end_ms - s.start_ms, pfad, groesse))

    async def _analyse_ablegen(self, a: feinschnitt_lauf.Analyse, ende: float, abschluss: bool) -> None:
        """Die Analyse bis zur letzten Grenze (zum späteren Neurechnen), je Durchgang eine Datei; kurze Aufnahmen haben nur eine."""
        self._nr += 1
        teil = a if abschluss else a.model_copy(update={
            "dauer": ende, "wechsel": [w for w in a.wechsel if w[0] < ende], "stillen": [s for s in a.stillen if s[0] < ende],
            "pegel": [p for p in a.pegel if p[0] < ende], "werbung": [w for w in a.werbung if w[0] < ende]})
        try:
            await feinschnitt_lauf.analyse_ablegen(self.sitzung_id, feinschnitt_lauf.schlank(teil), 0 if abschluss and self._nr == 1 else self._nr)
        except Exception as f:  # noqa: BLE001 - ohne gespeicherte Analyse geht nur das spätere Neurechnen nicht
            logger.warning(f"Analyse {self.sitzung_id} nicht abgelegt: {f}")
