"""Filter-Einstellungen der heutigen Oberfläche (bis Etappe 3b) auf der neuen Sichtbarkeit (RAD-7): Vorschau und
Ausblenden legen lebende Regeln an, die Liste der ausgeblendeten Sender kommt aus den Treffern der Regeln, Freigeben
schaltet Regeln aus oder gibt einzelne Sender frei. Ohne SQL (Regel D2)."""
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..services.senderquelle import alte_wege

router = APIRouter(prefix="/api/filters", tags=["filters"])


class FilterCriteria(BaseModel):
    excluded_languages: List[str] = []
    excluded_tags: List[str] = []
    min_votes: int = 0

    def kriterien(self) -> alte_wege.AlteKriterien:
        return alte_wege.AlteKriterien(sprachen=self.excluded_languages, tags=self.excluded_tags,
                                       mindeststimmen=max(0, self.min_votes))


class ReleaseRequest(BaseModel):
    uuids: Optional[List[str]] = None
    reason: Optional[str] = None
    all: bool = False


class Vorschau(BaseModel):
    count: int
    sample: list[alte_wege.SenderProbe]


class Ausgeblendet(BaseModel):
    hidden_count: int
    total_hidden: int


class Kategorie(BaseModel):
    count: int
    reasons: dict[str, int]


class Verborgene(BaseModel):
    count: int
    categories: dict[str, Kategorie]
    stations: list[alte_wege.AlteSperre]


class Freigegeben(BaseModel):
    released_count: int


class Sprachen(BaseModel):
    languages: list[alte_wege.Eintragszahl]


class Laender(BaseModel):
    countries: list[alte_wege.Landzahl]


@router.post("/preview", response_model=Vorschau)
async def filter_preview(criteria: FilterCriteria) -> Vorschau:
    """Vorschau: welche heute sichtbaren Sender würden zusätzlich ausgeblendet?"""
    anzahl, proben = await alte_wege.vorschau(criteria.kriterien())
    return Vorschau(count=anzahl, sample=proben)


@router.post("/push", response_model=Ausgeblendet)
async def filter_push(criteria: FilterCriteria) -> Ausgeblendet:
    """Ausblenden: lebende Regeln für die Kriterien, die noch keine Regel abdeckt."""
    neu, gesamt = await alte_wege.ausblenden(criteria.kriterien())
    return Ausgeblendet(hidden_count=neu, total_hidden=gesamt)


@router.get("/hidden", response_model=Verborgene)
async def get_hidden(reason: Optional[str] = None, category: Optional[str] = None) -> Verborgene:
    """Alle ausgeblendeten Sender mit Grund, nach Kategorien gezählt."""
    alle = await alte_wege.ausgeblendete()
    kategorien: dict[str, Kategorie] = {}
    for s in alle:
        k = kategorien.setdefault(s.category, Kategorie(count=0, reasons={}))
        k.count += 1
        k.reasons[s.reason] = k.reasons.get(s.reason, 0) + 1
    gewaehlt = [s for s in alle if (reason is None or reason in s.reason) and (category is None or s.category == category)]
    return Verborgene(count=len(gewaehlt), categories=kategorien, stations=gewaehlt)


@router.post("/release", response_model=Freigegeben)
async def release_stations(req: ReleaseRequest) -> Freigegeben:
    """Freigeben: einzelne Sender, je Grund (Regel aus) oder alle (alle Regeln aus); nichts wird gelöscht."""
    if not (req.uuids or req.reason or req.all):
        return Freigegeben(released_count=0)
    return Freigegeben(released_count=await alte_wege.freigeben(req.uuids, req.reason, req.all))


@router.get("/languages", response_model=Sprachen)
async def get_languages() -> Sprachen:
    """Sprachen, wie sie im Verzeichnis stehen, mit Anzahl (dieselben genauen Einträge wie beim Ausschließen)."""
    return Sprachen(languages=await alte_wege.spracheintraege())


@router.get("/countries", response_model=Laender)
async def get_countries() -> Laender:
    """Länder mit Anzahl der sichtbaren Sender."""
    return Laender(countries=await alte_wege.laender())
