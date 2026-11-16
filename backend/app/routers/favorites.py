"""
RadioHub v0.1.3 - Favorites Router

Favoriten speichern, laden, löschen
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db_session

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


class FavoriteAddRequest(BaseModel):
    stationuuid: str
    name: str
    url: str
    url_resolved: Optional[str] = None
    favicon: Optional[str] = None
    country: Optional[str] = None
    countrycode: Optional[str] = None
    tags: Optional[str] = None
    bitrate: int = 0


@router.get("")
async def get_favorites():
    """Alle Favoriten-UUIDs (für schnellen Check)"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT uuid FROM favorites")
        return [row[0] for row in c.fetchall()]


@router.get("/all")
async def get_favorites_all():
    """Alle Favoriten mit Details"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM favorites ORDER BY name")
        return [dict(row) for row in c.fetchall()]


@router.post("")
async def add_favorite(req: FavoriteAddRequest):
    """Favorit hinzufügen"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO favorites 
            (uuid, name, url, url_resolved, favicon, country, countrycode, tags, bitrate, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (req.stationuuid, req.name, req.url, req.url_resolved, req.favicon,
             req.country, req.countrycode, req.tags, req.bitrate,
             datetime.now().isoformat()))
    
    return {"success": True, "uuid": req.stationuuid}


@router.delete("/{uuid}")
async def remove_favorite(uuid: str):
    """Favorit entfernen"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM favorites WHERE uuid = ?", (uuid,))
        deleted = c.rowcount > 0
    
    return {"success": deleted}
