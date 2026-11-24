"""Schnitt für Aufnahmen und beliebige Audiodateien der Kellerwolke (RAD-17), an einer Stelle.

Ein Schnittgegenstand ist eine Aufnahme (Sitzung mit ihren Stücken in der Ablage) oder eine Datei der Kellerwolke.
Für beide gleich: Arbeitskopie, Wellenform, Schneiden in Stücke (behalten oder verwerfen, mit Namen),
Normalisieren, Umwandeln und Schritte mit Rückgängig, auch nach dem Neuladen (Tabelle schnitt_schritte).

- Aufnahme: ein Schritt ersetzt ihre Stücke. Vorher wandern die bisherigen Dateien in den Unterordner
  `Schritte/<Nr>` der Aufnahme (Verschieben kostet in der Kellerwolke nichts) und die Titel in den Schritt;
  Rückgängig legt die neuen in den Papierkorb und holt die alten zurück. Versionen allein reichen nicht, weil
  Schneiden Dateien hinzufügt und entfernt.
- Datei: das Original bleibt unberührt; Ergebnisse sind neue Dateien daneben, wo die Kellerwolke RadioHub das
  Schreiben erlaubt, sonst im eigenen Ordner unter `Schnitt/<Ordner>`. Rückgängig legt sie in den Papierkorb.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import werbestellen
from ..ablage import ablage, orte, wolke
from ..ablage.port import eltern, sauberer_pfad
from ..config import AUDIO_EXTENSIONS, get_arbeit_dir
from ..database import db_session
from .audio_utils import probe_duration
from .aufnahmen import AufnahmeFehler, aufnahmen
from .peaks_generator import peaks_gen
from .segment_splitter import Stueck, splitter, titel_eintraege

SCHRITTE_HALTEN = 10                       # so viele Schritte je Gegenstand lassen sich zurücknehmen
Fortschritt = Callable[[int, int, str], None]
Bearbeitung = Callable[[list[Path], Fortschritt], Awaitable[list[Path]]]


@dataclass
class StueckWahl:
    """Ein Stück zwischen zwei Markern, wie es der Schnitt zeigt: Lage, Name, behalten oder verwerfen."""
    von: float
    bis: float
    name: str
    behalten: bool = True


# --- Schritte ------------------------------------------------------------------------------------------------------

def schritte(schluessel: str) -> list[dict]:
    with db_session() as conn:
        zeilen = conn.execute("SELECT id, was, zeit FROM schnitt_schritte WHERE gegenstand = ? ORDER BY id",
                              (schluessel,)).fetchall()
    return [{"id": z[0], "was": z[1], "zeit": z[2]} for z in zeilen]


def _schritt_anlegen(schluessel: str, was: str, daten: dict) -> int:
    with db_session() as conn:
        return conn.execute("INSERT INTO schnitt_schritte (gegenstand, was, daten) VALUES (?, ?, ?)",
                            (schluessel, was, json.dumps(daten))).lastrowid


def schritt_fortschreiben(schluessel: str, schritt_id: int | None, was: str, daten: dict) -> int:
    """Einen Schritt anlegen oder den angelegten weiterschreiben (der laufende Feinschnitt wächst mit der Aufnahme)."""
    if schritt_id is None:
        return _schritt_anlegen(schluessel, was, daten)
    with db_session() as conn:
        conn.execute("UPDATE schnitt_schritte SET was = ?, daten = ? WHERE id = ?", (was, json.dumps(daten), schritt_id))
    return schritt_id


def zeiten_unveraendert(schluessel: str) -> bool:
    """Hat kein Schritt die Zeiten im Ton verschoben (nur Schnitte ohne Verwerfen, die das ausdrücklich vermerken)?"""
    with db_session() as conn:
        zeilen = conn.execute("SELECT daten FROM schnitt_schritte WHERE gegenstand = ?", (schluessel,)).fetchall()
    return all(json.loads(z[0]).get("zeiten_bleiben") is True for z in zeilen)


def _letzter(schluessel: str) -> tuple[int, str, dict] | None:
    with db_session() as conn:
        z = conn.execute("SELECT id, was, daten FROM schnitt_schritte WHERE gegenstand = ? ORDER BY id DESC LIMIT 1",
                         (schluessel,)).fetchone()
    return (z[0], z[1], json.loads(z[2])) if z else None


def _entfernen(schritt_id: int) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM schnitt_schritte WHERE id = ?", (schritt_id,))


# --- Gegenstand ----------------------------------------------------------------------------------------------------

class Gegenstand(ABC):
    art: str

    def __init__(self, kennung: str) -> None:
        self.kennung = kennung

    @property
    def schluessel(self) -> str:
        return f"{self.art}:{self.kennung}"

    @abstractmethod
    async def info(self) -> dict:
        """Titel, Format, Dauer, bisherige Stücke, Titelwechsel, wohin Ergebnisse gehen."""

    @abstractmethod
    async def arbeitskopie(self) -> Path:
        """Der ganze Ton als lokale Datei (Wellenform, Hören im Schnitt, Schneiden)."""

    @abstractmethod
    async def wellenform_groesse(self) -> int: ...

    @abstractmethod
    async def wellenform_lesen(self, start: int, ende: int) -> bytes: ...

    @abstractmethod
    async def _stuecke_uebernehmen(self, stuecke: list[Stueck], was: str, zeiten_bleiben: bool = False) -> int:
        """Geschnittene Stücke an ihren Platz und den Schritt anlegen; liefert die Zahl. `zeiten_bleiben`: nichts
        verworfen, jede Stelle im Ton bleibt, wo sie war (Werbestellen gelten weiter)."""

    @abstractmethod
    async def bearbeiten(self, was: str, bearbeitung: Bearbeitung, fortschritt: Fortschritt) -> int: ...

    @abstractmethod
    async def _zuruecknehmen(self, daten: dict) -> None: ...

    def _endung(self, kopie: Path) -> str:
        return kopie.suffix or ".mp3"

    def _titel(self) -> list[dict] | None:
        return None

    async def schneiden(self, wahl: list[StueckWahl], fortschritt: Fortschritt, was: str | None = None) -> int:
        """An den Grenzen der Stücke teilen, verworfene weglassen, Namen übernehmen. `was`: Name des Schritts (sonst
        "Geschnitten in N Stücke")."""
        behalten = [w for w in wahl if w.behalten]
        if not behalten:
            raise AufnahmeFehler("Kein Stück zum Behalten gewählt")
        fortschritt(1, 3, "Arbeitskopie")
        kopie = await self.arbeitskopie()
        dauer = await probe_duration(kopie) or max(w.bis for w in wahl)
        zeiten = sorted({w.von for w in wahl if w.von > 0})
        ziel_dir = get_arbeit_dir("schnitt", f"{hashlib.sha1(self.schluessel.encode()).hexdigest()[:12]}_neu")
        try:
            fortschritt(2, 3, "Schneiden")
            stuecke = await splitter.an_zeiten(kopie, zeiten, dauer, self._endung(kopie), ziel_dir, self._titel())
            if not stuecke:
                raise AufnahmeFehler("Schnitt fehlgeschlagen", 500)
            uebrig: list[Stueck] = []
            for s in stuecke:
                start = s.start_ms / 1000
                w = min(wahl, key=lambda x: abs(x.von - start)) if wahl else None
                if w is not None and abs(w.von - start) > 0.5:
                    w = None
                if w is not None and not w.behalten:
                    s.datei.unlink(missing_ok=True)
                    continue
                if w is not None and w.name.strip():
                    s.titel = w.name.strip()
                uebrig.append(s)
            stelle = 0                          # ohne die verworfenen rücken die übrigen zusammen
            for s in uebrig:
                s.start_ms, s.end_ms = stelle, stelle + s.dauer_ms
                stelle = s.end_ms
            fortschritt(3, 3, "Ablegen")
            weg = len(stuecke) - len(uebrig)
            was = was or (f"Geschnitten in {len(uebrig)} {'Stück' if len(uebrig) == 1 else 'Stücke'}" + (f", {weg} verworfen" if weg else ""))
            return await self._stuecke_uebernehmen(uebrig, was, zeiten_bleiben=weg == 0)
        finally:
            shutil.rmtree(ziel_dir, ignore_errors=True)

    async def rueckgaengig(self) -> str | None:
        letzter = _letzter(self.schluessel)
        if letzter is None:
            return None
        schritt_id, was, daten = letzter
        await self._zuruecknehmen(daten)
        _entfernen(schritt_id)
        return was

    async def _alte_schritte_raeumen(self) -> None:
        alle = schritte(self.schluessel)
        for s in alle[:-SCHRITTE_HALTEN]:
            with db_session() as conn:
                z = conn.execute("SELECT daten FROM schnitt_schritte WHERE id = ?", (s["id"],)).fetchone()
            ordner = json.loads(z[0]).get("archiv") if z else None
            if ordner:
                await ablage().loeschen(ordner)      # in den Papierkorb, nicht endgültig
            _entfernen(s["id"])


class SitzungGegenstand(Gegenstand):
    art = "sitzung"

    def _sitzung(self) -> dict:
        s = aufnahmen.sitzung(self.kennung)
        if not s:
            raise AufnahmeFehler("Aufnahme nicht gefunden", 404)
        if s.get("status") == "recording":
            raise AufnahmeFehler("Die Aufnahme läuft noch")
        return s

    async def info(self) -> dict:
        s = self._sitzung()
        segmente = aufnahmen.segmente(self.kennung)
        wechsel = [{"start": e.get("t", 0) / 1000, "titel": e.get("title") or ""}
                   for e in titel_eintraege(await aufnahmen.titelliste(s)) if not e.get("ignored")]
        return {"art": self.art, "kennung": self.kennung, "titel": s.get("station_name") or "Aufnahme",
                "zeit": s.get("start_time"), "format": (s.get("codec") or "").upper(), "bitrate": s.get("bitrate"),
                "dauer": s.get("duration") or sum((x.get("duration_ms") or 0) for x in segmente) / 1000,
                "stuecke": [{"von": (x.get("start_ms") or 0) / 1000, "bis": (x.get("end_ms") or 0) / 1000, "name": x["title"]}
                            for x in segmente],
                "titelwechsel": wechsel, "ziel": "Ersetzt die Stücke der Aufnahme; die vorige Fassung bleibt in den Schritten.",
                "schritte": (fertig := schritte(self.schluessel)), "werbestellen": self._werbestellen(fertig)}

    def _werbestellen(self, fertig: list[dict]) -> list[dict]:
        """Werbestellen der Aufnahme (RAD-33, aus den Sendedaten beim Aufnehmen). Ihre Zeiten gelten für den Ton, wie
        er aufgenommen wurde: nach einem Schritt, der etwas verworfen hat, nicht mehr, dann gibt es keine (Rückgängig
        bringt sie zurück). Ein Schnitt ohne Verwerfen (etwa der Feinschnitt nach dem Aufnehmen) lässt sie gelten."""
        if not zeiten_unveraendert(self.schluessel):
            return []
        return [{"von": w.von, "bis": w.bis, "text": w.text}
                for w in werbestellen.stellen(werbestellen.Bezug.aufnahme(self.kennung))]

    async def arbeitskopie(self) -> Path:
        self._sitzung()
        return await aufnahmen.arbeitskopie(self.kennung)

    async def wellenform_groesse(self) -> int:
        return (await aufnahmen.wellenform(self.kennung)).groesse

    async def wellenform_lesen(self, start: int, ende: int) -> bytes:
        return await ablage().lesen_ganz((await aufnahmen.wellenform(self.kennung)).pfad, start, ende)

    def _endung(self, kopie: Path) -> str:
        return kopie.suffix or self._sitzung().get("file_format") or ".mp3"

    async def _archivieren(self, segmente: list[dict]) -> str:
        """Die Dateien dieser Stücke in den Unterordner Schritte/<Nr>; liefert den Ordner."""
        ordner = self._sitzung()["file_path"]
        nr = len(schritte(self.schluessel)) + 1
        archiv = await ablage().freier_pfad(f"{ordner}/Schritte/{nr:03d}")
        for seg in segmente:
            await ablage().verschieben(seg["file_path"], f"{archiv}/{PurePosixPath(seg['file_path']).name}")
        return archiv

    @staticmethod
    def _zeilen(segmente: list[dict]) -> list[dict]:
        felder = ("segment_index", "title", "start_ms", "end_ms", "duration_ms", "file_path", "file_size")
        return [{f: s.get(f) for f in felder} for s in segmente]

    def _segmente_setzen(self, zeilen: list[dict]) -> None:
        with db_session() as conn:
            conn.execute("DELETE FROM segments WHERE session_id = ?", (self.kennung,))
            for z in zeilen:
                conn.execute("""INSERT INTO segments (session_id, segment_index, title, start_ms, end_ms, duration_ms,
                                file_path, file_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                             (self.kennung, z["segment_index"], z["title"], z["start_ms"], z["end_ms"],
                              z["duration_ms"], z["file_path"], z["file_size"]))
            # Größe und Länge der Aufnahme folgen ihren Stücken (nach dem Schneiden fehlen die verworfenen)
            conn.execute("UPDATE sessions SET file_size = ?, duration = ? WHERE id = ?",
                         (sum(z["file_size"] or 0 for z in zeilen), sum(z["duration_ms"] or 0 for z in zeilen) / 1000, self.kennung))

    def _titel(self) -> list[dict] | None:
        return None                 # Namen kommen aus der Wahl des Schnitts (dort vorbelegt mit den Titeln)

    async def _stuecke_uebernehmen(self, stuecke: list[Stueck], was: str, zeiten_bleiben: bool = False) -> int:
        sitzung = self._sitzung()
        alte = aufnahmen.segmente(self.kennung)
        archiv = await self._archivieren(alte)
        neue = []
        for index, stueck in enumerate(stuecke):
            pfad = orte.stueck(sitzung["file_path"], index, stueck.titel, stueck.datei.suffix)
            eintrag = await ablage().ablegen(pfad, stueck.datei)
            stueck.datei.unlink(missing_ok=True)
            neue.append({"segment_index": index, "title": stueck.titel, "start_ms": stueck.start_ms, "end_ms": stueck.end_ms,
                         "duration_ms": stueck.dauer_ms, "file_path": pfad, "file_size": eintrag.groesse})
        self._segmente_setzen(neue)
        _schritt_anlegen(self.schluessel, was, {"archiv": archiv, "vorher": self._zeilen(alte),
                                                "neu": [z["file_path"] for z in neue], "zeiten_bleiben": zeiten_bleiben})
        await aufnahmen._veraendert(sitzung)
        await self._alte_schritte_raeumen()
        return len(neue)

    async def bearbeiten(self, was: str, bearbeitung: Bearbeitung, fortschritt: Fortschritt) -> int:
        sitzung = self._sitzung()
        segmente = aufnahmen.segmente(self.kennung)
        if not segmente:
            raise AufnahmeFehler("Keine Stücke vorhanden", 404)
        lokal_dir = get_arbeit_dir("bearbeiten", self.kennung)
        try:
            lokal = [await ablage().herunterladen(s["file_path"], lokal_dir / PurePosixPath(s["file_path"]).name)
                     for s in segmente]
            fertig = await bearbeitung(lokal, fortschritt)
            archiv = await self._archivieren(segmente)
            neue = []
            for seg, datei in zip(segmente, fertig):
                pfad = str(PurePosixPath(seg["file_path"]).with_suffix(datei.suffix))
                eintrag = await ablage().ablegen(pfad, datei)
                neue.append({**{k: seg.get(k) for k in ("segment_index", "title", "start_ms", "end_ms", "duration_ms")},
                             "file_path": pfad, "file_size": eintrag.groesse})
            self._segmente_setzen(neue)
            _schritt_anlegen(self.schluessel, was, {"archiv": archiv, "vorher": self._zeilen(segmente),
                                                    "neu": [z["file_path"] for z in neue]})
        finally:
            shutil.rmtree(lokal_dir, ignore_errors=True)
        await aufnahmen._veraendert(sitzung)
        await self._alte_schritte_raeumen()
        return len(fertig)

    async def _zuruecknehmen(self, daten: dict) -> None:
        sitzung = self._sitzung()
        for pfad in daten.get("neu", []):
            await ablage().loeschen(pfad)
        archiv = daten["archiv"]
        for zeile in daten["vorher"]:
            await ablage().verschieben(f"{archiv}/{PurePosixPath(zeile['file_path']).name}", zeile["file_path"])
        await ablage().loeschen(archiv)
        self._segmente_setzen(daten["vorher"])
        await aufnahmen._veraendert(sitzung)


