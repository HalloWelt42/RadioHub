"""
RadioHub v0.4.0 - Aufnahmen in der Ablage

Was mit den Dateien einer Aufnahme geschieht, an einer Stelle: Stücke ablegen, Titelliste ablegen und lesen,
Arbeitskopie zum Schneiden, Wellenform, neu schneiden, löschen (Papierkorb der Ablage), verschieben, reparieren.

Eine Aufnahme ist ein Ordner in der Ablage (sessions.file_path), darin ihre Stücke (segments.file_path), die
Titelliste (sessions.meta_file_path) und bei Bedarf die Wellenform; die Namen vergibt `ablage.orte`. Lokal liegen nur
Zwischenstände im Arbeitsordner: die laufende Aufnahme (`arbeit/aufnahmen/<id>`) und die Arbeitskopie zum Schneiden
(`arbeit/schnitt/<id>.<endung>`), die nach `ARBEITSKOPIE_HALTEN_S` ohne Nutzung verschwindet.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import time
from pathlib import Path
from typing import Optional

from ..ablage import ablage, orte
from ..ablage.port import Eintrag
from ..config import AUDIO_EXTENSIONS, get_arbeit_dir
from ..database import db_session
from .audio_utils import probe_duration
from .peaks_generator import peaks_gen
from .segment_splitter import Stueck, splitter, titel_eintraege

ARBEITSKOPIE_HALTEN_S = 6 * 3600


class AufnahmeFehler(Exception):
    """Fachlicher Fehler mit Meldung für die Oberfläche (etwa: Aufnahme läuft noch)."""

    def __init__(self, meldung: str, status: int = 400):
        super().__init__(meldung)
        self.status = status


def _prefix_umschreiben(c, tabelle: str, spalte: str, alt: str, neu: str, bedingung: str, werte: tuple) -> None:
    """Pfade unter `alt` nach `neu` umschreiben (nur echte Präfixe: der Pfad selbst oder darunter)."""
    c.execute(f"""UPDATE {tabelle} SET {spalte} = ? || substr({spalte}, ?)
                  WHERE ({spalte} = ? OR substr({spalte}, 1, ?) = ?) AND {bedingung}""",
              (neu, len(alt) + 1, alt, len(alt) + 1, alt + "/", *werte))


class Aufnahmen:

    def __init__(self) -> None:
        self._sperren: dict[str, asyncio.Lock] = {}

    def _sperre(self, session_id: str) -> asyncio.Lock:
        return self._sperren.setdefault(session_id, asyncio.Lock())

    # --- Datenbank --------------------------------------------------------------------------------------------------

    def sitzung(self, session_id: str) -> Optional[dict]:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def segmente(self, session_id: str) -> list[dict]:
        with db_session() as conn:
            rows = conn.execute("SELECT * FROM segments WHERE session_id = ? ORDER BY segment_index",
                                (session_id,)).fetchall()
            return [dict(r) for r in rows]

    def alle_segmente(self) -> list[dict]:
        with db_session() as conn:
            rows = conn.execute("SELECT * FROM segments ORDER BY session_id DESC, segment_index").fetchall()
            return [dict(r) for r in rows]

    def segment(self, segment_id: int) -> Optional[dict]:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM segments WHERE id = ?", (segment_id,)).fetchone()
            return dict(row) if row else None

    def _neu_nummerieren(self, session_id: str) -> None:
        with db_session() as conn:
            for index, seg in enumerate(self.segmente(session_id)):
                if seg["segment_index"] != index:
                    conn.execute("UPDATE segments SET segment_index = ? WHERE id = ?", (index, seg["id"]))

    def _bereit(self, session_id: str) -> dict:
        sitzung = self.sitzung(session_id)
        if not sitzung:
            raise AufnahmeFehler("Aufnahme nicht gefunden", 404)
        if sitzung.get("status") == "recording":
            raise AufnahmeFehler("Aufnahme läuft noch")
        return sitzung

    # --- Ablegen ----------------------------------------------------------------------------------------------------

    async def teil_ablegen(self, session_id: str, index: int, titel: str, start_ms: int, dauer_ms: int,
                           datei: Path) -> dict:
        """Ein fertiges Stück aus dem Arbeitsordner ablegen und eintragen; die lokale Datei ist danach weg."""
        sitzung = self.sitzung(session_id)
        if not sitzung:
            raise AufnahmeFehler("Aufnahme nicht gefunden", 404)
        pfad = orte.stueck(sitzung["file_path"], index, titel, datei.suffix)
        eintrag = await ablage().ablegen(pfad, datei)
        with db_session() as conn:
            conn.execute("""INSERT INTO segments (session_id, segment_index, title, start_ms, end_ms, duration_ms,
                            file_path, file_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                         (session_id, index, titel, start_ms, start_ms + dauer_ms, dauer_ms, pfad, eintrag.groesse))
        datei.unlink(missing_ok=True)
        return {"index": index, "path": pfad, "size": eintrag.groesse}

    async def stuecke_ablegen(self, session_id: str, stuecke: list[Stueck]) -> int:
        for index, stueck in enumerate(stuecke):
            await self.teil_ablegen(session_id, index, stueck.titel, stueck.start_ms, stueck.dauer_ms, stueck.datei)
        return len(stuecke)

    async def titelliste_ablegen(self, session_id: str, datei: Path | None) -> Optional[str]:
        """Titelliste neben die Stücke legen und eintragen (None, wenn es keine gibt)."""
        sitzung = self.sitzung(session_id)
        if not sitzung or not datei or not datei.exists():
            return None
        pfad = orte.titelliste(sitzung["file_path"])
        await ablage().ablegen(pfad, datei)
        with db_session() as conn:
            conn.execute("UPDATE sessions SET meta_file_path = ? WHERE id = ?", (pfad, session_id))
        return pfad

    async def titelliste(self, sitzung: dict) -> dict | list | None:
        pfad = sitzung.get("meta_file_path")
        if not pfad:
            return None
        try:
            return json.loads(await ablage().lesen_ganz(pfad))
        except (ValueError, OSError):
            return None

    async def rest_ablegen(self, session_id: str, arbeitsordner: Path, start_ms: int) -> int:
        """Was von einer Aufnahme noch im Arbeitsordner liegt (abgebrochene Aufnahme, Neustart), als weitere Stücke
        ablegen; danach ist der Arbeitsordner weg. Liefert die Zahl der abgelegten Stücke."""
        if not arbeitsordner.exists():
            return 0
        abgelegt = 0
        index = len(self.segmente(session_id))
        for datei in sorted(arbeitsordner.iterdir()):
            if datei.suffix.lower() not in AUDIO_EXTENSIONS or datei.stat().st_size == 0:
                continue
            dauer_ms = int(await probe_duration(datei) * 1000)
            if dauer_ms <= 0:
                continue
            await self.teil_ablegen(session_id, index, f"Teil {index + 1}", start_ms, dauer_ms, datei)
            index += 1
            start_ms += dauer_ms
            abgelegt += 1
        titel = arbeitsordner / orte.TITELLISTE
        if titel.exists():
            await self.titelliste_ablegen(session_id, titel)
        shutil.rmtree(arbeitsordner, ignore_errors=True)
        return abgelegt

    async def liegengebliebene_ablegen(self) -> int:
        """Beim Start: Arbeitsordner von Aufnahmen, die ein Neustart unterbrochen hat, nachträglich ablegen."""
        wurzel = get_arbeit_dir("aufnahmen")
        gesamt = 0
        for ordner in sorted(p for p in wurzel.iterdir() if p.is_dir()):
            sitzung = self.sitzung(ordner.name)
            if not sitzung or sitzung.get("status") == "recording":
                continue  # unbekannt oder läuft gerade
            try:
                start_ms = sum(s["duration_ms"] or 0 for s in self.segmente(ordner.name))
                gesamt += await self.rest_ablegen(ordner.name, ordner, start_ms)
                dauer = sum(s["duration_ms"] or 0 for s in self.segmente(ordner.name)) / 1000.0
                with db_session() as conn:
                    conn.execute("UPDATE sessions SET duration = MAX(duration, ?), file_size = ? WHERE id = ?",
                                 (dauer, self._groesse(ordner.name), ordner.name))
            except Exception as f:  # die nächste Aufnahme soll trotzdem drankommen
                print(f"  Ablage: Aufnahme {ordner.name} nicht nachgeholt: {f}")
        return gesamt

    def _groesse(self, session_id: str) -> int:
        return sum(s["file_size"] or 0 for s in self.segmente(session_id))

    # --- Arbeitskopie und Wellenform --------------------------------------------------------------------------------

    def _kopie_pfad(self, session_id: str, endung: str) -> Path:
        return get_arbeit_dir("schnitt") / f"{session_id}{endung}"

    def _vorhandene_kopie(self, session_id: str) -> Optional[Path]:
        for datei in get_arbeit_dir("schnitt").glob(f"{session_id}.*"):
            if datei.suffix.lower() in AUDIO_EXTENSIONS and datei.stat().st_size > 0:
                return datei
        return None

    async def arbeitskopie(self, session_id: str) -> Path:
        """Die ganze Aufnahme als eine lokale Datei (Stücke zusammengefügt), für Schnitt, Wiedergabe im Schnitt und
        Wellenform. Bleibt liegen, solange damit gearbeitet wird."""
        self._bereit(session_id)
        async with self._sperre(session_id):
            vorhanden = self._vorhandene_kopie(session_id)
            if vorhanden:
                vorhanden.touch()
                return vorhanden
            self.aufraeumen()
            segmente = self.segmente(session_id)
            if not segmente:
                raise AufnahmeFehler("Keine Stücke vorhanden", 404)
            endung = Path(segmente[0]["file_path"]).suffix.lower()
            ziel = self._kopie_pfad(session_id, endung)
            teile_dir = get_arbeit_dir("schnitt", f"{session_id}_teile")
            try:
                teile = [await ablage().herunterladen(s["file_path"], teile_dir / f"{i:03d}{endung}")
                         for i, s in enumerate(segmente)]
                if len(teile) == 1:
                    teile[0].replace(ziel)
                elif not await splitter.zusammenfuegen(teile, ziel):
                    raise AufnahmeFehler("Zusammenfügen fehlgeschlagen", 500)
            finally:
                shutil.rmtree(teile_dir, ignore_errors=True)
            return ziel

    def verwerfen(self, session_id: str) -> None:
        """Lokale Arbeitskopie und ihre Wellenform weg."""
        for datei in get_arbeit_dir("schnitt").glob(f"{session_id}.*"):
            datei.unlink(missing_ok=True)

    def aufraeumen(self, halten_s: float = ARBEITSKOPIE_HALTEN_S) -> int:
        """Arbeitskopien, mit denen länger nicht gearbeitet wurde, löschen."""
        grenze = time.time() - halten_s
        weg = 0
        for datei in get_arbeit_dir("schnitt").iterdir():
            if datei.is_file() and datei.stat().st_mtime < grenze:
                datei.unlink(missing_ok=True)
                weg += 1
        return weg

    async def _veraendert(self, sitzung: dict) -> None:
        """Der Ton der Aufnahme hat sich geändert: Arbeitskopie und Wellenform gelten nicht mehr."""
        self.verwerfen(sitzung["id"])
        await ablage().loeschen(orte.wellenform(sitzung["file_path"]))

    async def wellenform(self, session_id: str) -> Eintrag:
        """Wellenform der Aufnahme in der Ablage; entsteht beim ersten Bedarf aus der Arbeitskopie."""
        sitzung = self._bereit(session_id)
        pfad = orte.wellenform(sitzung["file_path"])
        async with self._sperre(f"{session_id}:wellenform"):  # der Cutter fragt mehrere Abschnitte zugleich
            vorhanden = await ablage().eintrag(pfad)
            if vorhanden and vorhanden.groesse > 0:
                return vorhanden
            kopie = await self.arbeitskopie(session_id)
            peaks = await peaks_gen.generate_peaks(kopie, force=True)
            if not peaks:
                raise AufnahmeFehler("Wellenform konnte nicht berechnet werden", 500)
            try:
                return await ablage().ablegen(pfad, peaks)
            finally:
                peaks.unlink(missing_ok=True)

    async def wellenform_vorhanden(self, session_id: str) -> Optional[Eintrag]:
        sitzung = self._bereit(session_id)
        eintrag = await ablage().eintrag(orte.wellenform(sitzung["file_path"]))
        return eintrag if eintrag and eintrag.groesse > 0 else None

    # --- Schneiden --------------------------------------------------------------------------------------------------

    async def _ersetzen(self, sitzung: dict, stuecke: list[Stueck]) -> int:
        """Neue Stücke an die Stelle der alten: gleiche Namen werden neue Versionen, übrige alte gehen in den
        Papierkorb. Erst ablegen, dann aufräumen; so geht nichts verloren, wenn das Ablegen abbricht."""
        session_id, ordner = sitzung["id"], sitzung["file_path"]
        alte = self.segmente(session_id)
        neue: list[tuple[int, Stueck, str, int]] = []
        for index, stueck in enumerate(stuecke):
            pfad = orte.stueck(ordner, index, stueck.titel, stueck.datei.suffix)
            eintrag = await ablage().ablegen(pfad, stueck.datei)
            stueck.datei.unlink(missing_ok=True)
            neue.append((index, stueck, pfad, eintrag.groesse))
        neue_pfade = {pfad for _, _, pfad, _ in neue}
        for alt in alte:
            if alt["file_path"] not in neue_pfade:
                await ablage().loeschen(alt["file_path"])
        with db_session() as conn:
            conn.execute("DELETE FROM segments WHERE session_id = ?", (session_id,))
            for index, stueck, pfad, groesse in neue:
                conn.execute("""INSERT INTO segments (session_id, segment_index, title, start_ms, end_ms, duration_ms,
                                file_path, file_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                             (session_id, index, stueck.titel, stueck.start_ms, stueck.end_ms, stueck.dauer_ms,
                              pfad, groesse))
            conn.execute("UPDATE sessions SET file_size = ? WHERE id = ?",
                         (sum(g for _, _, _, g in neue), session_id))
        return len(neue)

    def _endung(self, sitzung: dict, kopie: Path) -> str:
        return kopie.suffix or sitzung.get("file_format") or ".mp3"

    async def neu_schneiden(self, session_id: str, schnittpunkte: list[float], trim_start: bool = False,
                            trim_end: bool = False) -> dict:
        """Schnitt aus dem Schnittplatz: an den Zeitpunkten teilen, auf Wunsch Anfang und Ende verwerfen."""
        sitzung = self._bereit(session_id)
        if not schnittpunkte:
            raise AufnahmeFehler("Keine Schnittpunkte angegeben")
        kopie = await self.arbeitskopie(session_id)
        titel = titel_eintraege(await self.titelliste(sitzung))
        dauer = await probe_duration(kopie) or sitzung.get("duration") or 0
        ziel_dir = get_arbeit_dir("schnitt", f"{session_id}_neu")
        try:
            stuecke = await splitter.an_zeiten(kopie, schnittpunkte, dauer, self._endung(sitzung, kopie), ziel_dir,
                                               titel)
            if not stuecke:
                raise AufnahmeFehler("Schnitt fehlgeschlagen", 500)
            weg = 0
            if trim_end and len(stuecke) > 1:
                stuecke.pop().datei.unlink(missing_ok=True)
                weg += 1
            if trim_start and len(stuecke) > 1:
                stuecke.pop(0).datei.unlink(missing_ok=True)
                weg += 1
            anzahl = await self._ersetzen(sitzung, stuecke)
        finally:
            shutil.rmtree(ziel_dir, ignore_errors=True)
        if weg:
            await self._veraendert(sitzung)
        return {"segments": anzahl, "trimmed": weg}

    async def nach_titeln_teilen(self, session_id: str) -> int:
        """Nachträglich an den Titelwechseln der Titelliste teilen (nur eine noch ungeteilte Aufnahme)."""
        sitzung = self._bereit(session_id)
        vorhanden = self.segmente(session_id)
        if len(vorhanden) > 1:
            raise AufnahmeFehler(f"Aufnahme hat bereits {len(vorhanden)} Stücke")
        titelliste = await self.titelliste(sitzung)
        if not titel_eintraege(titelliste):
            raise AufnahmeFehler("Keine Titelliste vorhanden")
        kopie = await self.arbeitskopie(session_id)
        dauer = await probe_duration(kopie) or sitzung.get("duration") or 0
        ziel_dir = get_arbeit_dir("schnitt", f"{session_id}_neu")
        try:
            stuecke = await splitter.nach_titelliste(kopie, titelliste, dauer, self._endung(sitzung, kopie), ziel_dir)
            if not stuecke:
                raise AufnahmeFehler("Teilen fehlgeschlagen", 500)
            return await self._ersetzen(sitzung, stuecke)
        finally:
            shutil.rmtree(ziel_dir, ignore_errors=True)

    async def stuecke_bearbeiten(self, session_id: str, segment_ids: list[int] | None, bearbeitung) -> list[dict]:
        """Stücke einzeln bearbeiten (Normalisieren, Umwandeln): Arbeitskopie holen, `bearbeitung(lokale_pfade)` gibt
        die fertigen Dateien zurück, die als neue Version (gleicher Name) oder neue Datei (andere Endung, die alte geht
        in den Papierkorb) zurückgehen."""
        sitzung = self._bereit(session_id)
        segmente = [s for s in self.segmente(session_id) if segment_ids is None or s["id"] in segment_ids]
        if not segmente:
            raise AufnahmeFehler("Keine Stücke gefunden", 404)
        ordner = get_arbeit_dir("bearbeiten", session_id)
        try:
            lokal = [await ablage().herunterladen(s["file_path"], ordner / Path(s["file_path"]).name)
                     for s in segmente]
            fertig = await bearbeitung(lokal)
            ergebnis = []
            for seg, datei in zip(segmente, fertig):
                alt = seg["file_path"]
                neu = str(Path(alt).with_suffix(datei.suffix)) if datei.suffix != Path(alt).suffix else alt
                eintrag = await ablage().ablegen(neu, datei)
                if neu != alt:
                    await ablage().loeschen(alt)
                with db_session() as conn:
                    conn.execute("UPDATE segments SET file_path = ?, file_size = ? WHERE id = ?",
                                 (neu, eintrag.groesse, seg["id"]))
                ergebnis.append({"id": seg["id"], "path": neu, "size": eintrag.groesse})
            with db_session() as conn:
                conn.execute("UPDATE sessions SET file_size = ? WHERE id = ?", (self._groesse(session_id), session_id))
        finally:
            shutil.rmtree(ordner, ignore_errors=True)
        await self._veraendert(sitzung)
        return ergebnis

    # --- Löschen, Reparieren ----------------------------------------------------------------------------------------

    async def sitzung_loeschen(self, session_id: str) -> bool:
        """Aufnahme in den Papierkorb der Ablage (Ordner mit Stücken, Titelliste, Wellenform) und austragen."""
        sitzung = self.sitzung(session_id)
        if not sitzung:
            return False
        if sitzung.get("file_path"):
            await ablage().loeschen(sitzung["file_path"])
        meta = sitzung.get("meta_file_path")
        if meta and not meta.startswith(f"{sitzung.get('file_path')}/"):
            await ablage().loeschen(meta)
        self.verwerfen(session_id)
        with db_session() as conn:
            conn.execute("DELETE FROM segments WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return True

    async def segment_loeschen(self, session_id: str, segment_id: int) -> bool:
        """Ein Stück in den Papierkorb; war es das letzte, geht die ganze Aufnahme."""
        segment = self.segment(segment_id)
        if not segment or segment["session_id"] != session_id:
            return False
        await ablage().loeschen(segment["file_path"])
        with db_session() as conn:
            conn.execute("DELETE FROM segments WHERE id = ?", (segment_id,))
        if self.segmente(session_id):
            self._neu_nummerieren(session_id)
            with db_session() as conn:
                conn.execute("UPDATE sessions SET file_size = ? WHERE id = ?", (self._groesse(session_id), session_id))
            sitzung = self.sitzung(session_id)
            if sitzung:
                await self._veraendert(sitzung)
        else:
            await self.sitzung_loeschen(session_id)
        return True

    async def reparieren(self, session_id: str) -> dict:
        """Einträge von Stücken, die in der Ablage fehlen, austragen (nur auf Anfrage, nie beim Listen)."""
        segmente = self.segmente(session_id)
        entfernt = []
        for seg in segmente:
            eintrag = await ablage().eintrag(seg["file_path"])
            if eintrag is None or eintrag.groesse == 0:
                entfernt.append(seg.get("title") or f"Segment {seg['segment_index']}")
                with db_session() as conn:
                    conn.execute("DELETE FROM segments WHERE id = ?", (seg["id"],))
        if entfernt:
            self._neu_nummerieren(session_id)
        return {"removed": len(entfernt), "kept": len(segmente) - len(entfernt), "removed_titles": entfernt}

    # --- Verschieben ------------------------------------------------------------------------------------------------

    async def sitzung_verschieben(self, session_id: str, ordner_name: Optional[str], folder_id: Optional[int]) -> bool:
        """Aufnahme in einen eigenen Aufnahmeordner (oder zurück zur Wurzel); True, wenn Dateien umgezogen sind."""
        sitzung = self.sitzung(session_id)
        if not sitzung:
            raise AufnahmeFehler("Aufnahme nicht gefunden", 404)
        if sitzung.get("status") == "recording":
            raise AufnahmeFehler("Aktive Aufnahme kann nicht verschoben werden")
        alt = sitzung["file_path"]
        neu = orte.aufnahmeordner(sitzung["station_name"], sitzung["start_time"], ordner_name)
        if alt != neu:
            await ablage().verschieben(alt, neu)
        with db_session() as conn:
            c = conn.cursor()
            if alt != neu:
                _prefix_umschreiben(c, "sessions", "file_path", alt, neu, "id = ?", (session_id,))
                _prefix_umschreiben(c, "sessions", "meta_file_path", alt, neu, "id = ?", (session_id,))
                _prefix_umschreiben(c, "segments", "file_path", alt, neu, "session_id = ?", (session_id,))
            c.execute("UPDATE sessions SET folder_id = ? WHERE id = ?", (folder_id, session_id))
        return alt != neu

    async def ordner_umbenennen(self, folder_id: int, alter_name: str, neuer_name: str) -> None:
        alt, neu = orte.eigener_ordner(alter_name), orte.eigener_ordner(neuer_name)
        if alt == neu:
            return
        if await ablage().eintrag(alt) is not None:
            await ablage().verschieben(alt, neu)
        with db_session() as conn:
            c = conn.cursor()
            ids = "id IN (SELECT id FROM sessions WHERE folder_id = ?)"
            _prefix_umschreiben(c, "sessions", "file_path", alt, neu, ids, (folder_id,))
            _prefix_umschreiben(c, "sessions", "meta_file_path", alt, neu, ids, (folder_id,))
            _prefix_umschreiben(c, "segments", "file_path", alt, neu,
                                "session_id IN (SELECT id FROM sessions WHERE folder_id = ?)", (folder_id,))

    async def ordner_loeschen(self, name: str) -> None:
        """Leeren Aufnahmeordner in den Papierkorb; mit Dateien darin bleibt er."""
        pfad = orte.eigener_ordner(name)
        dateien = [d for d in await ablage().alle_dateien(pfad) if d.name != orte.WELLENFORM]
        if dateien:
            raise AufnahmeFehler(f"Ordner enthält noch {len(dateien)} Dateien in der Ablage")
        await ablage().loeschen(pfad)


aufnahmen = Aufnahmen()
