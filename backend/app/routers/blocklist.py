"""Sperrliste der heutigen Oberfläche (bis Etappe 3b) auf der neuen Sichtbarkeit (RAD-7): Sperren wird zur
Einzelsperre (oder mit "ad:..." zur Werbeentscheidung), Entsperren gibt den Sender frei, die Liste zeigt alle
ausgeblendeten Sender mit Grund. Ohne SQL (Regel D2)."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.senderquelle import alte_wege, dienst

router = APIRouter(prefix="/api/blocklist", tags=["blocklist"])


class BlockRequest(BaseModel):
    uuid: str
    name: str
    reason: Optional[str] = "manual"


class Liste(BaseModel):
    count: int
    blocked: list[alte_wege.AlteSperre]


class Gesperrt(BaseModel):
    success: bool
    blocked: str


class Entsperrt(BaseModel):
    success: bool
    unblocked: str


class Pruefung(BaseModel):
    uuid: str
    blocked: bool


@router.get("", response_model=Liste)
async def get_blocklist() -> Liste:
    """Alle ausgeblendeten Sender mit Grund."""
    alle = await alte_wege.ausgeblendete()
    return Liste(count=len(alle), blocked=alle)


@router.post("", response_model=Gesperrt)
async def block_station(req: BlockRequest) -> Gesperrt:
    """Sender ausblenden (Einzelsperre; mit Grund "ad:..." als Werbeentscheidung)."""
    try:
        await alte_wege.sperren(req.uuid, req.reason)
    except dienst.NichtGefunden as f:
        raise HTTPException(404, str(f)) from f
    return Gesperrt(success=True, blocked=req.uuid)


@router.delete("/{uuid}", response_model=Entsperrt)
async def unblock_station(uuid: str) -> Entsperrt:
    """Sender wieder sichtbar (Einzelsperre weg, sonst als Ausnahme freigegeben)."""
    if not await alte_wege.ist_ausgeblendet(uuid):
        raise HTTPException(404, "Sender ist nicht ausgeblendet")
    await dienst.freigeben(uuid)
    return Entsperrt(success=True, unblocked=uuid)


@router.get("/check/{uuid}", response_model=Pruefung)
async def is_blocked(uuid: str) -> Pruefung:
    """Ist der Sender ausgeblendet?"""
    return Pruefung(uuid=uuid, blocked=await alte_wege.ist_ausgeblendet(uuid))
