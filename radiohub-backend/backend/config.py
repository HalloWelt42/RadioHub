"""
RadioHub v0.6.0 - Konfiguration

Daten-Verzeichnis wird per Environment-Variable gesetzt.
Docker mounted externes Verzeichnis nach /data.

Pfade werden jetzt über Storage-Zonen aufgelöst (storage.py).
Alle Konstanten und Funktionen bleiben als Wrapper erhalten,
damit bestehende Imports nicht geändert werden müssen.
"""
from pathlib import Path
from .storage import get_zone_path, get_data_dir as _get_data_dir

# === Version ===
VERSION = "0.6.0"

# === Pfade (delegiert an Storage-Zonen) ===
# Basis-Verzeichnis (Docker: /data, Lokal: ./data)
DATA_DIR = _get_data_dir()

# Datenbank (Zone: database)
DB_PATH = get_zone_path("database") / "radiohub.db"

# Cache (Zone: cache)
CACHE_DIR = get_zone_path("cache")

# Aufnahmen, Podcast-Folgen und alles, was daraus entsteht, liegen in der Ablage (Kellerwolke, siehe backend/ablage).
# Lokal bleiben nur Zwischenstände im Arbeitsordner (laufende Aufnahme, Download, Arbeitskopie beim Schneiden).


def get_cache_dir() -> Path:
    """Cache Verzeichnis (aus Storage-Zone)"""
    path = get_zone_path("cache")
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_arbeit_dir(*teile: str) -> Path:
    """Arbeitsordner für Zwischenstände (im Cache), etwa get_arbeit_dir("aufnahmen", session_id)."""
    path = get_cache_dir().joinpath("arbeit", *teile)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_active_recording_folder() -> tuple[str | None, int | None]:
    """Aktiver Aufnahmeordner: (Name, folder_id) oder (None, None) für die Wurzel der Aufnahmen."""
    import sqlite3
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id, name FROM recording_folders WHERE is_active = 1 LIMIT 1").fetchone()
        conn.close()
        if row:
            return row["name"], row["id"]
    except sqlite3.Error:
        pass
    return None, None


# Zentrale Audio-Konstanten
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac", ".aac"}

AUDIO_MIMETYPES = {
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".aac": "audio/aac",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
}
