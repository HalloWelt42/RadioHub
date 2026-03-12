"""
RadioHub - Audio Processing Router

Endpunkte fuer Audio-Nachbearbeitung:
- Normalisierung (EBU R128)
- Format-Konvertierung (MP3, OGG, AAC)
- Mono-Konvertierung
- Audio-Info
- Qualitaets-Presets
"""

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from ..services.audio_processor import audio_processor
from ..services.recorder import rec_manager
from ..services.segment_splitter import splitter
from ..config import get_cache_dir

router = APIRouter(prefix="/api/recording", tags=["audio-processing"])


def _resolve_audio_path(session: dict, session_id: str) -> Path:
    """Audio-Pfad einer Session aufloesen (auch segmentierte)."""
    file_path = session.get("file_path", "")
    if not file_path:
        raise HTTPException(400, "Keine Audio-Datei vorhanden")

    audio_file = Path(file_path)

    if audio_file.is_dir():
        # Segmentierte Session -> zusammengebaute Datei aus Cache nutzen
        segments = splitter.get_segments(session_id)
        if not segments:
            raise HTTPException(404, "Keine Segmente gefunden")
        ext = Path(segments[0]["file_path"]).suffix
        cache_dir = get_cache_dir()
        cached = cache_dir / f"{session_id}_peaks_source{ext}"
        if cached.exists() and cached.stat().st_size > 0:
            return cached
        raise HTTPException(400, "Session ist segmentiert. Bitte zuerst zusammenbauen.")

    if not audio_file.is_file():
        raise HTTPException(400, "Audio-Datei nicht gefunden")

    return audio_file


class ConvertRequest(BaseModel):
    format: str  # mp3, ogg, aac
    bitrate: int = 192  # kbps (z.B. 64, 128, 192, 256, 320)
    mono: bool = False
    segment_ids: Optional[list[int]] = None  # None = alle


class NormalizeRequest(BaseModel):
    target_lufs: float = -16.0
    segment_ids: Optional[list[int]] = None  # None = alle


@router.get("/sessions/{session_id}/audio-info")
async def get_audio_info(session_id: str):
    """Audio-Metadaten einer Session auslesen."""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    audio_file = _resolve_audio_path(session, session_id)
    info = await audio_processor.get_audio_info(audio_file)
    if not info:
        raise HTTPException(500, "Audio-Info konnte nicht gelesen werden")

    return info


