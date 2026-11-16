"""
RadioHub - Favicon Router

Liefert lokal gecachte Sender-Favicons aus.
Bei Cache-Miss wird on-demand aus der DB-URL heruntergeladen.
"""
import base64

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response

from ..services.favicon_cache import get_cached_path, get_or_download
from ..database import db_session

router = APIRouter(prefix="/api/favicon", tags=["favicon"])

# 1x1 transparentes PNG als Fallback (kein 404 mehr)
_TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB"
    "Nl7BcQAAAABJRU5ErkJggg=="
)

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
        return Response(
            content=_TRANSPARENT_PNG,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

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
