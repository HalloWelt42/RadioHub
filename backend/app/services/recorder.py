"""
RadioHub v0.5.0 - Recorder Service (Live-Split)

Stream-Aufnahme mit Live-Split bei ICY-Titelwechsel.

Ablauf:
1. Der Stromleser hält die eine Verbindung zum Sender (RAD-33) und gibt den Ton über stdin an FFmpeg, das ihn in
   eine Einzeldatei schreibt; die Sendedaten derselben Verbindung führt das Titelbuch
2. Titelwechsel -> Callback, zwischen zwei Blöcken des Tons, also genau an der Stelle
3. Callback: Neuen FFmpeg starten, den Ton dorthin lenken, dem alten das Ende des Tons geben (EOF), Segment ablegen.
   Früher verband jeder neue FFmpeg sich selbst neu, und Sender mit Werbung beim Verbinden setzten vor jedes Stück
   einen Spot
4. Stop: Letztes Segment finalisieren, kein Concat noetig
5. Fallback ohne ICY: Ein Segment pro Session; ist der Sender eine Wiedergabeliste, liest FFmpeg selbst
6. Werbung aus den Sendedaten (RAD-33): dieselben Angaben ergeben Werbestellen, die Grenze sitzt an der Stille, die
   der Stillenwächter meldet (ein eigener FFmpeg über den ganzen Ton, stillenwaechter.py). Beim Abschluss kommen die
   Stellen zur Aufnahme (Sekunden des ganzen Tons).
7. Feinschnitt nach dem Stopp (RAD-45): live wird grob beim Eintreffen der Angabe geteilt (die Stücke wachsen sichtbar);
   danach rücken die Grenzen ans Ende der Stille davor, Werbung wird ein Stück, Einschübe ohne Titel eigene Stücke
   (feinschnitt.py). Das ist ein Schritt des Schnitts, also mit Rückgängig. Solange er läuft, heißt die Aufnahme
   "feinschnitt" und die Oberfläche hält sie für laufend (Wiedergabe gesperrt).

Gap-Detection: Erkennt Dropouts ab 10s (gap_start/gap_end Events).
Stall nach 60s ohne Wachstum -> FFmpeg Kill.
Events werden in Session und meta.json gespeichert.
"""
import logging
import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..ablage import orte
from ..database import db_session
from ..config import get_arbeit_dir, get_active_recording_folder
from .aufnahmen import aufnahmen
from .config_service import config_service
from . import feinschnitt_lauf, werbestellen
from ..sendewerbung.sitzung import Sitzungswerbung
from .stromleser import StromFehler, Stromleser, Wiedergabeliste
from .stillenwaechter import Stillenwaechter
from .titelbuch import Titelbuch
from .audio_utils import probe_duration

logger = logging.getLogger("radiohub.recorder")

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

