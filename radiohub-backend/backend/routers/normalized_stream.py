"""
RadioHub v0.1.13 - Normalized Stream Router

Streamt Radio durch FFmpeg loudnorm Filter für Lautstärke-Angleichung.
"""
import asyncio
import subprocess
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/stream", tags=["stream"])


class StreamStartRequest(BaseModel):
    stream_url: str
    target_lufs: float = -16.0  # Standard für Podcasts/Radio
    

# Aktiver FFmpeg-Prozess
_ffmpeg_process: Optional[subprocess.Popen] = None
_current_url: Optional[str] = None


def _stop_ffmpeg():
    """Stoppt laufenden FFmpeg-Prozess"""
    global _ffmpeg_process, _current_url
    if _ffmpeg_process:
        try:
            _ffmpeg_process.terminate()
            _ffmpeg_process.wait(timeout=2)
        except:
            _ffmpeg_process.kill()
        _ffmpeg_process = None
        _current_url = None


@router.get("/normalized")
async def get_normalized_stream(
    url: str = Query(..., description="Stream-URL"),
    lufs: float = Query(-16.0, description="Ziel-LUFS (-16 = Standard)")
):
    """
    Streamt Audio durch FFmpeg mit Lautstärke-Normalisierung.
    
    FFmpeg loudnorm Filter normalisiert auf Ziel-LUFS.
    Latenz: ~2-3 Sekunden durch Look-ahead Buffer.
    
    Args:
        url: Stream-URL
        lufs: Ziel-LUFS (Standard: -16, Bereich: -24 bis -5)
    """
    global _ffmpeg_process, _current_url
    
    # LUFS validieren
    lufs = max(-24.0, min(-5.0, lufs))
    
    # Wenn gleiche URL, weiterlaufen lassen
    if _current_url == url and _ffmpeg_process and _ffmpeg_process.poll() is None:
        # Bereits am Streamen
        pass
    else:
        # Alten Prozess stoppen
        _stop_ffmpeg()
        _current_url = url
    
    async def stream_generator():
        global _ffmpeg_process
        
        try:
            # FFmpeg Command für Normalisierung
            # loudnorm Filter: I=integrierter LUFS, TP=True Peak, LRA=Loudness Range
            cmd = [
                "ffmpeg",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-i", url,
                "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=none",
                "-c:a", "libmp3lame",
                "-b:a", "192k",
                "-f", "mp3",
                "-"
            ]
            
            _ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=4096
            )
            
            # Stream-Chunks ausgeben
            while True:
                if _ffmpeg_process.poll() is not None:
                    break
                    
                chunk = _ffmpeg_process.stdout.read(4096)
                if not chunk:
                    await asyncio.sleep(0.01)
                    continue
                    
                yield chunk
                
        except Exception as e:
            print(f"✗ Stream error: {e}")
        finally:
            _stop_ffmpeg()
    
    return StreamingResponse(
        stream_generator(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Normalized-LUFS": str(lufs)
        }
    )


@router.post("/normalized/stop")
async def stop_normalized_stream():
    """Stoppt den normalisierten Stream"""
    _stop_ffmpeg()
    return {"success": True, "message": "Stream gestoppt"}


@router.get("/normalized/status")
async def get_stream_status():
    """Status des normalisierten Streams"""
    global _ffmpeg_process, _current_url
    
    is_active = _ffmpeg_process is not None and _ffmpeg_process.poll() is None
    
    return {
        "active": is_active,
        "url": _current_url if is_active else None
    }
