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

from ..services import titelsicherung
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
    max_minutes: int | None = None          # leer: Länge des Puffers aus den Einstellungen (RAD-11)
    override_bitrate: int = 0
    is_podcast: bool = False
    original: bool = False                  # Ton unverändert übernehmen, wenn das Format es erlaubt (RAD-92)


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
    max_bitrate = config.get("hls_max_bitrate", 320)
    sample_rate = config.get("hls_sample_rate", 44100)
    max_minutes = request.max_minutes or config.get("hls_puffer_minuten", 120)
    
    result = await hls_buffer.start(
        station_uuid=request.station_uuid,
        station_name=request.station_name,
        stream_url=request.stream_url,
        bitrate=request.bitrate,
        max_minutes=max_minutes,
        min_bitrate=min_bitrate,
        max_bitrate=max_bitrate,
        sample_rate=sample_rate,
        override_bitrate=request.override_bitrate,
        is_podcast=request.is_podcast,
        original=request.original
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
async def stop_hls_buffer(sid: Optional[str] = None):
    """Stoppt HLS Buffering und gibt Ressourcen frei; mit `sid` nur diese Sitzung"""
    return await hls_buffer.stop(sid)


@router.get("/status")
async def get_hls_status():
    """
    Aktueller HLS Buffer Status.
    
    Enthält Infos über gepufferte Segmente, Dauer, etc.
    """
    return hls_buffer.get_status()


# === HLS Streaming ===

@router.get("/abschnitte")
async def puffer_abschnitte():
    """Titel, Werbung und Einschübe im Puffer (RAD-46), Sekunden des Puffers wie die Segmente; das letzte läuft noch.
    Grenzen nach der Regel des Feinschnitts (an der Pause, bei Überblendung am Pegeltal)."""
    return {"versatz_s": hls_buffer.versatz_s, "abschnitte": hls_buffer.abschnitte()}


class PufferAufnahme(BaseModel):
    """Sekunden des Puffers; ohne `von_s` am Anfang des laufenden Titels, ohne `bis_s` bis zum Stopp."""
    von_s: Optional[float] = None
    bis_s: Optional[float] = None
    ziel: Optional[str] = None


@router.post("/aufnahme")
async def aufnahme_aus_dem_puffer(wunsch: PufferAufnahme):
    """Aufnahme ab hier oder einen Bereich sichern (RAD-46): ein Abschnitt des Empfangs hinter dem Puffer, fertig
    geschnitten wie jede Aufnahme. Ohne `bis_s` läuft sie weiter, auch wenn der Puffer endet."""
    from ..services.recorder import rec_manager
    sitzung, empfang = hls_buffer.session, hls_buffer.empfang
    if not sitzung or not empfang:
        raise HTTPException(409, "Kein Zeitversatz mit Sendedaten aktiv")
    if wunsch.bis_s is not None and wunsch.von_s is not None and wunsch.bis_s <= wunsch.von_s:
        raise HTTPException(422, "Das Ende liegt vor dem Anfang")
    v = hls_buffer.versatz_s
    ergebnis = await rec_manager.start(sitzung.station_uuid, sitzung.station_name, sitzung.stream_url,
                                       sitzung.input_bitrate, von_s=None if wunsch.von_s is None else wunsch.von_s + v,
                                       bis_s=None if wunsch.bis_s is None else wunsch.bis_s + v, ziel_id=wunsch.ziel)
    if not ergebnis.get("success"):
        raise HTTPException(409, ergebnis.get("error", "Aufnahme nicht gestartet"))
    return ergebnis


class Titelwunsch(BaseModel):
    """Eine Sekunde des Puffers, die im Titel liegt."""
    bei_s: float
    ziel: Optional[str] = None


class Abwahl(BaseModel):
    """Eine Sekunde des Puffers im Titel; `an`: abwählen, sonst wieder anwählen."""
    bei_s: float
    an: bool = True


@router.post("/abwahl")
async def abwaehlen(wunsch: Abwahl):
    """Einen Titel der laufenden Aufnahme abwählen (RAD-150): sie läuft weiter, der Titel fehlt danach ganz; solange sie läuft, lässt
    er sich wieder anwählen."""
    if not hls_buffer.abwaehlen(wunsch.bei_s, wunsch.an):
        raise HTTPException(409, "An dieser Stelle ist kein Titel der laufenden Aufnahme")
    return {"abgewaehlt": wunsch.an}


@router.post("/titel")
async def titel_sichern(wunsch: Titelwunsch):
    """Den fertigen Titel an dieser Stelle als eigene Aufnahme sichern (RAD-132), auch während eine Aufnahme läuft."""
    empfang = hls_buffer.empfang
    if not hls_buffer.session or not empfang:
        raise HTTPException(409, "Kein Zeitversatz mit Sendedaten aktiv")
    a = next((a for a in hls_buffer.abschnitte() if a["von"] - 0.5 <= wunsch.bei_s < a["bis"]), None)
    if a is None or not a["komplett"]:
        raise HTTPException(409, "An dieser Stelle ist kein fertiger Titel")
    v = hls_buffer.versatz_s
    try:
        kennung = await titelsicherung.sichern(empfang, a["von"] + v, a["bis"] + v, a["titel"], wunsch.ziel)
    except titelsicherung.SicherungFehler as f:
        raise HTTPException(409, str(f)) from f
    return {"session_id": kennung, "titel": a["titel"]}


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
    Gibt ein einzelnes Audio-Segment zurück.

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
