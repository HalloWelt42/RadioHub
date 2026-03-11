"""
RadioHub Storage API Router

Endpoints fuer Storage-Zone-Verwaltung.
Ermoeglicht Frontend-Konfiguration der Speicherpfade.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..storage import get_all_zones, update_zone, validate_path, reload as reload_storage

router = APIRouter(prefix="/api/storage", tags=["storage"])


class ZoneUpdateRequest(BaseModel):
    path: str


class PathValidateRequest(BaseModel):
    path: str


@router.get("/zones")
async def list_zones():
    """Alle Storage-Zonen mit Pfad, Speicherplatz, Status"""
    try:
        zones = get_all_zones()
        return {"zones": zones}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/zones/{zone}")
async def update_zone_path(zone: str, req: ZoneUpdateRequest):
    """Pfad einer Storage-Zone aendern.
    Verschiebt keine Daten - nur der Pfad wird aktualisiert."""
    try:
        result = update_zone(zone, req.path)
        # Konfiguration neu laden damit Aenderungen wirksam werden
        reload_storage()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate")
async def validate_storage_path(path: str):
    """Pfad pruefen (existiert, beschreibbar, Speicherplatz)"""
    if not path:
        raise HTTPException(status_code=400, detail="Pfad darf nicht leer sein")
    try:
        result = validate_path(path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
