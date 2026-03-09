"""
RadioHub v0.1.0 - Categories Router

Benutzerdefinierte Kategorien mit direkter Sender-Zuordnung.
"""
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel

from ..database import db_session

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str
    tags: str = ""
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[str] = None
    sort_order: Optional[int] = None


class StationAssignmentsRequest(BaseModel):
    uuids: List[str]


# === Batch-Endpoint MUSS vor /{cat_id} stehen (FastAPI Routing) ===

@router.post("/station-assignments")
async def get_station_assignments(body: StationAssignmentsRequest):
    """Kategorie-Zuordnungen fuer eine Liste von Station-UUIDs."""
    if not body.uuids:
        return {"assignments": {}}
    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(body.uuids))
        c.execute(
            f"SELECT station_uuid, category_id FROM category_stations WHERE station_uuid IN ({placeholders})",
            body.uuids
        )
        result = {}
        for row in c.fetchall():
            uuid = row["station_uuid"]
            if uuid not in result:
                result[uuid] = []
            result[uuid].append(row["category_id"])
    return {"assignments": result}


# === Standard-CRUD ===

@router.get("")
async def get_categories():
    """Alle Kategorien holen, sortiert nach sort_order."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM categories ORDER BY sort_order, id")
        rows = [dict(r) for r in c.fetchall()]
    return {"categories": rows}


@router.post("")
async def create_category(body: CategoryCreate):
    """Neue Kategorie anlegen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO categories (name, tags, sort_order) VALUES (?, ?, ?)",
            (body.name.strip(), body.tags.strip(), body.sort_order)
        )
        cat_id = c.lastrowid
    return {"id": cat_id, "name": body.name, "sort_order": body.sort_order}


@router.put("/{cat_id}")
async def update_category(cat_id: int, body: CategoryUpdate):
    """Kategorie aktualisieren (partial update)."""
    with db_session() as conn:
        c = conn.cursor()
        updates = []
        params = []
        if body.name is not None:
            updates.append("name = ?")
            params.append(body.name.strip())
        if body.tags is not None:
            updates.append("tags = ?")
            params.append(body.tags.strip())
        if body.sort_order is not None:
            updates.append("sort_order = ?")
            params.append(body.sort_order)
        if not updates:
            return {"error": "Keine Aenderungen"}
        params.append(cat_id)
        c.execute(f"UPDATE categories SET {', '.join(updates)} WHERE id = ?", params)
        if c.rowcount == 0:
            return {"error": "Kategorie nicht gefunden"}
    return {"id": cat_id, "updated": True}


@router.delete("/{cat_id}")
async def delete_category(cat_id: int):
    """Kategorie loeschen (CASCADE entfernt Zuordnungen)."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        if c.rowcount == 0:
            return {"error": "Kategorie nicht gefunden"}
    return {"deleted": True}


# === Station-Zuordnung ===

@router.post("/{cat_id}/stations/{station_uuid}")
async def assign_station(cat_id: int, station_uuid: str):
    """Sender einer Kategorie zuordnen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO category_stations (category_id, station_uuid) VALUES (?, ?)",
            (cat_id, station_uuid)
        )
    return {"assigned": True}


@router.delete("/{cat_id}/stations/{station_uuid}")
async def unassign_station(cat_id: int, station_uuid: str):
    """Sender aus Kategorie entfernen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM category_stations WHERE category_id = ? AND station_uuid = ?",
            (cat_id, station_uuid)
        )
    return {"removed": True}
