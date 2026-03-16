"""
RadioHub v0.5.0 - Recorder Service (Live-Split)

Stream-Aufnahme mit Live-Split bei ICY-Titelwechsel.

Ablauf:
1. FFmpeg schreibt Audio in eine Einzeldatei (stdin=PIPE fuer sauberes "q")
2. ICY-Logger erkennt Titelwechsel -> Callback
3. Callback: Neuen FFmpeg starten, alten per "q" stoppen, Segment in DB
4. Stop: Letztes Segment finalisieren, kein Concat noetig
5. Fallback ohne ICY: Ein Segment pro Session

Gap-Detection: Erkennt Dropouts ab 10s (gap_start/gap_end Events).
Stall nach 60s ohne Wachstum -> FFmpeg Kill.
Events werden in Session und meta.json gespeichert.
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
STALL_CHECK_INTERVAL = 10   # Sekunden zwischen Pruefungen
STALL_MAX_CHECKS = 6        # 6x keine Aenderung = 60s Stillstand -> stalled
GAP_THRESHOLD = 1           # Ab 1x ohne Wachstum = Gap-Event (10s)

# Minimum-Segment-Dauer: Titelwechsel unter dieser Schwelle werden
# ignoriert (Titel wird aktualisiert, aber kein neues Segment).
MIN_SEGMENT_SECONDS = 5

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

# Snapshot-Intervall: Alle N Monitor-Zyklen einen Groessen-Snapshot loggen
SNAPSHOT_INTERVAL = 10  # 10 * 10s = ~100 Sekunden


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
        self.meta_file_path: Optional[Path] = None
        self.icy_logger: Optional[IcyMetadataLogger] = None
        self.icy_task: Optional[asyncio.Task] = None
        self.logger: Optional[SessionLogger] = None
        self.events: list[dict] = []  # Gap/Stall/Codec-Events

        # Live-Split Felder
        self.segment_index: int = 0
        self.current_segment_file: Optional[Path] = None
        self.current_segment_title: str = ""
        self.current_segment_start: Optional[datetime] = None
        self.live_split: bool = False  # True sobald erster ICY-Split passiert
        self._split_lock: Optional[asyncio.Lock] = None  # Initialisiert bei Start

    @property
    def duration(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def file_size(self) -> int:
        """Gesamtgroesse aller Audio-Dateien im Session-Verzeichnis."""
        audio_exts = {'.mp3', '.aac', '.ogg', '.opus', '.flac', '.wav'}
        if self.session_dir and self.session_dir.exists():
            return sum(
                f.stat().st_size for f in self.session_dir.iterdir()
                if f.is_file() and f.suffix in audio_exts
            )
        return 0

    @property
    def segment_count(self) -> int:
        """Anzahl der bisher geschriebenen Segment-Dateien."""
        if not self.session_dir or not self.session_dir.exists():
            return 0
        return len([f for f in self.session_dir.iterdir()
                    if f.is_file() and f.name.startswith("seg_")])


# FFmpeg stderr-Patterns die auf Codec-/Format-Wechsel hindeuten
CODEC_ERROR_PATTERNS = [
    "Invalid data found when processing input",
    "Could not find codec parameters",
    "Error while decoding",
    "mismatching codec",
    "Header missing",
    "codec_id mismatch",
]


class RecorderManager:
    def __init__(self):
        self.active_session: Optional[RecordingSession] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
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
                        # Session-Verzeichnis: Audio-Dateien zaehlen
                        audio_exts = {'.mp3', '.aac', '.ogg', '.opus', '.flac', '.wav'}
                        file_size = sum(
                            f.stat().st_size for f in p.iterdir()
                            if f.is_file() and f.suffix in audio_exts
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

    def _build_ffmpeg_cmd(self, session: RecordingSession,
                          output_file: Path) -> list[str]:
        """Baut FFmpeg-Kommando fuer Einzeldatei-Aufnahme (mit stdin=PIPE)."""
        if session.codec:
            return [
                "ffmpeg", "-y",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-i", session.stream_url,
                "-c:a", "copy",
                str(output_file)
            ]
        else:
            configured_bitrate = config_service.get("recording_bitrate", 192)
            br = (f"{session.bitrate}k" if session.bitrate > 0
                  else f"{configured_bitrate}k")
            return [
                "ffmpeg", "-y",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-i", session.stream_url,
                "-c:a", "libmp3lame", "-b:a", br,
                str(output_file)
            ]

    async def _start_ffmpeg(self, session: RecordingSession,
                            output_file: Path) -> asyncio.subprocess.Process:
        """Startet FFmpeg-Prozess mit stdin=PIPE fuer sauberes Stoppen."""
        cmd = self._build_ffmpeg_cmd(session, output_file)
        return await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )

    async def _stop_ffmpeg_graceful(self, process: asyncio.subprocess.Process,
                                    timeout: float = 5.0):
        """Stoppt FFmpeg sauber via stdin 'q', Fallback auf terminate/kill."""
        if process.returncode is not None:
            return
        try:
            if process.stdin:
                process.stdin.write(b"q\n")
                await process.stdin.drain()
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except (asyncio.TimeoutError, Exception):
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=3)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    async def start(self, station_uuid: str, station_name: str, stream_url: str,
                    bitrate: int = 0) -> dict:
        """Startet Aufnahme mit Live-Split bei ICY-Titelwechsel."""

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

        # Session-Verzeichnis anlegen (kein chunks/-Unterverzeichnis mehr)
        session_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_dir = active_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        session = RecordingSession(
            session_id=session_id,
            station_uuid=station_uuid,
            station_name=station_name,
            stream_url=stream_url,
            bitrate=bitrate
        )
        session.session_dir = session_dir
        session.codec = codec
        session.file_format = ext
        session._split_lock = asyncio.Lock()

        # Debug-Logger (optional, per Config zuschaltbar)
        safe_name = "".join(
            c if c.isalnum() or c in " -_" else "_" for c in station_name
        )[:50]
        log_path = active_dir / f"{session_id}_{safe_name}.log"
        session.logger = SessionLogger(log_path)

        # Erstes Segment starten
        initial_file = session_dir / f"seg_000_Teil_1{ext}"
        session.current_segment_file = initial_file
        session.current_segment_title = "Teil 1"
        session.current_segment_start = datetime.now()

        try:
            session.process = await self._start_ffmpeg(session, initial_file)
            self.active_session = session

            # Monitor-Task + Stderr-Watcher
            self._monitor_task = asyncio.create_task(self._monitor_process(session))
            self._stderr_task = asyncio.create_task(self._watch_stderr(session))

            # ICY-Metadata-Logger mit Live-Split Callback starten
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
            session.icy_logger = IcyMetadataLogger(
                ignore_rules=ignore_rules,
                on_title_change=self._on_title_change
            )
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
            print(f"REC gestartet: {session_id} ({mode}, {codec or 'fallback'}, Live-Split)")
            session.logger.log(f"START {station_name}")
            session.logger.log(f"  Stream: {stream_url}")
            session.logger.log(f"  Codec: {codec or 'fallback->mp3'}, Mode: {mode}")
            session.logger.log(f"  Live-Split aktiv, Format: {ext}")
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
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            print(f"REC fehlgeschlagen: {e}")
            return {"success": False, "error": str(e)}

    async def _watch_stderr(self, session: RecordingSession):
        """Liest FFmpeg stderr zeilenweise und erkennt Codec-Wechsel.

        Bei Codec-Fehler: Aktuelles Segment finalisieren, Codec neu erkennen,
        neuen FFmpeg starten. Nutzt dieselbe Split-Logik wie _on_title_change.
        """
        last_codec_restart = 0.0  # Cooldown gegen Restart-Loops

        try:
            while self.active_session and self.active_session.id == session.id:
                process = session.process
                if not process or not process.stderr:
                    await asyncio.sleep(1)
                    continue

                try:
                    line = await asyncio.wait_for(
                        process.stderr.readline(), timeout=10
                    )
                except asyncio.TimeoutError:
                    continue

                if not line:
                    # stderr geschlossen (Prozess beendet)
                    await asyncio.sleep(0.5)
                    continue

                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue

                # Pruefen ob stderr-Zeile auf Codec-Fehler hinweist
                is_codec_error = any(
                    p.lower() in text.lower() for p in CODEC_ERROR_PATTERNS
                )
                if not is_codec_error:
                    continue

                # Cooldown: Nicht oefter als alle 10 Sekunden neu starten
                now = asyncio.get_event_loop().time()
                if now - last_codec_restart < 10.0:
                    continue
                last_codec_restart = now

                session.logger.log(f"CODEC-FEHLER: {text[:200]}")
                print(f"  REC Codec-Fehler: {text[:100]}")

                # Event loggen
                elapsed_ms = int(session.duration * 1000)
                session.events.append({
                    "type": "codec_change",
                    "t": elapsed_ms,
                    "detail": text[:200]
                })

                # Segment-Neustart (wie bei Titelwechsel)
                if not session._split_lock:
                    continue

                async with session._split_lock:
                    old_process = session.process
                    old_file = session.current_segment_file
                    old_title = session.current_segment_title

                    # Codec neu erkennen
                    new_codec, new_ext = await self._detect_codec(session.stream_url)
                    if new_ext != session.file_format:
                        session.logger.log(
                            f"CODEC-WECHSEL: {session.codec} -> {new_codec} "
                            f"({session.file_format} -> {new_ext})")
                        session.codec = new_codec
                        session.file_format = new_ext

                    # Neues Segment
                    from .segment_splitter import _safe_filename
                    session.segment_index += 1
                    safe_title = _safe_filename(old_title or "Teil")
                    new_file = session.session_dir / (
                        f"seg_{session.segment_index:03d}_{safe_title}"
                        f"{session.file_format}")

                    try:
                        session.process = await self._start_ffmpeg(
                            session, new_file)
                    except Exception as e:
                        print(f"  REC Codec-Recovery fehlgeschlagen: {e}")
                        session.process = old_process
                        continue

                    session.current_segment_file = new_file
                    session.current_segment_start = datetime.now()
                    session.live_split = True

                    # Alten Prozess stoppen
                    await self._stop_ffmpeg_graceful(old_process)

                    # Altes Segment registrieren
                    if old_file and old_file.exists() and old_file.stat().st_size > 0:
                        dur = await probe_duration(old_file)
                        if dur > 0:
                            self._register_segment(
                                session, session.segment_index - 1,
                                old_title or f"Teil {session.segment_index}",
                                old_file, int(dur * 1000))

                    session.logger.log(
                        f"CODEC-RECOVERY: Neues Segment #{session.segment_index}")
                    print(f"  REC Codec-Recovery: Segment #{session.segment_index}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            session.logger.log(f"STDERR-WATCHER Fehler: {e}")

    async def _on_title_change(self, title: str, elapsed_ms: int,
                               audio_bytes: int):
        """ICY-Callback: Titelwechsel -> Segment-Rotation."""
        session = self.active_session
        if not session or not session.process or not session._split_lock:
            return

        async with session._split_lock:
            # Minimum-Segment-Dauer pruefen
            if session.current_segment_start:
                age = (datetime.now() - session.current_segment_start).total_seconds()
                if age < MIN_SEGMENT_SECONDS:
                    # Zu kurz -- Titel aktualisieren, aber nicht splitten
                    session.current_segment_title = title
                    session.logger.log(
                        f"SKIP Split (zu kurz: {age:.1f}s): {title}")
                    return

            old_process = session.process
            old_file = session.current_segment_file
            old_title = session.current_segment_title

            # Neues Segment vorbereiten
            from .segment_splitter import _safe_filename
            session.segment_index += 1
            safe_title = _safe_filename(title)
            ext = session.file_format
            new_file = session.session_dir / (
                f"seg_{session.segment_index:03d}_{safe_title}{ext}")

            # Neuen FFmpeg starten BEVOR alter gestoppt wird (Overlap-Strategie)
            try:
                session.process = await self._start_ffmpeg(session, new_file)
            except Exception as e:
                print(f"  REC Split-Fehler: Neuer FFmpeg fehlgeschlagen: {e}")
                session.process = old_process  # Alten behalten
                return

            session.current_segment_file = new_file
            session.current_segment_title = title
            session.current_segment_start = datetime.now()
            session.live_split = True

            # Alten FFmpeg sauber stoppen
            await self._stop_ffmpeg_graceful(old_process)

            # Altes Segment finalisieren (DB-Insert)
            if old_file and old_file.exists() and old_file.stat().st_size > 0:
                duration = await probe_duration(old_file)
                if duration > 0:
                    self._register_segment(
                        session, session.segment_index - 1,
                        old_title or f"Teil {session.segment_index}",
                        old_file, int(duration * 1000)
                    )

            session.logger.log(
                f"SPLIT #{session.segment_index}: {title}")
            print(f"  REC Split #{session.segment_index}: {title}")

    def _register_segment(self, session: RecordingSession, index: int,
                          title: str, file_path: Path, duration_ms: int):
        """Registriert ein Live-Split-Segment in der DB."""
        # Kumulative Start/End-Zeit berechnen
        cumulative_ms = self._get_cumulative_ms(session.id)
        start_ms = cumulative_ms
        end_ms = cumulative_ms + duration_ms
        file_size = file_path.stat().st_size if file_path.exists() else 0

        with db_session() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO segments
                (session_id, segment_index, title, start_ms, end_ms,
                 duration_ms, file_path, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (session.id, index, title, start_ms, end_ms,
                 duration_ms, str(file_path), file_size))

    def _get_cumulative_ms(self, session_id: str) -> int:
        """Summe aller bisherigen Segment-Dauern einer Session."""
        with db_session() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT COALESCE(SUM(duration_ms), 0) FROM segments WHERE session_id = ?",
                (session_id,))
            return c.fetchone()[0]

    async def _monitor_process(self, session: RecordingSession):
        """Ueberwacht FFmpeg-Prozess: Stall-Detection + Disk-Space.

        Prüft alle STALL_CHECK_INTERVAL Sekunden ob Daten wachsen.
        Bei Live-Split kann session.process wechseln -- wird jede Runde neu gelesen.
        """
        if not session.process:
            return

        last_size = 0
        last_seg_count = 0
        stall_count = 0
        snapshot_counter = 0
        in_gap = False  # Gap-Tracking
        log = session.logger

        try:
            while True:
                try:
                    returncode = await asyncio.wait_for(
                        session.process.wait(),
                        timeout=STALL_CHECK_INTERVAL
                    )
                    # FFmpeg hat sich beendet -- bei Live-Split ist das normal
                    # (alter Prozess endet, neuer laeuft schon)
                    if session.live_split:
                        # Pruefen ob ein neuer Prozess existiert
                        await asyncio.sleep(1)  # Kurz warten auf Split-Abschluss
                        if (session.process and
                                session.process.returncode is None):
                            continue  # Neuer FFmpeg laeuft, weiter ueberwachen
                    if self.active_session and self.active_session.id == session.id:
                        if returncode != 0:
                            print(f"REC abgebrochen: {session.id} (exit {returncode})")
                            log.log(f"FFMPEG EXIT {returncode}")
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

                # --- Stall-Detection: Segment-Count + Dateigroesse pruefen ---
                current_size = session.file_size
                current_segs = session.segment_count

                # Neues Segment? -> loggen
                if current_segs > last_seg_count:
                    log.log(f"SEG {current_segs} "
                            f"({current_size/1024/1024:.1f}MB gesamt, "
                            f"{session.duration/60:.0f}min)")

                if current_size > last_size or current_segs > last_seg_count:
                    last_size = current_size
                    last_seg_count = current_segs
                    if in_gap:
                        # Gap beendet
                        elapsed_ms = int(session.duration * 1000)
                        session.events.append({
                            "type": "gap_end",
                            "t": elapsed_ms,
                            "detail": f"Daten fliessen wieder nach {stall_count * STALL_CHECK_INTERVAL}s"
                        })
                        log.log(f"GAP ENDE nach {stall_count * STALL_CHECK_INTERVAL}s")
                        in_gap = False
                    stall_count = 0
                else:
                    stall_count += 1
                    if stall_count >= GAP_THRESHOLD and not in_gap:
                        # Gap erkannt
                        in_gap = True
                        elapsed_ms = int(session.duration * 1000)
                        session.events.append({
                            "type": "gap_start",
                            "t": elapsed_ms,
                            "detail": f"Kein Wachstum seit {stall_count * STALL_CHECK_INTERVAL}s"
                        })
                        log.log(f"GAP START: Keine Aenderung seit {STALL_CHECK_INTERVAL}s "
                                f"({current_size/1024/1024:.1f}MB, "
                                f"{current_segs} Segmente)")
                    if stall_count >= STALL_MAX_CHECKS:
                        elapsed = stall_count * STALL_CHECK_INTERVAL
                        session.events.append({
                            "type": "stall",
                            "t": int(session.duration * 1000),
                            "detail": f"Stillstand seit {elapsed}s -- FFmpeg gekillt"
                        })
                        print(f"REC STALLED: {session.id} "
                              f"({current_segs} Segmente, "
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
                            f"{current_segs} Segmente, "
                            f"{current_size/1024/1024:.1f}MB{disk_info}")

        except asyncio.CancelledError:
            pass

    def _build_quality_json(self, session: RecordingSession) -> str:
        """Aggregiert Events zu einem Quality-Summary-JSON."""
        gaps = sum(1 for e in session.events if e["type"] == "gap_start")
        codec_changes = sum(1 for e in session.events if e["type"] == "codec_change")
        stalls = sum(1 for e in session.events if e["type"] == "stall")

        # Rating: gruen/gelb/rot
        if stalls > 0:
            rating = "red"
        elif gaps > 2 or codec_changes > 1:
            rating = "yellow"
        elif gaps > 0 or codec_changes > 0:
            rating = "yellow"
        else:
            rating = "green"

        return json.dumps({
            "gaps": gaps,
            "codec_changes": codec_changes,
            "stalls": stalls,
            "rating": rating
        })

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

        # Quality-Summary aus Events berechnen
        quality_json = self._build_quality_json(session) if session.events else None

        with db_session() as conn:
            c = conn.cursor()
            c.execute('''UPDATE sessions SET
                end_time = ?, duration = ?, file_size = ?, meta_file_path = ?,
                status = ?, quality_json = ?
                WHERE id = ?''',
                (end_time.isoformat(), duration, file_size,
                 str(meta_path) if meta_path else None, status,
                 quality_json, session.id))

        # Events in meta.json ergänzen (falls vorhanden)
        if session.events and meta_path and meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["events"] = session.events
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        if self.active_session and self.active_session.id == session.id:
            self.active_session = None

    async def stop(self) -> dict:
        """Stoppt aktive Aufnahme.

        Live-Split: Letztes Segment finalisieren, Segmente sind bereits in DB.
        Fallback (kein ICY): Einzeldatei als ein Segment registrieren.
        """

        if not self.active_session:
            return {"success": False, "error": "Keine aktive Aufnahme"}

        session = self.active_session

        # Monitor-Task + Stderr-Watcher abbrechen
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        # ICY-Logger stoppen (vor FFmpeg, damit kein Callback mehr kommt)
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
            await self._stop_ffmpeg_graceful(session.process)

        meta_count = session.icy_logger.entry_count if session.icy_logger else 0
        log = session.logger
        seg_count = session.segment_count

        print(f"REC gestoppt: {session.id} "
              f"({seg_count} Segmente, {session.file_size/1024/1024:.1f}MB, "
              f"{meta_count} ICY-Eintraege, "
              f"{'live-split' if session.live_split else 'fallback'})")
        log.log(f"STOP nach {session.duration/60:.1f}min")
        log.log(f"  {seg_count} Segmente, {session.file_size/1024/1024:.1f}MB, "
                f"{meta_count} ICY-Eintraege")

        result = {
            "success": True,
            "session_id": session.id,
            "codec": session.codec or "mp3",
            "file_format": session.file_format,
            "meta_count": meta_count
        }

        if session.live_split:
            # === Live-Split-Modus ===
            # Letztes Segment finalisieren (ist noch nicht in DB)
            last_file = session.current_segment_file
            if last_file and last_file.exists() and last_file.stat().st_size > 0:
                duration = await probe_duration(last_file)
                if duration > 0:
                    self._register_segment(
                        session, session.segment_index,
                        session.current_segment_title or f"Teil {session.segment_index + 1}",
                        last_file, int(duration * 1000)
                    )

            total_duration = self._get_cumulative_ms(session.id) / 1000.0
            self._finalize_session(session, "completed",
                                   real_duration=total_duration)

            db_seg_count = self._count_segments(session.id)
            result["segments"] = db_seg_count
            result["duration"] = total_duration
            result["file_size"] = session.file_size
            result["mode"] = "live-split"
            log.log(f"LIVE-SPLIT FERTIG: {total_duration:.0f}s, {db_seg_count} Segmente")
        else:
            # === Fallback: Kein ICY-Titelwechsel erkannt ===
            # Einzeldatei als ein Segment registrieren
            seg_file = session.current_segment_file
            if seg_file and seg_file.exists() and seg_file.stat().st_size > 0:
                real_duration = await probe_duration(seg_file)
                duration = real_duration if real_duration > 0 else session.duration
                file_size = seg_file.stat().st_size

                self._finalize_session(session, "completed",
                                       real_duration=duration)

                # Als einzelnes Segment registrieren
                self._register_segment(
                    session, 0,
                    session.current_segment_title or session.station_name,
                    seg_file, int(duration * 1000)
                )

                # Wenn ICY-Metadata vorhanden -> nachtraeglich splitten
                has_icy = (meta_count > 0 and session.meta_file_path
                           and session.meta_file_path.exists())
                if has_icy:
                    log.log(f"FALLBACK: Post-hoc Split ({meta_count} ICY-Eintraege)")
                    from .segment_splitter import splitter
                    try:
                        segments = await splitter.split_session(
                            session.id, seg_file, session.meta_file_path,
                            duration, session.file_format
                        )
                        if segments:
                            result["segments"] = len(segments)
                            print(f"  REC Post-hoc Split: {len(segments)} Segmente")
                            log.log(f"  Post-hoc Split: {len(segments)} Segmente")
                    except Exception as e:
                        print(f"  REC Split-Fehler: {e}")
                        log.log(f"  Split-Fehler: {e}")
                else:
                    result["segments"] = 1

                result["duration"] = duration
                result["file_size"] = file_size
            else:
                log.log("LEER: Keine Audiodaten geschrieben")
                self._finalize_session(session, "empty")
                result["duration"] = 0
                result["file_size"] = 0
                result["segments"] = 0

            result["mode"] = "fallback"

        log.log(f"FERTIG: {result.get('duration', 0):.0f}s, "
                f"{result.get('segments', 0)} Segmente")
        result["file_path"] = str(session.session_dir)
        return result

    def _count_segments(self, session_id: str) -> int:
        """Anzahl der Segmente einer Session in der DB."""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM segments WHERE session_id = ?",
                      (session_id,))
            return c.fetchone()[0]

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
            "bitrate": session.bitrate,
            "codec": session.codec or "mp3",
            "file_format": session.file_format,
            "free_disk_mb": free_mb,
            "segment_count": session.segment_count,
            "live_split": session.live_split,
            "events": session.events
        }

        # ICY-Daten mitliefern wenn Logger laeuft
        if session.icy_logger and session.icy_logger.entries:
            status["icy_title"] = session.icy_logger.entries[-1].get("title", "")
            status["icy_count"] = session.icy_logger.entry_count
            status["icy_entries"] = [
                {
                    "title": e.get("title", ""),
                    "t": e.get("t", 0),
                    "ignored": e.get("ignored", False),
                    "raw_title": e.get("raw_title", e.get("title", ""))
                }
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
