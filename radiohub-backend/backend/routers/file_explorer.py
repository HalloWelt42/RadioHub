"""
RadioHub v0.2.5 - File Explorer Router

Einheitlicher Datei-Explorer für Podcasts und Aufnahmen.
Ordnerstruktur, Datei-Löschung, ZIP+M3U Download.
"""
import os
import shutil
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
    """Audio-Dateien in einem Ordner rekursiv scannen"""
    files = []
    if not folder.exists():
        return files
    for item in sorted(folder.rglob("*")):
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
            stat = item.stat()
            # Relativer Pfad zum Ordner für verschachtelte Dateien
            rel = item.relative_to(folder)
            display_name = str(rel) if len(rel.parts) > 1 else item.name
            files.append({
                "name": display_name,
                "path": str(item),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": item.suffix.lower()
            })
    return files


def _get_recording_folder_info() -> dict:
    """Ordner-Pfade zu Session-Infos aus der DB mappen.
    Nutzt recording_folders (folder_id) UND file_path als Fallback.
    Liefert: { dir_name: { station_names: [...], start_time, end_time, known: bool } }
    known=True heißt: Ordner ist in recording_folders oder hat Sessions.
    """
    mapping = {}
    try:
        with db_session() as conn:
            # 1. Bekannte Ordner aus recording_folders
            rf_rows = conn.execute(
                "SELECT id, name, path FROM recording_folders"
            ).fetchall()
            folder_id_to_path = {}
            for rf in rf_rows:
                folder_id_to_path[rf["id"]] = rf["path"]
                # Ordner ist bekannt auch ohne Sessions
                mapping[rf["path"]] = {
                    "station_names": set(),
                    "display_name": rf["name"],
                    "start_time": None,
                    "end_time": None,
                    "known": True,
                }

            # 2. Sessions zuordnen
            rows = conn.execute(
                """SELECT file_path, station_name, start_time, end_time, folder_id
                   FROM sessions
                   WHERE file_path IS NOT NULL"""
            ).fetchall()
            for row in rows:
                # Ordnernamen bestimmen: über folder_id oder file_path
                dir_name = None
                if row["folder_id"] and row["folder_id"] in folder_id_to_path:
                    dir_name = folder_id_to_path[row["folder_id"]]
                if not dir_name and row["file_path"]:
                    fp = Path(row["file_path"])
                    try:
                        rel = fp.resolve().relative_to(RADIO_RECORDINGS_DIR.resolve())
                        parts = rel.parts
                        if parts:
                            # Erster Pfad-Teil relativ zu RADIO_RECORDINGS_DIR
                            dir_name = parts[0]
                    except (ValueError, RuntimeError):
                        pass

                if not dir_name:
                    continue

                if dir_name not in mapping:
                    mapping[dir_name] = {
                        "station_names": set(),
                        "display_name": None,
                        "start_time": None,
                        "end_time": None,
                        "known": True,
                    }
                else:
                    mapping[dir_name]["known"] = True

                if row["station_name"]:
                    mapping[dir_name]["station_names"].add(row["station_name"])
                if row["start_time"]:
                    cur = mapping[dir_name]["start_time"]
                    if not cur or row["start_time"] < cur:
                        mapping[dir_name]["start_time"] = row["start_time"]
                if row["end_time"]:
                    cur = mapping[dir_name]["end_time"]
                    if not cur or row["end_time"] > cur:
                        mapping[dir_name]["end_time"] = row["end_time"]
    except Exception:
        pass

    # Sets zu sortierten Listen konvertieren
    for key in mapping:
        mapping[key]["station_names"] = sorted(mapping[key]["station_names"])
    return mapping


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
    """Aufnahmen-Ordnerstruktur mit Dateien, angereichert mit Stationsnamen"""
    RADIO_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    folder_info = _get_recording_folder_info()
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

        info = folder_info.get(item.name, {})
        station_names = info.get("station_names", [])
        start_time = info.get("start_time")
        end_time = info.get("end_time")
        known = info.get("known", False)

        # Anzeigename: Ordnername aus DB > Stationsname(n) > Disk-Ordnername
        db_display = info.get("display_name")
        if db_display:
            display_name = db_display
        elif station_names:
            display_name = ", ".join(station_names)
        else:
            display_name = item.name

        # Verwaist = weder in recording_folders noch Sessions zugeordnet
        orphaned = not known

        folders.append({
            "id": f"rec_{item.name}",
            "name": display_name,
            "dir_name": item.name,
            "type": "recording",
            "file_count": len(files),
            "total_size": folder_size,
            "orphaned": orphaned,
            "station_names": station_names,
            "start_time": start_time,
            "end_time": end_time,
            "files": files
        })

    return {
        "folders": folders,
        "total_size": total_size,
        "total_files": total_files
    }


