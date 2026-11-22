"""
RadioHub HLS Buffer Service v1.2.0

HLS (HTTP Live Streaming) basierter Timeshift Buffer.
Nutzt ffmpeg um Radio-Streams in seekbare Segmente zu konvertieren.
Mit adaptiver Bitrate-Anpassung und ICY-Metadata-Tracking.

© HalloWelt42 - Nur für private Nutzung
"""
import logging
import asyncio
import shutil
import json
from collections import deque
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from .empfang import Abnehmer, Empfang, empfaenge
from .stromleser import StromFehler, Wiedergabeliste
from ..sendewerbung import spots as werbespots

logger = logging.getLogger("radiohub.hls_buffer")


# Standard-Bitrate-Stufen (kbps)
STANDARD_BITRATES = [32, 48, 64, 96, 128, 192, 256, 320]


def snap_to_step(bitrate: int) -> int:
    """Rundet auf die nächste Standard-Bitrate ab (nicht höher als Input)."""
    best = STANDARD_BITRATES[0]
    for step in STANDARD_BITRATES:
        if step <= bitrate:
            best = step
        else:
            break
    return best


@dataclass
class StreamInfo:
    """Informationen über den Eingabe-Stream"""
    codec: str = "unknown"
    bitrate: int = 128        # kbps
    sample_rate: int = 44100  # Hz
    channels: int = 2
    
    
#: Formate, die ffmpeg unverändert in die Stücke (MPEG-TS) übernehmen kann; alles andere wird umgewandelt (RAD-92).
#: Namen wie im Kopf des Stromlesers (FORMATE) und bei ffprobe (codec_name)
KOPIERBAR = frozenset({"mp3", "aac"})


@dataclass
class HLSSession:
    """Aktive HLS Buffer Session"""
    session_id: str
    station_uuid: str
    station_name: str
    stream_url: str
    start_time: datetime
    segment_duration: int = 1      # 1 Sekunde pro Segment für präzises Seeking
    max_segments: int = 600        # 600 * 1s = 10 Minuten Buffer
    # Bitrate-Einstellungen
    input_bitrate: int = 128       # Erkannte Input-Bitrate (kbps)
    output_bitrate: int = 128      # Berechnete Output-Bitrate (kbps)
    min_bitrate: int = 32          # User-Einstellung: Minimum
    max_bitrate: int = 256         # User-Einstellung: Maximum
    sample_rate: int = 44100       # Sample Rate
    input_codec: str = "unknown"   # Erkannter Input-Codec
    is_podcast: bool = False       # Podcast-Modus: alle Segmente behalten, kein ICY
    original: bool = False         # Ton unverändert übernommen (keine Neukodierung, kein Angleichen, RAD-92)
    is_active: bool = True
    error: Optional[str] = None


