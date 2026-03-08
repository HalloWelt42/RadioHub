"""
RadioHub HLS Buffer Service v1.1.0

HLS (HTTP Live Streaming) basierter Timeshift Buffer.
Nutzt ffmpeg um Radio-Streams in seekbare Segmente zu konvertieren.
Mit adaptiver Bitrate-Anpassung.

© HalloWelt42 - Nur für private Nutzung
"""
import asyncio
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


# Standard-Bitrate-Stufen (kbps)
STANDARD_BITRATES = [32, 48, 64, 96, 128, 192, 256, 320]


def snap_to_step(bitrate: int) -> int:
    """Rundet auf die naechste Standard-Bitrate ab (nicht hoeher als Input)."""
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
    is_active: bool = True
    error: Optional[str] = None


class HLSBufferService:
    """
    HLS Buffer Service
    
    Konvertiert Radio-Stream via ffmpeg in HLS-Segmente.
    Ermöglicht exaktes Seeking durch segment-basiertes Streaming.
    Mit adaptiver Bitrate basierend auf Input-Stream.
    """
    
    def __init__(self, buffer_dir: str = "/tmp/radiohub-hls"):
        self.buffer_dir = Path(buffer_dir)
        self.session: Optional[HLSSession] = None
        self._ffmpeg_process: Optional[asyncio.subprocess.Process] = None
        self._monitor_task: Optional[asyncio.Task] = None
        
    def _ensure_buffer_dir(self):
        """Buffer-Verzeichnis erstellen/leeren"""
        if self.buffer_dir.exists():
            shutil.rmtree(self.buffer_dir)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Buffer-Verzeichnis: {self.buffer_dir}")
    
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
                print(f"  ⚠ ffprobe Timeout nach {timeout}s - nutze Defaults")
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
                    
                    print(f"  📊 Stream erkannt: {info.codec} @ {info.bitrate} kbps, {info.sample_rate} Hz")
                    
        except Exception as e:
            print(f"  ⚠ Stream-Erkennung fehlgeschlagen: {e}")
        
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
        Sonst: Nicht hoeher als Input, auf Standard-Stufe snappen.
        """
        if override_bitrate and override_bitrate > 0:
            # User hat explizit gewaehlt
            return override_bitrate

        if input_bitrate <= 0:
            # Unbekannt -> max_bitrate als sicherer Fallback
            return snap_to_step(max_bitrate)

        # Nicht hoeher als Input (Aufblaehen ist sinnlos)
        output = min(input_bitrate, max_bitrate)
        # Aber mindestens min_bitrate
        output = max(output, min_bitrate)
        # Auf Standard-Stufe snappen
        return snap_to_step(output)
        
    def _build_ffmpeg_cmd(self, stream_url: str) -> list:
        """ffmpeg Kommando für HLS-Segmentierung mit adaptiver Bitrate"""
        playlist = self.buffer_dir / "playlist.m3u8"
        segment_pattern = str(self.buffer_dir / "segment_%d.ts")
        
        return [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-y",  # Überschreiben ohne Nachfrage
            "-reconnect", "1",
            "-reconnect_streamed", "1", 
            "-reconnect_delay_max", "5",
            "-i", stream_url,
            # Audio Filter: Normalisierung für konsistente Lautstärke
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            # Audio Encoding (adaptive Bitrate!)
            "-c:a", "aac",
            "-b:a", f"{self.session.output_bitrate}k",
            "-ac", "2",  # Stereo
            "-ar", str(self.session.sample_rate),
            # HLS Output
            "-f", "hls",
            "-hls_time", str(self.session.segment_duration),
            "-hls_list_size", str(self.session.max_segments),
            "-hls_flags", "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename", segment_pattern,
            str(playlist)
        ]
    
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
        override_bitrate: int = 0
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
        max_segments = max_minutes * 60  # Bei 1s Segmenten
        
        print(f"✓ HLS Buffer starten: {station_name}")
        
        # Stream-Info erkennen
        print(f"  🔍 Erkenne Stream-Eigenschaften...")
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
        
        print(f"  📈 Bitrate: Input {input_bitrate} kbps → Output {output_bitrate} kbps (Range: {min_bitrate}-{max_bitrate})")
        
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
            input_codec=stream_info.codec
        )
        
        # Buffer-Verzeichnis vorbereiten
        self._ensure_buffer_dir()
        
        # ffmpeg starten
        try:
            cmd = self._build_ffmpeg_cmd(stream_url)
            print(f"  ffmpeg: {' '.join(cmd[:5])}...")
            
            self._ffmpeg_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor-Task starten
            self._monitor_task = asyncio.create_task(self._monitor_ffmpeg())
            
            return {
                "status": "started",
                "session_id": session_id,
                "segment_duration": segment_duration,
                "max_segments": max_segments,
                "playlist_url": "/api/hls/playlist.m3u8"
            }
            
        except FileNotFoundError:
            self.session = None
            error_msg = "ffmpeg nicht gefunden. Bitte installieren: sudo apt install ffmpeg"
            print(f"✗ {error_msg}")
            return {"status": "error", "error": error_msg}
            
        except Exception as e:
            self.session = None
            print(f"✗ HLS Start Fehler: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _monitor_ffmpeg(self):
        """Überwacht ffmpeg Prozess im Hintergrund"""
        if not self._ffmpeg_process:
            return
            
        try:
            # Warten bis Prozess endet
            stderr_data = await self._ffmpeg_process.stderr.read()
            return_code = await self._ffmpeg_process.wait()
            
            if self.session:
                stderr_text = stderr_data.decode('utf-8', errors='ignore')[-500:]
                if return_code != 0:
                    self.session.error = f"ffmpeg beendet (Code {return_code}): {stderr_text}"
                    print(f"✗ ffmpeg Fehler: {stderr_text}")
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
        
        print(f"✓ HLS Buffer gestoppt: {station_name}")
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
            "min_bitrate": self.session.min_bitrate,
            "max_bitrate": self.session.max_bitrate,
            "sample_rate": self.session.sample_rate,
            "error": self.session.error
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
        """Gibt die aktuelle HLS Playlist zurueck.
        Segment-URLs enthalten Session-ID zur Cache-Isolation."""
        playlist_path = self.buffer_dir / "playlist.m3u8"

        if not playlist_path.exists():
            return None

        sid = self.get_session_id() or ""

        try:
            content = playlist_path.read_text()
            # Segment-Pfade anpassen fuer API-Zugriff
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
            print(f"Playlist lesen Fehler: {e}")
            return None
    
    def get_segment_path(self, segment_id: int) -> Optional[Path]:
        """Gibt Pfad zu einem Segment zurück"""
        segment_path = self.buffer_dir / f"segment_{segment_id}.ts"
        if segment_path.exists():
            return segment_path
        return None
    
    def get_session_id(self) -> Optional[str]:
        """Gibt aktuelle Session-ID zurueck (oder None)"""
        return self.session.session_id if self.session else None

    def is_active(self) -> bool:
        """Prueft ob Buffer aktiv ist"""
        return self.session is not None and self.session.is_active


# Singleton Instanz
hls_buffer = HLSBufferService()
