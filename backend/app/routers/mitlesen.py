"""Live mitlesen (RAD-129): starten am laufenden Sender, abfragen, Übersetzen schalten, beenden. Jede Abfrage hält es am Laufen."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ..services.empfang import empfaenge
from ..services.mitlesen import Stand, Wahl, mitleser

router = APIRouter(prefix="/api/mitlesen", tags=["mitlesen"])

KUERZEL = r"^[a-z]{2,3}$"


class Start(BaseModel):
    uuid: str = Field(min_length=1, max_length=100)
    #: Sprache laut Sprachlabel des Senders; leer oder mehrere: erkennen
    sprache: str = Field("", pattern=rf"{KUERZEL}|^$")
    #: Sprache der Oberfläche, in die übersetzt wird
    ziel: str = Field("de", pattern=KUERZEL)
    uebersetzen: bool = False


class Stellung(BaseModel):
    uebersetzen: bool | None = None
    sprechen: bool | None = None


class Faehigkeit(BaseModel):
    eingerichtet: bool


@router.get("/kann")
def kann() -> Faehigkeit:
    return Faehigkeit(eingerichtet=mitleser.eingerichtet)


@router.post("")
async def starten(s: Start) -> Stand:
    if not mitleser.eingerichtet:
        raise HTTPException(503, "Die Leitstelle ist nicht eingerichtet")
    e = empfaenge.von_sender(s.uuid)
    if e is None:
        raise HTTPException(409, "Der Sender läuft gerade nicht über den Puffer")
    return await mitleser.starten(e, Wahl(sprache=s.sprache, ziel=s.ziel, uebersetzen=s.uebersetzen))


@router.get("")
def lesen(ab: Annotated[int, Query(ge=0)] = 0) -> Stand:
    return mitleser.stand(ab)


@router.get("/ton/{nr}")
def ton(nr: int) -> Response:
    """Ein gesprochener Absatz."""
    daten = mitleser.ton(nr)
    if daten is None:
        raise HTTPException(404, "Dieser Absatz ist nicht gesprochen")
    return Response(daten, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=3600"})


@router.put("")
def stellen(s: Stellung) -> Stand:
    mitleser.stellen(s.uebersetzen, s.sprechen)
    return mitleser.stand(0)


@router.delete("")
async def beenden() -> Stand:
    await mitleser.beenden()
    return mitleser.stand(0)
