"""Werbestellen in Podcast-Folgen (RAD-32): lesen, von Hand setzen, verwerfen ("keine Werbung") und zurück, suchen
über alle möglichen Quellen und eine Fassung ohne Werbung neben die gespeicherte Folge legen (beides als Strom); je Abo
die Schalter überspringen und neue Folgen prüfen."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db_session
from ..services import werbestellen as ws
from ..services.podcast import podcast_service
from .ereignisstrom import ereignisstrom

router = APIRouter(prefix="/api/podcasts", tags=["werbung"])


class Werbestellen(BaseModel):
    stellen: list[ws.Werbestelle]
    #: welche Quellen eine Suche für diese Folge nutzen kann
    quellen: list[ws.Herkunft]


class Verwerfen(BaseModel):
    verworfen: bool


class AboWerbung(BaseModel):
    ueberspringen: bool | None = None
    pruefen: bool | None = None


async def _folge(folge_id: int) -> dict:
    f = await podcast_service.get_episode(folge_id)
    if not f:
        raise HTTPException(404, "Folge nicht gefunden")
    return f


@router.get("/episodes/{folge_id}/werbung")
async def lesen(folge_id: int) -> Werbestellen:
    return Werbestellen(stellen=ws.stellen(folge_id), quellen=ws.quellen(await _folge(folge_id)))


@router.post("/episodes/{folge_id}/werbung")
async def setzen(folge_id: int, neu: ws.Neu) -> ws.Werbestelle:
    try:
        return ws.anlegen(folge_id, neu, "hand")
    except LookupError as f:
        raise HTTPException(404, str(f)) from None
    except ValueError as f:
        raise HTTPException(400, str(f)) from None


@router.patch("/werbung/{stelle_id}")
async def verwerfen(stelle_id: int, req: Verwerfen) -> ws.Werbestelle:
    try:
        return ws.verwerfen(stelle_id, req.verworfen)
    except LookupError as f:
        raise HTTPException(404, str(f)) from None


@router.post("/episodes/{folge_id}/werbung/suchen")
async def suchen(folge_id: int):
    folge = await _folge(folge_id)
    return ereignisstrom(lambda fortschritt: ws.suchen(folge, fortschritt), "gefunden")


@router.post("/episodes/{folge_id}/ohne-werbung")
async def ohne_werbung(folge_id: int):
    folge = await _folge(folge_id)
    return ereignisstrom(lambda fortschritt: ws.ohne_werbung(folge, fortschritt), "pfad")


@router.put("/{podcast_id}/werbung")
async def abo_werbung(podcast_id: int, req: AboWerbung) -> dict:
    teile = {k: v for k, v in (("werbung_ueberspringen", req.ueberspringen), ("werbung_pruefen", req.pruefen)) if v is not None}
    if not teile:
        raise HTTPException(400, "Nichts zu ändern")
    with db_session() as conn:
        n = conn.execute(f"UPDATE podcast_subscriptions SET {', '.join(f'{k} = ?' for k in teile)} WHERE id = ?",
                         [int(v) for v in teile.values()] + [podcast_id]).rowcount
    if not n:
        raise HTTPException(404, "Abo nicht gefunden")
    return {"success": True}
