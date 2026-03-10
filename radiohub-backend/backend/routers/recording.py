"""
RadioHub v0.2.1 - Recording Router

Aufnahme starten/stoppen, Sessions verwalten, Segment-Verwaltung.
Async start/stop, dynamischer Media-Type.
"""
import json
import os
import zipfile
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from pathlib import Path

from ..services.recorder import rec_manager, EXTENSION_MIMETYPES
from ..services.segment_splitter import splitter
from ..config import RADIO_RECORDINGS_DIR

router = APIRouter(prefix="/api/recording", tags=["recording"])


class RecordingStartRequest(BaseModel):
    station_uuid: str
    station_name: str
    stream_url: str
    bitrate: int = 0


@router.post("/start")
async def start_recording(req: RecordingStartRequest):
    """Startet Aufnahme (async mit Codec-Erkennung)"""
    result = await rec_manager.start(
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
    result = await rec_manager.stop()

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
    """Session loeschen"""
    success = rec_manager.delete_session(session_id)
    if not success:
        raise HTTPException(404, "Session nicht gefunden oder aktiv")
    return {"success": True}


@router.get("/sessions/{session_id}/metadata")
async def get_session_metadata(session_id: str):
    """ICY-Metadata einer Session (Titelwechsel mit Zeitstempeln)"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    meta_path = session.get("meta_file_path")
    if not meta_path:
        return {"entries": [], "count": 0}

    meta_file = Path(meta_path)
    if not meta_file.exists():
        return {"entries": [], "count": 0}

    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Neues Format (dict mit entries) vs Legacy (flache Liste)
        if isinstance(raw, dict):
            entries = raw.get("entries", [])
        else:
            entries = raw
        return {"entries": entries, "count": len(entries)}
    except Exception:
        return {"entries": [], "count": 0}


@router.get("/download/{filename}")
async def download_recording(filename: str):
    """Aufnahme herunterladen (dynamischer Content-Type)"""
    file_path = RADIO_RECORDINGS_DIR / filename

    if not file_path.exists():
        raise HTTPException(404, "Datei nicht gefunden")

    # Dynamischer MIME-Type basierend auf Dateiendung
    ext = file_path.suffix.lower()
    media_type = EXTENSION_MIMETYPES.get(ext, "audio/mpeg")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


# === Segment-Endpoints ===

@router.get("/sessions/{session_id}/segments")
async def get_segments(session_id: str):
    """Alle Segmente einer Session"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    segments = splitter.get_segments(session_id)
    return {"count": len(segments), "segments": segments}


@router.get("/segments/{segment_id}/play")
async def play_segment(segment_id: int):
    """Einzelnes Segment streamen"""
    segment = splitter.get_segment(segment_id)
    if not segment:
        raise HTTPException(404, "Segment nicht gefunden")

    file_path = Path(segment["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "Segment-Datei nicht gefunden")

    ext = file_path.suffix.lower()
    media_type = EXTENSION_MIMETYPES.get(ext, "audio/mpeg")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_path.stat().st_size),
        }
    )


