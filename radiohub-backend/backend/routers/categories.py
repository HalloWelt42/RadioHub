"""
RadioHub v0.2.0 - Categories Router

Benutzerdefinierte Kategorien mit Scope (radio/podcast/recording)
und Zuordnungen zu Sendern, Podcasts und Aufnahmen.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import db_session

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str
    tags: str = ""
    scope: str = "radio"
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[str] = None
    scope: Optional[str] = None
    sort_order: Optional[int] = None


class StationAssignmentsRequest(BaseModel):
    uuids: List[str]


class PodcastAssignmentsRequest(BaseModel):
    ids: List[int]


class SessionAssignmentsRequest(BaseModel):
    ids: List[str]


# === Batch-Endpoints MUESSEN vor /{cat_id} stehen (FastAPI Routing) ===

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


@router.post("/podcast-assignments")
async def get_podcast_assignments(body: PodcastAssignmentsRequest):
    """Kategorie-Zuordnungen fuer eine Liste von Podcast-IDs."""
    if not body.ids:
        return {"assignments": {}}
    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(body.ids))
        c.execute(
            f"SELECT podcast_id, category_id FROM category_podcasts WHERE podcast_id IN ({placeholders})",
            body.ids
        )
        result = {}
        for row in c.fetchall():
            pid = row["podcast_id"]
            if pid not in result:
                result[pid] = []
            result[pid].append(row["category_id"])
    return {"assignments": result}


@router.post("/session-assignments")
async def get_session_assignments(body: SessionAssignmentsRequest):
    """Kategorie-Zuordnungen fuer eine Liste von Session-IDs."""
    if not body.ids:
        return {"assignments": {}}
    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(body.ids))
        c.execute(
            f"SELECT session_id, category_id FROM category_sessions WHERE session_id IN ({placeholders})",
            body.ids
        )
        result = {}
        for row in c.fetchall():
            sid = row["session_id"]
            if sid not in result:
                result[sid] = []
            result[sid].append(row["category_id"])
    return {"assignments": result}


# === Standard-CRUD ===

@router.get("")
async def get_categories(scope: Optional[str] = Query(None)):
    """Alle Kategorien holen, optional nach Scope gefiltert."""
    with db_session() as conn:
        c = conn.cursor()
        if scope:
            c.execute(
                "SELECT * FROM categories WHERE scope = ? ORDER BY sort_order, id",
                (scope,)
            )
        else:
            c.execute("SELECT * FROM categories ORDER BY sort_order, id")
        rows = [dict(r) for r in c.fetchall()]
    return {"categories": rows}


@router.post("")
async def create_category(body: CategoryCreate):
    """Neue Kategorie anlegen."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    if body.scope not in ("radio", "podcast", "recording"):
        raise HTTPException(status_code=400, detail="Scope muss radio, podcast oder recording sein")
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO categories (name, tags, scope, sort_order) VALUES (?, ?, ?, ?)",
            (name, body.tags.strip(), body.scope, body.sort_order)
        )
        cat_id = c.lastrowid
    return {"id": cat_id, "name": name, "scope": body.scope, "sort_order": body.sort_order}


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
        if body.scope is not None:
            if body.scope not in ("radio", "podcast", "recording"):
                raise HTTPException(status_code=400, detail="Scope muss radio, podcast oder recording sein")
            updates.append("scope = ?")
            params.append(body.scope)
        if body.sort_order is not None:
            updates.append("sort_order = ?")
            params.append(body.sort_order)
        if not updates:
            raise HTTPException(status_code=400, detail="Keine Änderungen")
        params.append(cat_id)
        c.execute(f"UPDATE categories SET {', '.join(updates)} WHERE id = ?", params)
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Kategorie nicht gefunden")
    return {"id": cat_id, "updated": True}


@router.delete("/{cat_id}")
async def delete_category(cat_id: int):
    """Kategorie loeschen (CASCADE entfernt Zuordnungen)."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Kategorie nicht gefunden")
    return {"deleted": True}


# === Station-Zuordnung ===

@router.post("/{cat_id}/stations/{station_uuid}")
async def assign_station(cat_id: int, station_uuid: str):
    """Sender einer Kategorie zuordnen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="Kategorie nicht gefunden")
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


# === Podcast-Zuordnung ===

@router.post("/{cat_id}/podcasts/{podcast_id}")
async def assign_podcast(cat_id: int, podcast_id: int):
    """Podcast einer Kategorie zuordnen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="Kategorie nicht gefunden")
        c.execute(
            "INSERT OR IGNORE INTO category_podcasts (category_id, podcast_id) VALUES (?, ?)",
            (cat_id, podcast_id)
        )
    return {"assigned": True}


@router.delete("/{cat_id}/podcasts/{podcast_id}")
async def unassign_podcast(cat_id: int, podcast_id: int):
    """Podcast aus Kategorie entfernen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM category_podcasts WHERE category_id = ? AND podcast_id = ?",
            (cat_id, podcast_id)
        )
    return {"removed": True}


# === Session-Zuordnung ===

@router.post("/{cat_id}/sessions/{session_id}")
async def assign_session(cat_id: int, session_id: str):
    """Aufnahme einer Kategorie zuordnen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="Kategorie nicht gefunden")
        c.execute(
            "INSERT OR IGNORE INTO category_sessions (category_id, session_id) VALUES (?, ?)",
            (cat_id, session_id)
        )
    return {"assigned": True}


@router.delete("/{cat_id}/sessions/{session_id}")
async def unassign_session(cat_id: int, session_id: str):
    """Aufnahme aus Kategorie entfernen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM category_sessions WHERE category_id = ? AND session_id = ?",
            (cat_id, session_id)
        )
    return {"removed": True}
