"""
RadioHub v0.1.4 - Recording Router

Aufnahme starten/stoppen, Sessions verwalten
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from ..services.recorder import rec_manager
from ..config import RADIO_RECORDINGS_DIR

router = APIRouter(prefix="/api/recording", tags=["recording"])


class RecordingStartRequest(BaseModel):
    station_uuid: str
    station_name: str
    stream_url: str
    bitrate: int = 0


@router.post("/start")
async def start_recording(req: RecordingStartRequest):
    """Startet Aufnahme"""
    result = rec_manager.start(
        station_uuid=req.station_uuid,
        station_name=req.station_name,
        stream_url=req.stream_url,
        bitrate=req.bitrate
    )
    
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Fehler"))
    
    return result


@router.post("/stop")
async def stop_recording():
    """Stoppt aktive Aufnahme"""
    result = rec_manager.stop()
    
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Keine aktive Aufnahme"))
    
    return result


@router.get("/status")
async def recording_status():
    """Aktueller Aufnahme-Status"""
    return rec_manager.get_status()


@router.get("/sessions")
async def get_sessions(limit: int = 50):
    """Alle Sessions"""
    sessions = rec_manager.get_sessions(limit)
    return {"count": len(sessions), "sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Einzelne Session"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Session löschen"""
    success = rec_manager.delete_session(session_id)
    if not success:
        raise HTTPException(404, "Session nicht gefunden")
    return {"success": True}


@router.get("/download/{filename}")
async def download_recording(filename: str):
    """Aufnahme herunterladen"""
    file_path = RADIO_RECORDINGS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(404, "Datei nicht gefunden")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="audio/mpeg"
    )
