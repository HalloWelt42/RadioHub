"""
RadioHub v0.1.0 - Peaks Router

Waveform-Peaks für den Cutter. On-demand Generierung + Chunk-Abruf.
Binary Transfer (Float32Array) für minimale Bandbreite.
Unterstützt sowohl einzelne Audio-Dateien als auch segmentierte Sessions.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, FileResponse
from pathlib import Path

from ..services.recorder import rec_manager
from ..services.segment_splitter import splitter
from ..services.peaks_generator import peaks_gen, SAMPLE_RATE
from ..config import get_cache_dir, AUDIO_MIMETYPES

router = APIRouter(prefix="/api/recording", tags=["peaks"])


async def _get_audio_path(session_id: str) -> Path:
    """Audio-Pfad einer Session ermitteln.

    Bei segmentierten Sessions: Segmente zusammenbauen und Cache-Datei liefern.
    """
    session = rec_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session nicht gefunden")
    if session.get("status") == "recording":
        raise HTTPException(400, "Aufnahme läuft noch")

    file_path = session.get("file_path", "")
    if not file_path:
        raise HTTPException(404, "Keine Audio-Datei")

    audio = Path(file_path)

    # Einzelne Datei -> direkt zurückgeben
    if audio.is_file():
        return audio

    # Verzeichnis = segmentierte Session -> zusammenbauen für Peaks
    if audio.is_dir():
        segments = splitter.get_segments(session_id)
        if not segments:
            raise HTTPException(404, "Keine Segmente gefunden")

        # Prüfen ob bereits eine zusammengebaute Datei im Cache existiert
        cache_dir = get_cache_dir()
        ext = Path(segments[0]["file_path"]).suffix
        cached = cache_dir / f"{session_id}_peaks_source{ext}"
        if cached.exists() and cached.stat().st_size > 0:
            return cached

        # Zusammenbauen via concat
        result = await splitter.concat_session(session_id)
        if not result or not result.exists():
            raise HTTPException(500, "Zusammenbau fehlgeschlagen")

        # Umbenennen für Peaks-Cache-Konsistenz
        result.rename(cached)
        return cached

    raise HTTPException(404, "Audio-Datei nicht gefunden")


@router.get("/sessions/{session_id}/audio")
async def get_session_audio(session_id: str):
    """Audio-Stream für die gesamte Session (auch segmentierte).

    Liefert die zusammengebaute Audio-Datei für Cutter-Playback.
    """
    audio = await _get_audio_path(session_id)
    ext = audio.suffix.lower()
    return FileResponse(
        path=audio,
        media_type=AUDIO_MIMETYPES.get(ext, "audio/mpeg"),
        filename=f"{session_id}{ext}",
        headers={"Accept-Ranges": "bytes"}
    )


@router.get("/sessions/{session_id}/peaks/info")
async def get_peaks_info(session_id: str):
    """Peaks-Info: Dauer, Samplerate, Cache-Status."""
    audio = await _get_audio_path(session_id)
    has_cache = peaks_gen.has_cache(audio)
    peaks_path = audio.with_suffix(".peaks")

    duration = 0.0
    if has_cache:
        duration = peaks_gen.get_total_duration(peaks_path)
    else:
        # Dauer aus Session-DB
        session = rec_manager.get_session(session_id)
        duration = session.get("duration", 0.0)

    return {
        "total_duration": duration,
        "sample_rate": SAMPLE_RATE,
        "has_cache": has_cache
    }


@router.get("/sessions/{session_id}/peaks")
async def get_peaks_chunk(
    session_id: str,
    start: float = Query(0, ge=0, description="Start in Sekunden"),
    duration: float = Query(300, gt=0, le=600, description="Dauer in Sekunden (max 600)")
):
    """Peaks-Daten für Zeitbereich als Float32Array (binary).

    Generiert Peaks on-demand wenn noch kein Cache existiert.
    """
    audio = await _get_audio_path(session_id)
    peaks_path = audio.with_suffix(".peaks")

    # On-demand generieren
    if not peaks_path.exists() or peaks_path.stat().st_size == 0:
        result = await peaks_gen.generate_peaks(audio)
        if not result:
            raise HTTPException(500, "Peaks-Generierung fehlgeschlagen")

    # Chunk lesen
    data = peaks_gen.get_peaks_chunk(peaks_path, start, duration)
    total_duration = peaks_gen.get_total_duration(peaks_path)

    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "X-Sample-Rate": str(SAMPLE_RATE),
            "X-Total-Duration": f"{total_duration:.3f}",
            "X-Chunk-Start": f"{start:.3f}",
            "X-Chunk-Samples": str(len(data) // 4),
            "Cache-Control": "public, max-age=3600"
        }
    )