# Art des Stroms (Stromleser) -> Codec und Dateiendung; andere Arten erkennt ffprobe
CODEC_AUS_FORMAT = {"mp3": ("mp3", ".mp3"), "aac": ("aac", ".aac")}

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
        self.titelbuch: Optional[Titelbuch] = None
        self.werbung: Optional[Sitzungswerbung] = None
        self.stillen: Optional[Stillenwaechter] = None
        self.pegel: list[tuple[float, float]] = []      # Momentanlautheit je 100 ms für den Feinschnitt
        self.stromleser: Optional[Stromleser] = None   # None: FFmpeg liest selbst (Wiedergabeliste)
        self.strom_task: Optional[asyncio.Task] = None
        self.eingang_format: Optional[str] = None
        self.logger: Optional[SessionLogger] = None
        self.events: list[dict] = []  # Gap/Stall/Codec-Events

        # Ablage: fertige Stücke gehen der Reihe nach im Hintergrund in die Ablage
        self.kumuliert_ms: int = 0
        self.abgelegt_bytes: int = 0
        self.abgelegte_segmente: int = 0
        self.ablage_tasks: list[asyncio.Task] = []
        self.ablage_lock = asyncio.Lock()
        self.abgeschlossen: bool = False

        # Live-Split Felder
        self.segment_index: int = 0
        self.current_segment_file: Optional[Path] = None
        self.current_segment_title: str = ""
        self.current_segment_start: Optional[datetime] = None
        #: wo im Ton das laufende Stück begann (Sekunden): der Mindestabstand zweier Teilungen gilt im Ton, nicht in
        #: der Uhrzeit, denn manche Sender schicken beim Verbinden 20 s Ton auf einmal (laut.fm, RAD-45)
        self.current_segment_ton_s: float = 0.0
        self.live_split: bool = False  # True sobald erster ICY-Split passiert
        self._split_lock: Optional[asyncio.Lock] = None  # Initialisiert bei Start

    @property
    def duration(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def _lokale_segmente(self) -> list[Path]:
        if not self.session_dir or not self.session_dir.exists():
            return []
        return [f for f in self.session_dir.iterdir() if f.is_file() and f.name.startswith("seg_")]

    @property
    def file_size(self) -> int:
        """Abgelegte Stücke plus was noch im Arbeitsordner liegt."""
        lokal = 0
        for f in self._lokale_segmente():
            try:
                lokal += f.stat().st_size
            except OSError:
                pass  # gerade abgelegt
        return self.abgelegt_bytes + lokal

    @property
    def segment_count(self) -> int:
        """Anzahl der bisher geschriebenen Stücke (abgelegt und lokal)."""
        return self.abgelegte_segmente + len(self._lokale_segmente())


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
        self._feinschnitt_task: Optional[asyncio.Task] = None

    def startup(self):
        """Beim Start der App, nachdem die Datenbank eingerichtet ist (betrieb.Radiobetrieb)."""
        self._cleanup_stale_sessions()

    def _cleanup_stale_sessions(self):
        """Beim Start: Verwaiste 'recording'-Sessions in DB bereinigen.
        Nach Server-Neustart existiert kein FFmpeg-Prozess mehr,
        aber die DB hat noch status='recording'."""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM sessions WHERE status = 'recording' AND COALESCE(rec_type, 'direct') != 'hls-rec'")
            stale = c.fetchall()
            # ein beim Neustart unterbrochener Feinschnitt: die groben Stücke gelten
            c.execute("UPDATE sessions SET status = 'completed' WHERE status = 'feinschnitt'")
            for row in stale:
                # Was noch im Arbeitsordner liegt, legt aufnahmen.liegengebliebene_ablegen beim Start ab
                c.execute(
                    "UPDATE sessions SET status = 'interrupted', "
                    "file_size = (SELECT COALESCE(SUM(file_size), 0) FROM segments WHERE session_id = ?) "
                    "WHERE id = ?", (row[0], row[0])
                )
            if stale:
                logger.info(f"{len(stale)} verwaiste Recording-Session(s) bereinigt")

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
                    logger.info(f"Codec erkannt: {codec} -> {ext}")
                    return codec, ext
                logger.warning(f"Unbekannter Codec: {codec}, Fallback auf MP3")

        except asyncio.TimeoutError:
            logger.warning("ffprobe Timeout, Fallback auf MP3")
        except Exception as e:
            logger.warning(f"ffprobe Fehler: {e}, Fallback auf MP3")

        return "", ".mp3"

    def _eingang(self, session: RecordingSession) -> list[str]:
        """Eingang von FFmpeg: der Ton des Stromlesers über stdin, ohne ihn liest FFmpeg selbst."""
        if session.stromleser:
            return (["-f", session.eingang_format] if session.eingang_format else []) + ["-i", "pipe:0"]
        return ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5", "-i", session.stream_url]

    def _build_ffmpeg_cmd(self, session: RecordingSession,
                          output_file: Path) -> list[str]:
        """Baut FFmpeg-Kommando fuer Einzeldatei-Aufnahme (mit stdin=PIPE)."""
        if session.codec:
            return [
                "ffmpeg", "-y",
                *self._eingang(session),
                "-c:a", "copy",
                str(output_file)
            ]
        else:
            configured_bitrate = config_service.get("recording_bitrate", 192)
            br = (f"{session.bitrate}k" if session.bitrate > 0
                  else f"{configured_bitrate}k")
            return [
                "ffmpeg", "-y",
                *self._eingang(session),
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-c:a", "libmp3lame", "-b:a", br,
                "-ac", "2",       # Stereo
                "-ar", "44100",   # Samplerate
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
                                    timeout: float = 5.0, ende_des_tons: bool = False):
        """Stoppt FFmpeg sauber, Fallback auf terminate/kill. Liest FFmpeg den Ton über stdin (`ende_des_tons`),
        endet es mit dem Ende des Tons (stdin schließen); sonst über "q" auf stdin."""
        if process.returncode is not None:
            return
        try:
            if process.stdin and ende_des_tons:
                if not process.stdin.is_closing():
                    process.stdin.close()
            elif process.stdin:
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

        # Platz im Arbeitsordner prüfen (dort liegt die laufende Aufnahme bis zur Ablage)
        rec_dir = get_arbeit_dir("aufnahmen")
        try:
            stat = shutil.disk_usage(str(rec_dir))
            free_mb = stat.free / (1024 * 1024)
            if free_mb < MIN_FREE_DISK_MB:
                return {"success": False,
                        "error": f"Zu wenig Speicherplatz (min. {MIN_FREE_DISK_MB} MB)"}
        except Exception:
            pass

        # Aktiven Aufnahmeordner bestimmen
        folder_name, folder_id = get_active_recording_folder()

        # Arbeitsordner der laufenden Aufnahme; der Ort in der Ablage steht ab Start fest
        session_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_dir = get_arbeit_dir("aufnahmen", session_id)

        session = RecordingSession(
            session_id=session_id,
            station_uuid=station_uuid,
            station_name=station_name,
            stream_url=stream_url,
            bitrate=bitrate
        )
        session.session_dir = session_dir
        session._split_lock = asyncio.Lock()

        # Eine Verbindung für Ton und Sendedaten (RAD-33): erst verbinden, dann den Codec aus der Art des Stroms
        meta_path = session_dir / orte.TITELLISTE
        session.meta_file_path = meta_path
        session.titelbuch = Titelbuch(sperrliste=self._sperrliste(), bei_wechsel=self._on_title_change, datei=meta_path)
        session.werbung = Sitzungswerbung(stillen_hoechstens=None)     # alle Stillen: der Feinschnitt braucht sie
        session.stromleser = Stromleser(stream_url, lambda daten: self._ton(session, daten),
                                        lambda angabe: self._angabe(session, angabe), bitrate=bitrate)
        try:
            kopf = await session.stromleser.verbinden()
            session.titelbuch.metaint = kopf.metaint
            session.eingang_format = kopf.format
            session.stillen = Stillenwaechter(kopf.format, session.werbung.stille_zeile,
                                              lambda t, m: session.pegel.append((round(t, 2), round(m, 1))))
            await session.stillen.starten()
        except StromFehler as f:
            art = "Wiedergabeliste" if isinstance(f, Wiedergabeliste) else f"Stromleser: {f}"
            logger.info(f"REC {art}; FFmpeg liest selbst, ohne Sendedaten")
            session.stromleser, kopf = None, None
        codec, ext = CODEC_AUS_FORMAT.get(kopf.format) if kopf and kopf.format in CODEC_AUS_FORMAT else \
            await self._detect_codec(stream_url)
        session.codec = codec
        session.file_format = ext

        # Debug-Logger (optional, per Config zuschaltbar)
        safe_name = "".join(
            c if c.isalnum() or c in " -_" else "_" for c in station_name
        )[:50]
        log_path = get_arbeit_dir("protokolle") / f"{session_id}_{safe_name}.log"
        session.logger = SessionLogger(log_path)
        ablage_ordner = orte.aufnahmeordner(station_name, session.start_time, folder_name)

        # Erstes Segment starten
        initial_file = session_dir / f"seg_000{ext}"
        session.current_segment_file = initial_file
        session.current_segment_title = "Teil 1"
        session.current_segment_start = datetime.now()

        try:
            session.process = await self._start_ffmpeg(session, initial_file)
            self.active_session = session

            # Monitor-Task + Stderr-Watcher
            self._monitor_task = asyncio.create_task(self._monitor_process(session))
            self._stderr_task = asyncio.create_task(self._watch_stderr(session))

            # Ton und Sendedaten aus der einen Verbindung lesen; Titelwechsel teilen die Aufnahme
            if session.stromleser:
                session.strom_task = asyncio.create_task(self._strom_laufen(session))

            # In DB speichern (file_path = Ordner der Aufnahme in der Ablage; die Titelliste
            # wird beim Ablegen eingetragen)
            with db_session() as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO sessions
                    (id, station_uuid, station_name, stream_url, bitrate,
                     start_time, file_path, status, codec, file_format,
                     meta_file_path, folder_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (session_id, station_uuid, station_name, stream_url, bitrate,
                     session.start_time.isoformat(), ablage_ordner, "recording",
                     codec, ext, None, folder_id))

            mode = "Stream-Copy" if codec else "MP3-Encoding"
            logger.info(f"REC gestartet: {session_id} ({mode}, {codec or 'fallback'}, Live-Split)")
            session.logger.log(f"START {station_name}")
            session.logger.log(f"  Stream: {stream_url}")
            session.logger.log(f"  Codec: {codec or 'fallback->mp3'}, Mode: {mode}")
            session.logger.log(f"  Live-Split aktiv, Format: {ext}")
            try:
                _stat = shutil.disk_usage(str(session_dir))
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
            if session.stromleser:
                session.stromleser.stop()
            if session.stillen:
                await session.stillen.beenden(2)
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            logger.warning(f"REC fehlgeschlagen: {e}")
            return {"success": False, "error": str(e)}

    def _sperrliste(self) -> list[dict]:
        """Gesperrte Titel (icy_title_ignore): sie teilen die Aufnahme nicht."""
        try:
            with db_session() as conn:
                return [{"pattern": r[0], "match_type": r[1]}
                        for r in conn.execute("SELECT pattern, match_type FROM icy_title_ignore")]
        except Exception:
            return []

    async def _angabe(self, session: RecordingSession, a) -> None:
        """Eine Angabe der Sendedaten: Werbung in die Werbestellen der Aufnahme, Titel ins Titelbuch (teilt die Aufnahme)."""
        if session.werbung and (neu := session.werbung.angabe(a.roh, a.sekunde)):
            session.logger.log(f"WERBUNG ab {neu.von:.2f} s: {neu.werbender or neu.kennung} ({neu.format})")
        if session.titelbuch:
            await session.titelbuch.angabe(a)

    def _werbung_ablegen(self, session: RecordingSession) -> None:
        """Die Werbestellen der Aufnahme speichern (Sekunden des ganzen aufgenommenen Tons); eine noch offene endet mit
        der Aufnahme."""
        if not session.werbung or not session.werbung.stellen:
            return
        ende = session.kumuliert_ms / 1000 or (session.stromleser.sekunde(session.stromleser.ton_bytes)
                                               if session.stromleser else session.duration)
        neue = [werbestellen.Neu(von=s.von, bis=min(ende, s.bis if s.bis is not None else ende),
                                 text=(s.werbender or s.titel or s.kennung) + (" (beim Verbinden)" if s.beim_verbinden else ""))
                for s in session.werbung.stellen if s.von < ende]
        try:
            zahl = werbestellen.ersetzen(werbestellen.Bezug.aufnahme(session.id), "sendedaten", neue)
            session.logger.log(f"WERBUNG {zahl} Stellen zur Aufnahme")
        except Exception as f:          # die Aufnahme hängt nicht an den Stellen
            logger.warning(f"REC Werbestellen nicht gespeichert: {f}")

    async def _ton(self, session: RecordingSession, daten: bytes) -> None:
        """Ziel des Stromlesers: der Ton zum Stillenwächter und in den laufenden FFmpeg; beim Teilen wartet er auf den
        neuen."""
        if session.stillen:
            await session.stillen.ton(daten)
        async with session._split_lock:
            prozess = session.process
            if not prozess or not prozess.stdin or prozess.stdin.is_closing():
                return
            try:
                prozess.stdin.write(daten)
                await prozess.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass   # FFmpeg endet gerade; die Überwachung entscheidet, wie es weitergeht

    async def _strom_laufen(self, session: RecordingSession) -> None:
        """Liest, bis die Aufnahme stoppt oder der Sender wegbleibt; dann bekommt FFmpeg das Ende des Tons und die
        Überwachung schließt die Aufnahme ab wie früher, wenn FFmpeg den Strom verlor."""
        try:
            await session.stromleser.laufen()
        finally:
            if session.titelbuch:
                session.titelbuch.abschliessen(session.stromleser.ton_bytes)
            prozess = session.process
            if prozess and prozess.stdin and not prozess.stdin.is_closing():
                prozess.stdin.close()

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
                logger.warning(f"REC Codec-Fehler: {text[:100]}")

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
                    session.segment_index += 1
                    new_file = session.session_dir / (
                        f"seg_{session.segment_index:03d}{session.file_format}")

                    try:
                        session.process = await self._start_ffmpeg(
                            session, new_file)
                    except Exception as e:
                        logger.warning(f"REC Codec-Recovery fehlgeschlagen: {e}")
                        session.process = old_process
                        continue

                    session.current_segment_file = new_file
                    session.current_segment_start = datetime.now()
                    if session.stromleser:
                        session.current_segment_ton_s = session.stromleser.sekunde(session.stromleser.ton_bytes)
                    session.live_split = True

                    # Alten Prozess stoppen
                    await self._stop_ffmpeg_graceful(old_process, ende_des_tons=session.stromleser is not None)

                    # Altes Segment ablegen
                    if old_file and old_file.exists() and old_file.stat().st_size > 0:
                        dur = await probe_duration(old_file)
                        if dur > 0:
                            self._ablegen(
                                session, session.segment_index - 1,
                                old_title or f"Teil {session.segment_index}",
                                old_file, int(dur * 1000))

                    session.logger.log(
                        f"CODEC-RECOVERY: Neues Segment #{session.segment_index}")
                    logger.info(f"REC Codec-Recovery: Segment #{session.segment_index}")

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
                age = elapsed_ms / 1000 - session.current_segment_ton_s
                if age < MIN_SEGMENT_SECONDS:
                    # Zu kurz -- Titel aktualisieren, aber nicht splitten
                    session.current_segment_title = title
                    session.logger.log(
                        f"SKIP Split (zu kurz: {age:.1f}s): {title}")
                    return

            old_process = session.process
            old_file = session.current_segment_file
            old_title = session.current_segment_title

            # Neues Segment vorbereiten (lokal nur nummeriert, den Titel bekommt es in der Ablage)
            session.segment_index += 1
            ext = session.file_format
            new_file = session.session_dir / f"seg_{session.segment_index:03d}{ext}"

            # Neuen FFmpeg starten BEVOR alter gestoppt wird (Overlap-Strategie)
            try:
                session.process = await self._start_ffmpeg(session, new_file)
            except Exception as e:
                logger.warning(f"REC Split-Fehler: Neuer FFmpeg fehlgeschlagen: {e}")
                session.process = old_process  # Alten behalten
                return

            session.current_segment_file = new_file
            session.current_segment_title = title
            session.current_segment_start = datetime.now()
            session.current_segment_ton_s = elapsed_ms / 1000
            session.live_split = True

            # Alten FFmpeg sauber stoppen
            await self._stop_ffmpeg_graceful(old_process, ende_des_tons=session.stromleser is not None)

            # Altes Segment ablegen
            if old_file and old_file.exists() and old_file.stat().st_size > 0:
                duration = await probe_duration(old_file)
                if duration > 0:
                    self._ablegen(
                        session, session.segment_index - 1,
                        old_title or f"Teil {session.segment_index}",
                        old_file, int(duration * 1000)
                    )

            session.logger.log(
                f"SPLIT #{session.segment_index}: {title}")
            logger.info(f"REC Split #{session.segment_index}: {title}")

    def _ablegen(self, session: RecordingSession, index: int, title: str,
                 file_path: Path, duration_ms: int):
        """Fertiges Stück im Hintergrund ablegen, der Reihe nach, damit die Aufnahme weiterläuft.
        Scheitert das Ablegen, bleibt die Datei im Arbeitsordner und wird beim Abschluss erneut versucht."""
        start_ms = session.kumuliert_ms
        session.kumuliert_ms += duration_ms

        async def ablegen():
            async with session.ablage_lock:
                try:
                    groesse = file_path.stat().st_size
                    await aufnahmen.teil_ablegen(session.id, index, title, start_ms, duration_ms, file_path)
                    session.abgelegt_bytes += groesse
                    session.abgelegte_segmente += 1
                except Exception as e:
                    logger.warning(f"REC Ablage-Fehler {file_path.name}: {e} (bleibt im Arbeitsordner)")
                    if session.logger:
                        session.logger.log(f"ABLAGE-FEHLER {file_path.name}: {e}")

        session.ablage_tasks.append(asyncio.create_task(ablegen()))

    async def _ablage_abwarten(self, session: RecordingSession):
        if session.ablage_tasks:
            await asyncio.gather(*session.ablage_tasks, return_exceptions=True)
            session.ablage_tasks.clear()

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
                            logger.warning(f"REC abgebrochen: {session.id} (exit {returncode})")
                            log.log(f"FFMPEG EXIT {returncode}")
                            await asyncio.shield(self._abschliessen(session, "failed"))
                        else:
                            logger.info(f"REC Stream beendet: {session.id}")
                            log.log("FFMPEG EXIT 0 (Stream beendet)")
                            await asyncio.shield(self._abschliessen(session, "completed"))
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
                        logger.warning(f"REC STALLED: {session.id} "
                              f"({current_segs} Segmente, "
                              f"unverändert seit {elapsed}s, "
                              f"{current_size/1024/1024:.1f}MB)")
                        log.log(f"STALLED nach {elapsed}s -- FFmpeg wird gekillt")
                        if session.process.returncode is None:
                            session.process.kill()
                            await session.process.wait()
                        await asyncio.shield(self._abschliessen(session, "stalled"))
                        return

                # --- Disk-Space pruefen ---
                try:
                    rec_dir = get_arbeit_dir("aufnahmen")
                    stat = shutil.disk_usage(str(rec_dir))
                    free_mb = stat.free / (1024 * 1024)
                    if free_mb < MIN_FREE_DISK_MB:
                        logger.warning(f"REC DISK FULL: {session.id} "
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
                        await asyncio.shield(self._abschliessen(session, "disk_full"))
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
                        _s = shutil.disk_usage(str(get_arbeit_dir("aufnahmen")))
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

    async def _abschliessen(self, session: RecordingSession, status: str,
                            real_duration: float = 0):
        """Aufnahme abschließen: offene Stücke und Titelliste ablegen, Arbeitsordner räumen, DB finalisieren.
        Was sich nicht ablegen lässt, bleibt im Arbeitsordner und wird beim nächsten Start nachgeholt."""
        if session.abgeschlossen:
            return
        session.abgeschlossen = True
        if self.active_session and self.active_session.id == session.id:
            self.active_session = None
        # die letzten Stillen abwarten: Werbestellen und Feinschnitt brauchen sie
        if session.stillen:
            await session.stillen.beenden()
            session.stillen = None

        # Laufendes Stück (bei Abbruch, Stillstand, vollem Speicher) mit seinem Titel ablegen
        rest = session.current_segment_file
        if rest and rest.exists() and rest.stat().st_size > 0:
            dauer = await probe_duration(rest)
            if dauer > 0:
                self._ablegen(session, session.segment_index,
                              session.current_segment_title or f"Teil {session.segment_index + 1}",
                              rest, int(dauer * 1000))
        session.current_segment_file = None
        await self._ablage_abwarten(session)

        # Ereignisse in die Titelliste
        meta_path = session.meta_file_path
        if session.events and meta_path and meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["events"] = session.events
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        self._werbung_ablegen(session)

        try:
            await aufnahmen.rest_ablegen(session.id, session.session_dir, session.kumuliert_ms)
        except Exception as e:
            logger.warning(f"REC Ablage beim Abschluss unvollständig: {e} (wird beim nächsten Start nachgeholt)")

        segmente = aufnahmen.segmente(session.id)
        if not segmente and status == "completed":
            status = "empty"
        duration = real_duration if real_duration > 0 else (
            sum(s["duration_ms"] or 0 for s in segmente) / 1000.0 or session.duration)
        quality_json = self._build_quality_json(session) if session.events else None
        plan = await self._feinschnitt_vorbereiten(session, duration) if status == "completed" and segmente else None
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''UPDATE sessions SET
                end_time = ?, duration = ?, file_size = ?, status = ?, quality_json = ?
                WHERE id = ?''',
                (datetime.now().isoformat(), duration,
                 sum(s["file_size"] or 0 for s in segmente), "feinschnitt" if plan else status, quality_json, session.id))
        if plan:
            self._feinschnitt_task = asyncio.create_task(self._feinschnitt(session, plan))

    async def feinschnitt_abwarten(self) -> None:
        """Bis ein laufender Feinschnitt fertig ist (Tests, Herunterfahren)."""
        if self._feinschnitt_task:
            await asyncio.gather(self._feinschnitt_task, return_exceptions=True)

    async def _feinschnitt_vorbereiten(self, session: RecordingSession, dauer: float) -> Optional[list]:
        """Die Analyse der Aufnahme festhalten (Analyse.json in der Ablage, zum späteren Neurechnen) und die Stücke des
        Feinschnitts planen; None, wenn es nichts zu verbessern gibt (ohne Sendedaten, ein Stück)."""
        if not session.titelbuch or not session.werbung or dauer <= 0:
            return None
        analyse = feinschnitt_lauf.Analyse(
            dauer=dauer, wechsel=session.titelbuch.wechsel, stillen=session.werbung.stillen, pegel=session.pegel,
            werbung=[(w.von, w.bis if w.bis is not None else dauer, w.werbender or w.titel or w.kennung)
                     for w in session.werbung.stellen])
        try:
            await feinschnitt_lauf.analyse_ablegen(session.id, analyse)
        except Exception as f:            # ohne gespeicherte Analyse geht nur das spätere Neurechnen nicht
            logger.warning(f"REC Analyse nicht abgelegt: {f}")
        stuecke = feinschnitt_lauf.planen(analyse)
        if stuecke:
            session.logger.log("FEINSCHNITT " + feinschnitt_lauf.zusammenfassung(stuecke))
        return stuecke

    async def _feinschnitt(self, session: RecordingSession, stuecke: list) -> None:
        """Den Feinschnitt ausführen; schlägt er fehl, bleiben die groben Stücke."""
        try:
            await feinschnitt_lauf.ausfuehren(session.id, stuecke)
        except Exception as f:
            logger.warning(f"REC Feinschnitt {session.id} fehlgeschlagen: {f} (die groben Stücke bleiben)")
            session.logger.log(f"FEINSCHNITT-FEHLER {f}")

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

        # Stromleser stoppen (vor FFmpeg, damit kein Ton und kein Titelwechsel mehr kommt)
        if session.stromleser:
            session.stromleser.stop()
        if session.strom_task and not session.strom_task.done():
            session.strom_task.cancel()
            try:
                await session.strom_task
            except asyncio.CancelledError:
                pass

        # FFmpeg sauber stoppen
        if session.process and session.process.returncode is None:
            await self._stop_ffmpeg_graceful(session.process, ende_des_tons=session.stromleser is not None)

        meta_count = session.titelbuch.entry_count if session.titelbuch else 0
        log = session.logger
        seg_count = session.segment_count

        logger.info(f"REC gestoppt: {session.id} "
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
            # === Live-Split-Modus: letztes Stück ablegen, die anderen sind schon unterwegs ===
            last_file = session.current_segment_file
            if last_file and last_file.exists() and last_file.stat().st_size > 0:
                duration = await probe_duration(last_file)
                if duration > 0:
                    self._ablegen(
                        session, session.segment_index,
                        session.current_segment_title or f"Teil {session.segment_index + 1}",
                        last_file, int(duration * 1000)
                    )
                    session.current_segment_file = None

            total_duration = session.kumuliert_ms / 1000.0
            await self._abschliessen(session, "completed", real_duration=total_duration)

            db_seg_count = self._count_segments(session.id)
            result["segments"] = db_seg_count
            result["duration"] = total_duration
            result["file_size"] = session.file_size
            result["mode"] = "live-split"
            log.log(f"LIVE-SPLIT FERTIG: {total_duration:.0f}s, {db_seg_count} Segmente")
        else:
            # === Fallback: Kein ICY-Titelwechsel erkannt ===
            # Mit Titelliste nachträglich lokal schneiden, sonst die Einzeldatei als ein Stück ablegen
            seg_file = session.current_segment_file
            if seg_file and seg_file.exists() and seg_file.stat().st_size > 0:
                real_duration = await probe_duration(seg_file)
                duration = real_duration if real_duration > 0 else session.duration
                file_size = seg_file.stat().st_size

                stuecke = []
                has_icy = (meta_count > 0 and session.meta_file_path
                           and session.meta_file_path.exists())
                if has_icy:
                    log.log(f"FALLBACK: Post-hoc Split ({meta_count} ICY-Eintraege)")
                    from .segment_splitter import splitter
                    try:
                        with open(session.meta_file_path, "r", encoding="utf-8") as f:
                            titelliste = json.load(f)
                        # Stücke direkt in den Arbeitsordner: was nicht abgelegt wird, holt der Abschluss
                        # oder der nächste Start nach (ein Unterordner würde dabei übersehen)
                        stuecke = await splitter.nach_titelliste(
                            seg_file, titelliste, duration, session.file_format,
                            session.session_dir)
                    except Exception as e:
                        logger.warning(f"REC Split-Fehler: {e}")
                        log.log(f"  Split-Fehler: {e}")
                        stuecke = []

                if stuecke:
                    seg_file.unlink(missing_ok=True)
                    for i, stueck in enumerate(stuecke):
                        self._ablegen(session, i, stueck.titel, stueck.datei, stueck.dauer_ms)
                    logger.info(f"REC Post-hoc Split: {len(stuecke)} Segmente")
                    log.log(f"  Post-hoc Split: {len(stuecke)} Segmente")
                    result["segments"] = len(stuecke)
                else:
                    self._ablegen(session, 0,
                                  session.current_segment_title or session.station_name,
                                  seg_file, int(duration * 1000))
                    result["segments"] = 1
                session.current_segment_file = None
                await self._abschliessen(session, "completed", real_duration=duration)

                result["duration"] = duration
                result["file_size"] = file_size
            else:
                log.log("LEER: Keine Audiodaten geschrieben")
                await self._abschliessen(session, "empty")
                result["duration"] = 0
                result["file_size"] = 0
                result["segments"] = 0

            result["mode"] = "fallback"

        log.log(f"FERTIG: {result.get('duration', 0):.0f}s, "
                f"{result.get('segments', 0)} Segmente")
        result["file_path"] = self.get_session(session.id)["file_path"]
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
            asyncio.create_task(self._abschliessen(session, "interrupted"))
            return {"recording": False}

        # Disk-Space
        free_mb = None
        try:
            rec_dir = get_arbeit_dir("aufnahmen")
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
        if session.titelbuch and session.titelbuch.entries:
            status["icy_title"] = session.titelbuch.entries[-1].get("title", "")
            status["icy_count"] = session.titelbuch.entry_count
            status["icy_entries"] = [
                {
                    "title": e.get("title", ""),
                    "t": e.get("t", 0),
                    "ignored": e.get("ignored", False),
                    "raw_title": e.get("raw_title", e.get("title", ""))
                }
                for e in session.titelbuch.entries
            ]

        return status

    SORTIERUNG = {"datum": "s.start_time", "sender": "s.station_name COLLATE NOCASE", "dauer": "s.duration",
                  "groesse": "s.file_size"}

    def get_sessions(self, limit: int = 50, ab: int = 0, suche: str = "", ordner: str = "", sort: str = "datum",
                     absteigend: bool = True) -> tuple[list, int]:
        """Sessions seitenweise (RAD-17: nicht mehr nur die neuesten 50), gefiltert nach Ordner ("" alle, "ohne" ohne
        Ordner, sonst die Kennung) und Suche in Sender und Titeln; dazu die Zahl aller Treffer. Hängengebliebene
        'recording'-Einträge ohne laufende Aufnahme werden 'interrupted'. Fehlende Dateien in der Ablage bereinigt nur
        `repair` auf Anfrage, nie das Listen."""
        bedingungen, werte = [], []
        if ordner == "ohne":
            bedingungen.append("s.folder_id IS NULL")
        elif ordner:
            bedingungen.append("s.folder_id = ?")
            werte.append(int(ordner))
        if suche.strip():
            muster = f"%{suche.strip()}%"
            bedingungen.append("(s.station_name LIKE ? OR EXISTS (SELECT 1 FROM segments t WHERE t.session_id = s.id AND t.title LIKE ?))")
            werte += [muster, muster]
        wo = f"WHERE {' AND '.join(bedingungen)}" if bedingungen else ""
        reihe = self.SORTIERUNG.get(sort, "s.start_time")
        richtung = "DESC" if absteigend else "ASC"
        with db_session() as conn:
            c = conn.cursor()
            gesamt = c.execute(f"SELECT COUNT(*) FROM sessions s {wo}", werte).fetchone()[0]
            c.execute(f'''SELECT s.*, COUNT(seg.id) as segment_count
                FROM sessions s
                LEFT JOIN segments seg ON seg.session_id = s.id
                {wo}
                GROUP BY s.id
                ORDER BY {reihe} {richtung}, s.start_time DESC LIMIT ? OFFSET ?''', (*werte, limit, ab))
            rows = [dict(row) for row in c.fetchall()]

        active_id = self.active_session.id if self.active_session else None
        from .hls_recorder import hls_recorder
        hls_active_id = hls_recorder.active_session.id if hls_recorder.active_session else None
        for row in rows:
            if row.get("status") == "recording" and row["id"] not in (active_id, hls_active_id):
                row["status"] = "interrupted"
                with db_session() as conn:
                    conn.cursor().execute(
                        "UPDATE sessions SET status = 'interrupted' WHERE id = ?", (row["id"],))
        return rows, gesamt

    def get_session(self, session_id: str) -> Optional[dict]:
        """Einzelne Session, mit der Zahl ihrer Stücke wie in der Liste (get_sessions)"""

        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT s.*, (SELECT COUNT(*) FROM segments t WHERE t.session_id = s.id) AS segment_count "
                      "FROM sessions s WHERE s.id = ?", (session_id,))
            row = c.fetchone()
            return dict(row) if row else None

    async def delete_session(self, session_id: str) -> bool:
        """Session löschen: Dateien in den Papierkorb der Ablage, Einträge weg."""
        if self.active_session and self.active_session.id == session_id:
            return False
        return await aufnahmen.sitzung_loeschen(session_id)


# Singleton
rec_manager = RecorderManager()
