"""
RadioHub v0.1.12 - Buffer Router

API-Endpunkte für Timeshift-Buffering (RAM-basiert).
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from ..services.timeshift_buffer import timeshift_buffer
from ..config import AUDIO_MIMETYPES

router = APIRouter(prefix="/api/buffer", tags=["buffer"])


class BufferStartRequest(BaseModel):
    station_uuid: str
    station_name: str
    stream_url: str
    bitrate: int = 128
    max_minutes: int = 10


class BufferSeekRequest(BaseModel):
    position_seconds: float


# === Buffer Control ===

@router.post("/start")
async def start_buffering(req: BufferStartRequest):
    """
    Startet Timeshift-Buffering für einen Stream.
    
    - station_uuid: UUID der Station
    - station_name: Name der Station
    - stream_url: Stream-URL
    - bitrate: Bitrate in kbps (Standard: 128)
    - max_minutes: Buffer-Größe in Minuten (Standard: 10)
    
    RAM-Verbrauch: ~1 MB pro Minute bei 128 kbps
    """
    result = await timeshift_buffer.start_buffering(
        station_uuid=req.station_uuid,
        station_name=req.station_name,
        stream_url=req.stream_url,
        bitrate=req.bitrate,
        max_minutes=req.max_minutes
    )
    return result


@router.post("/stop")
async def stop_buffering():
    """Stoppt Buffering und gibt RAM frei"""
    result = await timeshift_buffer.stop_buffering()
    return result


@router.get("/status")
async def get_status():
    """
    Aktueller Buffer-Status.
    
    Returns:
        - active: Buffer aktiv?
        - buffering: Liest gerade Stream?
        - buffered_seconds: Gepufferte Sekunden
        - max_seconds: Maximale Buffer-Größe
        - playback_position: Aktuelle Position
        - is_live: Am Live-Punkt?
        - format: Audio-Format
        - seekable: Format unterstützt Seeking?
        - total_mb: RAM-Verbrauch in MB
    """
    return timeshift_buffer.get_status()


@router.post("/seek")
async def seek_position(req: BufferSeekRequest):
    """
    Springt zu Position im Buffer.
    
    - position_seconds: Ziel-Position (0 = ältester Punkt)
    """
    result = timeshift_buffer.seek(req.position_seconds)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Seek fehlgeschlagen"))
    return result


@router.post("/live")
async def go_live():
    """Springt zum Live-Punkt"""
    result = timeshift_buffer.go_live()
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Go-Live fehlgeschlagen"))
    return result


@router.post("/to-recording")
async def convert_to_recording(include_buffer: bool = Query(True)):
    """
    Konvertiert Buffer zu Recording und startet Aufnahme.
    
    - include_buffer: Buffer-Inhalt übernehmen? (Standard: ja)
    
    Wenn include_buffer=true, wird der gesamte Buffer-Inhalt
    an den Anfang der Recording-Datei geschrieben.
    """
    result = await timeshift_buffer.convert_to_recording(include_buffer=include_buffer)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Konvertierung fehlgeschlagen"))
    return result


# === Audio Stream ===

@router.get("/stream")
async def get_buffer_stream(position: float = Query(0, description="Start-Position in Sekunden")):
    """
    Streamt Audio-Daten aus dem RAM-Buffer ab Position.
    
    Gibt alle gepufferten Daten ab der angegebenen Position zurück.
    """
    data = timeshift_buffer.get_audio_data(from_position=position)
    
    if not data:
        raise HTTPException(404, "Kein Buffer verfügbar oder leer")
    
    status = timeshift_buffer.get_status()
    
    # Content-Type basierend auf Format
    fmt = status.get("format", "mp3")
    content_type = AUDIO_MIMETYPES.get(f".{fmt}", "audio/mpeg")

    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(data)),
            "Cache-Control": "no-cache"
        }
    )


@router.get("/chunk")
async def get_current_chunk():
    """
    Holt den aktuellen Playback-Chunk.
    
    Für kontinuierliches Streaming: Frontend ruft dies wiederholt auf.
    """
    data = timeshift_buffer.get_current_chunk()
    
    if not data:
        raise HTTPException(404, "Kein Chunk verfügbar")
    
    status = timeshift_buffer.get_status()
    fmt = status.get("format", "mp3")
    content_type = AUDIO_MIMETYPES.get(f".{fmt}", "audio/mpeg")

    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "no-cache"}
    )
