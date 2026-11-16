"""
RadioHub v0.2.5 - Config Service

Globale App-Einstellungen in der Datenbank speichern.
"""
import json
from typing import Any, Optional

from ..database import db_session

# Standard-Einstellungen (thematisch gruppiert)
DEFAULT_CONFIG = {
    # --- UI ---
    "language": "de",
    "ui_click_sounds": True,
    # --- Audio / Aufnahme ---
    "recording_format": "mp3",
    "recording_bitrate": 192,
    "hls_min_bitrate": 32,    # Minimum kbps
    "hls_max_bitrate": 320,   # Maximum kbps
    "hls_sample_rate": 44100, # Sample Rate (Hz)
    # --- Podcast ---
    "podcast_auto_refresh": True,
    "podcast_refresh_interval": 21600,  # 6 Stunden in Sekunden
    # --- Session ---
    "last_station_uuid": None,
    "last_station_name": None,
    # --- Filter ---
    "sidebar_countries": None, # JSON-Array mit sichtbaren Country-Codes
    # --- Externe Dienste ---
    "service_radio_browser_servers": [
        "https://de1.api.radio-browser.info",
        "https://at1.api.radio-browser.info",
        "https://nl1.api.radio-browser.info"
    ],
    "service_itunes_search_url": "https://itunes.apple.com/search",
    "service_fyyd_search_url": "https://api.fyyd.de/0.2/search/podcast",
}


class ConfigService:
    """Verwaltet globale Einstellungen"""
    
    def __init__(self):
        self._cache: dict = {}
        self._loaded = False
    
    def _ensure_loaded(self):
        """Lädt Config aus DB wenn noch nicht geladen"""
        if not self._loaded:
            self._load_from_db()
            self._loaded = True
    
    def _load_from_db(self):
        """Lädt alle Config-Werte aus DB"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT key, value FROM config")
            for row in c.fetchall():
                try:
                    self._cache[row[0]] = json.loads(row[1])
                except:
                    self._cache[row[0]] = row[1]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Einzelnen Wert holen"""
        self._ensure_loaded()
        
        if key in self._cache:
            return self._cache[key]
        
        if key in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[key]
        
        return default
    
    def set(self, key: str, value: Any):
        """Einzelnen Wert setzen"""
        self._ensure_loaded()
        self._cache[key] = value
        
        with db_session() as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                     (key, json.dumps(value)))
    
    def get_all(self) -> dict:
        """Alle Einstellungen holen (mit Defaults)"""
        self._ensure_loaded()
        
        result = dict(DEFAULT_CONFIG)
        result.update(self._cache)
        return result
    
    def update(self, updates: dict) -> dict:
        """Mehrere Werte aktualisieren"""
        for key, value in updates.items():
            self.set(key, value)

        return self.get_all()
    
    def reset(self) -> dict:
        """Auf Standardwerte zurücksetzen"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM config")
        
        self._cache = {}
        self._loaded = False
        
        return self.get_all()


# Singleton
config_service = ConfigService()


def get_config_service() -> ConfigService:
    """Singleton-Zugriff"""
    return config_service