@router.get("/segments/{segment_id}/download")
async def download_segment(segment_id: int):
    """Einzelnes Segment herunterladen"""
    segment = splitter.get_segment(segment_id)
    if not segment:
        raise HTTPException(404, "Segment nicht gefunden")

    file_path = Path(segment["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "Segment-Datei nicht gefunden")

    ext = file_path.suffix.lower()
    media_type = EXTENSION_MIMETYPES.get(ext, "audio/mpeg")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'}
    )


@router.delete("/sessions/{session_id}/segments/{segment_id}")
async def delete_segment(session_id: str, segment_id: int):
    """Einzelnes Segment loeschen"""
    success = splitter.delete_segment(session_id, segment_id)
    if not success:
        raise HTTPException(404, "Segment nicht gefunden")
    return {"success": True}


@router.post("/sessions/{session_id}/split")
async def split_session(session_id: str):
    """Nachtraeglich splitten: Bestehende Aufnahme anhand .meta.json in Segmente schneiden"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    if session.get("status") == "recording":
        raise HTTPException(400, "Aufnahme laeuft noch")

    # Bereits Segmente vorhanden?
    existing = splitter.get_segments(session_id)
    if existing:
        raise HTTPException(400, f"Session hat bereits {len(existing)} Segmente")

    # Meta-Datei pruefen
    meta_path = session.get("meta_file_path")
    if not meta_path:
        raise HTTPException(400, "Keine Metadaten vorhanden")
    meta_file = Path(meta_path)
    if not meta_file.exists():
        raise HTTPException(400, "Meta-Datei nicht gefunden")

    # Audio-Datei pruefen
    file_path = session.get("file_path")
    if not file_path:
        raise HTTPException(400, "Keine Audio-Datei vorhanden")
    audio_file = Path(file_path)
    if not audio_file.is_file():
        raise HTTPException(400, "Audio-Datei nicht gefunden")

    duration = session.get("duration", 0)
    file_format = session.get("file_format", ".mp3")

    segments = await splitter.split_session(
        session_id, audio_file, meta_file, duration, file_format
    )

    if not segments:
        raise HTTPException(500, "Split fehlgeschlagen")

    return {"success": True, "segments": len(segments)}


def _cleanup_temp_file(path: str):
    """Background-Task: Temp-Datei loeschen"""
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
    except Exception:
        pass


@router.get("/sessions/{session_id}/download-full")
async def download_full_session(session_id: str, background_tasks: BackgroundTasks):
    """Alle Segmente reassemblieren und als Gesamtdatei herunterladen"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    # Pruefen ob Segmente existieren
    segments = splitter.get_segments(session_id)
    if not segments:
        # Keine Segmente -> direkt Datei servieren (Legacy)
        fp = session.get("file_path")
        if fp:
            file_path = Path(fp)
            if file_path.is_file():
                ext = file_path.suffix.lower()
                media_type = EXTENSION_MIMETYPES.get(ext, "audio/mpeg")
                return FileResponse(
                    path=file_path,
                    filename=file_path.name,
                    media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'}
                )
        raise HTTPException(404, "Keine Dateien vorhanden")

    # Segmente reassemblieren
    output_path = await splitter.concat_session(session_id)
    if not output_path or not output_path.exists():
        raise HTTPException(500, "Reassembly fehlgeschlagen")

    ext = output_path.suffix.lower()
    media_type = EXTENSION_MIMETYPES.get(ext, "audio/mpeg")

    # Dateiname: Station_Datum.ext
    station = session.get("station_name", session_id)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in station)[:50]
    download_name = f"{safe_name}_{session_id}{ext}"

    # Temp-Datei nach Response aufraeumen
    background_tasks.add_task(_cleanup_temp_file, str(output_path))

    return FileResponse(
        path=output_path,
        filename=download_name,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
    )


@router.get("/sessions/{session_id}/download-zip")
async def download_zip_session(session_id: str, background_tasks: BackgroundTasks):
    """Alle Segmente + Metadaten als unkomprimiertes ZIP-Paket"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    segments = splitter.get_segments(session_id)
    if not segments:
        raise HTTPException(404, "Keine Segmente vorhanden")

    # ZIP in Cache-Verzeichnis erstellen
    from ..config import get_cache_dir
    cache_dir = get_cache_dir()

    station = session.get("station_name", session_id)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in station)[:50]
    zip_name = f"{safe_name}_{session_id}.zip"
    zip_path = cache_dir / zip_name

    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            # Segmente hinzufuegen
            for seg in segments:
                fp = Path(seg["file_path"])
                if fp.exists():
                    zf.write(fp, fp.name)

            # Meta-Datei hinzufuegen
            meta_path = session.get("meta_file_path")
            if meta_path:
                mp = Path(meta_path)
                if mp.exists():
                    zf.write(mp, mp.name)
    except Exception as e:
        raise HTTPException(500, f"ZIP-Erstellung fehlgeschlagen: {e}")

    background_tasks.add_task(_cleanup_temp_file, str(zip_path))

    return FileResponse(
        path=zip_path,
        filename=zip_name,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'}
    )
