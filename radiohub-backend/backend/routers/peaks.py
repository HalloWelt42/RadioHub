"""
RadioHub v0.4.0 - Peaks Router

Waveform-Peaks und Wiedergabe für den Cutter. Die Wellenform liegt als Datei neben den Stücken in der Ablage
(entsteht beim ersten Bedarf aus der Arbeitskopie); Abschnitte werden per Bereichsanfrage gelesen.
Binary Transfer (Float32Array) für minimale Bandbreite.
"""
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, Response

from ..ablage import ablage
from ..config import AUDIO_MIMETYPES
from ..services.aufnahmen import aufnahmen
from ..services.peaks_generator import BYTES_PER_SAMPLE, SAMPLE_RATE, peaks_bereich

router = APIRouter(prefix="/api/recording", tags=["peaks"])


@router.get("/sessions/{session_id}/audio")
async def get_session_audio(session_id: str):
    """Ganze Aufnahme für die Wiedergabe im Cutter (lokale Arbeitskopie, Stücke zusammengefügt)."""
    kopie = await aufnahmen.arbeitskopie(session_id)
    endung = kopie.suffix.lower()
    return FileResponse(path=kopie, media_type=AUDIO_MIMETYPES.get(endung, "audio/mpeg"),
                        filename=f"{session_id}{endung}", content_disposition_type="inline")


@router.get("/sessions/{session_id}/peaks/info")
async def get_peaks_info(session_id: str):
    """Peaks-Info: Dauer, Samplerate, ob die Wellenform schon in der Ablage liegt."""
    vorhanden = await aufnahmen.wellenform_vorhanden(session_id)
    if vorhanden:
        duration = vorhanden.groesse / BYTES_PER_SAMPLE / SAMPLE_RATE
    else:
        duration = (aufnahmen.sitzung(session_id) or {}).get("duration", 0.0)
    return {"total_duration": duration, "sample_rate": SAMPLE_RATE, "has_cache": vorhanden is not None}


@router.get("/sessions/{session_id}/peaks")
async def get_peaks_chunk(
    session_id: str,
    start: float = Query(0, ge=0, description="Start in Sekunden"),
    duration: float = Query(300, gt=0, le=600, description="Dauer in Sekunden (max 600)")
):
    """Peaks-Daten für Zeitbereich als Float32Array (binary); erzeugt die Wellenform beim ersten Abruf."""
    wellenform = await aufnahmen.wellenform(session_id)
    bereich = peaks_bereich(wellenform.groesse, start, duration)
    data = await ablage().lesen_ganz(wellenform.pfad, *bereich) if bereich else b""
    total_duration = wellenform.groesse / BYTES_PER_SAMPLE / SAMPLE_RATE
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "X-Sample-Rate": str(SAMPLE_RATE),
            "X-Total-Duration": f"{total_duration:.3f}",
            "X-Chunk-Start": f"{start:.3f}",
            "X-Chunk-Samples": str(len(data) // BYTES_PER_SAMPLE),
            "Cache-Control": "no-cache"
        }
    )
