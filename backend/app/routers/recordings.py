"""
RadioHub - Recordings Router

Statistik der Aufnahmen und Wiedergabe einer Datei aus der Ablage (Pfad relativ zur Wurzel der Ablage).
Ordner und Dateien zeigen die Aufnahmen (routers/recording.py) und die Kellerwolke (routers/wolke.py).
"""
import shutil

from fastapi import APIRouter, HTTPException, Query, Request

from ..ablage import orte
from ..ablage.wiedergabe import ausliefern
from ..config import get_arbeit_dir
from ..database import db_session

router = APIRouter(prefix="/api/recordings", tags=["recordings"])


@router.get("/stats")
async def get_stats():
    """Aufnahmen in der Ablage (Zahl und Größe der Stücke) und freier Platz für Zwischenstände"""
    total, _, free = shutil.disk_usage(get_arbeit_dir())
    with db_session() as conn:
        anzahl, groesse = conn.execute("SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM segments").fetchone()
    return {
        "disk_free_gb": round(free / (1024**3), 2),
        "disk_total_gb": round(total / (1024**3), 2),
        "file_count": anzahl,
        "used_mb": round(groesse / (1024**2), 2)
    }


@router.get("/play")
async def play_file(request: Request, path: str = Query(..., description="Pfad in der Ablage")):
    """Audio-Datei unter Aufnahmen oder Podcasts aus der Ablage streamen, mit Range zum Spulen; andere Pfade 400"""
    try:
        pfad = orte.im_bereich(path)
    except ValueError as f:
        raise HTTPException(400, str(f)) from None
    return await ausliefern(pfad, request)
