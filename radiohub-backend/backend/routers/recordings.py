"""
RadioHub v0.1.5 - Recordings Router

Datei-Explorer für Aufnahmen (Ordner browsen, Dateien listen/löschen)
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..config import RECORDINGS_DIR, RADIO_RECORDINGS_DIR, AUDIO_EXTENSIONS, AUDIO_MIMETYPES

router = APIRouter(prefix="/api/recordings", tags=["recordings"])


def get_safe_path(rel_path: str) -> Path:
    """Sicherer Pfad innerhalb RECORDINGS_DIR"""
    # Normalisieren und ../ verhindern
    clean = os.path.normpath(rel_path).lstrip("/\\")
    full_path = RECORDINGS_DIR / clean
    
    # Sicherheitscheck
    try:
        full_path.resolve().relative_to(RECORDINGS_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Zugriff verweigert")
    
    return full_path


@router.get("/stats")
async def get_stats():
    """Speicher-Statistiken (nur Radio-Aufnahmen, ohne Podcasts/Cache)"""
    radio_dir = RADIO_RECORDINGS_DIR
    radio_dir.mkdir(parents=True, exist_ok=True)

    # Speicherplatz
    total, used, free = shutil.disk_usage(radio_dir)

    # Nur echte Audio-Dateien zählen (keine .peaks, .meta.json, .tmp)
    file_count = 0
    total_size = 0

    for root, dirs, files in os.walk(radio_dir):
        for f in files:
            if Path(f).suffix.lower() in AUDIO_EXTENSIONS:
                file_count += 1
                total_size += (Path(root) / f).stat().st_size

    return {
        "disk_free_gb": round(free / (1024**3), 2),
        "disk_total_gb": round(total / (1024**3), 2),
        "file_count": file_count,
        "used_mb": round(total_size / (1024**2), 2)
    }


@router.get("/folders")
async def get_folders(path: str = Query("/", description="Relativer Pfad")):
    """Ordnerstruktur holen"""
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    
    base = get_safe_path(path)
    if not base.exists():
        base = RECORDINGS_DIR
    
    folders = []
    
    def scan_folder(folder: Path, rel_prefix: str = ""):
        for item in sorted(folder.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                rel_path = f"{rel_prefix}/{item.name}".lstrip("/")
                
                # Dateien in diesem Ordner zählen
                file_count = sum(1 for f in item.iterdir() 
                               if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS)
                
                folders.append({
                    "name": item.name,
                    "path": rel_path,
                    "file_count": file_count
                })
                
                # Rekursiv (nur 1 Ebene tief)
                for sub in sorted(item.iterdir()):
                    if sub.is_dir() and not sub.name.startswith("."):
                        sub_rel = f"{rel_path}/{sub.name}"
                        sub_count = sum(1 for f in sub.iterdir() 
                                      if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS)
                        folders.append({
                            "name": sub.name,
                            "path": sub_rel,
                            "file_count": sub_count,
                            "parent": rel_path
                        })
    
    scan_folder(RECORDINGS_DIR)
    return {"folders": folders}


@router.get("/files")
async def get_files(
    path: str = Query("/", description="Relativer Pfad"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str = Query("", description="Suchbegriff")
):
    """Dateien in einem Ordner"""
    folder = get_safe_path(path)
    
    if not folder.exists() or not folder.is_dir():
        return {"files": [], "total": 0}
    
    files = []
    
    for item in folder.iterdir():
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
            # Suchfilter
            if search and search.lower() not in item.name.lower():
                continue
            
            stat = item.stat()
            files.append({
                "name": item.name,
                "path": str(item.relative_to(RECORDINGS_DIR)),
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024**2), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": item.suffix.lower()
            })
    
    # Sortieren nach Datum (neueste zuerst)
    files.sort(key=lambda x: x["modified"], reverse=True)
    
    total = len(files)
    files = files[offset:offset + limit]
    
    return {"files": files, "total": total, "path": path}


@router.delete("/file")
async def delete_file(path: str = Query(..., description="Dateipfad")):
    """Datei löschen"""
    file_path = get_safe_path(path)
    
    if not file_path.exists():
        raise HTTPException(404, "Datei nicht gefunden")
    
    if not file_path.is_file():
        raise HTTPException(400, "Kein gültiger Dateipfad")
    
    file_path.unlink()
    return {"success": True, "deleted": path}


@router.delete("/folder")
async def delete_folder(path: str = Query(..., description="Ordnerpfad")):
    """Ordner löschen (nur wenn leer)"""
    folder_path = get_safe_path(path)
    
    if not folder_path.exists():
        raise HTTPException(404, "Ordner nicht gefunden")
    
    if not folder_path.is_dir():
        raise HTTPException(400, "Kein gültiger Ordnerpfad")
    
    # Nur leere Ordner löschen
    if any(folder_path.iterdir()):
        raise HTTPException(400, "Ordner ist nicht leer")
    
    folder_path.rmdir()
    return {"success": True, "deleted": path}


@router.get("/play")
async def play_file(path: str = Query(..., description="Dateipfad")):
    """Audio-Datei streamen mit Range-Support für Seeking"""
    file_path = get_safe_path(path)
    
    if not file_path.exists():
        raise HTTPException(404, "Datei nicht gefunden")
    
    # Content-Type ermitteln
    ext = file_path.suffix.lower()

    file_size = file_path.stat().st_size

    return FileResponse(
        path=file_path,
        media_type=AUDIO_MIMETYPES.get(ext, "audio/mpeg"),
        filename=file_path.name,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        }
    )
