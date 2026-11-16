"""
Werte unter /api/config lesen und schreiben: Einstellungen des Servers (aus den Einstellungen des Appkerns) und Stand
der Oberfläche (Tabelle config), siehe services/config_service.py
"""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from appkern.einstellungen import FestesFeld, Unzulaessig

from ..services.config_service import config_service

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    """Beliebige Config-Updates"""
    updates: Dict[str, Any]


async def _aendern(updates: Dict[str, Any]) -> dict:
    """Ändern mit lesbaren Fehlern: feste Einstellungen (vom Ausrollen) 409, ungültige Werte 422."""
    try:
        return await config_service.aendern(updates)
    except FestesFeld as f:
        raise HTTPException(status_code=409, detail=f"Fest eingestellt (vom Ausrollen), hier nicht änderbar: {f}")
    except Unzulaessig as f:
        raise HTTPException(status_code=422, detail=f.meldung)
    except ValidationError as f:
        raise HTTPException(status_code=422, detail=f"Ungültiger Wert: {f.errors()[0].get('msg', f)}")


@router.get("")
async def get_config():
    """Alle Einstellungen holen"""
    return config_service.get_all()


@router.put("")
async def update_config(body: ConfigUpdate):
    """Einstellungen aktualisieren"""
    result = await _aendern(body.updates)
    return {"success": True, "config": result}


@router.post("/reset")
async def reset_config():
    """Auf Standardwerte zurücksetzen"""
    result = await config_service.reset()
    return {"success": True, "config": result}


@router.get("/{key}")
async def get_config_key(key: str):
    """Einzelne Einstellung holen"""
    value = config_service.get(key)
    return {"key": key, "value": value}


@router.put("/{key}")
async def set_config_key(key: str, value: Any):
    """Einzelne Einstellung setzen"""
    await _aendern({key: value})
    return {"success": True, "key": key, "value": config_service.get(key)}
