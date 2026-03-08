"""
RadioHub v0.1.11 - Stations Router

Sender-Suche, Cache-Sync, Filter mit Sortierung, Bitrate-Detection
"""
import asyncio
from typing import Optional, List, Literal
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..services.cache import cache_service
from ..services.bitrate_detector import (
    get_uuids_needing_probe, get_cached_bitrates, probe_stations
)

router = APIRouter(prefix="/api", tags=["stations"])


class StationSearchRequest(BaseModel):
    q: Optional[str] = None
    countries: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    bitrate_min: Optional[int] = None
    bitrate_max: Optional[int] = None
    votes_min: Optional[int] = None
    votes_max: Optional[int] = None
    sort_by: Literal['name', 'country', 'bitrate', 'votes'] = 'votes'
    sort_order: Literal['asc', 'desc'] = 'desc'
    offset: int = 0
    limit: int = 100
    favs_only: bool = False


# === Cache ===

@router.post("/cache/sync")
async def sync_cache(force: bool = Query(False)):
    """Synchronisiert Sender-Cache mit radio-browser.info"""
    result = await cache_service.sync_stations(force)
    return result


@router.get("/cache/stats")
async def cache_stats():
    """Cache-Statistiken"""
    return cache_service.get_stats()


@router.get("/cache/filters")
async def cache_filters():
    """Filter-Optionen (Länder, Genres, Bitraten, max_votes)"""
    return cache_service.get_filters()


# === Stations ===

@router.post("/stations/search")
async def search_stations(req: StationSearchRequest):
    """Sucht Sender mit Filtern und Sortierung"""
    stations = cache_service.search_stations(
        q=req.q,
        countries=req.countries,
        tags=req.tags,
        bitrate_min=req.bitrate_min,
        bitrate_max=req.bitrate_max,
        votes_min=req.votes_min,
        votes_max=req.votes_max,
        sort_by=req.sort_by,
        sort_order=req.sort_order,
        limit=req.limit,
        offset=req.offset,
        favs_only=req.favs_only
    )

    # Erkannte Bitrates/Codecs mergen -- reale Werte haben immer Vorrang
    if stations:
        uuids = [s["uuid"] for s in stations if "uuid" in s]
        detected = get_cached_bitrates(uuids)
        for s in stations:
            det = detected.get(s.get("uuid"))
            if det and det["bitrate"] > 0:
                s["bitrate"] = det["bitrate"]
                if det.get("codec"):
                    s["codec"] = det["codec"].upper()

    return {"count": len(stations), "stations": stations}


@router.get("/stations/{uuid}")
async def get_station(uuid: str):
    """Holt einzelnen Sender"""
    from ..database import db_session

    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM stations WHERE uuid = ?", (uuid,))
        row = c.fetchone()
        if row:
            return dict(row)

    return {"error": "Sender nicht gefunden"}


# === Bitrate Detection ===

class VerifyBitrateRequest(BaseModel):
    uuids: List[str]


@router.post("/stations/verify-bitrate")
async def verify_bitrate(req: VerifyBitrateRequest):
    """
    Startet Bitrate-Erkennung via ffprobe fuer Sender mit fehlender Bitrate.
    Laeuft im Hintergrund, Ergebnisse werden gecacht.
    """
    # Nur UUIDs die noch nicht geprobt wurden
    to_probe = get_uuids_needing_probe(req.uuids)

    if not to_probe:
        return {"queued": 0, "message": "Alle bereits geprueft"}

    # Stationen mit URLs aus DB holen
    from ..database import db_session
    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(to_probe))
        c.execute(
            f"SELECT uuid, name, url, url_resolved FROM stations WHERE uuid IN ({placeholders})",
            to_probe
        )
        stations = [dict(row) for row in c.fetchall()]

    if not stations:
        return {"queued": 0, "message": "Keine Stationen gefunden"}

    # Im Hintergrund proben (async in eigenem Task)
    async def _run_probes():
        await probe_stations(stations)

    asyncio.get_event_loop().create_task(_run_probes())

    return {"queued": len(stations)}


@router.post("/stations/bitrates")
async def get_bitrates(req: VerifyBitrateRequest):
    """Holt gecachte erkannte Bitrates fuer gegebene UUIDs."""
    cached = get_cached_bitrates(req.uuids)
    return {"bitrates": cached}
