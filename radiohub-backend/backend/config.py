"""
RadioHub v0.1.0 - Konfiguration

Daten-Verzeichnis wird per Environment-Variable gesetzt.
Docker mounted externes Verzeichnis nach /data.
"""
import os
from pathlib import Path

# === Version ===
VERSION = "0.2.3"

# === Pfade ===
# Daten-Verzeichnis (Docker: /data, Lokal: ./data)
DATA_DIR = Path(os.getenv("DATA_PATH", str(Path(__file__).resolve().parent.parent / "data")))

# Datenbank
DB_PATH = DATA_DIR / "radiohub.db"

# Aufnahmen
RECORDINGS_DIR = DATA_DIR / "recordings"
RADIO_RECORDINGS_DIR = RECORDINGS_DIR / "radio"
PODCAST_RECORDINGS_DIR = RECORDINGS_DIR / "podcasts"

# Cache
CACHE_DIR = DATA_DIR / "cache"


def ensure_directories():
    """Erstellt alle benötigten Verzeichnisse"""
    for dir_path in [DATA_DIR, RECORDINGS_DIR, RADIO_RECORDINGS_DIR, 
                     PODCAST_RECORDINGS_DIR, CACHE_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def get_radio_recordings_dir() -> Path:
    """Radio-Aufnahmen Verzeichnis"""
    RADIO_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    return RADIO_RECORDINGS_DIR


def get_podcast_recordings_dir() -> Path:
    """Podcast-Aufnahmen Verzeichnis"""
    PODCAST_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    return PODCAST_RECORDINGS_DIR


def get_cache_dir() -> Path:
    """Cache Verzeichnis"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR
