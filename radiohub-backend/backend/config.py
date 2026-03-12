"""
RadioHub v0.2.4 - Konfiguration

Daten-Verzeichnis wird per Environment-Variable gesetzt.
Docker mounted externes Verzeichnis nach /data.

Pfade werden jetzt über Storage-Zonen aufgelöst (storage.py).
Alle Konstanten und Funktionen bleiben als Wrapper erhalten,
damit bestehende Imports nicht geändert werden müssen.
"""
import os
from pathlib import Path
from .storage import get_zone_path, get_data_dir as _get_data_dir

# === Version ===
VERSION = "0.2.4"

# === Pfade (delegiert an Storage-Zonen) ===
# Basis-Verzeichnis (Docker: /data, Lokal: ./data)
DATA_DIR = _get_data_dir()

# Datenbank (Zone: database)
DB_PATH = get_zone_path("database") / "radiohub.db"

# Aufnahmen
# RECORDINGS_DIR bleibt als Eltern-Verzeichnis für Sicherheitschecks
RECORDINGS_DIR = DATA_DIR / "recordings"
RADIO_RECORDINGS_DIR = get_zone_path("recordings")
PODCAST_RECORDINGS_DIR = get_zone_path("podcasts")

# Cache (Zone: cache)
CACHE_DIR = get_zone_path("cache")


def ensure_directories():
    """Erstellt alle benötigten Verzeichnisse.
    Storage-Zonen erstellen ihre Verzeichnisse automatisch,
    RECORDINGS_DIR wird hier extra angelegt für Abwärtskompatibilität."""
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


def get_radio_recordings_dir() -> Path:
    """Radio-Aufnahmen Verzeichnis (aus Storage-Zone)"""
    path = get_zone_path("recordings")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_podcast_recordings_dir() -> Path:
    """Podcast-Aufnahmen Verzeichnis (aus Storage-Zone)"""
    path = get_zone_path("podcasts")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir() -> Path:
    """Cache Verzeichnis (aus Storage-Zone)"""
    path = get_zone_path("cache")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_active_recording_dir() -> tuple[Path, int | None]:
    """Aktives Aufnahme-Verzeichnis (Ordner oder Root).
    Returns: (Pfad, folder_id oder None)"""
    import sqlite3
    rec_dir = get_zone_path("recordings")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, path FROM recording_folders WHERE is_active = 1 LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            active_dir = rec_dir / row["path"]
            active_dir.mkdir(parents=True, exist_ok=True)
            return active_dir, row["id"]
    except Exception:
        pass
    rec_dir.mkdir(parents=True, exist_ok=True)
    return rec_dir, None