class HLSBufferService:
    """
    HLS Buffer Service
    
    Konvertiert Radio-Stream via ffmpeg in HLS-Segmente.
    Ermöglicht exaktes Seeking durch segment-basiertes Streaming.
    Mit adaptiver Bitrate basierend auf Input-Stream.
    """
    
    def __init__(self, buffer_dir: str | None = None):
        # Ort der Stücke: fest übergeben (Prüfungen) oder aus der Einstellung hls_puffer_ordner, am Pi ein Bereich im
        # Arbeitsspeicher (compose.pi.yml, RAD-92); gelesen beim Start jedes Puffers
        self._fester_ordner = Path(buffer_dir) if buffer_dir else None
        self.buffer_dir = self._fester_ordner or Path("/tmp/radiohub-hls")
        self.session: Optional[HLSSession] = None
        self._ffmpeg_process: Optional[asyncio.subprocess.Process] = None
        self._monitor_task: Optional[asyncio.Task] = None
        # Radio: der Puffer ist Abnehmer des Empfangs (RAD-46, eine Verbindung für Ton und Sendedaten); der Ton geht
        # über stdin an ffmpeg. Stück N des Puffers beginnt bei N Sekunden ab seinem Beginn, das ist die Sekunde
        # `_versatz_s` des Empfangs (der Empfang kann älter sein, etwa wenn eine Aufnahme schon lief)
        self._empfang: Optional[Empfang] = None
        self._abnehmer: Optional[Abnehmer] = None
        self._versatz_s: float = 0.0
        
    def _ensure_buffer_dir(self):
        """Buffer-Verzeichnis erstellen/leeren"""
        if self._fester_ordner is None:
            from .. import einstellungen
            self.buffer_dir = Path(einstellungen.stand().hls_puffer_ordner)
        if self.buffer_dir.exists():
            shutil.rmtree(self.buffer_dir)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Buffer-Verzeichnis: {self.buffer_dir}")
    
    async def _detect_stream_info(self, stream_url: str, timeout: float = 8.0) -> StreamInfo:
        """
        Erkennt Codec und Bitrate des Eingabe-Streams mit ffprobe.
        
        Args:
            stream_url: URL des Streams
            timeout: Maximale Wartezeit in Sekunden
            
        Returns:
            StreamInfo mit erkannten Werten
        """
        info = StreamInfo()
        
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-select_streams", "a:0",
                stream_url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.warning(f"ffprobe Timeout nach {timeout}s - nutze Defaults")
                return info
            
            if process.returncode == 0 and stdout:
                data = json.loads(stdout.decode())
                streams = data.get("streams", [])
                
                if streams:
                    stream = streams[0]
                    info.codec = stream.get("codec_name", "unknown")
                    
                    # Bitrate kann als String kommen
                    bitrate_raw = stream.get("bit_rate", "0")
                    if bitrate_raw:
                        info.bitrate = int(bitrate_raw) // 1000  # bps → kbps
                    
                    info.sample_rate = int(stream.get("sample_rate", 44100))
                    info.channels = int(stream.get("channels", 2))
                    
                    logger.info(f"Stream erkannt: {info.codec} @ {info.bitrate} kbps, {info.sample_rate} Hz")
                    
        except Exception as e:
            logger.warning(f"Stream-Erkennung fehlgeschlagen: {e}")
        
        return info
    
    def _calculate_output_bitrate(
        self,
        input_bitrate: int,
        min_bitrate: int,
        max_bitrate: int,
        override_bitrate: int = 0
    ) -> int:
        """
        Berechnet optimale Output-Bitrate.

        Bei Override: User-Wahl direkt verwenden (bereits Standard-Stufe).
        Sonst: Nicht höher als Input, auf Standard-Stufe snappen.
        """
        if override_bitrate and override_bitrate > 0:
            # User hat explizit gewählt
            return override_bitrate

        if input_bitrate <= 0:
            # Unbekannt -> max_bitrate als sicherer Fallback
            return snap_to_step(max_bitrate)

        # Nicht höher als Input (Aufblähen ist sinnlos)
        output = min(input_bitrate, max_bitrate)
        # Aber mindestens min_bitrate
        output = max(output, min_bitrate)
        # Auf Standard-Stufe snappen
        return snap_to_step(output)
        
    def _build_ffmpeg_cmd(self, stream_url: str, aus_empfang: bool = False, eingang_format: Optional[str] = None) -> list:
        """ffmpeg Kommando für HLS-Segmentierung mit adaptiver Bitrate. Mit `aus_empfang` liest ffmpeg den Ton
        über stdin (der Empfang verbindet und verbindet neu), sonst selbst von der Adresse."""
        playlist = self.buffer_dir / "playlist.m3u8"
        segment_pattern = str(self.buffer_dir / "segment_%d.ts")

        # Podcast-Modus: Segmente behalten, ENDLIST schreiben (VOD)
        # Radio-Modus: Rolling Window, Segmente löschen (Live)
        if self.session.is_podcast:
            hls_flags = "append_list"
        else:
            hls_flags = "delete_segments+append_list+omit_endlist"

        # -nostats: kein Fortschritt auf stderr; Stille und Pegel misst der Empfang (sein Stillenwächter)
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-nostats",
            "-y",  # Überschreiben ohne Nachfrage
        ]
        if aus_empfang:
            cmd += (["-f", eingang_format] if eingang_format else []) + ["-i", "pipe:0"]
        else:
            cmd += ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5", "-i", stream_url]

        # Original (RAD-92): der Ton geht unverändert in die Stücke, ohne Dekodieren, Angleichen und Neukodieren
        # Podcast: Kein loudnorm (buffert gesamten Stream, blockiert Output)
        #          + -vn: Embedded Cover/Chapter-Images ignorieren (blockieren sonst libx264)
        # Radio umgewandelt: loudnorm fuer konsistente Lautstaerke bei Live-Streams
        if self.session.original:
            cmd += ["-vn", "-c:a", "copy"]
        else:
            if self.session.is_podcast:
                cmd += ["-vn"]
            else:
                cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
            cmd += [
                # Audio Encoding (adaptive Bitrate!)
                "-c:a", "aac",
                "-b:a", f"{self.session.output_bitrate}k",
                "-ac", "2",  # Stereo
                "-ar", str(self.session.sample_rate),
            ]

        cmd += [
            # HLS Output
            "-f", "hls",
            "-hls_time", str(self.session.segment_duration),
            "-hls_list_size", str(self.session.max_segments),
            "-hls_flags", hls_flags,
            "-hls_segment_filename", segment_pattern,
            str(playlist)
        ]
        return cmd
    
    async def start(
        self,
        station_uuid: str,
        station_name: str,
        stream_url: str,
        bitrate: int = 128,
        max_minutes: int = 10,
        min_bitrate: int = 32,
        max_bitrate: int = 320,
        sample_rate: int = 44100,
        override_bitrate: int = 0,
        is_podcast: bool = False,
        original: bool = False
    ) -> dict:
        """
        Startet HLS Buffering für einen Stream.
        
        Args:
            station_uuid: Sender-ID
            station_name: Sender-Name für Logs
            stream_url: URL des Radio-Streams
            bitrate: Fallback Audio-Bitrate in kbps (wenn Erkennung fehlschlägt)
            max_minutes: Maximale Buffer-Länge
            min_bitrate: Minimum Bitrate (User-Einstellung)
            max_bitrate: Maximum Bitrate (User-Einstellung)
            sample_rate: Sample Rate in Hz
            original: den Ton des Senders unverändert übernehmen, wenn sein Format es erlaubt (KOPIERBAR); sonst
                wird wie bei "voll" umgewandelt (RAD-92)

        Returns:
            Status-Dictionary
        """
        
        # Bereits aktiv für gleichen Stream?
        if self.session and self.session.is_active:
            if self.session.stream_url == stream_url:
                return {
                    "status": "already_active",
                    "session_id": self.session.session_id
                }
            # Anderen Stream stoppen
            await self.stop()
        
        # Neue Session
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        segment_duration = 1  # 1 Sekunde für präzises Seeking
        # Podcast: 4h Buffer (ganzes File), Radio: Rolling Window
        max_segments = 14400 if is_podcast else max_minutes * 60

        mode_label = "Podcast" if is_podcast else "Radio"
        logger.info(f"HLS Buffer starten ({mode_label}): {station_name}")
        
        # Radio: der Empfang des Senders (ein laufender, etwa von einer Aufnahme, oder ein neuer); ffmpeg bekommt den
        # Ton über stdin. Eine Wiedergabeliste oder ein nicht lesbarer Kopf nimmt den bisherigen Weg (ffmpeg liest
        # selbst, ohne Sendedaten)
        kopf = None
        if not is_podcast:
            try:
                self._empfang = await empfaenge.holen(station_uuid, station_name, stream_url, bitrate, max_minutes * 60)
                kopf = self._empfang.kopf
            except Wiedergabeliste as f:
                logger.info(f"Wiedergabeliste ({f}): ffmpeg liest selbst, ohne Sendedaten")
                self._empfang = None
            except StromFehler as f:
                logger.warning(f"Empfang: {f}; ffmpeg liest selbst, ohne Sendedaten")
                self._empfang = None

        # Stream-Info: aus dem Kopf des Stromlesers, sonst ffprobe (das verbindet sich dafür eigens)
        if kopf and kopf.bitrate and kopf.format:
            stream_info = StreamInfo(codec=kopf.format, bitrate=kopf.bitrate)
        else:
            logger.info(f"Erkenne Stream-Eigenschaften...")
            stream_info = await self._detect_stream_info(stream_url)
        
        # Input-Bitrate: Erkannt oder Fallback
        input_bitrate = stream_info.bitrate if stream_info.bitrate > 0 else bitrate
        
        # Adaptive Output-Bitrate berechnen
        output_bitrate = self._calculate_output_bitrate(
            input_bitrate=input_bitrate,
            min_bitrate=min_bitrate,
            max_bitrate=max_bitrate,
            override_bitrate=override_bitrate
        )
        
        # Original (RAD-92): unverändert übernehmen spart Rechenzeit am Pi und eine zweite verlustbehaftete Umwandlung
        unveraendert = original and not is_podcast and stream_info.codec in KOPIERBAR
        if unveraendert:
            output_bitrate = input_bitrate
            logger.info(f"Ton unverändert: {stream_info.codec} {input_bitrate} kbps")
        else:
            if original:
                logger.info(f"Original nicht möglich ({stream_info.codec}): Umwandlung wie bei voll")
            logger.info(f"Bitrate: Input {input_bitrate} kbps → Output {output_bitrate} kbps (Range: {min_bitrate}-{max_bitrate})")
        
        self.session = HLSSession(
            session_id=session_id,
            station_uuid=station_uuid,
            station_name=station_name,
            stream_url=stream_url,
            start_time=datetime.now(),
            segment_duration=segment_duration,
            max_segments=max_segments,
            input_bitrate=input_bitrate,
            output_bitrate=output_bitrate,
            min_bitrate=min_bitrate,
            max_bitrate=max_bitrate,
            sample_rate=sample_rate,
            input_codec=stream_info.codec,
            is_podcast=is_podcast,
            original=unveraendert
        )
        
        # Buffer-Verzeichnis vorbereiten
        self._ensure_buffer_dir()
        

        # ffmpeg starten
        try:
            cmd = self._build_ffmpeg_cmd(stream_url, aus_empfang=self._empfang is not None,
                                         eingang_format=kopf.format if kopf else None)
            logger.info(f"ffmpeg: {' '.join(cmd[:8])}...")

            self._ffmpeg_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if self._empfang else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )

            # Monitor-Task starten
            self._monitor_task = asyncio.create_task(self._monitor_ffmpeg())

            if self._empfang:
                self._abnehmer = Abnehmer("Zeitversatz", self._in_ffmpeg, None, self._ende_des_tons)
                await self._empfang.anmelden(self._abnehmer)
                self._versatz_s = self._empfang.sekunde(self._abnehmer.ab)

            return {
                "status": "started",
                "session_id": session_id,
                "segment_duration": segment_duration,
                "max_segments": max_segments,
                "playlist_url": "/api/hls/playlist.m3u8"
            }
            
        except FileNotFoundError:
            await self._strom_stoppen()
            self.session = None
            error_msg = "ffmpeg nicht gefunden. Bitte installieren: sudo apt install ffmpeg"
            logger.warning(f"{error_msg}")
            return {"status": "error", "error": error_msg}

        except Exception as e:
            await self._strom_stoppen()
            self.session = None
            logger.warning(f"HLS Start Fehler: {e}")
            return {"status": "error", "error": str(e)}
    
    def _ueberspringt(self) -> bool:
        try:
            return bool(self.session and not self.session.is_podcast and werbespots.ueberspringt(self.session.station_uuid))
        except Exception:
            return False

    async def _in_ffmpeg(self, daten: bytes) -> None:
        """Ton vom Empfang in ffmpeg (stdin); ist ffmpeg weg, meldet sich der Puffer ab."""
        eingang = self._ffmpeg_process.stdin if self._ffmpeg_process else None
        if eingang is None or eingang.is_closing():
            self._abmelden_spaeter()
            return
        try:
            eingang.write(daten)
            await eingang.drain()
        except (BrokenPipeError, ConnectionResetError):
            self._abmelden_spaeter()

    def _abmelden_spaeter(self) -> None:
        e, a = self._empfang, self._abnehmer
        if e and a:
            self._abnehmer = None
            asyncio.create_task(e.abmelden(a))

    async def _ende_des_tons(self) -> None:
        """Der Sender bleibt weg: ffmpeg bekommt das Ende des Tons."""
        prozess = self._ffmpeg_process
        if prozess and prozess.stdin and not prozess.stdin.is_closing():
            prozess.stdin.close()

    async def _strom_stoppen(self) -> None:
        """Vom Empfang abmelden; er endet, wenn keine Aufnahme mehr an ihm hängt."""
        e, a = self._empfang, self._abnehmer
        eintraege = e.titelbuch.entry_count if e else 0
        if eintraege and self.session and self.session.station_uuid:
            logger.info(f"Sendedaten gestoppt ({eintraege} Titelwechsel)")
            self._update_icy_flag(self.session.station_uuid)
        self._empfang, self._abnehmer = None, None
        if e and a:
            await e.abmelden(a)
        elif e and not e.hat_abnehmer:       # verbunden, aber nie angemeldet (Fehler beim Start)
            await e.beenden()

    def _update_icy_flag(self, uuid: str):
        """Setzt icy=1 in detected_bitrates falls noch nicht gesetzt."""
        try:
            from ..database import db_session
            with db_session() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE detected_bitrates SET icy = 1 WHERE uuid = ? AND icy = 0",
                    (uuid,)
                )
                if c.rowcount > 0:
                    logger.info(f"ICY-Flag in DB korrigiert für {uuid[:12]}")
        except Exception as e:
            logger.warning(f"ICY-Flag Update fehlgeschlagen: {e}")

    @property
    def empfang(self) -> Optional[Empfang]:
        """Der Empfang hinter dem Puffer (Radio mit Sendedaten), sonst None."""
        return self._empfang

    @property
    def versatz_s(self) -> float:
        """Sekunde des Empfangs, bei der Stück 0 des Puffers beginnt."""
        return self._versatz_s

    def get_icy_entries(self) -> list[dict]:
        """Titelwechsel der laufenden Sitzung, Stellen in Millisekunden des Puffers (wie die Segmente)."""
        if not self._empfang:
            return []
        v = int(self._versatz_s * 1000)
        return [{**e, "t": e["t"] - v} for e in self._empfang.titelbuch.entries if e["t"] >= v]

    def werbestellen(self, ab_s: float) -> list[dict]:
        """Werbestellen im Puffer ab `ab_s` (Sekunden des Puffers)."""
        if not self._empfang:
            return []
        v = self._versatz_s
        return [{**w.model_dump(), "von": round(w.von - v, 3), "bis": None if w.bis is None else round(w.bis - v, 3)}
                for w in self._empfang.werbung.im_fenster(ab_s + v)]

    def abschnitte(self) -> list[dict]:
        """Die Abschnitte des Puffers (Titel, Werbung, Einschübe) nach der Regel des Feinschnitts, Sekunden des
        Puffers, das letzte läuft noch (RAD-46: Marken im Balken und Großansicht)."""
        if not self._empfang or not self.session:
            return []
        info = self._get_segment_info()
        anfang = (info["first"] or 0) * self.session.segment_duration
        v = self._versatz_s
        liste = self._empfang.stuecke(anfang + v)
        return [{"von": round(max(anfang, s.von - v), 3), "bis": round(s.bis - v, 3), "titel": s.name, "art": s.art,
                 "sicher": s.sicher, "laufend": i == len(liste) - 1} for i, s in enumerate(liste) if s.bis - v > anfang]

    async def _monitor_ffmpeg(self):
        """Überwacht ffmpeg Prozess im Hintergrund"""
        if not self._ffmpeg_process:
            return
            
        try:
            # stderr zeilenweise: Stille geht an die Werbestellen, die letzten Zeilen bleiben für eine Fehlermeldung
            letzte: deque[str] = deque(maxlen=12)
            while (zeile := await self._ffmpeg_process.stderr.readline()):
                letzte.append(zeile.decode("utf-8", errors="ignore").rstrip())
            return_code = await self._ffmpeg_process.wait()

            if self.session:
                stderr_text = "\n".join(letzte)[-500:]
                if return_code != 0 and self.session.is_active:     # beim Stoppen beendet: kein Fehler
                    self.session.error = f"ffmpeg beendet (Code {return_code}): {stderr_text}"
                    logger.warning(f"ffmpeg Fehler: {stderr_text}")
                self.session.is_active = False
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.session:
                self.session.error = str(e)
                self.session.is_active = False
    
    async def stop(self) -> dict:
        """Stoppt HLS Buffering"""
        
        if not self.session:
            return {"status": "not_active"}
        
        station_name = self.session.station_name

        # Stromleser stoppen (vor ffmpeg, damit kein Ton mehr nachkommt); die Sitzung gilt ab hier als beendet
        self.session.is_active = False
        await self._strom_stoppen()

        # ffmpeg beenden
        if self._ffmpeg_process and self._ffmpeg_process.returncode is None:
            try:
                self._ffmpeg_process.terminate()
                await asyncio.wait_for(
                    self._ffmpeg_process.wait(), 
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                self._ffmpeg_process.kill()
                await self._ffmpeg_process.wait()
        
        # Monitor-Task abbrechen
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Aufräumen
        self._ffmpeg_process = None
        self._monitor_task = None
        self.session = None
        
        if self.buffer_dir.exists():
            shutil.rmtree(self.buffer_dir, ignore_errors=True)
        
        logger.info(f"HLS Buffer gestoppt: {station_name}")
        return {"status": "stopped"}
    
    def get_status(self) -> dict:
        """Aktueller Buffer-Status mit Bitrate-Infos"""
        
        if not self.session:
            return {
                "active": False,
                "buffering": False
            }
        
        # Segmente zählen
        segments = self._get_segment_info()
        
        return {
            "active": True,
            "buffering": self.session.is_active,
            "session_id": self.session.session_id,
            "station_uuid": self.session.station_uuid,
            "station_name": self.session.station_name,
            "segment_duration": self.session.segment_duration,
            "segment_count": segments["count"],
            "buffered_seconds": segments["count"] * self.session.segment_duration,
            "first_segment": segments["first"],
            "last_segment": segments["last"],
            "max_segments": self.session.max_segments,
            # Bitrate-Infos
            "input_codec": self.session.input_codec,
            "input_bitrate": self.session.input_bitrate,
            "output_bitrate": self.session.output_bitrate,
            "original": self.session.original,
            "min_bitrate": self.session.min_bitrate,
            "max_bitrate": self.session.max_bitrate,
            "sample_rate": self.session.sample_rate,
            "error": self.session.error,
            # Aktueller ICY-Titel (letzter erkannter)
            "icy_title": (self._empfang.titelbuch.entries[-1].get("title", "")
                          if self._empfang and self._empfang.titelbuch.entries else None),
            # Werbestellen im Puffer (RAD-33), in Sekunden des Tons wie die Segmente, und ob sie hier gelten
            "werbung_ueberspringen": self._ueberspringt(),
            "werbestellen": self.werbestellen((segments["first"] or 0) * self.session.segment_duration),
        }
    
    def _get_segment_info(self) -> dict:
        """Informationen über vorhandene Segmente"""
        if not self.buffer_dir.exists():
            return {"count": 0, "first": None, "last": None}
        
        segment_files = list(self.buffer_dir.glob("segment_*.ts"))
        if not segment_files:
            return {"count": 0, "first": None, "last": None}
        
        # Segment-Nummern extrahieren
        numbers = []
        for f in segment_files:
            try:
                # segment_42.ts -> 42
                num = int(f.stem.split("_")[1])
                numbers.append(num)
            except (ValueError, IndexError):
                pass
        
        if not numbers:
            return {"count": 0, "first": None, "last": None}
            
        return {
            "count": len(numbers),
            "first": min(numbers),
            "last": max(numbers)
        }
    
    def get_playlist(self) -> Optional[str]:
        """Gibt die aktuelle HLS Playlist zurück.
        Segment-URLs enthalten Session-ID zur Cache-Isolation."""
        playlist_path = self.buffer_dir / "playlist.m3u8"

        if not playlist_path.exists():
            return None

        sid = self.get_session_id() or ""

        try:
            content = playlist_path.read_text()
            # Segment-Pfade anpassen für API-Zugriff
            # segment_42.ts -> /api/hls/segment/42?sid=SESSION_ID
            lines = []
            for line in content.split('\n'):
                if line.startswith('segment_') and line.endswith('.ts'):
                    num = line.replace('segment_', '').replace('.ts', '')
                    lines.append(f"/api/hls/segment/{num}?sid={sid}")
                else:
                    lines.append(line)
            return '\n'.join(lines)
        except Exception as e:
            logger.warning(f"Playlist lesen Fehler: {e}")
            return None
    
    def get_segment_path(self, segment_id: int) -> Optional[Path]:
        """Gibt Pfad zu einem Segment zurück"""
        segment_path = self.buffer_dir / f"segment_{segment_id}.ts"
        if segment_path.exists():
            return segment_path
        return None
    
    def get_session_id(self) -> Optional[str]:
        """Gibt aktuelle Session-ID zurück (oder None)"""
        return self.session.session_id if self.session else None

    def is_active(self) -> bool:
        """Prüft ob Buffer aktiv ist"""
        return self.session is not None and self.session.is_active


# Singleton Instanz
hls_buffer = HLSBufferService()
