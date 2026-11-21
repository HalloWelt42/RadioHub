"""Die ganze Kellerwolke für Aufnahmen und Schnitt (RAD-17): Ordner Ebene für Ebene mit ihren Audiodateien, Ton mit
Bereichsanfragen. Lesen braucht die Freigabe "Alles lesen" am App-Zugang; fehlt sie, sagt die Antwort das (403)."""
from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..ablage import AblageFehler, NichtGefunden, wolke
from ..ablage.port import KeinRecht, sauberer_pfad
from ..ablage.wiedergabe import ausliefern
from ..config import AUDIO_EXTENSIONS

router = APIRouter(prefix="/api/wolke", tags=["wolke"])

KEIN_RECHT = ("RadioHub darf die Kellerwolke nicht lesen. In der Kellerwolke unter Einstellungen, Zugänge dem "
              "App-Zugang von RadioHub die Freigabe \"Alles lesen\" geben.")


class Ordner(BaseModel):
    name: str
    pfad: str


class Datei(BaseModel):
    name: str
    pfad: str
    groesse: int
    geaendert: datetime | None = None


class Ebene(BaseModel):
    pfad: str
    kette: list[Ordner]          # von der obersten Ebene bis hier, ohne die oberste selbst
    ordner: list[Ordner]
    dateien: list[Datei]
    gesamt: int                  # Audiodateien in diesem Ordner, nicht nur die dieser Seite
    schreibbar: bool             # darf RadioHub hier Ergebnisse des Schnitts ablegen?


def _fehler(f: AblageFehler) -> HTTPException:
    if isinstance(f, KeinRecht):
        return HTTPException(403, KEIN_RECHT)
    if isinstance(f, NichtGefunden):
        return HTTPException(404, "Ordner nicht gefunden")
    return HTTPException(503, str(f))


def ist_audio(name: str) -> bool:
    return PurePosixPath(name).suffix.lower() in AUDIO_EXTENSIONS


@router.get("/ebene", response_model=Ebene)
async def ebene(pfad: str = "", ab: int = Query(0, ge=0), anzahl: int = Query(200, ge=1, le=500)) -> Ebene:
    try:
        pfad = sauberer_pfad(pfad)
    except ValueError as f:
        raise HTTPException(422, str(f)) from f
    try:
        eintraege = await wolke().liste(pfad)
        schreibbar = bool(pfad) and await wolke().darf_schreiben(pfad)
    except AblageFehler as f:
        raise _fehler(f) from f
    teile = pfad.split("/") if pfad else []
    kette = [Ordner(name=t, pfad="/".join(teile[: i + 1])) for i, t in enumerate(teile)]
    ordner = [Ordner(name=e.name, pfad=e.pfad) for e in eintraege if e.ist_ordner]
    audio = [Datei(name=e.name, pfad=e.pfad, groesse=e.groesse, geaendert=e.geaendert)
             for e in eintraege if not e.ist_ordner and ist_audio(e.name)]
    return Ebene(pfad=pfad, kette=kette, ordner=ordner, dateien=audio[ab: ab + anzahl], gesamt=len(audio),
                 schreibbar=schreibbar)


@router.get("/ton")
async def ton(request: Request, pfad: str, herunterladen: bool = False):
    """Eine Audiodatei der Kellerwolke hören (mit Bereich, damit Spulen geht) oder aufs Gerät laden."""
    if not ist_audio(pfad):
        raise HTTPException(415, "Keine Audiodatei")
    try:
        return await ausliefern(sauberer_pfad(pfad), request, herunterladen=herunterladen, quelle=wolke())
    except AblageFehler as f:
        raise _fehler(f) from f


__all__ = ["router"]
