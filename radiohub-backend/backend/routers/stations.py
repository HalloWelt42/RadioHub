"""
RadioHub v0.1.11 - Stations Router

Sender-Suche, Cache-Sync, Filter mit Sortierung, Bitrate-Detection
"""
import asyncio
from typing import Optional, List, Literal
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..services.cache import cache_service
from ..services.favicon_cache import cache_batch as favicon_cache_batch
from ..services.bitrate_detector import (
    get_uuids_needing_probe, get_cached_bitrates, probe_stations,
    fetch_icy_title, set_icy_quality
)

router = APIRouter(prefix="/api", tags=["stations"])


class StationSearchRequest(BaseModel):
    q: Optional[str] = None
    countries: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    exclude_languages: Optional[List[str]] = None
    exclude_tags: Optional[List[str]] = None
    bitrate_min: Optional[int] = None
    bitrate_max: Optional[int] = None
    votes_min: Optional[int] = None
    votes_max: Optional[int] = None
    sort_by: Literal['name', 'country', 'bitrate', 'votes'] = 'votes'
    sort_order: Literal['asc', 'desc'] = 'desc'
    offset: int = 0
    limit: int = 100
    favs_only: bool = False
    category_ids: Optional[List[int]] = None


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


@router.get("/cache/tags")
async def cache_tags(limit: int = Query(100)):
    """Erweiterte Tag-Liste mit Counts (fuer Kategorie-Verwaltung)."""
    tags = cache_service.get_tags(limit)
    return {"tags": tags}


# === Stations ===

@router.post("/stations/search")
async def search_stations(req: StationSearchRequest):
    """Sucht Sender mit Filtern und Sortierung"""
    stations = cache_service.search_stations(
        q=req.q,
        countries=req.countries,
        tags=req.tags,
        exclude_languages=req.exclude_languages,
        exclude_tags=req.exclude_tags,
        bitrate_min=req.bitrate_min,
        bitrate_max=req.bitrate_max,
        votes_min=req.votes_min,
        votes_max=req.votes_max,
        sort_by=req.sort_by,
        sort_order=req.sort_order,
        limit=req.limit,
        offset=req.offset,
        favs_only=req.favs_only,
        category_ids=req.category_ids
    )

    # Erkannte Bitrates/Codecs mergen -- nur fehlende Werte ergänzen
    if stations:
        uuids = [s["uuid"] for s in stations if "uuid" in s]
        detected = get_cached_bitrates(uuids)
        for s in stations:
            det = detected.get(s.get("uuid"))
            if det:
                if det["bitrate"] > 0:
                    # Nur ueberschreiben wenn Original-Wert fehlt oder 0
                    if not s.get("bitrate") or s["bitrate"] == 0:
                        s["bitrate"] = det["bitrate"]
                    if det.get("codec") and (not s.get("codec") or s["codec"] == ""):
                        s["codec"] = det["codec"].upper()
                # ICY-Status immer mitgeben
                if det.get("icy"):
                    s["icy"] = True
                    if det.get("icy_quality"):
                        s["icy_quality"] = det["icy_quality"]

    # Favicons im Hintergrund cachen
    if stations:
        asyncio.create_task(favicon_cache_batch(stations))

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
    Startet Bitrate-Erkennung via ffprobe für Sender mit fehlender Bitrate.
    Läuft im Hintergrund, Ergebnisse werden gecacht.
    """
    # Nur UUIDs die noch nicht geprobt wurden
    to_probe = get_uuids_needing_probe(req.uuids)

    if not to_probe:
        return {"queued": 0, "message": "Alle bereits geprüft"}

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
    """Holt gecachte erkannte Bitrates für gegebene UUIDs."""
    cached = get_cached_bitrates(req.uuids)
    return {"bitrates": cached}


# === Now Playing (ICY Title) ===

@router.get("/stations/{uuid}/now-playing")
async def now_playing(uuid: str):
    """Holt aktuellen ICY-StreamTitle fuer einen Sender.

    One-Shot: Verbindet, liest ersten Metadata-Block, schliesst.
    Fuer Polling im Frontend (alle ~15s).
    """
    from ..database import db_session

    # URL aus DB holen
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT url, url_resolved FROM stations WHERE uuid = ?", (uuid,))
        row = c.fetchone()

    if not row:
        return {"title": None}

    stream_url = row["url_resolved"] or row["url"]
    if not stream_url:
        return {"title": None}

    title = await fetch_icy_title(stream_url)
    return {"title": title}


# === ICY Quality Rating ===

class IcyQualityRequest(BaseModel):
    quality: Optional[str] = None  # 'good', 'poor', oder null (reset)


@router.put("/stations/{uuid}/icy-quality")
async def set_station_icy_quality(uuid: str, req: IcyQualityRequest):
    """Setzt die ICY-Cut-Qualitaetsbewertung fuer einen Sender.

    quality: 'good' = genaue Schnitte, 'poor' = ungenaue Schnitte, null = zuruecksetzen
    """
    if req.quality and req.quality not in ('good', 'poor'):
        return {"error": "quality muss 'good', 'poor' oder null sein"}

    set_icy_quality(uuid, req.quality)
    return {"uuid": uuid, "icy_quality": req.quality}
