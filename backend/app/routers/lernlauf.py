"""Lernlauf und Signaturen des Propaganda-Filters für die Oberfläche (HELF-256): was nachts gehört und gefunden wurde, was alles
weggefiltert werden kann, anhören, bestätigen, verwerfen. RadioHub reicht nur durch; die Wahrheit liegt beim Filter."""
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ..services import lernliste
from ..services import propagandafilter as pf

router = APIRouter(prefix="/api/werbefilter", tags=["werbung"])

Ab = Annotated[int, Query(ge=0)]
Anzahl = Annotated[int, Query(ge=1, le=200)]
ZEIT = r"^([01]\d|2[0-3]):[0-5]\d$"


class Lernlaufstellung(BaseModel):
    an: bool | None = None
    von: str | None = Field(None, pattern=ZEIT)
    bis: str | None = Field(None, pattern=ZEIT)
    gleichzeitig: int | None = Field(None, ge=1, le=12)


class Sofortlauf(BaseModel):
    minuten: float = Field(ge=0, le=720)


class Ausnahme(BaseModel):
    aus: bool


class Urteil(BaseModel):
    urteil: Literal["offen", "bestaetigt", "verworfen"]


class Quellenstand(BaseModel):
    stand: Literal["wirkt", "vorschlag"]


async def _filter(methode: str, pfad: str, **art: Any) -> Any:
    try:
        return (await pf.fragen(methode, pfad, **art)).json()
    except pf.FilterFehler as f:
        raise HTTPException(503, str(f)) from f


@router.get("")
async def stand() -> dict[str, Any]:
    """Eingerichtet, erreichbar, und was der Filter und sein Lernlauf gerade tun."""
    if not pf.FilterEinstellungen.jetzt().eingerichtet:
        return {"eingerichtet": False, "erreichbar": False, "grund": "", "filter": None, "lernlauf": None}
    try:
        return {"eingerichtet": True, "erreichbar": True, "grund": "", "filter": (await pf.fragen("GET", "stand")).json(),
                "lernlauf": (await pf.fragen("GET", "lernlauf")).json()}
    except pf.FilterFehler as f:
        return {"eingerichtet": True, "erreichbar": False, "grund": str(f), "filter": None, "lernlauf": None}


@router.put("/lernlauf")
async def lernlauf_stellen(neu: Lernlaufstellung) -> Any:
    return await _filter("PUT", "lernlauf", json=neu.model_dump(exclude_none=True))


@router.post("/lernlauf/jetzt")
async def lernlauf_jetzt(neu: Sofortlauf) -> Any:
    return await _filter("POST", "lernlauf/jetzt", json=neu.model_dump())


@router.get("/sender")
async def sender(ab: Ab = 0, anzahl: Anzahl = 25) -> Any:
    return await _filter("GET", "lernlauf/sender", params={"ab": ab, "anzahl": anzahl})


@router.post("/sender")
async def sender_neu_waehlen() -> dict[str, int]:
    """Die Liste jetzt neu nach dem Hörverhalten zusammenstellen."""
    try:
        return {"sender": await lernliste.weitergeben()}
    except pf.FilterFehler as f:
        raise HTTPException(503, str(f)) from f


@router.put("/sender/{uuid}")
async def sender_ausnehmen(uuid: UUID, neu: Ausnahme) -> Any:
    return await _filter("PUT", f"lernlauf/sender/{uuid}", json=neu.model_dump())


@router.get("/spots/{fach}")
async def spots(fach: Literal["pruefen", "wirkt", "verworfen"], ab: Ab = 0, anzahl: Anzahl = 25) -> Any:
    """Ein Stück eines Fachs der Durchsicht und wie viele in jedem Fach liegen."""
    return await _filter("GET", f"signaturen/fach/{fach}", params={"ab": ab, "anzahl": anzahl})


@router.get("/signaturen/{kennung}/ton")
async def ton(kennung: UUID) -> Response:
    try:
        a = await pf.fragen("GET", f"signaturen/{kennung}/ton")
    except pf.FilterFehler as f:
        raise HTTPException(503, str(f)) from f
    return Response(a.content, media_type=a.headers.get("content-type", "audio/mp4"), headers={"Cache-Control": "private, max-age=86400"})


@router.put("/signaturen/{kennung}")
async def beurteilen(kennung: UUID, neu: Urteil) -> Any:
    return await _filter("PUT", f"signaturen/{kennung}", json=neu.model_dump())


@router.put("/signaturen/{kennung}/quellen/{uuid}")
async def quelle_setzen(kennung: UUID, uuid: UUID, neu: Quellenstand) -> Any:
    return await _filter("PUT", f"signaturen/{kennung}/quellen/{uuid}", json=neu.model_dump())
