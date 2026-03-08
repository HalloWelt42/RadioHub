"""
RadioHub v0.1.7 - Stream Buffer Service

Buffert Live-Streams für stabiles Playback und Seek-Funktion.
Speichert Chunks im Speicher für schnelles Zurückspulen.
"""
import asyncio
import httpx
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class BufferChunk:
    """Ein Chunk aus dem Stream"""
    data: bytes
    timestamp: float
    index: int


@dataclass
class BufferState:
    """Aktueller Buffer-Zustand"""
    stream_url: str = ""
    is_buffering: bool = False
    chunks: List[BufferChunk] = field(default_factory=list)
    current_index: int = 0
    start_time: Optional[datetime] = None
    total_bytes: int = 0
    
    # Konfiguration
    max_chunks: int = 600  # ~10 Minuten bei 1s Chunks
    chunk_size: int = 16384  # 16KB pro Chunk


class StreamBufferManager:
    """Verwaltet Stream-Buffering"""
    
    def __init__(self):
        self.state = BufferState()
        self._task: Optional[asyncio.Task] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def start_buffering(self, stream_url: str) -> dict:
        """Startet Buffering eines Streams"""
        
        # Bereits aktiv?
        if self.state.is_buffering:
            if self.state.stream_url == stream_url:
                return {"status": "already_buffering", "stream_url": stream_url}
            else:
                await self.stop_buffering()
        
        # Neuen State initialisieren
        self.state = BufferState(
            stream_url=stream_url,
            is_buffering=True,
            start_time=datetime.now()
        )
        
        # Client erstellen
        self._client = httpx.AsyncClient(timeout=None, follow_redirects=True)
        
        # Buffer-Task starten
        self._task = asyncio.create_task(self._buffer_loop())
        
        print(f"✓ Buffer gestartet: {stream_url[:50]}...")
        return {"status": "started", "stream_url": stream_url}
    
    async def stop_buffering(self) -> dict:
        """Stoppt Buffering"""
        
        if not self.state.is_buffering:
            return {"status": "not_buffering"}
        
        self.state.is_buffering = False
        
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
        
        # State zurücksetzen
        url = self.state.stream_url
        self.state = BufferState()
        
        print(f"✓ Buffer gestoppt")
        return {"status": "stopped", "stream_url": url}
    
    async def _buffer_loop(self):
        """Haupt-Buffer-Schleife"""
        try:
            async with self._client.stream("GET", self.state.stream_url, headers={
                "User-Agent": "RadioHub/0.1",
                "Icy-MetaData": "1"
            }) as response:
                
                chunk_index = 0
                buffer = b""
                
                async for data in response.aiter_bytes(chunk_size=4096):
                    if not self.state.is_buffering:
                        break
                    
                    buffer += data
                    
                    # Wenn genug Daten, Chunk erstellen
                    while len(buffer) >= self.state.chunk_size:
                        chunk_data = buffer[:self.state.chunk_size]
                        buffer = buffer[self.state.chunk_size:]
                        
                        chunk = BufferChunk(
                            data=chunk_data,
                            timestamp=asyncio.get_event_loop().time(),
                            index=chunk_index
                        )
                        
                        self.state.chunks.append(chunk)
                        self.state.total_bytes += len(chunk_data)
                        chunk_index += 1
                        
                        # Alte Chunks entfernen
                        while len(self.state.chunks) > self.state.max_chunks:
                            removed = self.state.chunks.pop(0)
                            self.state.total_bytes -= len(removed.data)
                        
                        # Current Index nachführen (wenn am Ende)
                        if self.state.current_index >= len(self.state.chunks) - 2:
                            self.state.current_index = len(self.state.chunks) - 1
                            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"✗ Buffer error: {e}")
            self.state.is_buffering = False
    
    def get_status(self) -> dict:
        """Aktueller Buffer-Status"""
        if not self.state.is_buffering:
            return {"buffering": False}
        
        buffer_seconds = len(self.state.chunks) * (self.state.chunk_size / 16000)  # ~16KB/s
        current_offset = (len(self.state.chunks) - 1 - self.state.current_index) * (self.state.chunk_size / 16000)
        
        return {
            "buffering": True,
            "stream_url": self.state.stream_url,
            "chunks": len(self.state.chunks),
            "total_bytes": self.state.total_bytes,
            "buffer_seconds": round(buffer_seconds, 1),
            "current_index": self.state.current_index,
            "current_offset_seconds": round(current_offset, 1),
            "is_live": self.state.current_index >= len(self.state.chunks) - 2
        }
    
    def seek(self, seconds_ago: int) -> dict:
        """Springt X Sekunden zurück"""
        if not self.state.is_buffering or not self.state.chunks:
            return {"success": False, "error": "Nicht am Buffern"}
        
        # Chunks pro Sekunde berechnen (~16KB/s bei 128kbps)
        chunks_per_second = 16000 / self.state.chunk_size
        chunks_back = int(seconds_ago * chunks_per_second)
        
        new_index = len(self.state.chunks) - 1 - chunks_back
        new_index = max(0, min(new_index, len(self.state.chunks) - 1))
        
        self.state.current_index = new_index
        
        actual_offset = (len(self.state.chunks) - 1 - new_index) / chunks_per_second
        
        return {
            "success": True,
            "requested_seconds": seconds_ago,
            "actual_offset_seconds": round(actual_offset, 1),
            "chunk_index": new_index
        }
    
    def go_live(self) -> dict:
        """Springt zum Live-Punkt"""
        if not self.state.is_buffering or not self.state.chunks:
            return {"success": False, "error": "Nicht am Buffern"}
        
        self.state.current_index = len(self.state.chunks) - 1
        return {"success": True, "is_live": True}
    
    async def get_audio_chunk(self) -> Optional[bytes]:
        """Holt aktuellen Audio-Chunk für Streaming"""
        if not self.state.is_buffering or not self.state.chunks:
            return None
        
        if self.state.current_index >= len(self.state.chunks):
            self.state.current_index = len(self.state.chunks) - 1
        
        if self.state.current_index < 0:
            return None
        
        chunk = self.state.chunks[self.state.current_index]
        
        # Automatisch vorwärts wenn nicht live
        if self.state.current_index < len(self.state.chunks) - 1:
            self.state.current_index += 1
        
        return chunk.data


# Singleton
buffer_manager = StreamBufferManager()
