"""Speicherzonen und Ablage anzeigen (RAD-11: nur lesen; Pfade setzt das Ausrollen)."""
from fastapi import APIRouter, HTTPException

from ..ablage import ablage
from ..storage import get_all_zones

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/zones")
async def list_zones():
    """Alle Speicherzonen mit Pfad, Belegung und freiem Platz"""
    try:
        return {"zones": get_all_zones()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ablage")
async def ablage_zustand():
    """Stand der Ablage (Kellerwolke): Ziel, Wurzelordner, verbunden, Meldung"""
    return await ablage().zustand()
