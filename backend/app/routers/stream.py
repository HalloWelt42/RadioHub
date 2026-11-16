"""
RadioHub v0.1.7 - Stream Router

Buffer-basiertes Streaming mit Seek-Funktion
"""
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services.stream_buffer import buffer_manager

router = APIRouter(prefix="/api/stream", tags=["stream"])


class BufferStartRequest(BaseModel):
    stream_url: str


class SeekRequest(BaseModel):
    seconds_ago: int


@router.get("/buffer/status")
async def buffer_status():
    """Aktueller Buffer-Status"""
    return buffer_manager.get_status()


@router.post("/buffer/start")
async def buffer_start(req: BufferStartRequest):
    """Startet Buffering eines Streams"""
    if not req.stream_url:
        raise HTTPException(400, "stream_url erforderlich")
    
    result = await buffer_manager.start_buffering(req.stream_url)
    return result


@router.post("/buffer/stop")
async def buffer_stop():
    """Stoppt Buffering"""
    result = await buffer_manager.stop_buffering()
    return result


@router.post("/buffer/seek")
async def buffer_seek(req: SeekRequest):
    """Springt X Sekunden zurück im Buffer"""
    result = buffer_manager.seek(req.seconds_ago)
    
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Seek fehlgeschlagen"))
    
    return result


@router.post("/buffer/go-live")
async def buffer_go_live():
    """Springt zum Live-Punkt"""
    result = buffer_manager.go_live()
    
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Go-Live fehlgeschlagen"))
    
    return result


@router.get("/buffer/audio")
async def buffer_audio():
    """Streamt Audio aus dem Buffer"""
    
    if not buffer_manager.state.is_buffering:
        raise HTTPException(400, "Nicht am Buffern")
    
    async def generate():
        """Generator für Audio-Chunks"""
        while buffer_manager.state.is_buffering:
            chunk = await buffer_manager.get_audio_chunk()
            
            if chunk:
                yield chunk
            else:
                # Warten auf neue Daten
                await asyncio.sleep(0.1)
    
    return StreamingResponse(
        generate(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked"
        }
    )
