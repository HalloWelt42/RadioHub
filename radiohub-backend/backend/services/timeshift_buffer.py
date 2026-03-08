"""
RadioHub v0.1.12 - Timeshift Buffer Service (RAM-basiert)

RAM-basierter Ring-Buffer für Live-Radio Timeshift.
Ermöglicht Zurückspulen im Live-Stream und Übernahme in Recording.

Bei 16 GB RAM problemlos 60+ Minuten Buffer möglich.
Kein SD-Karten-Verschleiß, schnelleres Seeking.
"""
import asyncio
import httpx
from collections import deque
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class AudioChunk:
    """Ein Audio-Chunk mit Zeitstempel"""
    data: bytes
    timestamp: float  # Sekunden seit Buffer-Start
    index: int


@dataclass
class BufferSession:
    """Aktive Buffer-Session"""
    session_id: str
    station_uuid: str
    station_name: str
    stream_url: str
    bitrate: int
    format: str  # mp3, aac, ogg, etc.
    
    # Timing
    start_time: datetime
    max_seconds: int  # Konfigurierte Buffer-Größe
    
    # Ring-Buffer (deque für effizientes Pop von links)
    chunks: deque = field(default_factory=deque)
    total_bytes: int = 0
    chunk_index: int = 0
    
    # Playback
    playback_chunk_index: int = 0  # Welcher Chunk wird gerade abgespielt
    is_live: bool = True
    
    # Status
    is_active: bool = True
    error: Optional[str] = None


