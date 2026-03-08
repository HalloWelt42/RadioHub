"""
RadioHub HLS API Router v1.1.0

API Endpoints für HLS Timeshift Buffer.
Mit adaptiver Bitrate basierend auf Config.

Endpoints:
- POST /api/hls/start    - Buffer starten
- POST /api/hls/stop     - Buffer stoppen  
- GET  /api/hls/status   - Status abrufen
- GET  /api/hls/playlist.m3u8 - HLS Playlist
- GET  /api/hls/segment/{id}  - Audio Segment

© HalloWelt42 - Nur für private Nutzung
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from typing import Optional

from ..services.hls_buffer import hls_buffer
from ..services.config_service import get_config_service
from ..services.bitrate_detector import save_detected_bitrate


router = APIRouter(prefix="/api/hls", tags=["HLS Buffer"])


class HLSStartRequest(BaseModel):
    """Request zum Starten des HLS Buffers"""
    station_uuid: str
    station_name: str
    stream_url: str
    bitrate: int = 128
    max_minutes: int = 10
    override_bitrate: int = 0


# === Buffer Control ===

@router.post("/start")
async def start_hls_buffer(request: HLSStartRequest):
    """
    Startet HLS Buffering für einen Radio-Stream.
    
    ffmpeg konvertiert den Stream in 1-Sekunden HLS-Segmente.
    Ermöglicht exaktes Seeking und Time-Shift bis zu max_minutes.
    
    Bitrate wird automatisch angepasst:
    - Erkennt Input-Bitrate des Streams
    - Begrenzt auf min/max aus Config
    - Bläht niedrige Streams nicht auf
    """
    # Config-Werte laden
    config = get_config_service()
    min_bitrate = config.get("hls_min_bitrate", 32)
    max_bitrate = config.get("hls_max_bitrate", 256)
    sample_rate = config.get("hls_sample_rate", 44100)
    
    result = await hls_buffer.start(
        station_uuid=request.station_uuid,
        station_name=request.station_name,
        stream_url=request.stream_url,
        bitrate=request.bitrate,
        max_minutes=request.max_minutes,
        min_bitrate=min_bitrate,
        max_bitrate=max_bitrate,
        sample_rate=sample_rate,
        override_bitrate=request.override_bitrate
    )
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Unbekannter Fehler")
        )

    # Erkannte Stream-Infos in detected_bitrates speichern
    if hls_buffer.session:
        br = hls_buffer.session.input_bitrate
        codec = hls_buffer.session.input_codec
        sr = hls_buffer.session.sample_rate
        if br > 0 or (codec and codec != "unknown"):
            save_detected_bitrate(request.station_uuid, br, codec, sr)

    return result


@router.post("/stop")
async def stop_hls_buffer():
    """Stoppt HLS Buffering und gibt Ressourcen frei"""
    return await hls_buffer.stop()


@router.get("/status")
async def get_hls_status():
    """
    Aktueller HLS Buffer Status.
    
    Enthält Infos über gepufferte Segmente, Dauer, etc.
    """
    return hls_buffer.get_status()


# === HLS Streaming ===

@router.get("/playlist.m3u8")
async def get_hls_playlist():
    """
    Gibt die aktuelle HLS Playlist zurück.
    
    Die Playlist wird von ffmpeg generiert und enthält
    Referenzen zu allen verfügbaren Segmenten.
    
    CORS und Cache-Header sind für Live-Streaming optimiert.
    """
    playlist = hls_buffer.get_playlist()
    
    if not playlist:
        raise HTTPException(
            status_code=404,
            detail="Keine Playlist verfügbar. Buffer aktiv?"
        )
    
    return Response(
        content=playlist,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/segment/{segment_id}")
async def get_hls_segment(segment_id: int, sid: Optional[str] = None):
    """
    Gibt ein einzelnes Audio-Segment zurueck.

    Segmente sind 1 Sekunde lang im MPEG-TS Format.
    sid-Parameter verhindert Cache-Kollisionen bei Senderwechsel.
    """
    # Session-ID validieren: verhindert Auslieferung alter Segmente
    current_sid = hls_buffer.get_session_id()
    if sid and current_sid and sid != current_sid:
        raise HTTPException(
            status_code=404,
            detail=f"Session {sid} nicht mehr aktiv"
        )

    segment_path = hls_buffer.get_segment_path(segment_id)

    if not segment_path:
        raise HTTPException(
            status_code=404,
            detail=f"Segment {segment_id} nicht gefunden"
        )

    return FileResponse(
        path=segment_path,
        media_type="video/mp2t",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*"
        }
    )


# === Debug Endpoints ===

@router.get("/debug/files")
async def debug_list_files():
    """Debug: Listet alle Dateien im Buffer-Verzeichnis"""
    buffer_dir = hls_buffer.buffer_dir
    
    if not buffer_dir.exists():
        return {
            "exists": False,
            "path": str(buffer_dir)
        }
    
    files = []
    for f in sorted(buffer_dir.iterdir()):
        files.append({
            "name": f.name,
            "size": f.stat().st_size
        })
    
    return {
        "exists": True,
        "path": str(buffer_dir),
        "count": len(files),
        "files": files[:100]  # Max 100 anzeigen
    }


@router.get("/debug/ffmpeg")
async def debug_ffmpeg_check():
    """Debug: Prüft ob ffmpeg verfügbar ist"""
    import shutil
    import subprocess
    
    ffmpeg_path = shutil.which("ffmpeg")
    
    if not ffmpeg_path:
        return {
            "available": False,
            "error": "ffmpeg nicht im PATH gefunden"
        }
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_line = result.stdout.split('\n')[0] if result.stdout else "unbekannt"
        
        return {
            "available": True,
            "path": ffmpeg_path,
            "version": version_line
        }
    except Exception as e:
        return {
            "available": False,
            "path": ffmpeg_path,
            "error": str(e)
        }
