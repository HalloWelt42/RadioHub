"""
RadioHub v0.4.0 - File Explorer Router

Einheitlicher Datei-Explorer für Podcasts und Aufnahmen in der Ablage (Kellerwolke).
Ordnerstruktur, Datei-Löschung (Papierkorb der Ablage), ZIP+M3U Download.
Pfade sind Pfade in der Ablage, relativ zu ihrer Wurzel (etwa `Podcasts/<Abo>/<Folge>.mp3`).
"""
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..ablage import Eintrag, ablage, orte
from ..config import AUDIO_EXTENSIONS, get_arbeit_dir
from ..database import db_session
from ..services.aufnahmen import aufnahmen

router = APIRouter(prefix="/api/files", tags=["file-explorer"])


def _in_bereich(pfad: str) -> str:
    """Nur Pfade unter Aufnahmen oder Podcasts (keine Ausbrüche, keine anderen Ordner der App)."""
    teile = [t for t in pfad.replace("\\", "/").split("/") if t]
    if not teile or teile[0] not in (orte.AUFNAHMEN, orte.PODCASTS) or any(t in (".", "..") for t in teile):
        raise HTTPException(403, "Zugriff verweigert")
    return "/".join(teile)


def _datei(e: Eintrag, ordner: str) -> dict:
    rel = e.pfad[len(ordner):].lstrip("/")
    return {"name": rel, "path": e.pfad, "size": e.groesse, "modified": e.geaendert.isoformat(),
            "extension": e.endung}


async def _audio_dateien(ordner: str) -> list[dict]:
    dateien = [e for e in await ablage().alle_dateien(ordner) if e.endung in AUDIO_EXTENSIONS]
    return [_datei(e, ordner) for e in sorted(dateien, key=lambda e: e.pfad)]


@router.get("/podcasts")
async def get_podcast_files():
    """Podcast-Ordner (je Abo einer) mit ihren Folgen"""
    with db_session() as conn:
        abos = {orte.name(r["title"] or "", ersatz="Unbekannter Podcast"): r["id"]
                for r in conn.execute("SELECT id, title FROM podcast_subscriptions").fetchall()}
    folders, total_size, total_files = [], 0, 0
    for ordner in await ablage().liste(orte.PODCASTS):
        if not ordner.ist_ordner:
            continue
        files = await _audio_dateien(ordner.pfad)
        groesse = sum(f["size"] for f in files)
        total_size += groesse
        total_files += len(files)
        folders.append({
            "id": f"podcast_{ordner.name}",
            "name": ordner.name,
            "type": "podcast",
            "file_count": len(files),
            "total_size": groesse,
            "orphaned": ordner.name not in abos,
            "files": files,
        })
    return {"folders": folders, "total_size": total_size, "total_files": total_files}


def _aufnahmen_je_ordner() -> dict:
    """Erster Ordner unter Aufnahmen -> Sender, Zeitraum, ob ihn die Datenbank kennt."""
    mapping: dict[str, dict] = {}

    def eintrag(name: str) -> dict:
        return mapping.setdefault(name, {"station_names": set(), "start_time": None, "end_time": None,
                                         "display_name": None})

    with db_session() as conn:
        for row in conn.execute("SELECT name FROM recording_folders").fetchall():
            eintrag(orte.name(row["name"]))["display_name"] = row["name"]
        rows = conn.execute("SELECT file_path, station_name, start_time, end_time FROM sessions "
                            "WHERE file_path IS NOT NULL").fetchall()
    for row in rows:
        teile = row["file_path"].split("/")
        if len(teile) < 2 or teile[0] != orte.AUFNAHMEN:
            continue
        info = eintrag(teile[1])
        if row["station_name"]:
            info["station_names"].add(row["station_name"])
        if row["start_time"] and (not info["start_time"] or row["start_time"] < info["start_time"]):
            info["start_time"] = row["start_time"]
        if row["end_time"] and (not info["end_time"] or row["end_time"] > info["end_time"]):
            info["end_time"] = row["end_time"]
    return mapping


