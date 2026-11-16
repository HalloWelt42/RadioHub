"""
RadioHub v0.1.8 - Config Router

Globale Einstellungen lesen/schreiben
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict

from ..services.config_service import config_service

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    """Beliebige Config-Updates"""
    updates: Dict[str, Any]


@router.get("")
async def get_config():
    """Alle Einstellungen holen"""
    return config_service.get_all()


@router.put("")
async def update_config(body: ConfigUpdate):
    """Einstellungen aktualisieren"""
    result = config_service.update(body.updates)
    return {"success": True, "config": result}


@router.post("/reset")
async def reset_config():
    """Auf Standardwerte zurücksetzen"""
    result = config_service.reset()
    return {"success": True, "config": result}


@router.get("/{key}")
async def get_config_key(key: str):
    """Einzelne Einstellung holen"""
    value = config_service.get(key)
    return {"key": key, "value": value}


@router.put("/{key}")
async def set_config_key(key: str, value: Any):
    """Einzelne Einstellung setzen"""
    config_service.set(key, value)
    return {"success": True, "key": key, "value": value}
