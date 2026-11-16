"""
RadioHub v0.4.0 - Audio Processing Router

Endpunkte für Audio-Nachbearbeitung:
- Normalisierung (EBU R128)
- Format-Konvertierung (MP3, OGG, AAC)
- Mono-Konvertierung
- Audio-Info
- Qualitäts-Presets

Bearbeitet werden lokale Arbeitskopien der Stücke; das Ergebnis geht als neue Version (gleiches Format) oder als
neue Datei (anderes Format, die alte in den Papierkorb) zurück in die Ablage (services.aufnahmen).
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services.audio_processor import audio_processor
from ..services.aufnahmen import AufnahmeFehler, aufnahmen

router = APIRouter(prefix="/api/recording", tags=["audio-processing"])


class ConvertRequest(BaseModel):
    format: str  # mp3, ogg, aac
    bitrate: int = 192  # kbps (z.B. 64, 128, 192, 256, 320)
    mono: bool = False
    segment_ids: Optional[list[int]] = None  # None = alle


class NormalizeRequest(BaseModel):
    target_lufs: float = -16.0
    segment_ids: Optional[list[int]] = None  # None = alle


def _sse(session_id: str, segment_ids: Optional[list[int]], bearbeitung, start_info: dict) -> StreamingResponse:
    """Stücke bearbeiten und den Fortschritt als SSE-Strom melden (start, progress, done oder error)."""
    queue: asyncio.Queue = asyncio.Queue()

    def on_progress(step, total, message):
        queue.put_nowait({"type": "progress", "step": step, "total": total, "message": message})

    async def laufen():
        try:
            ergebnis = await aufnahmen.stuecke_bearbeiten(session_id, segment_ids,
                                                          lambda pfade: bearbeitung(pfade, on_progress))
            queue.put_nowait({"type": "done", "success": True, "segments": len(ergebnis)})
        except Exception as e:
            queue.put_nowait({"type": "error", "message": str(e)})

    async def strom():
        yield f"data: {json.dumps({'type': 'start', **start_info})}\n\n"
        task = asyncio.create_task(laufen())
        while True:
            try:
                evt = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if task.done() and queue.empty():
                    break
                continue
            yield f"data: {json.dumps(evt)}\n\n"
            if evt["type"] in ("done", "error"):
                break
        await task

    return StreamingResponse(strom(), media_type="text/event-stream")


def _auswahl(session_id: str, segment_ids: Optional[list[int]]) -> list[dict]:
    """Prüft vor dem Strom, dass es etwas zu bearbeiten gibt (Fehler als HTTP-Status statt im Strom)."""
    sitzung = aufnahmen.sitzung(session_id)
    if not sitzung:
        raise HTTPException(404, "Session nicht gefunden")
    if sitzung.get("status") == "recording":
        raise HTTPException(400, "Aufnahme läuft noch")
    segmente = [s for s in aufnahmen.segmente(session_id) if segment_ids is None or s["id"] in segment_ids]
    if not segmente:
        raise HTTPException(404, "Keine Segment-Dateien gefunden")
    return segmente


@router.get("/sessions/{session_id}/audio-info")
async def get_audio_info(session_id: str):
    """Audio-Metadaten einer Session auslesen (aus der Arbeitskopie)."""
    info = await audio_processor.get_audio_info(await aufnahmen.arbeitskopie(session_id))
    if not info:
        raise HTTPException(500, "Audio-Info konnte nicht gelesen werden")
    return info


@router.post("/sessions/{session_id}/normalize")
async def normalize_session(session_id: str, req: Optional[NormalizeRequest] = None):
    """Audio-Normalisierung (EBU R128). Alle Stücke: gemeinsame LUFS-Messung, gleicher Gain; Auswahl: jedes Stück
    für sich. Response ist SSE-Stream mit Fortschritt und Endergebnis."""
    target_lufs = req.target_lufs if req else -16.0
    segment_ids = req.segment_ids if req else None
    segmente = _auswahl(session_id, segment_ids)
    total_duration = sum(s.get("duration_ms") or 0 for s in segmente) / 1000

    async def bearbeitung(pfade: list[Path], on_progress) -> list[Path]:
        if segment_ids is None:
            return await audio_processor.normalize_segments(pfade, target_lufs, on_progress=on_progress)
        fertig = []
        for i, pfad in enumerate(pfade):
            on_progress(i + 1, len(pfade), f"Segment {i + 1}/{len(pfade)}...")
            fertig.append(await audio_processor.normalize(pfad, target_lufs))
        return fertig

    return _sse(session_id, segment_ids, bearbeitung,
                {"segments": len(segmente), "estimated_seconds": int(total_duration * 2)})


@router.post("/sessions/{session_id}/convert")
async def convert_session(session_id: str, req: ConvertRequest):
    """Stücke in ein anderes Format umwandeln. Response ist SSE-Stream mit Fortschritt."""
    segmente = _auswahl(session_id, req.segment_ids)

    async def bearbeitung(pfade: list[Path], on_progress) -> list[Path]:
        fertig = []
        for i, pfad in enumerate(pfade):
            on_progress(i + 1, len(pfade), f"Segment {i + 1}/{len(pfade)}...")
            fertig.append(await audio_processor.convert(pfad, req.format, req.bitrate, req.mono))
        return fertig

    return _sse(session_id, req.segment_ids, bearbeitung, {"segments": len(segmente)})


@router.post("/sessions/{session_id}/to-mono")
async def to_mono_session(session_id: str):
    """Stereo -> Mono für alle Stücke."""
    _auswahl(session_id, None)

    async def bearbeitung(pfade: list[Path]) -> list[Path]:
        return [await audio_processor.to_mono(p) for p in pfade]

    try:
        ergebnis = await aufnahmen.stuecke_bearbeiten(session_id, None, bearbeitung)
    except RuntimeError as e:
        raise AufnahmeFehler(str(e), 500) from e
    return {"success": True, "segments": len(ergebnis)}


@router.get("/audio-processing/presets")
async def get_presets():
    """Verfügbare Bitraten pro Format zurückgeben."""
    return audio_processor.get_format_bitrates()
