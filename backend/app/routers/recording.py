"""
RadioHub v0.4.0 - Recording Router

Aufnahme starten/stoppen, Sessions verwalten, Segment-Verwaltung.
Async start/stop, dynamischer Media-Type.
HLS-REC: Aufnahme aus HLS-Buffer mit Lookback.
Dateien (Stücke, Titelliste) liegen in der Ablage; Schneiden über services.aufnahmen.
"""
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..ablage import ablage
from ..ablage.wiedergabe import ausliefern
from ..config import AUDIO_MIMETYPES, get_arbeit_dir
from ..services.aufnahmen import aufnahmen
from ..services.recorder import rec_manager
from ..services.hls_recorder import hls_recorder
from ..services.segment_splitter import titel_eintraege

router = APIRouter(prefix="/api/recording", tags=["recording"])


def _download_name(session: dict, endung: str) -> str:
    station = session.get("station_name") or session["id"]
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in station)[:50]
    return f"{safe_name}_{session['id']}{endung}"


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
    """Session löschen (Dateien in den Papierkorb der Ablage)"""
    success = await rec_manager.delete_session(session_id)
    if not success:
        raise HTTPException(404, "Session nicht gefunden oder aktiv")
    return {"success": True}


@router.get("/sessions/{session_id}/metadata")
async def get_session_metadata(session_id: str):
    """ICY-Metadata einer Session (Titelwechsel mit Zeitstempeln) aus der Titelliste in der Ablage"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")
    entries = titel_eintraege(await aufnahmen.titelliste(session))
    return {"entries": entries, "count": len(entries)}


# === Segment-Endpoints ===

@router.get("/segments")
async def get_all_segments():
    """Alle Segmente aller Sessions."""
    segments = aufnahmen.alle_segmente()
    return {"count": len(segments), "segments": segments}


@router.get("/sessions/{session_id}/segments")
async def get_segments(session_id: str):
    """Alle Segmente einer Session."""
    if not rec_manager.get_session(session_id):
        raise HTTPException(404, "Session nicht gefunden")
    segments = aufnahmen.segmente(session_id)
    return {"count": len(segments), "segments": segments}


def _segment(segment_id: int) -> dict:
    segment = aufnahmen.segment(segment_id)
    if not segment:
        raise HTTPException(404, "Segment nicht gefunden")
    return segment


@router.get("/segments/{segment_id}/play")
async def play_segment(segment_id: int, request: Request):
    """Einzelnes Segment aus der Ablage streamen (mit Range zum Spulen)"""
    return await ausliefern(_segment(segment_id)["file_path"], request)


@router.get("/segments/{segment_id}/download")
async def download_segment(segment_id: int, request: Request):
    """Einzelnes Segment herunterladen"""
    return await ausliefern(_segment(segment_id)["file_path"], request, herunterladen=True)


@router.delete("/sessions/{session_id}/segments/{segment_id}")
async def delete_segment(session_id: str, segment_id: int):
    """Einzelnes Segment löschen (Papierkorb der Ablage)"""
    success = await aufnahmen.segment_loeschen(session_id, segment_id)
    if not success:
        raise HTTPException(404, "Segment nicht gefunden")
    return {"success": True}


@router.post("/sessions/{session_id}/repair")
async def repair_session(session_id: str):
    """Bereinigt verwaiste Segmente (Einträge ohne Datei in der Ablage)."""
    if not rec_manager.get_session(session_id):
        raise HTTPException(404, "Session nicht gefunden")
    result = await aufnahmen.reparieren(session_id)
    return {"success": True, **result}


@router.post("/repair-all")
async def repair_all_sessions():
    """Prüft alle Sessions auf verwaiste Segmente und bereinigt sie."""
    session_ids = sorted({s["session_id"] for s in aufnahmen.alle_segmente()})
    total_removed = 0
    repaired = []
    for sid in session_ids:
        result = await aufnahmen.reparieren(sid)
        if result["removed"] > 0:
            total_removed += result["removed"]
            repaired.append({"session_id": sid, **result})
    return {"success": True, "sessions_checked": len(session_ids), "total_removed": total_removed,
            "repaired": repaired}


@router.post("/sessions/{session_id}/split")
async def split_session(session_id: str):
    """Nachträglich an den Titelwechseln der Titelliste teilen"""
    anzahl = await aufnahmen.nach_titeln_teilen(session_id)
    return {"success": True, "segments": anzahl}


class CustomSplitRequest(BaseModel):
    cut_points: list[float]
    trim_start: bool = False  # Erstes Segment (Anfangsfragment) löschen
    trim_end: bool = False    # Letztes Segment (Endfragment) löschen


@router.post("/sessions/{session_id}/custom-split")
async def custom_split_session(session_id: str, req: CustomSplitRequest):
    """Manueller Schnitt an expliziten Zeitpunkten (vom Cutter-UI); neue Stücke gehen in die Ablage."""
    result = await aufnahmen.neu_schneiden(session_id, req.cut_points, req.trim_start, req.trim_end)
    return {"success": True, **result}


def _aufraeumen(*pfade: str):
    """Background-Task: Zwischendateien des Downloads löschen"""
    for pfad in pfade:
        p = Path(pfad)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)


@router.get("/sessions/{session_id}/download-full")
async def download_full_session(session_id: str, request: Request):
    """Ganze Aufnahme als eine Datei herunterladen (Stücke zusammengefügt)"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")
    segments = aufnahmen.segmente(session_id)
    if not segments:
        raise HTTPException(404, "Keine Dateien vorhanden")
    if len(segments) == 1:
        endung = Path(segments[0]["file_path"]).suffix.lower()
        return await ausliefern(segments[0]["file_path"], request, herunterladen=True,
                                dateiname=_download_name(session, endung))
    kopie = await aufnahmen.arbeitskopie(session_id)
    name = _download_name(session, kopie.suffix.lower())
    return FileResponse(path=kopie, filename=name, media_type=AUDIO_MIMETYPES.get(kopie.suffix.lower(), "audio/mpeg"))


