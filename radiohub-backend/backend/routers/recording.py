"""
RadioHub v0.2.3 - Recording Router

Aufnahme starten/stoppen, Sessions verwalten, Segment-Verwaltung.
Async start/stop, dynamischer Media-Type.
HLS-REC: Aufnahme aus HLS-Buffer mit Lookback.
"""
import json
import zipfile
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from ..services.recorder import rec_manager
from ..services.hls_recorder import hls_recorder
from ..services.segment_splitter import splitter
from ..config import RADIO_RECORDINGS_DIR, get_cache_dir, AUDIO_MIMETYPES

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
    """Session löschen"""
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
    media_type = AUDIO_MIMETYPES.get(ext, "audio/mpeg")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


# === Segment-Endpoints ===

@router.get("/segments")
async def get_all_segments():
    """Alle Segmente aller Sessions (bereinigt automatisch verwaiste)."""
    segments = splitter.get_all_segments()

    # Verwaiste Segmente erkennen und bereinigen
    orphan_sessions = set()
    for seg in segments:
        fp = Path(seg["file_path"])
        if not fp.exists():
            orphan_sessions.add(seg["session_id"])

    if orphan_sessions:
        for sid in orphan_sessions:
            splitter.repair_session(sid)
        # Bereinigte Liste neu laden
        segments = splitter.get_all_segments()

    return {"count": len(segments), "segments": segments}


@router.get("/sessions/{session_id}/segments")
async def get_segments(session_id: str):
    """Alle Segmente einer Session (bereinigt automatisch verwaiste)."""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    segments = splitter.get_segments(session_id)

    # Verwaiste Segmente automatisch bereinigen
    has_orphans = any(not Path(s["file_path"]).exists() for s in segments)
    if has_orphans:
        result = splitter.repair_session(session_id)
        if result["removed"] > 0:
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
    media_type = AUDIO_MIMETYPES.get(ext, "audio/mpeg")

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
    media_type = AUDIO_MIMETYPES.get(ext, "audio/mpeg")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'}
    )


@router.delete("/sessions/{session_id}/segments/{segment_id}")
async def delete_segment(session_id: str, segment_id: int):
    """Einzelnes Segment löschen"""
    success = splitter.delete_segment(session_id, segment_id)
    if not success:
        raise HTTPException(404, "Segment nicht gefunden")
    return {"success": True}


@router.post("/sessions/{session_id}/repair")
async def repair_session(session_id: str):
    """Bereinigt verwaiste Segmente (DB-Eintraege ohne Datei).

    Entfernt Geister-Eintraege, re-indexiert verbleibende Segmente.
    """
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    result = splitter.repair_session(session_id)
    return {"success": True, **result}


@router.post("/repair-all")
async def repair_all_sessions():
    """Prueft alle Sessions auf verwaiste Segmente und bereinigt sie."""
    all_segments = splitter.get_all_segments()
    if not all_segments:
        return {"success": True, "sessions_checked": 0, "total_removed": 0}

    # Alle betroffenen Session-IDs sammeln
    session_ids = sorted(set(s["session_id"] for s in all_segments))
    total_removed = 0
    repaired = []

    for sid in session_ids:
        result = splitter.repair_session(sid)
        if result["removed"] > 0:
            total_removed += result["removed"]
            repaired.append({
                "session_id": sid,
                "removed": result["removed"],
                "kept": result["kept"],
                "removed_titles": result["removed_titles"]
            })

    return {
        "success": True,
        "sessions_checked": len(session_ids),
        "total_removed": total_removed,
        "repaired": repaired
    }


@router.post("/sessions/{session_id}/split")
async def split_session(session_id: str):
    """Nachträglich splitten: Bestehende Aufnahme anhand .meta.json in Segmente schneiden"""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    if session.get("status") == "recording":
        raise HTTPException(400, "Aufnahme läuft noch")

    # Bereits Segmente vorhanden?
    existing = splitter.get_segments(session_id)
    if existing:
        raise HTTPException(400, f"Session hat bereits {len(existing)} Segmente")

    # Meta-Datei prüfen
    meta_path = session.get("meta_file_path")
    if not meta_path:
        raise HTTPException(400, "Keine Metadaten vorhanden")
    meta_file = Path(meta_path)
    if not meta_file.exists():
        raise HTTPException(400, "Meta-Datei nicht gefunden")

    # Audio-Datei prüfen
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


