"""
RadioHub v0.1.10 - Blocklist Router

Negativliste für Sender - blockierte Sender werden aus Suchergebnissen gefiltert
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db_session

router = APIRouter(prefix="/api/blocklist", tags=["blocklist"])


class BlockRequest(BaseModel):
    uuid: str
    name: str
    reason: Optional[str] = "manual"


@router.get("")
async def get_blocklist():
    """Alle blockierten Sender"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM blocklist ORDER BY blocked_at DESC")
        blocked = [dict(row) for row in c.fetchall()]
    
    return {"count": len(blocked), "blocked": blocked}


@router.post("")
async def block_station(req: BlockRequest):
    """Sender blockieren"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO blocklist (uuid, name, reason, category, blocked_at) VALUES (?, ?, ?, ?, ?)",
            (req.uuid, req.name, req.reason,
             'ad' if (req.reason or '').startswith('ad:') else 'manual',
             datetime.now().isoformat())
        )
    
    return {"success": True, "blocked": req.uuid}


@router.delete("/{uuid}")
async def unblock_station(uuid: str):
    """Sender entsperren"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM blocklist WHERE uuid = ?", (uuid,))
        if c.rowcount == 0:
            raise HTTPException(404, "Sender nicht in Blocklist")
    
    return {"success": True, "unblocked": uuid}


@router.get("/check/{uuid}")
async def is_blocked(uuid: str):
    """Prüfen ob Sender blockiert ist"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM blocklist WHERE uuid = ?", (uuid,))
        blocked = c.fetchone() is not None
    
    return {"uuid": uuid, "blocked": blocked}
