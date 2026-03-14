"""
RadioHub v0.3.2 - Recorder Service (Segmented Recording)

Stream-Aufnahme mit FFmpeg Segment-Muxer. Ein Chunk pro Session
(segment_time 24h). Das ICY-basierte Splitting passiert beim Stop.

Ablauf:
1. FFmpeg schreibt einen Chunk via -f segment -segment_time 86400
2. Monitor: Stall-Detection + Disk-Space + Chunk-Tracking
3. Stop:
   a) Mit ICY-Metadata: Chunks concat -> Titel-Split -> fertig
   b) Ohne ICY-Metadata: Chunks als 30-Min-Segmente registrieren

Debug-Log: Zuschaltbar per Config 'recording_debug_log'.
Schreibt eine .log-Datei neben die Aufnahme mit allen wichtigen Events.
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

# Stall-Detection: Nach so vielen Pruefungen ohne Wachstum -> stalled
STALL_CHECK_INTERVAL = 30   # Sekunden zwischen Pruefungen
STALL_MAX_CHECKS = 3        # 3x keine Aenderung = 90s Stillstand -> stalled

# Segment-Aufnahme: FFmpeg schreibt Chunks statt einer Datei
# 86400s = 24h -> praktisch nur ein Chunk pro Session.
# Vorher: 1800s (30 Min) verursachte Datenverlust bei Stall/Abbruch
# weil chunk_001 nie finalisiert wurde (ERR-001).
CHUNK_DURATION = 86400

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

# Dateiendung -> FFmpeg Segment-Format
SEGMENT_FORMATS = {
    ".mp3": "mp3",
    ".aac": "adts",
    ".ogg": "ogg",
    ".opus": "ogg",
    ".flac": "flac",
    ".wav": "wav",
}

# Snapshot-Intervall: Alle N Monitor-Zyklen einen Groessen-Snapshot loggen
SNAPSHOT_INTERVAL = 10  # 10 * 30s = 5 Minuten


class SessionLogger:
    """Optionales Debug-Log pro Aufnahme-Session.

    Schreibt eine .log-Datei neben die Aufnahme. Nur aktiv wenn
    Config 'recording_debug_log' = true. Loggt keine Audio-Daten,
    nur Events mit Timestamps: Start, Chunks, Stalls, Groesse, Stop.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self._path = log_path
        self._enabled = False
        if log_path:
            self._enabled = bool(config_service.get("recording_debug_log", False))

    def log(self, msg: str):
        """Schreibt eine Zeile ins Log (wenn aktiv)."""
        if not self._enabled or not self._path:
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {msg}\n")
        except Exception:
            pass

    @property
    def enabled(self) -> bool:
        return self._enabled


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
        self.session_dir: Optional[Path] = None
        self.chunk_dir: Optional[Path] = None
        self.meta_file_path: Optional[Path] = None
        self.icy_logger: Optional[IcyMetadataLogger] = None
        self.icy_task: Optional[asyncio.Task] = None
        self.logger: Optional[SessionLogger] = None

    @property
    def duration(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def file_size(self) -> int:
        """Gesamtgroesse aller Chunks."""
        if self.chunk_dir and self.chunk_dir.exists():
            return sum(
                f.stat().st_size for f in self.chunk_dir.iterdir() if f.is_file()
            )
        return 0

    @property
    def chunk_count(self) -> int:
        """Anzahl der bisher geschriebenen Chunks."""
        if self.chunk_dir and self.chunk_dir.exists():
            return len(list(self.chunk_dir.glob("chunk_*")))
        return 0

    def get_chunks(self) -> list[Path]:
        """Sortierte Liste aller Chunk-Dateien."""
        if not self.chunk_dir or not self.chunk_dir.exists():
            return []
        return sorted(self.chunk_dir.glob("chunk_*"))


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
                    if p.is_dir():
                        # Segmentiertes Recording: Chunks zaehlen
                        chunk_dir = p / "chunks"
                        if chunk_dir.exists():
                            file_size = sum(
                                f.stat().st_size for f in chunk_dir.iterdir()
                                if f.is_file()
                            )
                    elif p.exists():
                        file_size = p.stat().st_size
                c.execute(
                    "UPDATE sessions SET status = 'interrupted', file_size = ? WHERE id = ?",
                    (file_size, sid)
                )
            if stale:
                print(f"  {len(stale)} verwaiste Recording-Session(s) bereinigt")

    async def _detect_codec(self, stream_url: str) -> tuple[str, str]:
        """Erkennt Audio-Codec via ffprobe. Gibt (codec_name, extension) zurueck."""
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
        """Startet segmentierte Aufnahme (30-Min-Chunks)."""

        if self.active_session:
            return {
                "success": False,
                "error": "Aufnahme laeuft bereits",
                "session_id": self.active_session.id
            }

        # Disk-Space pruefen
        rec_dir = get_radio_recordings_dir()
        try:
            stat = shutil.disk_usage(str(rec_dir))
            free_mb = stat.free / (1024 * 1024)
            if free_mb < MIN_FREE_DISK_MB:
                return {"success": False,
                        "error": f"Zu wenig Speicherplatz (min. {MIN_FREE_DISK_MB} MB)"}
        except Exception:
            pass

        # Codec erkennen
        codec, ext = await self._detect_codec(stream_url)

        # Aktiven Aufnahmeordner bestimmen
        active_dir, folder_id = get_active_recording_dir()

        # Session-Verzeichnis + Chunk-Unterverzeichnis anlegen
        session_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_dir = active_dir / session_id
        chunk_dir = session_dir / "chunks"
        chunk_dir.mkdir(parents=True, exist_ok=True)

        session = RecordingSession(
            session_id=session_id,
            station_uuid=station_uuid,
            station_name=station_name,
            stream_url=stream_url,
            bitrate=bitrate
        )
        session.session_dir = session_dir
        session.chunk_dir = chunk_dir
        session.codec = codec
        session.file_format = ext

        # Debug-Logger (optional, per Config zuschaltbar)
        safe_name = "".join(
            c if c.isalnum() or c in " -_" else "_" for c in station_name
        )[:50]
        log_path = active_dir / f"{session_id}_{safe_name}.log"
        session.logger = SessionLogger(log_path)

        # FFmpeg-Kommando: Segment-Muxer fuer 30-Min-Chunks
        seg_fmt = SEGMENT_FORMATS.get(ext, "mp3")
        chunk_pattern = str(chunk_dir / f"chunk_%03d{ext}")

        if codec:
            # Stream-Copy: kein Re-Encoding, originale Qualitaet
            cmd = [
                "ffmpeg", "-y",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-i", stream_url,
                "-c:a", "copy",
                "-f", "segment",
                "-segment_time", str(CHUNK_DURATION),
                "-segment_format", seg_fmt,
                "-reset_timestamps", "1",
                chunk_pattern
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
                "-f", "segment",
                "-segment_time", str(CHUNK_DURATION),
                "-segment_format", "mp3",
                "-reset_timestamps", "1",
                chunk_pattern
            ]

        try:
            session.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            self.active_session = session

            # Monitor-Task
            self._monitor_task = asyncio.create_task(self._monitor_process(session))

            # ICY-Metadata-Logger starten (parallel, optional)
            safe_name = "".join(
                c if c.isalnum() or c in " -_" else "_" for c in station_name
            )[:50]
            meta_path = active_dir / f"{session_id}_{safe_name}.meta.json"
            session.meta_file_path = meta_path
            # Ignorier-Liste aus DB laden
            ignore_rules = []
            try:
                with db_session() as conn:
                    c = conn.cursor()
                    c.execute("SELECT pattern, match_type FROM icy_title_ignore")
                    ignore_rules = [{"pattern": r[0], "match_type": r[1]} for r in c.fetchall()]
            except Exception:
                pass  # Tabelle existiert evtl. noch nicht
            session.icy_logger = IcyMetadataLogger(ignore_rules=ignore_rules)
            session.icy_task = asyncio.create_task(
                session.icy_logger.run(stream_url, meta_path)
            )

            # In DB speichern (file_path = session_dir)
            with db_session() as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO sessions
                    (id, station_uuid, station_name, stream_url, bitrate,
                     start_time, file_path, status, codec, file_format,
                     meta_file_path, folder_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (session_id, station_uuid, station_name, stream_url, bitrate,
                     session.start_time.isoformat(), str(session_dir), "recording",
                     codec, ext, str(meta_path), folder_id))

            mode = "Stream-Copy" if codec else "MP3-Encoding"
            print(f"REC gestartet: {session_id} ({mode}, {codec or 'fallback'}, "
                  f"Chunks a {CHUNK_DURATION}s)")
            session.logger.log(f"START {station_name}")
            session.logger.log(f"  Stream: {stream_url}")
            session.logger.log(f"  Codec: {codec or 'fallback->mp3'}, Mode: {mode}")
            session.logger.log(f"  Chunk-Dauer: {CHUNK_DURATION}s, Format: {ext}")
            try:
                _stat = shutil.disk_usage(str(active_dir))
                session.logger.log(f"  Disk frei: {_stat.free / 1024 / 1024:.0f}MB")
            except Exception:
                pass
            return {
                "success": True,
                "session_id": session_id,
                "codec": codec or "mp3",
                "mode": "copy" if codec else "encode"
            }

        except Exception as e:
            # Aufraumen bei Fehler
            if chunk_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            print(f"REC fehlgeschlagen: {e}")
            return {"success": False, "error": str(e)}

    async def _monitor_process(self, session: RecordingSession):
        """Ueberwacht FFmpeg-Prozess: Stall-Detection + Disk-Space.

        Stall wird erkannt wenn weder neue Chunks erscheinen noch der
        aktuelle Chunk waechst (3x 30s = 90s Stillstand).
        """
        if not session.process:
            return

        last_size = 0
        last_chunk_count = 0
        stall_count = 0
        snapshot_counter = 0
        log = session.logger

        try:
            while True:
                try:
                    returncode = await asyncio.wait_for(
                        session.process.wait(),
                        timeout=STALL_CHECK_INTERVAL
                    )
                    # FFmpeg hat sich beendet
                    if self.active_session and self.active_session.id == session.id:
                        if returncode != 0:
                            stderr = b""
                            if session.process.stderr:
                                stderr = await session.process.stderr.read()
                            err_msg = stderr.decode("utf-8", errors="replace")[-500:]
                            print(f"REC abgebrochen: {session.id} (exit {returncode})")
                            if err_msg.strip():
                                print(f"  FFmpeg: {err_msg.strip()}")
                            log.log(f"FFMPEG EXIT {returncode}: {err_msg.strip()[:200]}")
                            self._finalize_session(session, "failed")
                        else:
                            print(f"REC Stream beendet: {session.id}")
                            log.log("FFMPEG EXIT 0 (Stream beendet)")
                            self._finalize_session(session, "completed")
                    return

                except asyncio.TimeoutError:
                    pass

                if not self.active_session or self.active_session.id != session.id:
                    return

                # --- Stall-Detection: Chunks + Dateigroesse pruefen ---
                current_size = session.file_size
                current_chunks = session.chunk_count

                # Neuer Chunk? -> loggen
                if current_chunks > last_chunk_count:
                    log.log(f"CHUNK {current_chunks} "
                            f"({current_size/1024/1024:.1f}MB gesamt, "
                            f"{session.duration/60:.0f}min)")

                if current_size > last_size or current_chunks > last_chunk_count:
                    last_size = current_size
                    last_chunk_count = current_chunks
                    stall_count = 0
                else:
                    stall_count += 1
                    if stall_count == 1:
                        log.log(f"STALL? Keine Aenderung seit {STALL_CHECK_INTERVAL}s "
                                f"({current_size/1024/1024:.1f}MB, "
                                f"{current_chunks} Chunks)")
                    if stall_count >= STALL_MAX_CHECKS:
                        elapsed = stall_count * STALL_CHECK_INTERVAL
                        print(f"REC STALLED: {session.id} "
                              f"({current_chunks} Chunks, "
                              f"unverändert seit {elapsed}s, "
                              f"{current_size/1024/1024:.1f}MB)")
                        log.log(f"STALLED nach {elapsed}s -- FFmpeg wird gekillt")
                        if session.process.returncode is None:
                            session.process.kill()
                            await session.process.wait()
                        self._finalize_session(session, "stalled")
                        return

                # --- Disk-Space pruefen ---
                try:
                    rec_dir = get_radio_recordings_dir()
                    stat = shutil.disk_usage(str(rec_dir))
                    free_mb = stat.free / (1024 * 1024)
                    if free_mb < MIN_FREE_DISK_MB:
                        print(f"REC DISK FULL: {session.id} "
                              f"(nur {free_mb:.0f}MB frei)")
                        log.log(f"DISK FULL: {free_mb:.0f}MB frei -- Aufnahme beendet")
                        if session.process.returncode is None:
                            session.process.terminate()
                            try:
                                await asyncio.wait_for(
                                    session.process.wait(), timeout=5
                                )
                            except asyncio.TimeoutError:
                                session.process.kill()
                                await session.process.wait()
                        self._finalize_session(session, "disk_full")
                        return
                except Exception:
                    pass

                # --- Periodischer Snapshot (alle ~5 Minuten) ---
                snapshot_counter += 1
                if snapshot_counter >= SNAPSHOT_INTERVAL:
                    snapshot_counter = 0
                    elapsed_min = session.duration / 60
                    disk_info = ""
                    try:
                        _s = shutil.disk_usage(str(get_radio_recordings_dir()))
                        disk_info = f", Disk {_s.free/1024/1024:.0f}MB frei"
                    except Exception:
                        pass
                    log.log(f"SNAPSHOT {elapsed_min:.0f}min: "
                            f"{current_chunks} Chunks, "
                            f"{current_size/1024/1024:.1f}MB{disk_info}")

        except asyncio.CancelledError:
            pass

    def _finalize_session(self, session: RecordingSession, status: str,
                          real_duration: float = 0):
        """Finalisiert Session in DB."""
        end_time = datetime.now()
        duration = real_duration if real_duration > 0 else session.duration
        file_size = session.file_size

        # meta_file_path bereinigen: NULL setzen wenn Datei nicht existiert
        meta_path = session.meta_file_path
        if meta_path and not meta_path.exists():
            meta_path = None

        with db_session() as conn:
            c = conn.cursor()
            c.execute('''UPDATE sessions SET
                end_time = ?, duration = ?, file_size = ?, meta_file_path = ?, status = ?
                WHERE id = ?''',
                (end_time.isoformat(), duration, file_size,
                 str(meta_path) if meta_path else None, status, session.id))

        if self.active_session and self.active_session.id == session.id:
            self.active_session = None

    async def _concat_chunks(self, session: RecordingSession) -> Optional[Path]:
        """Concateniert alle Chunks zu einer Datei. Gibt Pfad zurueck oder None."""
        chunks = session.get_chunks()
        if not chunks:
            return None

        ext = session.file_format
        concat_list = session.session_dir / "concat.txt"
        output_file = session.session_dir / f"{session.id}_full{ext}"

        with open(concat_list, "w", encoding="utf-8") as f:
            for chunk in chunks:
                safe_path = str(chunk).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
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
                print(f"  REC Concat-Fehler: {err}")
                return None

        except asyncio.TimeoutError:
            print("  REC Concat-Timeout")
            return None
        except Exception as e:
            print(f"  REC Concat-Fehler: {e}")
            return None
        finally:
            if concat_list.exists():
                concat_list.unlink()

        return output_file

    async def _register_chunks_as_segments(self, session: RecordingSession,
                                           total_duration: float):
        """Registriert die Chunks als Segmente in der DB (ohne ICY = 30-Min-Teile)."""
        chunks = session.get_chunks()
        if not chunks:
            return 0

        # Segment-Verzeichnis = session_dir (Chunks raus, Segmente rein)
        ext = session.file_format
        segments = []
        cumulative_ms = 0

        for i, chunk in enumerate(chunks):
            chunk_duration = await probe_duration(chunk)
            if chunk_duration <= 0:
                chunk_duration = CHUNK_DURATION  # Fallback

            duration_ms = int(chunk_duration * 1000)
            start_ms = cumulative_ms
            end_ms = start_ms + duration_ms

            # Chunk umbenennen: chunk_000.mp3 -> 000_Teil_1.mp3
            segment_name = f"{i:03d}_Teil_{i + 1}{ext}"
            segment_path = session.session_dir / segment_name
            shutil.move(str(chunk), str(segment_path))

            segments.append({
                "session_id": session.id,
                "segment_index": i,
                "title": f"Teil {i + 1}",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": duration_ms,
                "file_path": str(segment_path),
                "file_size": segment_path.stat().st_size
            })
            cumulative_ms = end_ms

        # Chunks-Verzeichnis loeschen (jetzt leer)
        if session.chunk_dir and session.chunk_dir.exists():
            try:
                session.chunk_dir.rmdir()
            except Exception:
                pass

        # In DB speichern
        with db_session() as conn:
            c = conn.cursor()
            for seg in segments:
                c.execute('''INSERT INTO segments
                    (session_id, segment_index, title, start_ms, end_ms,
                     duration_ms, file_path, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (seg["session_id"], seg["segment_index"], seg["title"],
                     seg["start_ms"], seg["end_ms"], seg["duration_ms"],
                     seg["file_path"], seg["file_size"]))

        return len(segments)

    async def stop(self) -> dict:
        """Stoppt aktive Aufnahme. Chunks werden concat+split oder als Segmente registriert."""

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

        # FFmpeg sauber stoppen
        if session.process and session.process.returncode is None:
            session.process.terminate()
            try:
                await asyncio.wait_for(session.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                session.process.kill()
                await session.process.wait()

        chunks = session.get_chunks()
        chunk_count = len(chunks)
        meta_count = session.icy_logger.entry_count if session.icy_logger else 0
        log = session.logger

        print(f"REC gestoppt: {session.id} "
              f"({chunk_count} Chunks, {session.file_size/1024/1024:.1f}MB, "
              f"{meta_count} ICY-Eintraege)")
        log.log(f"STOP nach {session.duration/60:.1f}min")
        log.log(f"  {chunk_count} Chunks, {session.file_size/1024/1024:.1f}MB, "
                f"{meta_count} ICY-Eintraege")

        if chunk_count == 0:
            log.log("LEER: Keine Chunks geschrieben")
            self._finalize_session(session, "empty")
            return {"success": True, "session_id": session.id,
                    "duration": 0, "file_size": 0, "segments": 0}

        # --- Strategie entscheiden ---
        # Mit ICY-Metadata: Concat -> Titel-Split (praezise Schnitte)
        # Ohne ICY-Metadata: Chunks als 30-Min-Segmente registrieren
        has_icy = (meta_count > 0 and session.meta_file_path
                   and session.meta_file_path.exists())

        result = {
            "success": True,
            "session_id": session.id,
            "codec": session.codec or "mp3",
            "file_format": session.file_format,
            "meta_count": meta_count
        }

        if has_icy:
            log.log(f"STRATEGIE: Titel-Split ({meta_count} ICY-Eintraege)")
            # Chunks concatenieren -> eine Datei -> Titel-Split
            concat_file = await self._concat_chunks(session)
            if concat_file and concat_file.exists():
                real_duration = await probe_duration(concat_file)
                duration = real_duration if real_duration > 0 else session.duration
                file_size = concat_file.stat().st_size
                log.log(f"  Concat OK: {duration:.0f}s, {file_size/1024/1024:.1f}MB")

                self._finalize_session(session, "completed",
                                       real_duration=real_duration)

                # Chunk-Verzeichnis loeschen (Dateien sind jetzt in concat_file)
                if session.chunk_dir and session.chunk_dir.exists():
                    shutil.rmtree(session.chunk_dir, ignore_errors=True)

                # Titel-Split via segment_splitter
                from .segment_splitter import splitter
                try:
                    segments = await splitter.split_session(
                        session.id, concat_file, session.meta_file_path,
                        duration, session.file_format
                    )
                    if segments:
                        result["segments"] = len(segments)
                        print(f"  REC Titel-Split: {len(segments)} Segmente")
                        log.log(f"  Titel-Split: {len(segments)} Segmente")
                except Exception as e:
                    print(f"  REC Split-Fehler: {e}")
                    log.log(f"  Split-Fehler: {e}")

                result["duration"] = duration
                result["file_size"] = file_size
            else:
                # Concat fehlgeschlagen -> Fallback: Chunks als Segmente
                print("  REC Concat fehlgeschlagen, Fallback auf Chunk-Segmente")
                log.log("CONCAT FEHLGESCHLAGEN -- Fallback auf Chunk-Segmente")
                has_icy = False  # Fallthrough zu Chunk-Registrierung

        if not has_icy:
            log.log(f"STRATEGIE: Chunk-Segmente (kein ICY oder Concat-Fallback)")
            # Chunks direkt als Segmente registrieren (30-Min-Teile)
            total_duration = 0
            for chunk in chunks:
                d = await probe_duration(chunk)
                if d > 0:
                    total_duration += d

            duration = total_duration if total_duration > 0 else session.duration
            file_size = session.file_size

            self._finalize_session(session, "completed",
                                   real_duration=duration)

            seg_count = await self._register_chunks_as_segments(
                session, duration
            )
            result["segments"] = seg_count
            result["duration"] = duration
            result["file_size"] = file_size
            print(f"  REC Chunk-Segmente: {seg_count} Teile")
            log.log(f"  {seg_count} Segmente, {duration:.0f}s gesamt")

        log.log(f"FERTIG: {result.get('duration', 0):.0f}s, "
                f"{result.get('segments', 0)} Segmente")
        result["file_path"] = str(session.session_dir)
        return result

    def get_status(self) -> dict:
        """Aktueller Aufnahme-Status"""

        if not self.active_session:
            return {"recording": False}

        session = self.active_session

        # Pruefen ob FFmpeg noch laeuft
        alive = session.process and session.process.returncode is None

        if not alive:
            self._finalize_session(session, "interrupted")
            return {"recording": False}

        # Disk-Space
        free_mb = None
        try:
            rec_dir = get_radio_recordings_dir()
            stat = shutil.disk_usage(str(rec_dir))
            free_mb = round(stat.free / (1024 * 1024))
        except Exception:
            pass

        status = {
            "recording": True,
            "session_id": session.id,
            "station_name": session.station_name,
            "station_uuid": session.station_uuid,
            "duration": session.duration,
            "file_size": session.file_size,
            "codec": session.codec or "mp3",
            "file_format": session.file_format,
            "free_disk_mb": free_mb,
            "chunk_count": session.chunk_count
        }

        # ICY-Daten mitliefern wenn Logger laeuft
        if session.icy_logger and session.icy_logger.entries:
            status["icy_title"] = session.icy_logger.entries[-1].get("title", "")
            status["icy_count"] = session.icy_logger.entry_count
            status["icy_entries"] = [
                {"title": e.get("title", ""), "t": e.get("t", 0)}
                for e in session.icy_logger.entries
            ]

        return status

    def get_sessions(self, limit: int = 50) -> list:
        """Alle Sessions aus DB. Bereinigt verwaiste Eintraege (Datei fehlt)."""

        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT s.*, COUNT(seg.id) as segment_count
                FROM sessions s
                LEFT JOIN segments seg ON seg.session_id = s.id
                GROUP BY s.id
                ORDER BY s.start_time DESC LIMIT ?''', (limit,))
            rows = [dict(row) for row in c.fetchall()]

        orphans = []
        valid = []
        active_id = self.active_session.id if self.active_session else None
        from .hls_recorder import hls_recorder
        hls_active_id = hls_recorder.active_session.id if hls_recorder.active_session else None
        for row in rows:
            if row.get("status") == "recording":
                if row["id"] == active_id or row["id"] == hls_active_id:
                    valid.append(row)
                else:
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
        """Session und Datei/Segmente loeschen"""

        if self.active_session and self.active_session.id == session_id:
            return False

        session = self.get_session(session_id)
        if not session:
            return False

        # Audio-Datei oder Session-Verzeichnis loeschen
        if session.get("file_path"):
            file_path = Path(session["file_path"])
            parent_dir = file_path.parent
            if file_path.is_dir():
                shutil.rmtree(file_path, ignore_errors=True)
            elif file_path.is_file():
                file_path.unlink()

            # Verwaiste Cache-Dateien (.peaks) zum Session-Prefix aufraeumen
            session_prefix = file_path.stem
            if parent_dir.exists():
                for cache_file in parent_dir.glob(f"{session_prefix}*"):
                    if cache_file.suffix in (".peaks", ".tmp") and cache_file.is_file():
                        cache_file.unlink(missing_ok=True)

        # Meta-Datei loeschen
        if session.get("meta_file_path"):
            meta_path = Path(session["meta_file_path"])
            if meta_path.exists():
                meta_path.unlink()

        # DB-Eintrag loeschen (CASCADE loescht auch segments)
        with db_session() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

        return True


# Singleton
rec_manager = RecorderManager()