@router.get("/recordings")
async def get_recording_files():
    """Aufnahme-Ordner (Sender oder eigener Aufnahmeordner) mit ihren Stücken, angereichert mit Sendernamen"""
    bekannt = _aufnahmen_je_ordner()
    folders, total_size, total_files = [], 0, 0
    for ordner in await ablage().liste(orte.AUFNAHMEN):
        if not ordner.ist_ordner:
            continue
        files = await _audio_dateien(ordner.pfad)
        groesse = sum(f["size"] for f in files)
        total_size += groesse
        total_files += len(files)
        info = bekannt.get(ordner.name)
        stationen = sorted(info["station_names"]) if info else []
        folders.append({
            "id": f"rec_{ordner.name}",
            "name": (info and info["display_name"]) or ordner.name,
            "dir_name": ordner.name,
            "type": "recording",
            "file_count": len(files),
            "total_size": groesse,
            "orphaned": info is None,
            "station_names": stationen,
            "start_time": info["start_time"] if info else None,
            "end_time": info["end_time"] if info else None,
            "files": files,
        })
    return {"folders": folders, "total_size": total_size, "total_files": total_files}


@router.delete("/delete")
async def delete_file(path: str = Query(..., description="Pfad in der Ablage")):
    """Einzelne Datei in den Papierkorb der Ablage; die Datenbank folgt (Stück einer Aufnahme, Podcast-Folge)"""
    pfad = _in_bereich(path)
    eintrag = await ablage().eintrag(pfad)
    if eintrag is None:
        raise HTTPException(404, "Datei nicht gefunden")
    if eintrag.ist_ordner:
        raise HTTPException(400, "Kein gültiger Dateipfad")
    with db_session() as conn:
        segment = conn.execute("SELECT id, session_id FROM segments WHERE file_path = ?", (pfad,)).fetchone()
    if segment:
        await aufnahmen.segment_loeschen(segment["session_id"], segment["id"])
    else:
        await ablage().loeschen(pfad)
        with db_session() as conn:
            conn.execute("UPDATE podcast_episodes SET is_downloaded = 0, local_path = NULL, file_size = 0 "
                         "WHERE local_path = ?", (pfad,))
    return {"success": True, "deleted": pfad}


@router.delete("/delete-orphaned")
async def delete_orphaned_folders():
    """Verwaiste Aufnahme-Ordner ohne Ton (keine Aufnahme und kein Aufnahmeordner kennt sie) in den Papierkorb."""
    bekannt = _aufnahmen_je_ordner()
    deleted, skipped = [], []
    for ordner in await ablage().liste(orte.AUFNAHMEN):
        if not ordner.ist_ordner or ordner.name in bekannt:
            continue
        if any(e.endung in AUDIO_EXTENSIONS for e in await ablage().alle_dateien(ordner.pfad)):
            skipped.append(ordner.name)
            continue
        await ablage().loeschen(ordner.pfad)
        deleted.append(ordner.name)
    return {"success": True, "deleted": deleted, "skipped": skipped, "count": len(deleted)}


# === ZIP + M3U Download ===

class ZipDownloadRequest(BaseModel):
    files: List[str]  # Pfade in der Ablage
    include_playlist: bool = True


def _aufraeumen(*pfade: str):
    for pfad in pfade:
        p = Path(pfad)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)


@router.post("/download-zip")
async def download_zip(req: ZipDownloadRequest, background_tasks: BackgroundTasks):
    """Selektierte Dateien als ZIP mit optionaler M3U-Playlist"""
    pfade = []
    for pfad in req.files:
        try:
            pfade.append(_in_bereich(pfad))
        except HTTPException:
            continue
    if not pfade:
        raise HTTPException(400, "Keine Dateien ausgewählt")

    stempel = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f"radiohub_download_{stempel}.zip"
    ordner = get_arbeit_dir("zip", f"auswahl_{stempel}_{datetime.now().microsecond}")
    zip_path = ordner.with_suffix(".zip")
    namen = []
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for pfad in pfade:
                if await ablage().eintrag(pfad) is None:
                    continue
                lokal = await ablage().herunterladen(pfad, ordner / Path(pfad).name)
                zf.write(lokal, lokal.name)
                lokal.unlink(missing_ok=True)
                namen.append(lokal.name)
            if not namen:
                raise HTTPException(404, "Keine gültigen Dateien gefunden")
            if req.include_playlist and len(namen) > 1:
                m3u = ["#EXTM3U"]
                for name in namen:
                    m3u += [f"#EXTINF:-1,{Path(name).stem}", name]
                zf.writestr("playlist.m3u", "\n".join(m3u) + "\n")
    except HTTPException:
        _aufraeumen(str(ordner), str(zip_path))
        raise
    except Exception as e:
        _aufraeumen(str(ordner), str(zip_path))
        raise HTTPException(500, f"ZIP-Erstellung fehlgeschlagen: {e}")

    background_tasks.add_task(_aufraeumen, str(ordner), str(zip_path))
    return FileResponse(path=zip_path, filename=zip_name, media_type="application/zip")
