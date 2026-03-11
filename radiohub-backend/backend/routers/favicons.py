"""
RadioHub - Favicon Router

Liefert lokal gecachte Sender-Favicons aus.
Bei Cache-Miss wird on-demand aus der DB-URL heruntergeladen.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..services.favicon_cache import get_cached_path, get_or_download
from ..database import db_session

router = APIRouter(prefix="/api/favicon", tags=["favicon"])

_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".svg": "image/svg+xml",
}


@router.get("/{uuid}")
async def get_favicon(uuid: str):
    """Gecachtes Sender-Favicon ausliefern, bei Bedarf on-demand downloaden."""
    path = get_cached_path(uuid)

    if not path:
        # Favicon-URL aus DB holen und on-demand downloaden
        favicon_url = _get_favicon_url(uuid)
        if favicon_url:
            path = await get_or_download(uuid, favicon_url)

    if not path:
        raise HTTPException(404, "Favicon nicht verfuegbar")

    content_type = _CONTENT_TYPES.get(path.suffix.lower(), "image/png")
    return FileResponse(
        path,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=604800"},
    )


def _get_favicon_url(uuid: str) -> str | None:
    """Favicon-URL aus stations oder favorites Tabelle holen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT favicon FROM stations WHERE uuid = ?", (uuid,))
        row = c.fetchone()
        if row and row["favicon"]:
            return row["favicon"]
        c.execute("SELECT favicon FROM favorites WHERE uuid = ?", (uuid,))
        row = c.fetchone()
        if row and row["favicon"]:
            return row["favicon"]
    return None
