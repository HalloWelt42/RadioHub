"""
RadioHub - Recording Folders Router

Ordner für Aufnahmen: CRUD, Aktivierung, Session-Verschiebung.
Ein Aufnahmeordner ist in der Ablage `Aufnahmen/<Name>/`; Dateiarbeit über services.aufnahmen.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..ablage import orte
from ..database import db_session
from ..services.aufnahmen import aufnahmen

router = APIRouter(prefix="/api/recording/folders", tags=["recording-folders"])


class FolderCreate(BaseModel):
    name: str


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class MoveSessionRequest(BaseModel):
    folder_id: Optional[int] = None


# === CRUD ===

@router.get("")
async def get_folders():
    """Alle Aufnahme-Ordner mit Session-Anzahl."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute('''SELECT rf.*, COUNT(s.id) as session_count
            FROM recording_folders rf
            LEFT JOIN sessions s ON s.folder_id = rf.id
            GROUP BY rf.id
            ORDER BY rf.sort_order, rf.id''')
        folders = [dict(row) for row in c.fetchall()]
    return {"folders": folders}


@router.post("")
async def create_folder(body: FolderCreate):
    """Neuen Aufnahme-Ordner anlegen."""
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Ordnername darf nicht leer sein")

    # Der Ordner entsteht in der Ablage mit der ersten Aufnahme darin
    safe_path = orte.eigener_ordner(name)

    with db_session() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO recording_folders (name, path) VALUES (?, ?)",
                (name, safe_path)
            )
            conn.commit()
            folder_id = c.lastrowid
        except Exception:
            raise HTTPException(409, "Ordnername existiert bereits")

    return {"id": folder_id, "name": name, "path": safe_path}


@router.delete("/{folder_id}")
async def delete_folder(folder_id: int):
    """Ordner löschen (nur wenn keine Sessions zugewiesen)."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM recording_folders WHERE id = ?", (folder_id,))
        folder = c.fetchone()
        if not folder:
            raise HTTPException(404, "Ordner nicht gefunden")

        c.execute("SELECT COUNT(*) FROM sessions WHERE folder_id = ?", (folder_id,))
        count = c.fetchone()[0]
        if count > 0:
            raise HTTPException(400, f"Ordner enthält noch {count} Aufnahmen")

        name = folder["name"]

    # Leeren Ordner in der Ablage in den Papierkorb (mit Dateien darin bleibt alles)
    await aufnahmen.ordner_loeschen(name)

    with db_session() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM recording_folders WHERE id = ?", (folder_id,))
        conn.commit()

    return {"success": True}


# === Aktivierung ===

@router.put("/deactivate")
async def deactivate_folder():
    """Aktiven Ordner zurücksetzen (Aufnahmen gehen in Root)."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("UPDATE recording_folders SET is_active = 0 WHERE is_active = 1")
        conn.commit()

    return {"activated": False}


@router.put("/{folder_id}/activate")
async def activate_folder(folder_id: int):
    """Ordner als aktiven Aufnahmeordner setzen."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM recording_folders WHERE id = ?", (folder_id,))
        folder = c.fetchone()
        if not folder:
            raise HTTPException(404, "Ordner nicht gefunden")

        c.execute("UPDATE recording_folders SET is_active = 0 WHERE is_active = 1")
        c.execute("UPDATE recording_folders SET is_active = 1 WHERE id = ?", (folder_id,))
        conn.commit()

    return {"activated": True, "folder_id": folder_id, "name": folder["name"]}


@router.put("/{folder_id}")
async def update_folder(folder_id: int, body: FolderUpdate):
    """Ordner umbenennen oder Sortierung ändern."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM recording_folders WHERE id = ?", (folder_id,))
        folder = c.fetchone()
        if not folder:
            raise HTTPException(404, "Ordner nicht gefunden")

        updates = {}
        if body.name is not None:
            new_name = body.name.strip()
            if not new_name:
                raise HTTPException(400, "Ordnername darf nicht leer sein")
            c.execute("SELECT 1 FROM recording_folders WHERE name = ? AND id != ?", (new_name, folder_id))
            if c.fetchone():
                raise HTTPException(409, "Ordnername existiert bereits")
            updates["name"] = new_name
            updates["path"] = orte.eigener_ordner(new_name)
            alter_name = folder["name"]

        if body.sort_order is not None:
            updates["sort_order"] = body.sort_order

        if "name" in updates:
            # Ordner in der Ablage umbenennen, Pfade der Aufnahmen darin folgen
            await aufnahmen.ordner_umbenennen(folder_id, alter_name, updates["name"])

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            c.execute(
                f"UPDATE recording_folders SET {set_clause} WHERE id = ?",
                list(updates.values()) + [folder_id]
            )
            conn.commit()

    return {"success": True}


# === Session verschieben ===

@router.put("/move-session/{session_id}")
async def move_session(session_id: str, body: MoveSessionRequest):
    """Session in einen Ordner verschieben (oder zurück zu Root); die Dateien ziehen in der Ablage mit."""
    ordner_name = None
    if body.folder_id is not None:
        with db_session() as conn:
            folder = conn.execute("SELECT * FROM recording_folders WHERE id = ?", (body.folder_id,)).fetchone()
        if not folder:
            raise HTTPException(404, "Zielordner nicht gefunden")
        ordner_name = folder["name"]
    moved = await aufnahmen.sitzung_verschieben(session_id, ordner_name, body.folder_id)
    return {"success": True, "moved": moved}