class TimeshiftBufferManager:
    """
    RAM-basierter Timeshift-Buffer für Live-Radio.
    
    Vorteile gegenüber Datei:
    - Kein SD-Karten-Verschleiß
    - Sofortiges Seeking
    - Einfachere Implementierung
    - Bei 16 GB RAM: 60 Min @ 320kbps = nur 140 MB (0,9%)
    """
    
    CHUNK_SIZE = 16384  # 16 KB pro Chunk (~0.5s bei 256kbps)
    
    def __init__(self):
        self.session: Optional[BufferSession] = None
        self._task: Optional[asyncio.Task] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    def _detect_format(self, content_type: str, url: str) -> str:
        """Erkennt Audio-Format aus Content-Type oder URL"""
        ct = content_type.lower()
        
        if 'mpeg' in ct or 'mp3' in ct:
            return 'mp3'
        elif 'aac' in ct or 'mp4' in ct:
            return 'aac'
        elif 'ogg' in ct:
            return 'ogg'
        elif 'flac' in ct:
            return 'flac'
        
        # Fallback: URL-Endung
        url_lower = url.lower()
        for ext in ['.mp3', '.aac', '.ogg', '.flac', '.m4a']:
            if ext in url_lower:
                return ext[1:]
        
        return 'mp3'  # Default
    
    def _is_seekable_format(self, fmt: str) -> bool:
        """Prüft ob Format seekbar ist"""
        return fmt in ['mp3', 'aac', 'flac']
    
    def _calc_max_chunks(self, bitrate: int, max_seconds: int) -> int:
        """Berechnet maximale Chunk-Anzahl"""
        bytes_per_second = (bitrate * 1000) // 8
        total_bytes = bytes_per_second * max_seconds
        return max(100, total_bytes // self.CHUNK_SIZE)
    
    async def start_buffering(
        self,
        station_uuid: str,
        station_name: str,
        stream_url: str,
        bitrate: int = 128,
        max_minutes: int = 10
    ) -> dict:
        """Startet Buffering eines Streams"""
        
        # Bereits aktiv?
        if self.session and self.session.is_active:
            if self.session.stream_url == stream_url:
                return {
                    "status": "already_buffering",
                    "session_id": self.session.session_id,
                    "format": self.session.format,
                    "seekable": self._is_seekable_format(self.session.format)
                }
            else:
                await self.stop_buffering()
        
        # Session-ID
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Client erstellen und Format erkennen
        self._client = httpx.AsyncClient(timeout=None, follow_redirects=True)
        
        try:
            head_resp = await self._client.head(stream_url, headers={
                "User-Agent": "RadioHub/0.1"
            })
            content_type = head_resp.headers.get("content-type", "audio/mpeg")
            audio_format = self._detect_format(content_type, stream_url)
        except Exception:
            audio_format = "mp3"
        
        # Session erstellen
        max_seconds = max_minutes * 60
        
        self.session = BufferSession(
            session_id=session_id,
            station_uuid=station_uuid,
            station_name=station_name,
            stream_url=stream_url,
            bitrate=bitrate,
            format=audio_format,
            start_time=datetime.now(),
            max_seconds=max_seconds,
            chunks=deque(maxlen=self._calc_max_chunks(bitrate, max_seconds))
        )
        
        # Buffer-Task starten
        self._task = asyncio.create_task(self._buffer_loop())
        
        print(f"✓ Timeshift-Buffer gestartet: {station_name} ({audio_format}, max {max_minutes} Min)")
        
        return {
            "status": "started",
            "session_id": session_id,
            "format": audio_format,
            "seekable": self._is_seekable_format(audio_format),
            "max_seconds": max_seconds
        }
    
    async def stop_buffering(self) -> dict:
        """Stoppt Buffering und gibt RAM frei"""
        
        if not self.session:
            return {"status": "not_buffering"}
        
        self.session.is_active = False
        
        # Task abbrechen
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Client schließen
        if self._client:
            await self._client.aclose()
            self._client = None
        
        session_id = self.session.session_id
        total_mb = self.session.total_bytes / (1024 * 1024)
        
        # RAM freigeben
        self.session.chunks.clear()
        self.session = None
        
        print(f"✓ Timeshift-Buffer gestoppt ({total_mb:.1f} MB freigegeben)")
        
        return {"status": "stopped", "session_id": session_id}
    
    async def _buffer_loop(self):
        """Haupt-Buffer-Schleife - liest Stream in RAM"""
        
        if not self.session or not self._client:
            return
        
        try:
            async with self._client.stream(
                "GET",
                self.session.stream_url,
                headers={
                    "User-Agent": "RadioHub/0.1",
                    "Icy-MetaData": "0"
                }
            ) as response:
                
                buffer = b""
                bytes_per_second = (self.session.bitrate * 1000) // 8
                
                async for data in response.aiter_bytes(chunk_size=4096):
                    if not self.session or not self.session.is_active:
                        break
                    
                    buffer += data
                    
                    # Wenn genug Daten, Chunk erstellen
                    while len(buffer) >= self.CHUNK_SIZE:
                        chunk_data = buffer[:self.CHUNK_SIZE]
                        buffer = buffer[self.CHUNK_SIZE:]
                        
                        # Zeitstempel berechnen
                        elapsed = (datetime.now() - self.session.start_time).total_seconds()
                        
                        chunk = AudioChunk(
                            data=chunk_data,
                            timestamp=elapsed,
                            index=self.session.chunk_index
                        )
                        
                        # In Ring-Buffer (deque mit maxlen entfernt automatisch alte)
                        self.session.chunks.append(chunk)
                        self.session.total_bytes = len(self.session.chunks) * self.CHUNK_SIZE
                        self.session.chunk_index += 1
                        
                        # Wenn live, Playback-Position nachführen
                        if self.session.is_live:
                            self.session.playback_chunk_index = len(self.session.chunks) - 1
                            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"✗ Buffer error: {e}")
            if self.session:
                self.session.error = str(e)
                self.session.is_active = False
    
    def get_status(self) -> dict:
        """Aktueller Buffer-Status"""
        
        if not self.session:
            return {
                "active": False,
                "buffering": False
            }
        
        # Gepufferte Sekunden
        bytes_per_second = (self.session.bitrate * 1000) // 8
        buffered_seconds = self.session.total_bytes / bytes_per_second if bytes_per_second > 0 else 0
        
        # Aktuelle Position
        if self.session.chunks and len(self.session.chunks) > 0:
            if self.session.playback_chunk_index < len(self.session.chunks):
                current_chunk = self.session.chunks[self.session.playback_chunk_index]
                playback_position = current_chunk.timestamp
            else:
                playback_position = buffered_seconds
        else:
            playback_position = 0
        
        return {
            "active": True,
            "buffering": self.session.is_active,
            "session_id": self.session.session_id,
            "station_name": self.session.station_name,
            "format": self.session.format,
            "seekable": self._is_seekable_format(self.session.format),
            "buffered_seconds": round(buffered_seconds, 1),
            "max_seconds": self.session.max_seconds,
            "playback_position": round(playback_position, 1),
            "is_live": self.session.is_live,
            "total_bytes": self.session.total_bytes,
            "total_mb": round(self.session.total_bytes / (1024 * 1024), 2),
            "chunks": len(self.session.chunks),
            "error": self.session.error
        }
    
    def seek(self, position_seconds: float) -> dict:
        """Springt zu Position im Buffer"""
        
        if not self.session or not self.session.is_active:
            return {"success": False, "error": "Nicht am Buffern"}
        
        if not self._is_seekable_format(self.session.format):
            return {"success": False, "error": f"Format {self.session.format} nicht seekbar"}
        
        if not self.session.chunks:
            return {"success": False, "error": "Buffer leer"}
        
        # Chunk finden der am nächsten zur Position ist
        target_chunk_idx = 0
        for i, chunk in enumerate(self.session.chunks):
            if chunk.timestamp <= position_seconds:
                target_chunk_idx = i
            else:
                break
        
        self.session.playback_chunk_index = target_chunk_idx
        
        # Prüfen ob live (innerhalb letzter 2 Sekunden)
        buffered_seconds = self.session.total_bytes / ((self.session.bitrate * 1000) // 8)
        self.session.is_live = (position_seconds >= buffered_seconds - 2)
        
        actual_position = self.session.chunks[target_chunk_idx].timestamp if self.session.chunks else 0
        
        return {
            "success": True,
            "position": round(actual_position, 1),
            "is_live": self.session.is_live
        }
    
    def go_live(self) -> dict:
        """Springt zum Live-Punkt"""
        
        if not self.session or not self.session.is_active:
            return {"success": False, "error": "Nicht am Buffern"}
        
        self.session.playback_chunk_index = len(self.session.chunks) - 1 if self.session.chunks else 0
        self.session.is_live = True
        
        buffered_seconds = self.session.total_bytes / ((self.session.bitrate * 1000) // 8)
        
        return {
            "success": True,
            "position": round(buffered_seconds, 1),
            "is_live": True
        }
    
    def get_audio_data(self, from_position: float = 0) -> Optional[bytes]:
        """
        Holt Audio-Daten ab Position.
        
        Returns:
            Alle Chunks ab Position als zusammenhängende Bytes
        """
        
        if not self.session or not self.session.chunks:
            return None
        
        # Start-Chunk finden
        start_idx = 0
        for i, chunk in enumerate(self.session.chunks):
            if chunk.timestamp >= from_position:
                start_idx = i
                break
        
        # Alle Chunks ab Position zusammenfügen
        data = b""
        for i in range(start_idx, len(self.session.chunks)):
            data += self.session.chunks[i].data
        
        return data if data else None
    
    def get_current_chunk(self) -> Optional[bytes]:
        """Holt aktuellen Playback-Chunk und rückt vor"""
        
        if not self.session or not self.session.chunks:
            return None
        
        if self.session.playback_chunk_index >= len(self.session.chunks):
            self.session.playback_chunk_index = len(self.session.chunks) - 1
        
        if self.session.playback_chunk_index < 0:
            return None
        
        chunk = self.session.chunks[self.session.playback_chunk_index]
        
        # Vorwärts wenn nicht live
        if not self.session.is_live and self.session.playback_chunk_index < len(self.session.chunks) - 1:
            self.session.playback_chunk_index += 1
        
        return chunk.data
    
    async def convert_to_recording(self, include_buffer: bool = True) -> dict:
        """Konvertiert Buffer zu Recording"""
        
        if not self.session:
            return {"success": False, "error": "Kein Buffer aktiv"}
        
        from .recorder import rec_manager
        
        # Recording starten
        result = rec_manager.start(
            station_uuid=self.session.station_uuid,
            station_name=self.session.station_name,
            stream_url=self.session.stream_url,
            bitrate=self.session.bitrate
        )
        
        if not result.get("success"):
            return result
        
        # Buffer-Daten in Recording übernehmen
        if include_buffer and self.session.chunks:
            try:
                from pathlib import Path
                rec_path = Path(result.get("file_path", ""))
                
                if rec_path.exists():
                    # Buffer-Daten sammeln
                    buffer_data = b"".join(chunk.data for chunk in self.session.chunks)
                    
                    # An Recording-Datei voranstellen
                    with open(rec_path, 'r+b') as f:
                        existing = f.read()
                        f.seek(0)
                        f.write(buffer_data + existing)
                    
                    buffer_mb = len(buffer_data) / (1024 * 1024)
                    print(f"✓ Buffer ({buffer_mb:.1f} MB) in Recording übernommen")
            except Exception as e:
                print(f"✗ Buffer-Übernahme fehlgeschlagen: {e}")
        
        return {
            "success": True,
            "recording_session_id": result.get("session_id"),
            "buffer_included": include_buffer,
            "buffer_bytes": self.session.total_bytes if include_buffer else 0
        }


# Singleton
timeshift_buffer = TimeshiftBufferManager()