class DateiGegenstand(Gegenstand):
    art = "datei"

    def __init__(self, kennung: str) -> None:
        super().__init__(sauberer_pfad(kennung))
        if PurePosixPath(self.kennung).suffix.lower() not in AUDIO_EXTENSIONS:
            raise AufnahmeFehler("Keine Audiodatei", 415)

    @property
    def _stamm(self) -> str:
        return hashlib.sha1(self.kennung.encode()).hexdigest()[:16]

    async def _zielordner(self) -> str:
        """Neben dem Original, wo RadioHub schreiben darf; sonst im eigenen Ordner unter Schnitt/<Ordner>."""
        ordner = eltern(self.kennung)
        if ordner and await wolke().darf_schreiben(ordner):
            return ordner
        from ..einstellungen import stand
        return f"{stand().kellerwolke_wurzel}/Schnitt/{orte.name(PurePosixPath(ordner).name or 'Kellerwolke')}"

    async def info(self) -> dict:
        eintrag = await wolke().eintrag(self.kennung)
        if eintrag is None:
            raise AufnahmeFehler("Datei nicht gefunden", 404)
        kopie = await self.arbeitskopie()
        dauer = await probe_duration(kopie) or 0
        ziel = await self._zielordner()
        name = PurePosixPath(self.kennung).stem
        return {"art": self.art, "kennung": self.kennung, "titel": PurePosixPath(self.kennung).name, "zeit": None,
                "format": PurePosixPath(self.kennung).suffix.lstrip(".").upper(), "bitrate": None, "dauer": dauer,
                "stuecke": [{"von": 0, "bis": dauer, "name": name}], "titelwechsel": [],
                "ziel": f"Neue Dateien in {ziel}; das Original bleibt.", "zielordner": ziel,
                "neben": ziel == eltern(self.kennung), "schritte": schritte(self.schluessel), "werbestellen": []}

    async def arbeitskopie(self) -> Path:
        ziel = get_arbeit_dir("schnitt") / f"w_{self._stamm}{PurePosixPath(self.kennung).suffix.lower()}"
        if ziel.exists() and ziel.stat().st_size > 0:
            ziel.touch()
            return ziel
        return await wolke().herunterladen(self.kennung, ziel)

    async def _wellenform(self) -> Path:
        datei = get_arbeit_dir("schnitt") / f"w_{self._stamm}.peaks"
        if not datei.exists():
            erzeugt = await peaks_gen.generate_peaks(await self.arbeitskopie(), force=True)
            if not erzeugt:
                raise AufnahmeFehler("Wellenform konnte nicht berechnet werden", 500)
            if erzeugt != datei:
                shutil.move(erzeugt, datei)
        return datei

    async def wellenform_groesse(self) -> int:
        return (await self._wellenform()).stat().st_size

    async def wellenform_lesen(self, start: int, ende: int) -> bytes:
        with open(await self._wellenform(), "rb") as f:
            f.seek(start)
            return f.read(ende - start + 1)

    async def _ablegen(self, dateien: list[tuple[str, Path]], was: str) -> int:
        ordner = await self._zielordner()
        neu = []
        for name, datei in dateien:
            pfad = await wolke().freier_pfad(f"{ordner}/{orte.name(name)}{datei.suffix}")
            await wolke().ablegen(pfad, datei)
            datei.unlink(missing_ok=True)
            neu.append(pfad)
        _schritt_anlegen(self.schluessel, was, {"neu": neu})
        await self._alte_schritte_raeumen()
        return len(neu)

    async def _stuecke_uebernehmen(self, stuecke: list[Stueck], was: str, zeiten_bleiben: bool = False) -> int:
        stamm = PurePosixPath(self.kennung).stem
        # eigener Name, sonst nummeriert nach dem Original (der vorgeschlagene Name ist der des Originals selbst)
        eigen = lambda t: bool(t) and not t.startswith("Teil ") and t != stamm
        namen = [s.titel if eigen(s.titel) else f"{stamm} {i + 1}" for i, s in enumerate(stuecke)]
        if len(stuecke) == 1 and namen[0] == f"{stamm} 1":
            namen = [f"{stamm} (geschnitten)"]
        return await self._ablegen(list(zip(namen, (s.datei for s in stuecke))), was)

    async def bearbeiten(self, was: str, bearbeitung: Bearbeitung, fortschritt: Fortschritt) -> int:
        kopie = await self.arbeitskopie()
        lokal_dir = get_arbeit_dir("bearbeiten", self._stamm)
        try:
            eingabe = shutil.copy(kopie, lokal_dir / PurePosixPath(self.kennung).name)
            [fertig] = await bearbeitung([Path(eingabe)], fortschritt)
            zusatz = "normalisiert" if was.startswith("Normalisiert") else "umgewandelt"
            return await self._ablegen([(f"{PurePosixPath(self.kennung).stem} ({zusatz})", fertig)], was)
        finally:
            shutil.rmtree(lokal_dir, ignore_errors=True)

    async def _zuruecknehmen(self, daten: dict) -> None:
        for pfad in daten.get("neu", []):
            await wolke().loeschen(pfad)


def gegenstand(art: str, kennung: str) -> Gegenstand:
    if art == "sitzung":
        return SitzungGegenstand(kennung)
    if art == "datei":
        return DateiGegenstand(kennung)
    raise AufnahmeFehler("Unbekannte Art", 422)
