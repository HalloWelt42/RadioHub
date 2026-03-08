"""
RadioHub v0.1.6 - Podcasts Router

Podcast-Suche, Abonnements, Episoden
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ..services.podcast import podcast_service

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


class SubscribeRequest(BaseModel):
    feed_url: str


class PositionUpdate(BaseModel):
    position_seconds: int


# === Suche ===

@router.get("/search")
async def search_podcasts(
    q: str = Query(..., min_length=2, description="Suchbegriff"),
    source: str = Query("all", description="itunes, fyyd oder all"),
    limit: int = Query(20, ge=1, le=50)
):
    """Sucht Podcasts über iTunes und/oder fyyd"""
    results = await podcast_service.search(q, source, limit)
    
    return {
        "query": q,
        "source": source,
        "count": len(results),
        "results": [
            {
                "title": r.title,
                "author": r.author,
                "feed_url": r.feed_url,
                "image_url": r.image_url,
                "description": r.description,
                "source": r.source
            }
            for r in results
        ]
    }


# === Storage ===

@router.get("/storage/stats")
async def get_storage_stats():
    """Speicher-Statistiken"""
    return await podcast_service.get_storage_stats()


# === Abonnements ===

@router.get("/subscriptions")
async def get_subscriptions():
    """Alle abonnierten Podcasts"""
    subs = await podcast_service.get_subscriptions()
    return {"count": len(subs), "subscriptions": subs}


@router.post("/subscribe")
async def subscribe(req: SubscribeRequest):
    """Podcast abonnieren"""
    if not req.feed_url:
        raise HTTPException(400, "feed_url erforderlich")
    
    result = await podcast_service.subscribe(req.feed_url)
    
    if not result:
        raise HTTPException(400, "Feed konnte nicht geparst werden")
    
    return {"success": True, "podcast": result}


@router.delete("/{podcast_id}")
async def unsubscribe(podcast_id: int):
    """Podcast-Abo entfernen"""
    success = await podcast_service.unsubscribe(podcast_id)
    
    if not success:
        raise HTTPException(404, "Podcast nicht gefunden")
    
    return {"success": True}


@router.get("/{podcast_id}")
async def get_podcast(podcast_id: int):
    """Podcast-Details"""
    podcast = await podcast_service.get_subscription(podcast_id)
    
    if not podcast:
        raise HTTPException(404, "Podcast nicht gefunden")
    
    return podcast


@router.post("/{podcast_id}/refresh")
async def refresh_podcast(podcast_id: int):
    """Podcast-Feed aktualisieren"""
    success = await podcast_service.refresh_podcast(podcast_id)
    
    if not success:
        raise HTTPException(400, "Aktualisierung fehlgeschlagen")
    
    return {"success": True}


# === Episoden ===

@router.get("/{podcast_id}/episodes")
async def get_episodes(
    podcast_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Episoden eines Podcasts"""
    result = await podcast_service.get_episodes(podcast_id, limit, offset)
    return result


@router.get("/episodes/{episode_id}")
async def get_episode(episode_id: int):
    """Einzelne Episode"""
    episode = await podcast_service.get_episode(episode_id)
    
    if not episode:
        raise HTTPException(404, "Episode nicht gefunden")
    
    return episode


@router.put("/episodes/{episode_id}/position")
async def update_position(episode_id: int, update: PositionUpdate):
    """Resume-Position speichern"""
    success = await podcast_service.update_episode_position(
        episode_id,
        update.position_seconds
    )
    
    if not success:
        raise HTTPException(404, "Episode nicht gefunden")
    
    return {"success": True, "position_seconds": update.position_seconds}