@router.delete("/delete")
async def delete_file(path: str = Query(..., description="Absoluter Dateipfad")):
    """Einzelne Datei löschen (nur innerhalb RECORDINGS_DIR)"""
    file_path = Path(path)

    # Sicherheitscheck: muss innerhalb RECORDINGS_DIR liegen
    try:
        file_path.resolve().relative_to(RECORDINGS_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Zugriff verweigert")

    if not file_path.exists():
        raise HTTPException(404, "Datei nicht gefunden")
    if not file_path.is_file():
        raise HTTPException(400, "Kein gültiger Dateipfad")

    file_path.unlink()

    # Leeren Eltern-Ordner aufräumen
    parent = file_path.parent
    if parent != RECORDINGS_DIR and not any(parent.iterdir()):
        parent.rmdir()

    return {"success": True, "deleted": str(file_path)}


@router.delete("/delete-orphaned")
async def delete_orphaned_folders():
    """Verwaiste Aufnahme-Ordner löschen (ohne DB-Zuordnung).

    Sicherheit: Nur Ordner löschen die weder in recording_folders
    noch als session file_path referenziert werden.
    """
    folder_info = _get_recording_folder_info()

    # Session-Pfade aus DB laden (auch segmentierte Sessions haben Verzeichnisse)
    session_dirs = set()
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT file_path FROM sessions WHERE file_path IS NOT NULL")
        for row in c.fetchall():
            p = Path(row[0])
            # file_path kann Datei oder Verzeichnis sein
            if p.is_dir():
                session_dirs.add(p.resolve())
            else:
                session_dirs.add(p.parent.resolve())

    deleted = []
    skipped = []

    RADIO_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    for item in list(RADIO_RECORDINGS_DIR.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        info = folder_info.get(item.name, {})
        if info.get("known", False):
            continue
        # Prüfen ob der Ordner von einer Session referenziert wird
        if item.resolve() in session_dirs:
            skipped.append(item.name)
            continue
        # Sicherheitscheck: Nur löschen wenn keine Audio-Dateien enthalten
        audio_exts = {".mp3", ".aac", ".m4a", ".ogg", ".opus", ".flac", ".wav"}
        has_audio = any(f.suffix.lower() in audio_exts for f in item.rglob("*") if f.is_file())
        if has_audio:
            skipped.append(item.name)
            continue
        # Verwaist und leer: löschen
        try:
            shutil.rmtree(item)
            deleted.append(item.name)
        except Exception:
            pass

    return {"success": True, "deleted": deleted, "skipped": skipped, "count": len(deleted)}


# === ZIP + M3U Download ===

class ZipDownloadRequest(BaseModel):
    files: List[str]  # Absolute Dateipfade
    include_playlist: bool = True


def _cleanup_temp_file(path: str):
    """Temp-Datei nach Download löschen"""
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


@router.post("/download-zip")
async def download_zip(req: ZipDownloadRequest, background_tasks: BackgroundTasks):
    """Selektierte Dateien als ZIP mit optionaler M3U-Playlist"""
    if not req.files:
        raise HTTPException(400, "Keine Dateien ausgewählt")

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
        raise HTTPException(404, "Keine gültigen Dateien gefunden")

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
