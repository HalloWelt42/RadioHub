"""
RadioHub - Recording Folders Router

Ordner für Aufnahmen: CRUD, Aktivierung, Session-Verschiebung.
"""
import re
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db_session
from ..config import RADIO_RECORDINGS_DIR

router = APIRouter(prefix="/api/recording/folders", tags=["recording-folders"])


class FolderCreate(BaseModel):
    name: str


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class MoveSessionRequest(BaseModel):
    folder_id: Optional[int] = None


def _safe_path(name: str) -> str:
    """Ordnername zu sicherem Dateisystem-Pfad."""
    safe = re.sub(r'[<>:"/\\|?*]', '_', name.strip())
    safe = re.sub(r'\.{2,}', '_', safe)
    return safe[:100] or 'ordner'


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

    safe_path = _safe_path(name)
    folder_dir = RADIO_RECORDINGS_DIR / safe_path
    folder_dir.mkdir(parents=True, exist_ok=True)

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

        # Physisches Verzeichnis löschen (verwaiste leere Unterordner mit aufräumen)
        folder_dir = RADIO_RECORDINGS_DIR / folder["path"]
        if folder_dir.exists():
            import shutil
            # Cache-Suffixe die beim Löschen ignoriert/aufgeräumt werden dürfen
            cache_suffixes = {".peaks", ".peaks.tmp"}
            # Prüfen ob noch echte Dateien vorhanden sind (Cache-Dateien ignorieren)
            real_files = [f for f in folder_dir.rglob("*") if f.is_file() and f.suffix not in cache_suffixes]
            if real_files:
                raise HTTPException(400, f"Ordner enthält noch {len(real_files)} Dateien auf der Festplatte")
            # Nur Cache-Dateien und leere Unterordner -> komplett aufräumen
            shutil.rmtree(folder_dir, ignore_errors=True)

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

            old_path = folder["path"]
            new_path = _safe_path(new_name)

            # Physisches Verzeichnis umbenennen
            old_dir = RADIO_RECORDINGS_DIR / old_path
            new_dir = RADIO_RECORDINGS_DIR / new_path
            if old_dir.exists() and old_path != new_path:
                if new_dir.exists():
                    raise HTTPException(409, "Zielordner existiert bereits")
                old_dir.rename(new_dir)

                # DB-Pfade in Sessions und Segmenten aktualisieren
                old_prefix = str(RADIO_RECORDINGS_DIR / old_path)
                new_prefix = str(RADIO_RECORDINGS_DIR / new_path)
                c.execute(
                    "UPDATE sessions SET file_path = REPLACE(file_path, ?, ?) WHERE folder_id = ?",
                    (old_prefix, new_prefix, folder_id)
                )
                c.execute(
                    "UPDATE sessions SET meta_file_path = REPLACE(meta_file_path, ?, ?) WHERE folder_id = ?",
                    (old_prefix, new_prefix, folder_id)
                )
                # Segmente der betroffenen Sessions
                c.execute("""
                    UPDATE segments SET file_path = REPLACE(file_path, ?, ?)
                    WHERE session_id IN (SELECT id FROM sessions WHERE folder_id = ?)
                """, (old_prefix, new_prefix, folder_id))

            updates["name"] = new_name
            updates["path"] = new_path

        if body.sort_order is not None:
            updates["sort_order"] = body.sort_order

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
    """Session in einen Ordner verschieben (oder zurück zu Root)."""
    with db_session() as conn:
        c = conn.cursor()

        # Session laden
        c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = c.fetchone()
        if not session:
            raise HTTPException(404, "Session nicht gefunden")
        if session["status"] == "recording":
            raise HTTPException(400, "Aktive Aufnahme kann nicht verschoben werden")

        # Zielordner bestimmen
        target_dir = RADIO_RECORDINGS_DIR
        if body.folder_id is not None:
            c.execute("SELECT * FROM recording_folders WHERE id = ?", (body.folder_id,))
            folder = c.fetchone()
            if not folder:
                raise HTTPException(404, "Zielordner nicht gefunden")
            target_dir = RADIO_RECORDINGS_DIR / folder["path"]
            target_dir.mkdir(parents=True, exist_ok=True)

        # Quellpfad bestimmen
        src_path = Path(session["file_path"])
        if not src_path.exists():
            raise HTTPException(404, "Quelldatei/Verzeichnis nicht gefunden")

        # Zielname = gleicher Basename
        dst_path = target_dir / src_path.name
        if dst_path == src_path:
            # Schon am richtigen Ort, nur folder_id updaten
            c.execute("UPDATE sessions SET folder_id = ? WHERE id = ?", (body.folder_id, session_id))
            conn.commit()
            return {"success": True, "moved": False}

        if dst_path.exists():
            raise HTTPException(409, "Ziel existiert bereits")

        # Physisch verschieben
        shutil.move(str(src_path), str(dst_path))

        # Meta-Datei verschieben (falls vorhanden)
        meta_path = Path(session["meta_file_path"]) if session["meta_file_path"] else None
        new_meta_path = None
        if meta_path and meta_path.exists():
            new_meta = target_dir / meta_path.name
            shutil.move(str(meta_path), str(new_meta))
            new_meta_path = str(new_meta)

        # DB-Pfade aktualisieren
        old_prefix = str(src_path)
        new_prefix = str(dst_path)

        c.execute(
            "UPDATE sessions SET file_path = ?, meta_file_path = ?, folder_id = ? WHERE id = ?",
            (str(dst_path), new_meta_path or session["meta_file_path"], body.folder_id, session_id)
        )

        # Segment-Pfade aktualisieren (bei segmentierten Sessions ist file_path ein Verzeichnis)
        if src_path.is_dir() or dst_path.is_dir():
            c.execute(
                "UPDATE segments SET file_path = REPLACE(file_path, ?, ?) WHERE session_id = ?",
                (old_prefix, new_prefix, session_id)
            )

        conn.commit()

    return {"success": True, "moved": True}
