"""
RadioHub v0.2.5 - File Explorer Router

Einheitlicher Datei-Explorer fuer Podcasts und Aufnahmen.
Ordnerstruktur, Datei-Loeschung, ZIP+M3U Download.
"""
import os
import zipfile
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List

from ..config import RECORDINGS_DIR, PODCAST_RECORDINGS_DIR, RADIO_RECORDINGS_DIR, get_cache_dir
from ..database import db_session

router = APIRouter(prefix="/api/files", tags=["file-explorer"])

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac", ".aac"}


def _safe_path(base_dir: Path, rel_path: str) -> Path:
    """Sicherer Pfad innerhalb base_dir"""
    clean = os.path.normpath(rel_path).lstrip("/\\")
    full = base_dir / clean
    try:
        full.resolve().relative_to(base_dir.resolve())
    except ValueError:
        raise HTTPException(403, "Zugriff verweigert")
    return full


def _scan_audio_files(folder: Path) -> list:
    """Audio-Dateien in einem Ordner scannen"""
    files = []
    if not folder.exists():
        return files
    for item in sorted(folder.iterdir()):
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
            stat = item.stat()
            files.append({
                "name": item.name,
                "path": str(item),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": item.suffix.lower()
            })
    return files


def _get_podcast_names() -> dict:
    """Podcast-IDs zu Namen aus der DB mappen"""
    mapping = {}
    try:
        with db_session() as conn:
            rows = conn.execute(
                "SELECT id, title FROM podcast_subscriptions"
            ).fetchall()
            for row in rows:
                mapping[str(row["id"])] = row["title"]
    except Exception:
        pass
    return mapping


@router.get("/podcasts")
async def get_podcast_files():
    """Podcast-Ordnerstruktur mit Dateien"""
    audio_base = PODCAST_RECORDINGS_DIR / "audio"
    audio_base.mkdir(parents=True, exist_ok=True)

    podcast_names = _get_podcast_names()
    folders = []
    total_size = 0
    total_files = 0

    for item in sorted(audio_base.iterdir()):
        if not item.is_dir():
            continue

        folder_id = item.name
        name = podcast_names.get(folder_id, f"Unbekannt ({folder_id})")
        orphaned = folder_id not in podcast_names

        files = _scan_audio_files(item)
        folder_size = sum(f["size"] for f in files)
        total_size += folder_size
        total_files += len(files)

        folders.append({
            "id": f"podcast_{folder_id}",
            "name": name,
            "type": "podcast",
            "file_count": len(files),
            "total_size": folder_size,
            "orphaned": orphaned,
            "files": files
        })

    return {
        "folders": folders,
        "total_size": total_size,
        "total_files": total_files
    }


@router.get("/recordings")
async def get_recording_files():
    """Aufnahmen-Ordnerstruktur mit Dateien"""
    RADIO_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    folders = []
    total_size = 0
    total_files = 0

    for item in sorted(RADIO_RECORDINGS_DIR.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue

        files = _scan_audio_files(item)
        folder_size = sum(f["size"] for f in files)
        total_size += folder_size
        total_files += len(files)

        # Session-Name aus Ordnername ableiten
        folders.append({
            "id": f"rec_{item.name}",
            "name": item.name,
            "type": "recording",
            "file_count": len(files),
            "total_size": folder_size,
            "orphaned": False,
            "files": files
        })

    return {
        "folders": folders,
        "total_size": total_size,
        "total_files": total_files
    }


@router.delete("/delete")
async def delete_file(path: str = Query(..., description="Absoluter Dateipfad")):
    """Einzelne Datei loeschen (nur innerhalb RECORDINGS_DIR)"""
    file_path = Path(path)

    # Sicherheitscheck: muss innerhalb RECORDINGS_DIR liegen
    try:
        file_path.resolve().relative_to(RECORDINGS_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Zugriff verweigert")

    if not file_path.exists():
        raise HTTPException(404, "Datei nicht gefunden")
    if not file_path.is_file():
        raise HTTPException(400, "Kein gueltiger Dateipfad")

    file_path.unlink()

    # Leeren Eltern-Ordner aufraeumen
    parent = file_path.parent
    if parent != RECORDINGS_DIR and not any(parent.iterdir()):
        parent.rmdir()

    return {"success": True, "deleted": str(file_path)}


# === ZIP + M3U Download ===

class ZipDownloadRequest(BaseModel):
    files: List[str]  # Absolute Dateipfade
    include_playlist: bool = True


def _cleanup_temp_file(path: str):
    """Temp-Datei nach Download loeschen"""
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


@router.post("/download-zip")
async def download_zip(req: ZipDownloadRequest, background_tasks: BackgroundTasks):
    """Selektierte Dateien als ZIP mit optionaler M3U-Playlist"""
    if not req.files:
        raise HTTPException(400, "Keine Dateien ausgewaehlt")

    # Dateien validieren
    valid_files = []
    for fp_str in req.files:
        fp = Path(fp_str)
        try:
            fp.resolve().relative_to(RECORDINGS_DIR.resolve())
        except ValueError:
            continue
        if fp.exists() and fp.is_file():
            valid_files.append(fp)

    if not valid_files:
        raise HTTPException(404, "Keine gueltigen Dateien gefunden")

    cache_dir = get_cache_dir()
    zip_name = f"radiohub_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = cache_dir / zip_name

    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for fp in valid_files:
                zf.write(fp, fp.name)

            if req.include_playlist and len(valid_files) > 1:
                # M3U-Playlist erzeugen
                m3u_lines = ["#EXTM3U"]
                for fp in valid_files:
                    m3u_lines.append(f"#EXTINF:-1,{fp.stem}")
                    m3u_lines.append(fp.name)
                m3u_content = "\n".join(m3u_lines) + "\n"
                zf.writestr("playlist.m3u", m3u_content)
    except Exception as e:
        raise HTTPException(500, f"ZIP-Erstellung fehlgeschlagen: {e}")

    background_tasks.add_task(_cleanup_temp_file, str(zip_path))

    return FileResponse(
        path=zip_path,
        filename=zip_name,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'}
    )
