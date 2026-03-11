"""
RadioHub - Favicon Cache Service

Laedt Sender-Favicons herunter und speichert sie lokal.
Externe URLs werden nur einmal aufgerufen, danach aus Cache bedient.
"""
import logging
from pathlib import Path

import httpx

from ..config import CACHE_DIR

logger = logging.getLogger(__name__)

FAVICON_DIR = CACHE_DIR / "favicons"
FAVICON_DIR.mkdir(parents=True, exist_ok=True)

# Content-Type -> Extension Mapping
_EXT_MAP = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "image/svg+xml": ".svg",
}

MAX_SIZE = 512 * 1024  # 500 KB
TIMEOUT = 5.0


def get_cached_path(uuid: str) -> Path | None:
    """Gibt den Pfad zum gecachten Favicon zurueck, oder None."""
    matches = list(FAVICON_DIR.glob(f"{uuid}.*"))
    return matches[0] if matches else None


async def get_or_download(uuid: str, favicon_url: str) -> Path | None:
    """Favicon aus Cache holen oder herunterladen."""
    cached = get_cached_path(uuid)
    if cached:
        return cached

    if not favicon_url:
        return None

    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "RadioHub/1.0"}
        ) as client:
            resp = await client.get(favicon_url)
            if resp.status_code != 200:
                return None

            content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            ext = _EXT_MAP.get(content_type, ".png")

            data = resp.content
            if len(data) > MAX_SIZE or len(data) < 100:
                return None

            path = FAVICON_DIR / f"{uuid}{ext}"
            path.write_bytes(data)
            return path

    except Exception as e:
        logger.debug("Favicon-Download fehlgeschlagen fuer %s: %s", uuid, e)
        return None


async def cache_batch(stations: list[dict], max_count: int = 50):
    """Favicons fuer eine Liste von Sendern im Hintergrund cachen."""
    count = 0
    for s in stations:
        if count >= max_count:
            break
        uuid = s.get("uuid") or s.get("stationuuid")
        url = s.get("favicon")
        if not uuid or not url:
            continue
        if get_cached_path(uuid):
            continue
        await get_or_download(uuid, url)
        count += 1
    if count > 0:
        logger.info("Favicon-Cache: %d neue Icons heruntergeladen", count)
