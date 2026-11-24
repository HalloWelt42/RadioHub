"""Messmodus (RAD-143): Ereignisse der Oberfläche annehmen, Messdateien auflisten, laden, auswerten, löschen."""
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..services.messung import Bericht, Datei, messung

router = APIRouter(prefix="/api/messung", tags=["messung"])


class Ereignis(BaseModel):
    art: str = Field(pattern=r"^[a-z_]{1,40}$")
    werte: dict[str, Any] = {}
    #: so lange ist es her (gesammelt wird auf dem Gerät)
    vor_ms: float = Field(0, ge=0, le=3_600_000)


class Meldung(BaseModel):
    geraet: str = Field("", max_length=80)
    ereignisse: list[Ereignis] = Field(max_length=500)


@router.get("")
def stand() -> dict[str, bool | list[Datei]]:
    messung.schreiben()
    return {"aktiv": messung.aktiv, "dateien": messung.dateien()}


@router.get("/aktiv")
def aktiv() -> dict[str, bool]:
    return {"aktiv": messung.aktiv}


@router.post("", status_code=202)
def melden(m: Meldung) -> dict[str, bool]:
    for e in m.ereignisse:
        messung.merken(e.art, vor_ms=e.vor_ms, geraet=m.geraet, **{k: v for k, v in e.werte.items() if k not in ("art", "t", "geraet", "vor_ms")})
    return {"aktiv": messung.aktiv}


@router.get("/{name}/bericht")
def bericht(name: str) -> Bericht:
    b = messung.bericht(name)
    if b is None:
        raise HTTPException(404, "Messung nicht gefunden")
    return b


@router.get("/{name}")
def laden(name: str) -> FileResponse:
    pfad = messung.pfad(name)
    if pfad is None:
        raise HTTPException(404, "Messung nicht gefunden")
    return FileResponse(pfad, media_type="application/x-ndjson", filename=name)


@router.delete("")
def loeschen() -> dict[str, int]:
    return {"geloescht": messung.loeschen()}
