"""
RadioHub v0.8.0 - Zeitansage

Stand der Bausteine, Erzeugen der fehlenden (im Hintergrund, über die Vertonung) und Ausliefern aus der Ablage.
"""
import asyncio

from fastapi import APIRouter, HTTPException, Query, Request

from ..ablage import orte
from ..ablage.wiedergabe import ausliefern
from ..einstellungen import stand as einstellungen_stand
from ..services.zeitansage import ZeitansageEinstellungen, bausteine, zeitansage

router = APIRouter(prefix="/api/zeitansage", tags=["zeitansage"])
_lauf: asyncio.Task | None = None


@router.get("")
async def stand():
    """Alle Bausteine, die fehlenden und der Stand einer laufenden Erzeugung."""
    return await zeitansage.stand()


@router.post("/erzeugen", status_code=202)
async def erzeugen():
    """Fehlende Bausteine im Hintergrund sprechen lassen; der Stand steht danach unter GET /api/zeitansage."""
    global _lauf
    if not (_lauf and not _lauf.done()):
        _lauf = asyncio.create_task(zeitansage.erzeugen())
    return {"gestartet": True}


@router.get("/ton/{name}")
async def ton(name: str, request: Request, stimme: str | None = Query(None, max_length=200)):
    """Ein Baustein als MP3, von `stimme` (wie im Stand genannt; so trennt der Zwischenspeicher die Stimmen), ohne
    Angabe von der eingestellten."""
    if name not in bausteine():
        raise HTTPException(404, "Unbekannter Baustein")
    stimme = stimme or ZeitansageEinstellungen.aus(einstellungen_stand()).stimme
    antwort = await ausliefern(orte.zeitansage(stimme, name), request)
    antwort.headers["Cache-Control"] = "public, max-age=86400"
    return antwort
