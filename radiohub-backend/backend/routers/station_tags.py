"""
Station-Tags: Bewertungen und Markierungen fuer Sender.

tag_key Werte:
  Inhalt:   werbung, religioes, politisch_extrem, populistisch, nicht_jugendfrei
  Qualitaet: schlechte_qualitaet, schwankende_qualitaet, haeufig_offline, hoher_sprachanteil
  Aktionen: werbung_widerspruch, user_vote

source Werte: user, auto, community
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import db_session

router = APIRouter(prefix="/api/station-tags", tags=["station-tags"])

VALID_TAGS = {
    "werbung", "religioes", "politisch_extrem", "populistisch", "nicht_jugendfrei",
    "schlechte_qualitaet", "schwankende_qualitaet", "haeufig_offline", "hoher_sprachanteil",
    "werbung_widerspruch", "user_vote_up", "user_vote_down",
}

VALID_SOURCES = {"user", "auto", "community"}


class TagSet(BaseModel):
    tag_key: str
    tag_value: str = "true"
    source: str = "user"
    confidence: float = 1.0


class TagBulk(BaseModel):
    station_uuids: list[str]


# --- GET: Tags fuer einen Sender ---
@router.get("/{station_uuid}")
async def get_tags(station_uuid: str):
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, tag_key, tag_value, source, confidence, created_at FROM station_tags WHERE station_uuid = ?",
            (station_uuid,)
        )
        tags = [dict(r) for r in c.fetchall()]
    return {"tags": tags}


# --- GET: Tags fuer mehrere Sender (Bulk) ---
@router.post("/bulk")
async def get_tags_bulk(body: TagBulk):
    if not body.station_uuids:
        return {"assignments": {}}
    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(body.station_uuids))
        c.execute(
            f"SELECT station_uuid, tag_key, tag_value, source FROM station_tags WHERE station_uuid IN ({placeholders})",
            body.station_uuids
        )
        result = {}
        for row in c.fetchall():
            uuid = row["station_uuid"]
            if uuid not in result:
                result[uuid] = []
            result[uuid].append({
                "tag_key": row["tag_key"],
                "tag_value": row["tag_value"],
                "source": row["source"],
            })
    return {"assignments": result}


# --- PUT: Tag setzen (toggle) ---
@router.put("/{station_uuid}/{tag_key}")
async def set_tag(station_uuid: str, tag_key: str, body: Optional[TagSet] = None):
    if tag_key not in VALID_TAGS:
        raise HTTPException(status_code=400, detail=f"Unbekannter Tag: {tag_key}")

    source = body.source if body else "user"
    tag_value = body.tag_value if body else "true"
    confidence = body.confidence if body else 1.0

    if source not in VALID_SOURCES:
        raise HTTPException(status_code=400, detail=f"Unbekannte Quelle: {source}")

    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO station_tags (station_uuid, tag_key, tag_value, source, confidence)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(station_uuid, tag_key, source) DO UPDATE SET
                 tag_value = excluded.tag_value,
                 confidence = excluded.confidence,
                 created_at = CURRENT_TIMESTAMP""",
            (station_uuid, tag_key, tag_value, source, confidence)
        )
    return {"ok": True}


# --- DELETE: Tag entfernen ---
@router.delete("/{station_uuid}/{tag_key}")
async def remove_tag(station_uuid: str, tag_key: str, source: str = "user"):
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM station_tags WHERE station_uuid = ? AND tag_key = ? AND source = ?",
            (station_uuid, tag_key, source)
        )
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tag nicht gefunden")
    return {"ok": True}
