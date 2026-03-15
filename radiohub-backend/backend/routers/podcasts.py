"""
RadioHub v0.2.4 - Podcasts Router

Podcast-Suche, Abonnements, Episoden, Downloads, Cover-Art, Statistiken.
"""
import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from ..services.podcast import podcast_service
from ..config import AUDIO_MIMETYPES

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


# === Request-Models ===

class SubscribeRequest(BaseModel):
    feed_url: str

class PositionUpdate(BaseModel):
    position_seconds: int

class BatchDownloadRequest(BaseModel):
    episode_ids: List[int]

class CategoriesUpdate(BaseModel):
    categories: str

class AutoDownloadUpdate(BaseModel):
    enabled: bool


# === Suche ===

@router.get("/search")
async def search_podcasts(
    q: str = Query(..., min_length=2, description="Suchbegriff"),
    source: str = Query("all", description="itunes, fyyd oder all"),
    limit: int = Query(20, ge=1, le=50)
):
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


@router.get("/episodes/search")
async def search_episodes(
    q: str = Query(..., min_length=2, description="Suchbegriff"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search_in: str = Query("all", description="all, title, description, transcript")
):
    return await podcast_service.search_episodes(q, limit, offset, search_in)


@router.get("/subscriptions/search")
async def search_subscriptions(
    q: str = Query(..., min_length=2, description="Suchbegriff")
):
    results = await podcast_service.search_subscriptions(q)
    return {"subscriptions": results, "count": len(results)}


# === Statistiken ===

@router.get("/stats")
async def get_stats():
    return await podcast_service.get_stats()


@router.get("/storage/stats")
async def get_storage_stats():
    return await podcast_service.get_storage_stats()


# === Abonnements ===

@router.get("/subscriptions")
async def get_subscriptions():
    subs = await podcast_service.get_subscriptions()
    return {"count": len(subs), "subscriptions": subs}


@router.post("/subscribe")
async def subscribe(req: SubscribeRequest):
    if not req.feed_url:
        raise HTTPException(400, "feed_url erforderlich")
    result = await podcast_service.subscribe(req.feed_url)
    if not result:
        raise HTTPException(400, "Feed konnte nicht geparst werden")
    return {"success": True, "podcast": result}


@router.get("/refresh-status")
async def refresh_status():
    """Nächster automatischer Refresh-Zeitpunkt"""
    return podcast_service.get_refresh_status()


@router.post("/refresh-all")
async def refresh_all():
    result = await podcast_service.refresh_all()
    podcast_service.reset_refresh_timer()
    return result


@router.delete("/{podcast_id}")
async def unsubscribe(podcast_id: int):
    success = await podcast_service.unsubscribe(podcast_id)
    if not success:
        raise HTTPException(404, "Podcast nicht gefunden")
    return {"success": True}


@router.get("/{podcast_id}")
async def get_podcast(podcast_id: int):
    podcast = await podcast_service.get_subscription(podcast_id)
    if not podcast:
        raise HTTPException(404, "Podcast nicht gefunden")
    return podcast


@router.post("/{podcast_id}/refresh")
async def refresh_podcast(podcast_id: int):
    result = await podcast_service.refresh_podcast(podcast_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Aktualisierung fehlgeschlagen"))
    return result


@router.put("/{podcast_id}/categories")
async def update_categories(podcast_id: int, req: CategoriesUpdate):
    success = await podcast_service.update_subscription_categories(podcast_id, req.categories)
    if not success:
        raise HTTPException(404, "Podcast nicht gefunden")
    return {"success": True}


@router.put("/{podcast_id}/auto-download")
async def set_auto_download(podcast_id: int, req: AutoDownloadUpdate):
    success = await podcast_service.set_auto_download(podcast_id, req.enabled)
    if not success:
        raise HTTPException(404, "Podcast nicht gefunden")
    return {"success": True}


# === Cover-Art ===

@router.get("/{podcast_id}/image")
async def get_podcast_image(podcast_id: int):
    """Podcast Cover-Art ausliefern (mit On-Demand-Download)"""
    path = podcast_service.get_image_path(podcast_id)

    # On-Demand: falls kein lokales Bild, aus DB image_url laden und cachen
    if not path:
        from ..database import db_session
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT image_url FROM podcast_subscriptions WHERE id = ?", (podcast_id,))
            row = c.fetchone()
        if row and row["image_url"]:
            await podcast_service.download_image(row["image_url"], podcast_id)
            path = podcast_service.get_image_path(podcast_id)

    if not path:
        raise HTTPException(404, "Kein Cover vorhanden")

    content_type = "image/jpeg"
    if path.suffix == ".png":
        content_type = "image/png"
    elif path.suffix == ".webp":
        content_type = "image/webp"

    return FileResponse(
        path, media_type=content_type,
        headers={"Cache-Control": "public, max-age=604800"}
    )


# === Episoden ===

@router.get("/episodes/all")
async def get_all_episodes(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    filter_status: str = Query("all"),
    sort_by: str = Query("published_at"),
    sort_order: str = Query("desc"),
    podcast_ids: Optional[str] = Query(None, description="Komma-getrennte Podcast-IDs")
):
    """Episoden über alle Abos"""
    pid_list = None
    if podcast_ids:
        try:
            pid_list = [int(x) for x in podcast_ids.split(",")]
        except ValueError:
            raise HTTPException(400, "Ungültige podcast_ids")

    return await podcast_service.get_all_episodes(
        limit=limit, offset=offset, filter_status=filter_status,
        sort_by=sort_by, sort_order=sort_order, podcast_ids=pid_list
    )


@router.get("/{podcast_id}/episodes")
async def get_episodes(
    podcast_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    filter_status: str = Query("all"),
    sort_by: str = Query("published_at"),
    sort_order: str = Query("desc")
):
    return await podcast_service.get_episodes(
        podcast_id, limit, offset, filter_status, sort_by, sort_order
    )


@router.get("/episodes/{episode_id}")
async def get_episode(episode_id: int):
    episode = await podcast_service.get_episode(episode_id)
    if not episode:
        raise HTTPException(404, "Episode nicht gefunden")
    return episode


@router.get("/episodes/{episode_id}/image")
async def get_episode_image(episode_id: int):
    """Episode-Bild (Fallback: Podcast-Cover, mit On-Demand-Download)"""
    episode = await podcast_service.get_episode(episode_id)
    if not episode:
        raise HTTPException(404, "Episode nicht gefunden")

    podcast_id = episode["podcast_id"]

    # Zuerst Episode-spezifisches Bild, dann Podcast-Cover
    path = podcast_service.get_image_path(podcast_id, episode_id)
    if not path:
        path = podcast_service.get_image_path(podcast_id)

    # On-Demand: Episode-Bild oder Podcast-Cover herunterladen
    if not path:
        img_url = episode.get("image_url")
        if img_url:
            await podcast_service.download_image(img_url, podcast_id, episode_id)
            path = podcast_service.get_image_path(podcast_id, episode_id)
        if not path:
            from ..database import db_session
            with db_session() as conn:
                c = conn.cursor()
                c.execute("SELECT image_url FROM podcast_subscriptions WHERE id = ?", (podcast_id,))
                row = c.fetchone()
            if row and row["image_url"]:
                await podcast_service.download_image(row["image_url"], podcast_id)
                path = podcast_service.get_image_path(podcast_id)

    if not path:
        raise HTTPException(404, "Kein Bild vorhanden")

    content_type = "image/jpeg"
    if path.suffix == ".png":
        content_type = "image/png"
    elif path.suffix == ".webp":
        content_type = "image/webp"

    return FileResponse(
        path, media_type=content_type,
        headers={"Cache-Control": "public, max-age=604800"}
    )


# === Episode-Playback ===

@router.get("/episodes/{episode_id}/play")
async def play_episode(episode_id: int):
    """Heruntergeladene Episode streamen"""
    path = podcast_service.get_episode_audio_path(episode_id)
    if not path:
        raise HTTPException(404, "Episode nicht lokal vorhanden")

    ext = path.suffix.lower()
    media_type = AUDIO_MIMETYPES.get(ext, "audio/mpeg")

    return FileResponse(
        path=path,
        media_type=media_type,
        filename=path.name,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(path.stat().st_size),
        }
    )


@router.get("/episodes/{episode_id}/stream")
async def stream_episode(episode_id: int, request: Request):
    """Remote-Episode per Proxy streamen (fuer nicht heruntergeladene Episoden)"""
    episode = await podcast_service.get_episode(episode_id)
    if not episode:
        raise HTTPException(404, "Episode nicht gefunden")

    audio_url = episode.get("audio_url")
    if not audio_url:
        raise HTTPException(404, "Keine Audio-URL vorhanden")

    # Range-Header vom Client durchreichen
    headers = {"User-Agent": "RadioHub/1.0"}
    range_header = request.headers.get("range")
    if range_header:
        headers["Range"] = range_header

    try:
        client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
        resp = await client.send(
            client.build_request("GET", audio_url, headers=headers),
            stream=True
        )
    except httpx.RequestError as e:
        raise HTTPException(502, f"Upstream-Fehler: {e}")

    if resp.status_code not in (200, 206):
        await resp.aclose()
        await client.aclose()
        raise HTTPException(resp.status_code, "Upstream-Server-Fehler")

    content_type = resp.headers.get("content-type", "audio/mpeg")

    response_headers = {}
    for h in ("content-length", "content-range", "accept-ranges"):
        if h in resp.headers:
            response_headers[h] = resp.headers[h]

    async def stream_chunks():
        try:
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_chunks(),
        status_code=resp.status_code,
        media_type=content_type,
        headers=response_headers,
    )


# === Episode-Position und Status ===

@router.put("/episodes/{episode_id}/position")
async def update_position(episode_id: int, update: PositionUpdate):
    success = await podcast_service.update_episode_position(
        episode_id, update.position_seconds
    )
    if not success:
        raise HTTPException(404, "Episode nicht gefunden")
    return {"success": True, "position_seconds": update.position_seconds}


@router.put("/episodes/{episode_id}/played")
async def mark_played(episode_id: int):
    success = await podcast_service.mark_played(episode_id)
    if not success:
        raise HTTPException(404, "Episode nicht gefunden")
    return {"success": True}


@router.put("/episodes/{episode_id}/unplayed")
async def mark_unplayed(episode_id: int):
    success = await podcast_service.mark_unplayed(episode_id)
    if not success:
        raise HTTPException(404, "Episode nicht gefunden")
    return {"success": True}


@router.put("/{podcast_id}/mark-all-played")
async def mark_all_played(podcast_id: int):
    count = await podcast_service.mark_all_played(podcast_id)
    return {"success": True, "count": count}


# === Downloads ===

@router.post("/episodes/{episode_id}/download")
async def download_episode(episode_id: int):
    result = await podcast_service.download_episode(episode_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Download fehlgeschlagen"))
    return result


@router.post("/{podcast_id}/download-batch")
async def download_batch(podcast_id: int, req: BatchDownloadRequest):
    if not req.episode_ids:
        raise HTTPException(400, "episode_ids erforderlich")
    result = await podcast_service.download_episodes_batch(req.episode_ids)
    return result


@router.delete("/episodes/{episode_id}/download")
async def delete_download(episode_id: int):
    success = await podcast_service.delete_episode_download(episode_id)
    if not success:
        raise HTTPException(404, "Episode nicht gefunden")
    return {"success": True}


@router.get("/episodes/{episode_id}/transcript")
async def get_transcript(episode_id: int):
    """Transkript einer Episode holen (aus Feed oder Cache)"""
    transcript = await podcast_service.get_transcript(episode_id)
    if transcript is None:
        return {"available": False, "text": None}
    return {"available": True, "text": transcript}


@router.delete("/{podcast_id}/played-downloads")
async def delete_played_downloads(podcast_id: int):
    """Gehörte Downloads eines Podcasts löschen"""
    count = await podcast_service.delete_played_downloads(podcast_id)
    return {"success": True, "deleted": count}
