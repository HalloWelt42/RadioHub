"""
Custom Stream URLs: Benutzerdefinierte Stream-Adressen fuer Sender.

Erlaubt es, die Original-URL eines Senders durch eine bereinigte URL zu ersetzen
(z.B. ohne Tracking-Parameter). Original wird als Backup gespeichert.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import db_session

router = APIRouter(prefix="/api/station-custom-urls", tags=["station-custom-urls"])


class CustomUrlSet(BaseModel):
    custom_url: str
    note: str = ""


class CustomUrlBulk(BaseModel):
    station_uuids: list[str]


# --- GET: Custom URL fuer einen Sender ---
@router.get("/{station_uuid}")
async def get_custom_url(station_uuid: str):
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT custom_url, original_url, original_url_resolved, note, updated_at FROM station_custom_urls WHERE station_uuid = ?",
            (station_uuid,)
        )
        row = c.fetchone()
    if not row:
        return {"custom_url": None}
    return {
        "custom_url": row["custom_url"],
        "original_url": row["original_url"],
        "original_url_resolved": row["original_url_resolved"],
        "note": row["note"],
        "updated_at": row["updated_at"],
    }


# --- POST: Custom URLs fuer mehrere Sender (Bulk) ---
@router.post("/bulk")
async def get_custom_urls_bulk(body: CustomUrlBulk):
    if not body.station_uuids:
        return {"custom_urls": {}}
    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(body.station_uuids))
        c.execute(
            f"SELECT station_uuid, custom_url FROM station_custom_urls WHERE station_uuid IN ({placeholders})",
            body.station_uuids
        )
        result = {}
        for row in c.fetchall():
            result[row["station_uuid"]] = row["custom_url"]
    return {"custom_urls": result}


# --- PUT: Custom URL setzen ---
@router.put("/{station_uuid}")
async def set_custom_url(station_uuid: str, body: CustomUrlSet):
    if not body.custom_url.strip():
        raise HTTPException(status_code=400, detail="URL darf nicht leer sein")

    with db_session() as conn:
        c = conn.cursor()
        # Original-URL aus stations-Tabelle holen (Snapshot)
        c.execute("SELECT url, url_resolved FROM stations WHERE uuid = ?", (station_uuid,))
        station = c.fetchone()
        if not station:
            # Auch in favorites suchen
            c.execute("SELECT url, url_resolved FROM favorites WHERE uuid = ?", (station_uuid,))
            station = c.fetchone()

        original_url = station["url"] if station else ""
        original_url_resolved = station["url_resolved"] if station else ""

        c.execute(
            """INSERT INTO station_custom_urls (station_uuid, custom_url, original_url, original_url_resolved, note)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(station_uuid) DO UPDATE SET
                 custom_url = excluded.custom_url,
                 note = excluded.note,
                 updated_at = CURRENT_TIMESTAMP""",
            (station_uuid, body.custom_url.strip(), original_url, original_url_resolved, body.note)
        )
    return {"ok": True}


# --- DELETE: Custom URL entfernen (zurueck zum Original) ---
@router.delete("/{station_uuid}")
async def reset_custom_url(station_uuid: str):
    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM station_custom_urls WHERE station_uuid = ?", (station_uuid,))
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Keine Custom URL gefunden")
    return {"ok": True}