@router.post("/sessions/{session_id}/normalize")
async def normalize_session(session_id: str, req: Optional[NormalizeRequest] = None):
    """Audio-Normalisierung (EBU R128) auf eine Session anwenden.

    Bei segmentierten Sessions: Gemeinsame LUFS-Messung, gleicher Gain auf alle Segmente.
    Response ist SSE-Stream mit Fortschritt und Endergebnis.
    """
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    if session.get("status") == "recording":
        raise HTTPException(400, "Aufnahme laeuft noch")

    target_lufs = req.target_lufs if req else -16.0
    segment_ids = req.segment_ids if req else None

    # Segmente pruefen
    segments = splitter.get_segments(session_id)

    if segments:
        # Optional: nur bestimmte Segmente
        if segment_ids is not None:
            segments = [s for s in segments if s.get("id") in segment_ids]

        seg_paths = [Path(s["file_path"]) for s in segments if Path(s["file_path"]).is_file()]
        if not seg_paths:
            raise HTTPException(404, "Keine Segment-Dateien gefunden")

        # Bei Teilauswahl: Jedes Segment einzeln normalisieren (eigene LUFS)
        # Bei alle: Gemeinsame LUFS-Messung
        is_partial = segment_ids is not None

        total_duration = sum(s.get("duration_ms", 0) for s in segments) / 1000

        async def sse_stream():
            queue = asyncio.Queue()

            def on_progress(step, total, message):
                queue.put_nowait({"type": "progress", "step": step, "total": total, "message": message})

            async def run_normalize():
                try:
                    if is_partial:
                        # Einzelne Segmente: jeweils eigene LUFS-Analyse
                        results = []
                        for i, seg_path in enumerate(seg_paths):
                            on_progress(i + 1, len(seg_paths),
                                        f"Segment {i + 1}/{len(seg_paths)}...")
                            result = await audio_processor.normalize(seg_path, target_lufs)
                            results.append(result)
                        queue.put_nowait({"type": "done", "success": True,
                                          "segments": len(results)})
                    else:
                        # Alle: gemeinsame LUFS
                        results = await audio_processor.normalize_segments(
                            seg_paths, target_lufs, on_progress=on_progress
                        )
                        queue.put_nowait({"type": "done", "success": True,
                                          "segments": len(results)})
                except Exception as e:
                    queue.put_nowait({"type": "error", "message": str(e)})

            est_seconds = int(total_duration * 2)
            yield f"data: {json.dumps({'type': 'start', 'segments': len(seg_paths), 'estimated_seconds': est_seconds})}\n\n"

            task = asyncio.create_task(run_normalize())

            while not task.done() or not queue.empty():
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(evt)}\n\n"
                    if evt["type"] in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    pass

            await task

        return StreamingResponse(sse_stream(), media_type="text/event-stream")

    # Einzelne Datei (nicht segmentiert)
    audio_file = _resolve_audio_path(session, session_id)

    try:
        result = await audio_processor.normalize(audio_file, target_lufs)
        info = await audio_processor.get_audio_info(result)
        return {"success": True, "path": str(result), "info": info}
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/sessions/{session_id}/convert")
async def convert_session(session_id: str, req: ConvertRequest):
    """Audio konvertieren -- einzelne Datei oder alle Segmente.

    Bei segmentierten Sessions: Jedes Segment einzeln konvertieren.
    Response ist SSE-Stream mit Fortschritt.
    """
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    if session.get("status") == "recording":
        raise HTTPException(400, "Aufnahme läuft noch")

    segments = splitter.get_segments(session_id)

    if segments:
        # Optional: nur bestimmte Segmente
        if req.segment_ids is not None:
            segments = [s for s in segments if s.get("id") in req.segment_ids]

        seg_paths = [Path(s["file_path"]) for s in segments if Path(s["file_path"]).is_file()]
        if not seg_paths:
            raise HTTPException(404, "Keine Segment-Dateien gefunden")

        async def sse_stream():
            total = len(seg_paths)
            yield f"data: {json.dumps({'type': 'start', 'segments': total})}\n\n"

            for i, seg_path in enumerate(seg_paths):
                yield f"data: {json.dumps({'type': 'progress', 'step': i + 1, 'total': total, 'message': f'Segment {i + 1}/{total}...'})}\n\n"
                try:
                    await audio_processor.convert(seg_path, req.format, req.bitrate, req.mono)
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    return

            yield f"data: {json.dumps({'type': 'done', 'success': True, 'segments': total})}\n\n"

        return StreamingResponse(sse_stream(), media_type="text/event-stream")

    # Einzelne Datei
    audio_file = _resolve_audio_path(session, session_id)

    try:
        result = await audio_processor.convert(
            audio_file, req.format, req.bitrate, req.mono
        )
        info = await audio_processor.get_audio_info(result)
        return {
            "success": True,
            "path": str(result),
            "new_format": req.format,
            "info": info,
        }
    except (RuntimeError, ValueError) as e:
        raise HTTPException(500, str(e))


@router.post("/sessions/{session_id}/to-mono")
async def to_mono_session(session_id: str):
    """Stereo -> Mono konvertieren."""
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")

    if session.get("status") == "recording":
        raise HTTPException(400, "Aufnahme laeuft noch")

    audio_file = _resolve_audio_path(session, session_id)

    try:
        result = await audio_processor.to_mono(audio_file)
        info = await audio_processor.get_audio_info(result)
        return {"success": True, "path": str(result), "info": info}
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.get("/audio-processing/presets")
async def get_presets():
    """Verfuegbare Bitraten pro Format zurueckgeben."""
    return audio_processor.get_format_bitrates()
