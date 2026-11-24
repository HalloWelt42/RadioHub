"""Schnitt für Aufnahmen und Dateien der Kellerwolke (RAD-17), ein Weg für beide (services/schnitt.py).

Jeder Aufruf nennt den Gegenstand: `art` (sitzung oder datei) und `kennung` (Kennung der Aufnahme oder Pfad der Datei
in der Kellerwolke). Schneiden, Normalisieren und Umwandeln melden ihren Fortschritt als Ereignisstrom (start,
progress, done oder error)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from ..ablage import AblageFehler
from ..config import AUDIO_MIMETYPES
from ..services.audio_processor import audio_processor
from ..services.aufnahmen import AufnahmeFehler, aufnahmen
from ..services.peaks_generator import BYTES_PER_SAMPLE, SAMPLE_RATE, peaks_bereich
from ..services.schnitt import StueckWahl, gegenstand
from .ereignisstrom import ereignisstrom

router = APIRouter(prefix="/api/schnitt", tags=["schnitt"])

Art = Literal["sitzung", "datei"]


def _gegenstand(art: str, kennung: str):
    try:
        return gegenstand(art, kennung)
    except AufnahmeFehler as f:
        raise HTTPException(f.status, str(f)) from f


def _zum_aendern(art: str, kennung: str):
    """Wie `_gegenstand`, aber nicht, solange die Aufnahme läuft oder ihr Feinschnitt noch arbeitet (RAD-139)."""
    if art == "sitzung" and aufnahmen.laeuft(kennung):
        raise HTTPException(409, "Die Aufnahme läuft noch oder wird gerade geschnitten")
    return _gegenstand(art, kennung)


async def _sicher(arbeit):
    try:
        return await arbeit
    except AufnahmeFehler as f:
        raise HTTPException(f.status, str(f)) from f
    except AblageFehler as f:
        raise HTTPException(503, str(f)) from f


class Gegenstand(BaseModel):
    art: Art
    kennung: str = Field(min_length=1, max_length=1000)


class Stueck(BaseModel):
    von: float = Field(ge=0)
    bis: float = Field(gt=0)
    name: str = Field("", max_length=200)
    behalten: bool = True


class Schneiden(Gegenstand):
    stuecke: list[Stueck] = Field(min_length=1)


class Umwandeln(Gegenstand):
    format: Literal["mp3", "ogg", "aac"]
    bitrate: int = Field(192, ge=32, le=320)
    mono: bool = False


def _strom(arbeit) -> StreamingResponse:
    """`arbeit(fortschritt)` im Hintergrund, Fortschritt und Ende als Ereignisstrom (gemeinsamer Baustein)."""
    return ereignisstrom(arbeit)


@router.get("/info")
async def info(art: Art, kennung: str):
    return await _sicher(_gegenstand(art, kennung).info())


@router.get("/ton")
async def ton(art: Art, kennung: str):
    """Der ganze Ton (Arbeitskopie) zum Hören im Schnitt, mit Bereichsanfragen."""
    kopie: Path = await _sicher(_gegenstand(art, kennung).arbeitskopie())
    return FileResponse(kopie, media_type=AUDIO_MIMETYPES.get(kopie.suffix.lower(), "audio/mpeg"), content_disposition_type="inline")


@router.get("/wellenform")
async def wellenform(art: Art, kennung: str, start: float = Query(0, ge=0), dauer: float = Query(300, gt=0, le=600)):
    """Abschnitt der Wellenform als Float32 (100 Werte je Sekunde); entsteht beim ersten Abruf."""
    g = _gegenstand(art, kennung)
    groesse = await _sicher(g.wellenform_groesse())
    teil = peaks_bereich(groesse, start, dauer)
    daten = await _sicher(g.wellenform_lesen(*teil)) if teil else b""
    return Response(content=daten, media_type="application/octet-stream", headers={
        "X-Sample-Rate": str(SAMPLE_RATE), "X-Total-Duration": f"{groesse / BYTES_PER_SAMPLE / SAMPLE_RATE:.3f}",
        "X-Chunk-Start": f"{start:.3f}", "Cache-Control": "no-cache"})


@router.post("/schneiden")
async def schneiden(req: Schneiden):
    g = _zum_aendern(req.art, req.kennung)
    wahl = [StueckWahl(s.von, s.bis, s.name, s.behalten) for s in req.stuecke]
    if not any(w.behalten for w in wahl):
        raise HTTPException(422, "Kein Stück zum Behalten gewählt")
    return _strom(lambda fortschritt: g.schneiden(wahl, fortschritt))


@router.post("/normalisieren")
async def normalisieren(req: Gegenstand):
    """Auf -16 LUFS, alle Stücke gemeinsam gemessen (gleicher Pegel über die ganze Aufnahme)."""
    g = _zum_aendern(req.art, req.kennung)

    async def bearbeitung(pfade: list[Path], fortschritt) -> list[Path]:
        return await audio_processor.normalize_segments(pfade, -16.0, on_progress=fortschritt)

    return _strom(lambda fortschritt: g.bearbeiten("Normalisiert auf -16 LUFS", bearbeitung, fortschritt))


@router.post("/umwandeln")
async def umwandeln(req: Umwandeln):
    g = _zum_aendern(req.art, req.kennung)

    async def bearbeitung(pfade: list[Path], fortschritt) -> list[Path]:
        fertig = []
        for i, pfad in enumerate(pfade):
            fortschritt(i + 1, len(pfade), f"Stück {i + 1} von {len(pfade)}")
            fertig.append(await audio_processor.convert(pfad, req.format, req.bitrate, req.mono))
        return fertig

    was = f"Umgewandelt in {req.format.upper()} {req.bitrate} kbit/s" + (", Mono" if req.mono else "")
    return _strom(lambda fortschritt: g.bearbeiten(was, bearbeitung, fortschritt))


@router.post("/rueckgaengig")
async def rueckgaengig(req: Gegenstand):
    was = await _sicher(_zum_aendern(req.art, req.kennung).rueckgaengig())
    if was is None:
        raise HTTPException(409, "Kein Schritt zum Zurücknehmen")
    return {"zurueckgenommen": was}
