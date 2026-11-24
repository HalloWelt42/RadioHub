"""Vertonte Fassungen einer Folge (RAD-26): vertonen lassen, Fortschritt, abbrechen, Fassung wählen; dazu, welche Dateien zu einer
gespeicherten Folge gehören (Rückfrage vor dem Löschen)."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..ablage import AblageFehler, ablage
from ..einstellungen import SPRACHEN
from ..einstellungen import stand as einstellungen_stand
from ..services import folgenvertonung as fv
from ..services.podcast import podcast_service

router = APIRouter(prefix="/api/podcasts", tags=["folgenvertonung"])


class Lauf(BaseModel):
    id: str
    #: 0 bis 1, None: noch nicht messbar
    fortschritt: float | None = None
    schritt: str = ""


class Sprachfassung(BaseModel):
    sprache: str
    name: str
    stimme: str = ""


class Stand(BaseModel):
    fassungen: list[Sprachfassung] = []
    #: welche man hört, leer: das Original
    gewaehlt: str = ""
    #: in diese Sprache wird vertont
    ziel: str
    zielname: str
    lauf: Lauf | None = None
    fehler: str = ""
    kann_vertonen: bool = False


class Vertonen(BaseModel):
    stimme: str = Field("", max_length=200)          # leer: die Einstellung


class Wahl(BaseModel):
    sprache: str = Field("", max_length=8)


class Datei(BaseModel):
    pfad: str
    groesse: int
    art: Literal["folge", "begleiter"]


class Dateien(BaseModel):
    dateien: list[Datei]


async def _folge(folge_id: int) -> dict:
    f = await podcast_service.get_episode(folge_id)
    if not f:
        raise HTTPException(404, "Folge nicht gefunden")
    return f


async def _auftrag(request: Request, folge_id: int):
    eintraege = (await request.app.state.geruest.auftraege.liste(art=fv.ART, grenze=100)).eintraege
    return next((a for a in eintraege if a.eingabe.get("folge_id") == folge_id), None)


async def _stand(folge_id: int, request: Request) -> Stand:
    folge = await _folge(folge_id)
    a = await _auftrag(request, folge_id)
    offen = a is not None and a.zustand in ("wartet", "laeuft")
    da = fv.fassungen(folge_id)
    ziel = einstellungen_stand().podcast_sprache
    return Stand(fassungen=[Sprachfassung(sprache=f.sprache, name=SPRACHEN.get(f.sprache, f.sprache), stimme=f.stimme) for f in da],
                 gewaehlt=folge.get("fassung") or "", ziel=ziel, zielname=SPRACHEN.get(ziel, ziel),
                 lauf=Lauf(id=a.id, fortschritt=a.fortschritt, schritt=a.schritt) if offen else None,
                 fehler=(a.fehler or "") if a is not None and a.zustand in ("fehler", "unterbrochen") else "",
                 kann_vertonen=fv.folgenvertonung.kann())


@router.get("/episodes/{folge_id}/vertonung")
async def lesen(folge_id: int, request: Request) -> Stand:
    return await _stand(folge_id, request)


@router.post("/episodes/{folge_id}/vertonung")
async def vertonen(folge_id: int, eingabe: Vertonen, request: Request) -> Stand:
    folge = await _folge(folge_id)
    if not fv.folgenvertonung.kann():
        raise HTTPException(503, "Vertonung, Stimme oder Transkription fehlt (Einstellungen)")
    ziel = einstellungen_stand().podcast_sprache
    await request.app.state.geruest.auftraege.einreihen(
        fv.ART, {"folge_id": folge_id, "sprache": ziel, "stimme": eingabe.stimme.strip()},
        titel=f"Vertonen ({SPRACHEN.get(ziel, ziel)}): {folge.get('title') or folge_id}", von="RadioHub")
    return await _stand(folge_id, request)


@router.delete("/episodes/{folge_id}/vertonung/lauf")
async def abbrechen(folge_id: int, request: Request) -> Stand:
    a = await _auftrag(request, folge_id)
    if a is not None and a.zustand in ("wartet", "laeuft"):
        await request.app.state.geruest.auftraege.abbrechen(a.id)
    return await _stand(folge_id, request)


@router.put("/episodes/{folge_id}/fassung")
async def fassung_waehlen(folge_id: int, wahl: Wahl, request: Request) -> Stand:
    await _folge(folge_id)
    if wahl.sprache and fv.fassung(folge_id, wahl.sprache) is None:
        raise HTTPException(404, "Diese Fassung gibt es nicht")
    fv.waehlen(folge_id, wahl.sprache)
    return await _stand(folge_id, request)


@router.get("/episodes/{folge_id}/dateien")
async def dateien(folge_id: int) -> Dateien:
    """Alles, was zur gespeicherten Folge gehört und mit ihr in den Papierkorb kommt."""
    folge = await _folge(folge_id)
    pfad = folge.get("local_path") if folge.get("is_downloaded") else None
    if not pfad:
        return Dateien(dateien=[])
    try:
        haupt = await ablage().eintrag(pfad)
        begleiter = await ablage().begleiter(pfad)
    except AblageFehler as f:
        raise HTTPException(503, str(f)) from f
    aus = [Datei(pfad=haupt.pfad, groesse=haupt.groesse, art="folge")] if haupt else []
    return Dateien(dateien=aus + [Datei(pfad=b.pfad, groesse=b.groesse, art="begleiter") for b in begleiter])
