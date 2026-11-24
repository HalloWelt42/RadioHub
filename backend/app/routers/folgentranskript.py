"""Transkript einer Podcast-Folge (RAD-22): lesen (gehört oder vom Feed), transkribieren lassen, Fortschritt, abbrechen."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..services.folgentranskript import ART, Transkript, folgentranskripte
from ..services.podcast import podcast_service

router = APIRouter(prefix="/api/podcasts", tags=["folgentranskript"])


class Lauf(BaseModel):
    id: str
    #: 0 bis 1, None: noch nicht messbar
    fortschritt: float | None = None
    schritt: str = ""


class Stand(BaseModel):
    transkript: Transkript | None = None
    #: es wird gerade transkribiert
    lauf: Lauf | None = None
    #: woran der letzte Versuch scheiterte
    fehler: str = ""
    kann_transkribieren: bool = False


async def _folge(folge_id: int) -> dict:
    f = await podcast_service.get_episode(folge_id)
    if not f:
        raise HTTPException(404, "Folge nicht gefunden")
    return f


async def _auftrag(request: Request, folge_id: int):
    eintraege = (await request.app.state.geruest.auftraege.liste(art=ART, grenze=100)).eintraege
    return next((a for a in eintraege if a.eingabe.get("folge_id") == folge_id), None)


@router.get("/episodes/{folge_id}/transkript")
async def lesen(folge_id: int, request: Request, fassung: str = "") -> Stand:
    folge = await _folge(folge_id)
    a = await _auftrag(request, folge_id)
    offen = a is not None and a.zustand in ("wartet", "laeuft")
    t = None if offen else await folgentranskripte.lesen(folge, fassung)
    return Stand(transkript=t, kann_transkribieren=folgentranskripte.kann(),
                 lauf=Lauf(id=a.id, fortschritt=a.fortschritt, schritt=a.schritt) if offen else None,
                 fehler=(a.fehler or "") if a is not None and a.zustand in ("fehler", "unterbrochen") and t is None else "")


@router.post("/episodes/{folge_id}/transkript")
async def transkribieren(folge_id: int, request: Request) -> Stand:
    folge = await _folge(folge_id)
    if not folgentranskripte.kann():
        raise HTTPException(503, "Keine Transkription eingestellt")
    await request.app.state.geruest.auftraege.einreihen(ART, {"folge_id": folge_id}, titel=f"Transkribieren: {folge.get('title') or folge_id}", von="RadioHub")
    return await lesen(folge_id, request)


@router.delete("/episodes/{folge_id}/transkript/lauf")
async def abbrechen(folge_id: int, request: Request) -> Stand:
    a = await _auftrag(request, folge_id)
    if a is not None and a.zustand in ("wartet", "laeuft"):
        await request.app.state.geruest.auftraege.abbrechen(a.id)
    return await lesen(folge_id, request)