class CustomSplitRequest(BaseModel):
    cut_points: list[float]
    trim_start: bool = False  # Erstes Segment (Anfangsfragment) löschen
    trim_end: bool = False    # Letztes Segment (Endfragment) löschen


@router.post("/sessions/{session_id}/custom-split")
async def custom_split_session(session_id: str, req: CustomSplitRequest):
    """Manueller Schnitt an expliziten Zeitpunkten (vom Cutter-UI)."""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    if session.get("status") == "recording":
        raise HTTPException(400, "Aufnahme läuft noch")

    if not req.cut_points or len(req.cut_points) == 0:
        raise HTTPException(400, "Keine Schnittpunkte angegeben")

    # Audio-Datei prüfen (auch segmentierte Sessions unterstützen)
    file_path = session.get("file_path", "")
    if not file_path:
        raise HTTPException(400, "Keine Audio-Datei vorhanden")
    audio_file = Path(file_path)

    if audio_file.is_dir():
        # Segmentierte Session -> erst zusammenbauen
        segments = splitter.get_segments(session_id)
        if not segments:
            raise HTTPException(404, "Keine Segmente gefunden")
        ext = Path(segments[0]["file_path"]).suffix
        cache_dir = get_cache_dir()
        cached = cache_dir / f"{session_id}_peaks_source{ext}"
        if cached.exists() and cached.stat().st_size > 0:
            audio_file = cached
        else:
            result = await splitter.concat_session(session_id)
            if not result or not result.exists():
                raise HTTPException(500, "Zusammenbau fehlgeschlagen")
            result.rename(cached)
            audio_file = cached
    elif not audio_file.is_file():
        raise HTTPException(400, "Audio-Datei nicht gefunden")

    duration = session.get("duration", 0)
    file_format = session.get("file_format", ".mp3")

    # Meta-Entries laden (optional, für Titel-Zuordnung)
    meta_entries = None
    meta_path = session.get("meta_file_path")
    if meta_path:
        meta_file = Path(meta_path)
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    meta_entries = raw.get("entries", [])
                else:
                    meta_entries = raw
            except Exception:
                pass

    result = await splitter.split_at_times(
        session_id, audio_file, req.cut_points, duration, file_format,
        meta_entries=meta_entries
    )

    if not result:
        raise HTTPException(500, "Split fehlgeschlagen")

    # Frische Segmente aus DB laden (mit ID)
    segments = splitter.get_segments(session_id)
    if not segments:
        raise HTTPException(500, "Segmente nach Split nicht gefunden")

    # Anfangs-/Endfragmente entfernen wenn gewünscht
    trimmed = 0
    if req.trim_end and len(segments) > 1:
        last_seg = segments[-1]
        splitter.delete_segment(session_id, last_seg["id"])
        trimmed += 1
        segments = splitter.get_segments(session_id)
    if req.trim_start and len(segments) > 1:
        first_seg = segments[0]
        splitter.delete_segment(session_id, first_seg["id"])
        trimmed += 1
        segments = splitter.get_segments(session_id)

    return {"success": True, "segments": len(segments), "trimmed": trimmed}


def _cleanup_temp_file(path: str):
    """Background-Task: Temp-Datei löschen"""
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

    # Prüfen ob Segmente existieren
    segments = splitter.get_segments(session_id)
    if not segments:
        # Keine Segmente -> direkt Datei servieren (Legacy)
        fp = session.get("file_path")
        if fp:
            file_path = Path(fp)
            if file_path.is_file():
                ext = file_path.suffix.lower()
                media_type = AUDIO_MIMETYPES.get(ext, "audio/mpeg")
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
    media_type = AUDIO_MIMETYPES.get(ext, "audio/mpeg")

    # Dateiname: Station_Datum.ext
    station = session.get("station_name", session_id)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in station)[:50]
    download_name = f"{safe_name}_{session_id}{ext}"

    # Temp-Datei nach Response aufräumen
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
            # Segmente hinzufügen
            for seg in segments:
                fp = Path(seg["file_path"])
                if fp.exists():
                    zf.write(fp, fp.name)

            # Meta-Datei hinzufügen
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
