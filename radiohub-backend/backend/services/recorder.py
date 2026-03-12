"""
RadioHub v0.2.1 - Recorder Service

Stream-Aufnahme mit FFmpeg: Stream-Copy (kein Re-Encoding),
automatische Codec-Erkennung via ffprobe, Fallback auf MP3.
Disk-Space-Guard gegen vollaufende Platte.
"""
import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..database import db_session
from ..config import get_radio_recordings_dir, get_active_recording_dir
from .config_service import config_service
from .icy_metadata import IcyMetadataLogger
from .audio_utils import probe_duration

# Minimaler freier Speicherplatz (100 MB)
MIN_FREE_DISK_MB = 100


# Codec -> Dateiendung
CODEC_EXTENSIONS = {
    "mp3": ".mp3",
    "aac": ".aac",
    "opus": ".opus",
    "vorbis": ".ogg",
    "flac": ".flac",
    "pcm_s16le": ".wav",
    "pcm_s16be": ".wav",
}

class RecordingSession:
    def __init__(self, session_id: str, station_uuid: str, station_name: str,
                 stream_url: str, bitrate: int = 0):
        self.id = session_id
        self.station_uuid = station_uuid
        self.station_name = station_name
        self.stream_url = stream_url
        self.bitrate = bitrate
        self.codec: str = ""
        self.file_format: str = ""
        self.start_time = datetime.now()
        self.process: Optional[asyncio.subprocess.Process] = None
        self.file_path: Optional[Path] = None
        self.meta_file_path: Optional[Path] = None
        self.icy_logger: Optional[IcyMetadataLogger] = None
        self.icy_task: Optional[asyncio.Task] = None

    @property
    def duration(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def file_size(self) -> int:
        if self.file_path and self.file_path.exists():
            return self.file_path.stat().st_size
        return 0


class RecorderManager:
    def __init__(self):
        self.active_session: Optional[RecordingSession] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._cleanup_stale_sessions()

    def _cleanup_stale_sessions(self):
        """Beim Start: Verwaiste 'recording'-Sessions in DB bereinigen.
        Nach Server-Neustart existiert kein FFmpeg-Prozess mehr,
        aber die DB hat noch status='recording'."""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT id, file_path FROM sessions WHERE status = 'recording'")
            stale = c.fetchall()
            for row in stale:
                sid = row[0]
                fp = row[1]
                file_size = 0
                if fp:
                    p = Path(fp)
                    file_size = p.stat().st_size if p.exists() else 0
                # Als abgebrochen markieren mit tatsächlicher Dateigröße
                c.execute(
                    "UPDATE sessions SET status = 'interrupted', file_size = ? WHERE id = ?",
                    (file_size, sid)
                )
            if stale:
                print(f"  {len(stale)} verwaiste Recording-Session(s) bereinigt")

    async def _detect_codec(self, stream_url: str) -> tuple[str, str]:
        """Erkennt Audio-Codec via ffprobe. Gibt (codec_name, extension) zurück."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-select_streams", "a:0",
            "-timeout", "8000000",  # 8s Timeout (in Mikrosekunden)
            stream_url
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=12)
            data = json.loads(stdout)

            streams = data.get("streams", [])
            if streams:
                codec = streams[0].get("codec_name", "").lower()
                ext = CODEC_EXTENSIONS.get(codec, "")
                if ext:
                    print(f"  Codec erkannt: {codec} -> {ext}")
                    return codec, ext
                print(f"  Unbekannter Codec: {codec}, Fallback auf MP3")

        except asyncio.TimeoutError:
            print("  ffprobe Timeout, Fallback auf MP3")
        except Exception as e:
            print(f"  ffprobe Fehler: {e}, Fallback auf MP3")

        return "", ".mp3"

    async def start(self, station_uuid: str, station_name: str, stream_url: str,
                    bitrate: int = 0) -> dict:
        """Startet Aufnahme mit Stream-Copy oder Fallback-Encoding"""

        if self.active_session:
            return {
                "success": False,
                "error": "Aufnahme läuft bereits",
                "session_id": self.active_session.id
            }

        # Disk-Space prüfen
        rec_dir = get_radio_recordings_dir()
        try:
            stat = shutil.disk_usage(str(rec_dir))
            free_mb = stat.free / (1024 * 1024)
            if free_mb < MIN_FREE_DISK_MB:
                return {"success": False,
                        "error": f"Zu wenig Speicherplatz (min. {MIN_FREE_DISK_MB} MB)"}
        except Exception:
            pass  # Im Zweifel nicht blockieren

        # Codec erkennen
        codec, ext = await self._detect_codec(stream_url)

        # Aktiven Aufnahmeordner bestimmen
        active_dir, folder_id = get_active_recording_dir()

        # Session erstellen
        session_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in station_name)[:50]
        filename = f"{session_id}_{safe_name}{ext}"
        file_path = active_dir / filename

        session = RecordingSession(
            session_id=session_id,
            station_uuid=station_uuid,
            station_name=station_name,
            stream_url=stream_url,
            bitrate=bitrate
        )
        session.file_path = file_path
        session.codec = codec
        session.file_format = ext

        # FFmpeg-Kommando bauen
        if codec:
            # Stream-Copy: kein Re-Encoding, originale Qualität
            cmd = [
                "ffmpeg", "-y",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-i", stream_url,
                "-c:a", "copy",
                str(file_path)
            ]
        else:
            # Fallback: Re-Encoding zu MP3
            configured_bitrate = config_service.get("recording_bitrate", 192)
            br = f"{bitrate}k" if bitrate > 0 else f"{configured_bitrate}k"
            cmd = [
                "ffmpeg", "-y",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-i", stream_url,
                "-c:a", "libmp3lame",
                "-b:a", br,
                str(file_path)
            ]

        try:
            session.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            self.active_session = session

            # Monitor-Task für Prozess-Überwachung
            self._monitor_task = asyncio.create_task(self._monitor_process(session))

            # ICY-Metadata-Logger starten (parallel, optional)
            meta_path = file_path.with_suffix(".meta.json")
            session.meta_file_path = meta_path
            session.icy_logger = IcyMetadataLogger()
            session.icy_task = asyncio.create_task(
                session.icy_logger.run(stream_url, meta_path)
            )

            # In DB speichern
            with db_session() as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO sessions
                    (id, station_uuid, station_name, stream_url, bitrate,
                     start_time, file_path, status, codec, file_format, meta_file_path, folder_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (session_id, station_uuid, station_name, stream_url, bitrate,
                     session.start_time.isoformat(), str(file_path), "recording",
                     codec, ext, str(meta_path), folder_id))

            mode = "Stream-Copy" if codec else "MP3-Encoding"
            print(f"REC gestartet: {session_id} ({mode}, {codec or 'fallback'})")
            return {
                "success": True,
                "session_id": session_id,
                "codec": codec or "mp3",
                "mode": "copy" if codec else "encode"
            }

        except Exception as e:
            print(f"REC fehlgeschlagen: {e}")
            return {"success": False, "error": str(e)}

    async def _monitor_process(self, session: RecordingSession):
        """Überwacht FFmpeg-Prozess auf unerwartetes Ende"""
        if not session.process:
            return

        try:
            returncode = await session.process.wait()

            # Nur reagieren wenn Session noch aktiv (nicht manuell gestoppt)
            if self.active_session and self.active_session.id == session.id:
                if returncode != 0:
                    stderr = b""
                    if session.process.stderr:
                        stderr = await session.process.stderr.read()
                    err_msg = stderr.decode("utf-8", errors="replace")[-500:]
                    print(f"REC abgebrochen: {session.id} (exit {returncode})")
                    if err_msg.strip():
                        print(f"  FFmpeg: {err_msg.strip()}")

                    # Session als fehlgeschlagen markieren
                    self._finalize_session(session, "failed")
                else:
                    # Sauberes Ende (z.B. Stream endet)
                    print(f"REC Stream beendet: {session.id}")
                    self._finalize_session(session, "completed")

        except asyncio.CancelledError:
            pass

    def _finalize_session(self, session: RecordingSession, status: str,
                          real_duration: float = 0):
        """Finalisiert Session in DB"""
        end_time = datetime.now()
        duration = real_duration if real_duration > 0 else session.duration
        file_size = session.file_size

        with db_session() as conn:
            c = conn.cursor()
            c.execute('''UPDATE sessions SET
                end_time = ?, duration = ?, file_size = ?, status = ?
                WHERE id = ?''',
                (end_time.isoformat(), duration, file_size, status, session.id))

        if self.active_session and self.active_session.id == session.id:
            self.active_session = None

    async def stop(self) -> dict:
        """Stoppt aktive Aufnahme"""

        if not self.active_session:
            return {"success": False, "error": "Keine aktive Aufnahme"}

        session = self.active_session

        # Monitor-Task abbrechen
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # ICY-Logger stoppen
        if session.icy_logger:
            session.icy_logger.stop()
        if session.icy_task and not session.icy_task.done():
            session.icy_task.cancel()
            try:
                await session.icy_task
            except asyncio.CancelledError:
                pass

        # FFmpeg sauber stoppen (SIGTERM -> warten -> SIGKILL)
        if session.process and session.process.returncode is None:
            session.process.terminate()
            try:
                await asyncio.wait_for(session.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                session.process.kill()
                await session.process.wait()

        # Echte Audio-Dauer per ffprobe ermitteln
        real_duration = await probe_duration(session.file_path)
        duration = real_duration if real_duration > 0 else session.duration
        file_size = session.file_size
        self._finalize_session(session, "completed", real_duration=real_duration)

        print(f"REC gestoppt: {session.id} ({duration:.0f}s, {file_size/1024/1024:.1f}MB)")

        meta_count = session.icy_logger.entry_count if session.icy_logger else 0

        result = {
            "success": True,
            "session_id": session.id,
            "duration": duration,
            "file_size": file_size,
            "file_path": str(session.file_path),
            "codec": session.codec or "mp3",
            "file_format": session.file_format,
            "meta_count": meta_count
        }

        # Segment-Split wenn Metadata vorhanden
        if session.meta_file_path and session.meta_file_path.exists() and meta_count > 0:
            from .segment_splitter import splitter
            try:
                segments = await splitter.split_session(
                    session.id, session.file_path, session.meta_file_path,
                    duration, session.file_format
                )
                if segments:
                    result["segments"] = len(segments)
            except Exception as e:
                print(f"  Split-Fehler: {e}")

        return result

    def get_status(self) -> dict:
        """Aktueller Aufnahme-Status"""

        if not self.active_session:
            return {"recording": False}

        session = self.active_session

        # Prüfen ob FFmpeg noch läuft
        alive = session.process and session.process.returncode is None

        if not alive:
            # FFmpeg ist gestorben -- Session bereinigen
            self._finalize_session(session, "interrupted")
            return {"recording": False}

        status = {
            "recording": True,
            "session_id": session.id,
            "station_name": session.station_name,
            "station_uuid": session.station_uuid,
            "duration": session.duration,
            "file_size": session.file_size,
            "codec": session.codec or "mp3",
            "file_format": session.file_format
        }

        # ICY-Daten mitliefern wenn Logger läuft
        if session.icy_logger and session.icy_logger.entries:
            status["icy_title"] = session.icy_logger.entries[-1].get("title", "")
            status["icy_count"] = session.icy_logger.entry_count
            status["icy_entries"] = [
                {"title": e.get("title", ""), "t": e.get("t", 0)}
                for e in session.icy_logger.entries
            ]

        return status

    def get_sessions(self, limit: int = 50) -> list:
        """Alle Sessions aus DB. Bereinigt verwaiste Einträge (Datei fehlt)."""

        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT s.*, COUNT(seg.id) as segment_count
                FROM sessions s
                LEFT JOIN segments seg ON seg.session_id = s.id
                GROUP BY s.id
                ORDER BY s.start_time DESC LIMIT ?''', (limit,))
            rows = [dict(row) for row in c.fetchall()]

        # Verwaiste Sessions entfernen (Datei fehlt, nicht aktiv)
        orphans = []
        valid = []
        active_id = self.active_session.id if self.active_session else None
        # HLS-Recorder hat eigene active_session -- nicht als verwaist markieren
        from .hls_recorder import hls_recorder
        hls_active_id = hls_recorder.active_session.id if hls_recorder.active_session else None
        for row in rows:
            if row.get("status") == "recording":
                if row["id"] == active_id or row["id"] == hls_active_id:
                    valid.append(row)
                else:
                    # Verwaiste recording-Session: Prozess existiert nicht mehr
                    row["status"] = "interrupted"
                    with db_session() as conn2:
                        conn2.cursor().execute(
                            "UPDATE sessions SET status = 'interrupted' WHERE id = ?",
                            (row["id"],))
                    valid.append(row)
                continue
            fp = row.get("file_path")
            if fp:
                p = Path(fp)
                # Datei oder Verzeichnis (Segmente) muss existieren
                if not p.exists():
                    orphans.append(row)
                else:
                    valid.append(row)
            else:
                valid.append(row)

        if orphans:
            with db_session() as conn:
                c = conn.cursor()
                for orphan in orphans:
                    c.execute("DELETE FROM sessions WHERE id = ?", (orphan["id"],))
                    meta = orphan.get("meta_file_path")
                    if meta:
                        mp = Path(meta)
                        if mp.exists():
                            mp.unlink()
            print(f"  {len(orphans)} verwaiste Session(s) bereinigt")

        return valid

    def get_session(self, session_id: str) -> Optional[dict]:
        """Einzelne Session"""

        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def delete_session(self, session_id: str) -> bool:
        """Session und Datei/Segmente löschen"""

        # Aktive Session kann nicht gelöscht werden
        if self.active_session and self.active_session.id == session_id:
            return False

        session = self.get_session(session_id)
        if not session:
            return False

        # Audio-Datei oder Session-Verzeichnis löschen
        if session.get("file_path"):
            file_path = Path(session["file_path"])
            parent_dir = file_path.parent if file_path.is_file() else file_path.parent
            if file_path.is_dir():
                # Segmente: Verzeichnis mit Inhalt löschen
                for f in file_path.iterdir():
                    if f.is_file():
                        f.unlink()
                try:
                    file_path.rmdir()
                except Exception:
                    pass
                parent_dir = file_path.parent
            elif file_path.is_file():
                parent_dir = file_path.parent
                file_path.unlink()

            # Verwaiste Cache-Dateien (.peaks) zum Session-Prefix aufräumen
            session_prefix = file_path.stem  # z.B. "rec_20260312_184024_..."
            if parent_dir.exists():
                for cache_file in parent_dir.glob(f"{session_prefix}*"):
                    if cache_file.suffix in (".peaks", ".tmp") and cache_file.is_file():
                        cache_file.unlink(missing_ok=True)

        # Meta-Datei löschen
        if session.get("meta_file_path"):
            meta_path = Path(session["meta_file_path"])
            if meta_path.exists():
                meta_path.unlink()

        # DB-Eintrag löschen (CASCADE löscht auch segments)
        with db_session() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

        return True


# Singleton
rec_manager = RecorderManager()
