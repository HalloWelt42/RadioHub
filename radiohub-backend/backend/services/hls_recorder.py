"""
RadioHub v0.2.4 - HLS Recorder Service

Aufnahme aus dem HLS-Buffer mit konfigurierbarem Lookback.
Kopiert .ts Segmente, konkateniert per ffmpeg Stream-Copy zu .aac.
Nutzt ICY-Metadata aus dem HLS-Buffer fuer Segment-Split.

Edge-Case-Haertung:
- Stale-Session-Cleanup bei Server-Neustart
- Auto-Finalisierung wenn HLS-Buffer waehrend Aufnahme stirbt
- Disk-Space-Guard vor Start und waehrend Aufnahme
"""
import asyncio
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..database import db_session
from ..config import get_radio_recordings_dir, get_active_recording_dir
from .hls_buffer import hls_buffer
from .recorder import rec_manager

# Minimaler freier Speicherplatz (100 MB)
MIN_FREE_DISK_MB = 100


class HLSRecSession:
    """Aktive HLS-REC Session."""

    def __init__(self, session_id: str, station_uuid: str, station_name: str,
                 stream_url: str, lookback_seconds: int):
        self.id = session_id
        self.station_uuid = station_uuid
        self.station_name = station_name
        self.stream_url = stream_url
        self.lookback_seconds = lookback_seconds
        self.start_time = datetime.now()
        self.ts_dir: Optional[Path] = None
        self.collected_segments: list[int] = []
        self.start_segment: int = 0
        self.icy_start_index: int = 0  # Index in ICY-Entries bei REC-Start

    @property
    def duration(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def total_seconds(self) -> float:
        """Geschaetzte Gesamtdauer inkl. Lookback (1 Segment = 1 Sekunde)."""
        return float(len(self.collected_segments))


def _check_disk_space(path: Path) -> bool:
    """Prueft ob genug Speicherplatz vorhanden ist."""
    try:
        stat = shutil.disk_usage(str(path))
        free_mb = stat.free / (1024 * 1024)
        return free_mb >= MIN_FREE_DISK_MB
    except Exception:
        return True  # Im Zweifel nicht blockieren


class HLSRecorderService:
    """Aufnahme aus dem HLS-Buffer mit Lookback."""

    def __init__(self):
        self.active_session: Optional[HLSRecSession] = None
        self._collector_task: Optional[asyncio.Task] = None
        self._stopping = False  # Guard gegen doppeltes stop()
        self._cleanup_stale_sessions()

    def _cleanup_stale_sessions(self):
        """Beim Start: Verwaiste HLS-REC-Sessions bereinigen.

        Nach Server-Neustart existiert kein Collector-Task mehr,
        aber die DB hat noch status='recording' mit rec_type='hls-rec'.
        Ausserdem .ts Verzeichnisse von abgebrochenen Sessions aufraeumen.
        """
        with db_session() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, file_path FROM sessions "
                "WHERE status = 'recording' AND rec_type = 'hls-rec'"
            )
            stale = c.fetchall()
            for row in stale:
                sid = row[0]
                fp = row[1]
                file_size = 0
                if fp:
                    p = Path(fp)
                    # HLS-REC speichert Session-Dir als file_path waehrend Aufnahme
                    if p.is_dir():
                        # .ts Verzeichnis aufraeumen
                        ts_dir = p / "ts"
                        if ts_dir.exists():
                            shutil.rmtree(ts_dir, ignore_errors=True)
                    elif p.is_file():
                        file_size = p.stat().st_size
                c.execute(
                    "UPDATE sessions SET status = 'interrupted', file_size = ? "
                    "WHERE id = ?",
                    (file_size, sid)
                )
            if stale:
                print(f"  {len(stale)} verwaiste HLS-REC-Session(s) bereinigt")

    async def start(self, lookback_seconds: int = 300) -> dict:
        """Startet HLS-REC.

        1. Prueft ob HLS-Buffer aktiv und keine andere Aufnahme laeuft
        2. Kopiert Lookback-Segmente aus dem Buffer
        3. Startet Collector-Task fuer neue Segmente
        """
        # Guards
        if not hls_buffer.is_active():
            return {"success": False, "error": "HLS-Buffer nicht aktiv"}

        if self.active_session:
            return {"success": False, "error": "HLS-REC laeuft bereits",
                    "session_id": self.active_session.id}

        if rec_manager.active_session:
            return {"success": False, "error": "Direkt-Aufnahme laeuft bereits"}

        # Aktiven Aufnahmeordner bestimmen
        active_dir, folder_id = get_active_recording_dir()

        # Disk-Space pruefen
        if not _check_disk_space(active_dir):
            return {"success": False,
                    "error": f"Zu wenig Speicherplatz (min. {MIN_FREE_DISK_MB} MB)"}

        # HLS-Status holen
        hls_status = hls_buffer.get_status()
        if not hls_status.get("active"):
            return {"success": False, "error": "HLS-Buffer nicht aktiv"}

        first_seg = hls_status.get("first_segment")
        last_seg = hls_status.get("last_segment")
        if first_seg is None or last_seg is None:
            return {"success": False, "error": "Keine HLS-Segmente verfuegbar"}

        station_uuid = hls_status.get("station_uuid", "")
        station_name = hls_status.get("station_name", "")
        stream_url = hls_buffer.session.stream_url if hls_buffer.session else ""

        # Session erstellen
        session_id = f"hlsrec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ts_dir = active_dir / session_id / "ts"
        ts_dir.mkdir(parents=True, exist_ok=True)

        session = HLSRecSession(
            session_id=session_id,
            station_uuid=station_uuid,
            station_name=station_name,
            stream_url=stream_url,
            lookback_seconds=lookback_seconds
        )
        session.ts_dir = ts_dir

        # Lookback: Segmente aus Buffer kopieren
        start_seg = max(first_seg, last_seg - lookback_seconds)
        session.start_segment = start_seg

        copied = 0
        for seg_num in range(start_seg, last_seg + 1):
            src = hls_buffer.get_segment_path(seg_num)
            if src and src.exists():
                dst = ts_dir / f"segment_{seg_num}.ts"
                shutil.copy2(str(src), str(dst))
                session.collected_segments.append(seg_num)
                copied += 1

        # ICY-Snapshot: Merke Position in ICY-Entries
        icy_entries = hls_buffer.get_icy_entries()
        session.icy_start_index = len(icy_entries)

        self.active_session = session

        # Collector-Task starten
        self._collector_task = asyncio.create_task(
            self._collect_segments(session)
        )

        # In DB speichern
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO sessions
                (id, station_uuid, station_name, stream_url, bitrate,
                 start_time, file_path, status, codec, file_format,
                 meta_file_path, rec_type, folder_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (session_id, station_uuid, station_name, stream_url,
                 hls_status.get("output_bitrate", 0),
                 session.start_time.isoformat(), str(ts_dir.parent),
                 "recording", "aac", ".aac", None, "hls-rec", folder_id))

        print(f"HLS-REC gestartet: {session_id} "
              f"(Lookback: {copied} Segmente / {lookback_seconds}s)")

        return {
            "success": True,
            "session_id": session_id,
            "lookback_segments": copied,
            "lookback_seconds": lookback_seconds
        }

    async def _collect_segments(self, session: HLSRecSession):
        """Kopiert periodisch neue HLS-Segmente in das Recording-Verzeichnis.

        Bricht automatisch ab wenn:
        - HLS-Buffer nicht mehr aktiv
        - Speicherplatz unter Minimum faellt
        """
        last_copied = max(session.collected_segments) if session.collected_segments else 0
        disk_check_counter = 0
        buffer_dead = False

        try:
            while True:
                await asyncio.sleep(0.5)

                if not hls_buffer.is_active():
                    print("  HLS-REC: Buffer gestoppt, beende Collector")
                    buffer_dead = True
                    break

                # Disk-Space alle 30 Zyklen pruefen (~15 Sekunden)
                disk_check_counter += 1
                if disk_check_counter >= 30:
                    disk_check_counter = 0
                    if not _check_disk_space(session.ts_dir):
                        print("  HLS-REC: Speicherplatz knapp, beende Collector")
                        buffer_dead = True  # Triggert Auto-Finalisierung
                        break

                status = hls_buffer.get_status()
                current_last = status.get("last_segment", 0)

                for seg_num in range(last_copied + 1, current_last + 1):
                    src = hls_buffer.get_segment_path(seg_num)
                    if src and src.exists():
                        dst = session.ts_dir / f"segment_{seg_num}.ts"
                        shutil.copy2(str(src), str(dst))
                        session.collected_segments.append(seg_num)
                        last_copied = seg_num

        except asyncio.CancelledError:
            # Finaler Sweep: letzte Segmente noch holen
            if hls_buffer.is_active():
                status = hls_buffer.get_status()
                current_last = status.get("last_segment", 0)
                for seg_num in range(last_copied + 1, current_last + 1):
                    src = hls_buffer.get_segment_path(seg_num)
                    if src and src.exists():
                        dst = session.ts_dir / f"segment_{seg_num}.ts"
                        shutil.copy2(str(src), str(dst))
                        session.collected_segments.append(seg_num)
            return

        # Buffer-Tod oder Disk-Space: Automatisch finalisieren
        if buffer_dead and self.active_session:
            print("  HLS-REC: Auto-Finalisierung nach Collector-Abbruch")
            asyncio.create_task(self._auto_finalize())

    async def stop(self) -> dict:
        """Stoppt HLS-REC und finalisiert die Aufnahme.

        1. Collector stoppen + finaler Sweep
        2. .ts Segmente konkatenieren -> .aac
        3. ICY-Metadata filtern und speichern
        4. Segment-Split ausloesen
        """
        if not self.active_session:
            return {"success": False, "error": "Keine aktive HLS-Aufnahme"}
        if self._stopping:
            return {"success": False, "error": "Stopp laeuft bereits"}
        self._stopping = True

        session = self.active_session

        # Collector stoppen
        if self._collector_task and not self._collector_task.done():
            self._collector_task.cancel()
            try:
                await self._collector_task
            except asyncio.CancelledError:
                pass

        total_segments = len(session.collected_segments)
        if total_segments == 0:
            self._cleanup(session)
            return {"success": False, "error": "Keine Segmente gesammelt"}

        # Segmente sortieren
        session.collected_segments.sort()

        # Concat-Liste schreiben
        session_dir = session.ts_dir.parent
        concat_file = session_dir / "concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for seg_num in session.collected_segments:
                ts_path = session.ts_dir / f"segment_{seg_num}.ts"
                if ts_path.exists():
                    safe_path = str(ts_path).replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

        # ffmpeg: .ts -> .aac (Stream-Copy, kein Re-Encoding)
        safe_name = "".join(
            c if c.isalnum() or c in " -_" else "_"
            for c in session.station_name
        )[:50]
        output_file = session_dir / f"{session.id}_{safe_name}.aac"

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "copy",
            str(output_file)
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="replace")[-300:]
                print(f"  HLS-REC Concat-Fehler: {err}")
                self._cleanup(session)
                return {"success": False, "error": f"Concat fehlgeschlagen: {err[:100]}"}

        except asyncio.TimeoutError:
            print("  HLS-REC Concat-Timeout")
            self._cleanup(session)
            return {"success": False, "error": "Concat Timeout"}

        # Audio-Dauer per ffprobe
        real_duration = await self._probe_duration(output_file)
        file_size = output_file.stat().st_size if output_file.exists() else 0

        # ICY-Metadata filtern und speichern
        meta_file = session_dir / f"{session.id}.meta.json"
        meta_count = self._save_icy_metadata(session, meta_file, real_duration)

        # .ts Verzeichnis + concat-Datei aufraeumen
        if concat_file.exists():
            concat_file.unlink()
        if session.ts_dir.exists():
            shutil.rmtree(session.ts_dir, ignore_errors=True)

        # DB finalisieren
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''UPDATE sessions SET
                end_time = ?, duration = ?, file_size = ?, file_path = ?,
                meta_file_path = ?, status = ?
                WHERE id = ?''',
                (datetime.now().isoformat(), real_duration, file_size,
                 str(output_file), str(meta_file) if meta_count > 0 else None,
                 "completed", session.id))

        print(f"HLS-REC gestoppt: {session.id} "
              f"({total_segments} Segmente, {real_duration:.0f}s, "
              f"{file_size / 1024 / 1024:.1f}MB, {meta_count} ICY-Eintraege)")

        result = {
            "success": True,
            "session_id": session.id,
            "duration": real_duration,
            "file_size": file_size,
            "file_path": str(output_file),
            "codec": "aac",
            "file_format": ".aac",
            "meta_count": meta_count,
            "total_segments": total_segments
        }

        # Segment-Split wenn Metadata vorhanden
        if meta_count > 0 and meta_file.exists():
            from .segment_splitter import splitter
            try:
                segments = await splitter.split_session(
                    session.id, output_file, meta_file,
                    real_duration, ".aac"
                )
                if segments:
                    result["segments"] = len(segments)
            except Exception as e:
                print(f"  HLS-REC Split-Fehler: {e}")

        self.active_session = None
        self._collector_task = None
        self._stopping = False

        return result

    def _save_icy_metadata(self, session: HLSRecSession,
                           meta_file: Path, total_duration: float) -> int:
        """Filtert ICY-Eintraege auf das Aufnahme-Zeitfenster und speichert sie."""
        all_entries = hls_buffer.get_icy_entries()
        if not all_entries:
            return 0

        # Lookback-Zeitfenster berechnen
        lookback_ms = session.lookback_seconds * 1000
        rec_elapsed_ms = int(session.duration * 1000)
        total_window_ms = lookback_ms + rec_elapsed_ms

        # Letzte ICY-Zeit als Referenz
        last_icy_t = all_entries[-1].get("t", 0)
        # Start des Aufnahme-Fensters in ICY-Zeit
        window_start_t = max(0, last_icy_t - total_window_ms)

        filtered = []
        for entry in all_entries:
            t = entry.get("t", 0)
            if t >= window_start_t:
                # Timestamp relativ zum Aufnahme-Start umrechnen
                relative_t = t - window_start_t
                filtered.append({
                    "t": relative_t,
                    "b": entry.get("b", 0),
                    "title": entry.get("title", ""),
                    "raw": entry.get("raw", "")
                })

        if not filtered:
            return 0

        # Byte-Positionen relativ machen
        if filtered[0].get("b", 0) > 0:
            base_bytes = filtered[0]["b"]
            total_bytes = all_entries[-1].get("b", 0)
            relative_total = total_bytes - base_bytes
            for entry in filtered:
                entry["b"] = entry["b"] - base_bytes
        else:
            relative_total = 0

        meta = {
            "metaint": 0,
            "total_audio_bytes": relative_total if relative_total > 0 else 0,
            "entries": filtered
        }

        try:
            meta_file.parent.mkdir(parents=True, exist_ok=True)
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  HLS-REC Meta-Speichern fehlgeschlagen: {e}")
            return 0

        return len(filtered)

    async def _probe_duration(self, file_path: Path) -> float:
        """Ermittelt Audio-Dauer per ffprobe."""
        if not file_path or not file_path.exists():
            return 0.0
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(file_path)
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            data = json.loads(stdout)
            dur = float(data.get("format", {}).get("duration", 0))
            if dur > 0:
                return dur
        except Exception as e:
            print(f"  HLS-REC ffprobe-Fehler: {e}")
        return 0.0

    def _cleanup(self, session: HLSRecSession):
        """Bereinigt bei Fehler: Session-Dir + DB-Eintrag."""
        session_dir = session.ts_dir.parent if session.ts_dir else None
        if session_dir and session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

        with db_session() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE id = ?", (session.id,))

        self.active_session = None
        self._collector_task = None
        self._stopping = False

    async def _auto_finalize(self):
        """Automatische Finalisierung wenn Collector unerwartet endet.

        Versucht die bisherigen Segmente zu retten (concat -> .aac),
        anstatt die Aufnahme zu verwerfen.
        """
        try:
            result = await self.stop()
            if result.get("success"):
                print(f"  HLS-REC Auto-Finalisierung erfolgreich: {result.get('session_id')}")
            else:
                print(f"  HLS-REC Auto-Finalisierung fehlgeschlagen: {result.get('error')}")
        except Exception as e:
            print(f"  HLS-REC Auto-Finalisierung Fehler: {e}")
            # Im schlimmsten Fall: Session aufräumen
            if self.active_session:
                self._cleanup(self.active_session)

    def get_status(self) -> dict:
        """Aktueller HLS-REC Status.

        Prueft auch ob Collector-Task noch lebt.
        """
        if not self.active_session:
            return {"recording": False}

        session = self.active_session

        # Collector-Health-Check: Task tot aber Session noch aktiv?
        collector_alive = (
            self._collector_task is not None
            and not self._collector_task.done()
        )

        status = {
            "recording": True,
            "session_id": session.id,
            "station_name": session.station_name,
            "station_uuid": session.station_uuid,
            "duration": session.duration,
            "lookback_seconds": session.lookback_seconds,
            "collected_segments": len(session.collected_segments),
            "total_seconds": session.total_seconds,
            "collector_alive": collector_alive
        }

        # ICY-Daten seit REC-Start
        icy_entries_raw = hls_buffer.get_icy_entries()
        rec_entries = icy_entries_raw[session.icy_start_index:]
        if rec_entries:
            status["icy_count"] = len(rec_entries)
            status["icy_entries"] = [
                {"title": e.get("title", ""), "t": e.get("t", 0)}
                for e in rec_entries
            ]

        return status


# Singleton
hls_recorder = HLSRecorderService()