@router.get("/sessions/{session_id}/download-zip")
async def download_zip_session(session_id: str, background_tasks: BackgroundTasks):
    """Alle Segmente + Titelliste als unkomprimiertes ZIP-Paket"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")
    segments = aufnahmen.segmente(session_id)
    if not segments:
        raise HTTPException(404, "Keine Segmente vorhanden")

    zip_name = _download_name(session, ".zip")
    ordner = get_arbeit_dir("zip", f"{session_id}_{datetime.now().strftime('%H%M%S%f')}")
    zip_path = ordner.with_suffix(".zip")
    pfade = [s["file_path"] for s in segments]
    if session.get("meta_file_path"):
        pfade.append(session["meta_file_path"])
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for pfad in pfade:
                lokal = await ablage().herunterladen(pfad, ordner / Path(pfad).name)
                zf.write(lokal, lokal.name)
                lokal.unlink(missing_ok=True)
    except Exception as e:
        _aufraeumen(str(ordner), str(zip_path))
        raise HTTPException(500, f"ZIP-Erstellung fehlgeschlagen: {e}")

    background_tasks.add_task(_aufraeumen, str(ordner), str(zip_path))
    return FileResponse(path=zip_path, filename=zip_name, media_type="application/zip")


# === HLS-REC Endpoints ===

class HLSRecStartRequest(BaseModel):
    lookback_seconds: int = 300  # Default 5 Minuten


@router.post("/hls-start")
async def start_hls_recording(req: HLSRecStartRequest):
    """Startet HLS-REC (Aufnahme aus HLS-Buffer mit Lookback)"""
    result = await hls_recorder.start(lookback_seconds=req.lookback_seconds)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Fehler"))
    return result


@router.post("/hls-stop")
async def stop_hls_recording():
    """Stoppt HLS-REC"""
    result = await hls_recorder.stop()
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Keine aktive HLS-Aufnahme"))
    return result


@router.get("/hls-status")
async def hls_recording_status():
    """Status der HLS-Aufnahme"""
    return hls_recorder.get_status()


# === ICY-Titel Ignorier-Liste ===

class IcyIgnoreRequest(BaseModel):
    pattern: str
    match_type: str = "exact"


@router.get("/icy-ignore")
async def get_icy_ignore_list():
    """Alle ignorierten ICY-Titel."""
    from ..database import db_session
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT id, pattern, match_type, source, created_at FROM icy_title_ignore ORDER BY id")
        rows = c.fetchall()
    return {
        "count": len(rows),
        "items": [
            {"id": r[0], "pattern": r[1], "match_type": r[2], "source": r[3], "created_at": r[4]}
            for r in rows
        ]
    }


@router.post("/icy-ignore")
async def add_icy_ignore(req: IcyIgnoreRequest):
    """Titel zur Ignorier-Liste hinzufuegen."""
    if not req.pattern.strip():
        raise HTTPException(400, "Pattern darf nicht leer sein")
    if req.match_type not in ("exact", "contains"):
        raise HTTPException(400, "match_type muss 'exact' oder 'contains' sein")

    from ..database import db_session
    with db_session() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO icy_title_ignore (pattern, match_type) VALUES (?, ?)",
                (req.pattern.strip(), req.match_type)
            )
            new_id = c.lastrowid
        except Exception:
            raise HTTPException(409, "Pattern existiert bereits")
    return {"success": True, "id": new_id}


@router.delete("/icy-ignore/{item_id}")
async def remove_icy_ignore(item_id: int):
    """Eintrag aus der Ignorier-Liste entfernen."""
    from ..database import db_session
    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM icy_title_ignore WHERE id = ?", (item_id,))
        if c.rowcount == 0:
            raise HTTPException(404, "Eintrag nicht gefunden")
    return {"success": True}


class IcyIgnoreByPatternRequest(BaseModel):
    pattern: str


@router.post("/icy-ignore/remove-by-pattern")
async def remove_icy_ignore_by_pattern(req: IcyIgnoreByPatternRequest):
    """Eintrag per Pattern-String entfernen (fuer Toggle im UI)."""
    if not req.pattern.strip():
        raise HTTPException(400, "Pattern darf nicht leer sein")
    from ..database import db_session
    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM icy_title_ignore WHERE pattern = ?", (req.pattern.strip(),))
        if c.rowcount == 0:
            raise HTTPException(404, "Pattern nicht in Ignorier-Liste")
    return {"success": True}
