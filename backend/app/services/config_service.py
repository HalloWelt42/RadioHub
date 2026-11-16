"""Werte unter /api/config: Einstellungen des Servers und Stand der Oberfläche unter einem Dach (bis Teil 2c).

Die Schlüssel in `einstellungen.CONFIG_FELDER` sind Einstellungen des Servers; sie kommen aus den Einstellungen des
Appkerns (eine Quelle, RAD-6) und werden dort geändert. Alle übrigen Schlüssel sind Stand der Oberfläche (Sprache,
Klickgeräusche, zuletzt gehörter Sender, Länder der Seitenleiste, Filter, Ort der Sonnenzeiten) und bleiben in der
Tabelle config der Datenbank des RadioHub.
"""
import json
import logging
from typing import Any

from .. import einstellungen
from ..database import db_session
from ..einstellungen import CONFIG_FELDER

log = logging.getLogger("radiohub.config")

# Vorgaben des Stands der Oberfläche (die der Einstellungen stehen in einstellungen.AppEinstellungen)
DEFAULT_CONFIG = {
    # --- UI ---
    "language": "de",
    "ui_click_sounds": True,
    # --- Audio / Aufnahme ---
    "recording_format": "mp3",
    # --- Session ---
    "last_station_uuid": None,
    "last_station_name": None,
    # --- Filter ---
    "sidebar_countries": None, # JSON-Array mit sichtbaren Country-Codes
}


class ConfigService:
    """Liest und schreibt die Werte unter /api/config."""

    def __init__(self):
        self._cache: dict = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Lädt den Stand der Oberfläche aus der Datenbank, wenn noch nicht geladen"""
        if not self._loaded:
            self._load_from_db()
            self._loaded = True

    def _load_from_db(self):
        """Lädt alle Werte der Tabelle config außer denen, die jetzt Einstellungen sind"""
        with db_session() as conn:
            for row in conn.execute("SELECT key, value FROM config"):
                if row[0] in CONFIG_FELDER:
                    continue
                try:
                    self._cache[row[0]] = json.loads(row[1])
                except (TypeError, ValueError):
                    self._cache[row[0]] = row[1]

    def get(self, key: str, default: Any = None) -> Any:
        """Einzelnen Wert holen"""
        if key in CONFIG_FELDER:
            return getattr(einstellungen.stand(), key)
        self._ensure_loaded()
        if key in self._cache:
            return self._cache[key]
        if key in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[key]
        return default

    def set(self, key: str, value: Any):
        """Einen Wert des Stands der Oberfläche setzen (Einstellungen gehen über `aendern`)"""
        if key in CONFIG_FELDER:
            raise ValueError(f"{key} ist eine Einstellung des Servers; ändern über aendern()")
        self._ensure_loaded()
        self._cache[key] = value
        with db_session() as conn:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, json.dumps(value)))

    def get_all(self) -> dict:
        """Alle Werte (mit Vorgaben)"""
        self._ensure_loaded()
        result = dict(DEFAULT_CONFIG)
        result.update(self._cache)
        stand = einstellungen.stand()
        result.update({k: getattr(stand, k) for k in sorted(CONFIG_FELDER)})
        return result

    async def aendern(self, updates: dict) -> dict:
        """Mehrere Werte ändern: Einstellungen zusammen (alles oder nichts, `None` heißt Vorgabe), danach der Stand der
        Oberfläche."""
        felder = {k: v for k, v in updates.items() if k in CONFIG_FELDER}
        if felder:
            await einstellungen.aendern(felder)
        for key, value in updates.items():
            if key not in CONFIG_FELDER:
                self.set(key, value)
        return self.get_all()

    def update(self, updates: dict) -> dict:
        """Mehrere Werte des Stands der Oberfläche setzen (ohne Einstellungen; die gehen über `aendern`)"""
        for key, value in updates.items():
            self.set(key, value)
        return self.get_all()

    async def reset(self) -> dict:
        """Auf die Vorgaben zurücksetzen: den Stand der Oberfläche und die hier gespeicherten Einstellungen (feste
        Einstellungen vom Ausrollen bleiben)"""
        with db_session() as conn:
            platzhalter = ",".join("?" * len(CONFIG_FELDER))
            conn.execute(f"DELETE FROM config WHERE key NOT IN ({platzhalter})", tuple(CONFIG_FELDER))
        self._cache = {}
        self._loaded = False
        zurueck = {k: None for k in CONFIG_FELDER if einstellungen.herkunft(k) == "gespeichert"}
        if zurueck:
            await einstellungen.aendern(zurueck)
        return self.get_all()


# Singleton
config_service = ConfigService()


def get_config_service() -> ConfigService:
    """Singleton-Zugriff"""
    return config_service
