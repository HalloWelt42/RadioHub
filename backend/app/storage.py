"""Speicherzonen des Datenordners: wo Datenbank und Puffer liegen. Gesetzt beim Ausrollen über storage.json
(Priorität: STORAGE_CONFIG > {Datenordner}/storage.json > Vorgabe), in der Oberfläche nur angezeigt (RAD-11: ein neuer
Pfad aus der Oberfläche verschob nichts und startete danach mit leerer Datenbank).

Zonen:
  database   - Datenbank des Radios
  cache      - Puffer des Zeitversatzes, Cover, Zwischenstände von Aufnahme, Download und Schnitt

Aufnahmen und Podcast-Folgen liegen nicht lokal, sondern in der Ablage (Kellerwolke, siehe backend/ablage).
"""
import os
import json
import logging
import shutil
from pathlib import Path
from typing import Optional

from .ort import daten_ordner, speicherzonen_datei

log = logging.getLogger("radiohub.speicherzonen")

# === Basis-Datenverzeichnis (ort.daten_ordner: RADIOHUB_DATEN, früher DATA_PATH) ===
_DATA_DIR = daten_ordner()

# Standardstruktur (matcht bestehende Verzeichnisstruktur exakt)
_DEFAULT_ZONE_SUBDIRS = {
    "database": "",                     # radiohub.db liegt direkt in DATA_DIR
    "cache": "cache",                   # Puffer, Cover, Zwischenstände
}

# Zone-Beschreibungen für die UI
ZONE_INFO = {
    "database": {"label": "Datenbank", "description": "Sender, Regeln, Abos, Wecker und Stand der Oberfläche", "icon": "fa-database"},
    "cache": {"label": "Puffer", "description": "Puffer des Zeitversatzes, Cover, Zwischenstände von Aufnahme, Download und Schnitt",
              "icon": "fa-bolt"},
}

_storage_config: Optional[dict] = None


def _find_config_path() -> Optional[Path]:
    """Sucht storage.json in Prioritätsreihenfolge"""
    # 1. STORAGE_CONFIG Env-Variable
    p = speicherzonen_datei()
    if p is not None and p.exists():
        return p
    # 2. {DATA_PATH}/storage.json
    data_path = _DATA_DIR / "storage.json"
    if data_path.exists():
        return data_path
    return None


def _default_zone_path(zone: str) -> str:
    """Default-Pfad einer Zone unter DATA_DIR."""
    subdir = _DEFAULT_ZONE_SUBDIRS.get(zone, "")
    return str(_DATA_DIR / subdir) if subdir else str(_DATA_DIR)


def _load_or_create() -> dict:
    """Lädt oder erstellt Storage-Konfiguration.

    Pfad-Validierung: Solange kein STORAGE_CONFIG-Env gesetzt ist (Single-Volume-
    Setup), müssen alle Zone-Pfade unter DATA_DIR liegen. Pfade aus fremden Hosts
    (z.B. nach Daten-Migration Mac → Pi) werden automatisch durch Defaults ersetzt
    und storage.json wird zurückgeschrieben. Verhindert, dass das Backend eine
    frische DB im falschen Pfad öffnet, während die migrierte DB unbeachtet bleibt.
    Multi-Volume-Setups (STORAGE_CONFIG gesetzt) bleiben ungeprüft.
    """
    global _storage_config
    if _storage_config is not None:
        return _storage_config

    config_path = _find_config_path()
    multi_volume = speicherzonen_datei() is not None
    data_dir_str = str(_DATA_DIR)
    config_changed = False

    if config_path:
        with open(config_path, "r") as f:
            _storage_config = json.load(f)
        zones = _storage_config.setdefault("zones", {})
        for zone in _DEFAULT_ZONE_SUBDIRS:
            default_path = _default_zone_path(zone)
            if zone not in zones:
                zones[zone] = {"path": default_path}
                config_changed = True
                continue
            current = zones[zone].get("path", "")
            if not multi_volume and not current.startswith(data_dir_str):
                log.warning("storage.json: Zone %s hatte fremden Pfad %s, ersetzt durch %s", zone, current, default_path)
                zones[zone]["path"] = default_path
                config_changed = True
    else:
        # Neue Default-Config erstellen
        _storage_config = {
            "version": 1,
            "zones": {zone: {"path": _default_zone_path(zone)} for zone in _DEFAULT_ZONE_SUBDIRS},
        }
        config_changed = True

    if config_changed:
        _save_config()

    # Verzeichnisse erstellen
    for zone_name, zone_info in _storage_config["zones"].items():
        if zone_name not in _DEFAULT_ZONE_SUBDIRS:
            continue
        try:
            Path(zone_info["path"]).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Pfad evtl. nicht erreichbar (Docker-Volume noch nicht gemounted)

    return _storage_config


def _save_config():
    """Speichert storage.json"""
    if _storage_config is None:
        return

    save_path = speicherzonen_datei() or _DATA_DIR / "storage.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(save_path, "w") as f:
        json.dump(_storage_config, f, indent=2, ensure_ascii=False)


# ============================================================
#  Öffentliche API
# ============================================================

def get_zone_path(zone: str) -> Path:
    """Gibt den Pfad einer Storage-Zone zurück.

    Args:
        zone: Name der Zone (database, cache, config)

    Returns:
        Path-Objekt zum Zone-Verzeichnis
    """
    config = _load_or_create()
    zones = config.get("zones", {})
    if zone not in zones or zone not in _DEFAULT_ZONE_SUBDIRS:
        raise ValueError(f"Unbekannte Storage-Zone: {zone}")
    return Path(zones[zone]["path"])


def get_all_zones() -> dict:
    """Alle Zonen mit Pfad, Speicherplatz, Status und Meta-Info."""
    config = _load_or_create()
    result = {}

    for zone_name, zone_conf in config.get("zones", {}).items():
        if zone_name not in _DEFAULT_ZONE_SUBDIRS:
            continue  # frühere Zonen (recordings, podcasts) liegen jetzt in der Ablage
        path = Path(zone_conf["path"])
        meta = ZONE_INFO.get(zone_name, {})

        data = {
            "path": str(path),
            "label": meta.get("label", zone_name),
            "description": meta.get("description", ""),
            "icon": meta.get("icon", "fa-folder"),
            "writable": False,
            "exists": path.exists(),
            "used_bytes": 0,
            "free_bytes": 0,
            "total_bytes": 0,
            "file_count": 0,
        }

        try:
            path.mkdir(parents=True, exist_ok=True)
            total, used, free = shutil.disk_usage(path)
            data["exists"] = True
            data["writable"] = os.access(path, os.W_OK)
            data["free_bytes"] = free
            data["total_bytes"] = total

            # Dateien in Zone zählen
            zone_size = 0
            zone_files = 0
            for f in path.rglob("*"):
                if f.is_file():
                    try:
                        zone_size += f.stat().st_size
                        zone_files += 1
                    except OSError:
                        pass
            data["used_bytes"] = zone_size
            data["file_count"] = zone_files
        except OSError:
            pass

        result[zone_name] = data

    return result


def get_data_dir() -> Path:
    """Basis-Datenverzeichnis (für Abwärtskompatibilität)."""
    return _DATA_DIR


def reload():
    """Konfiguration neu laden (z.B. nach API-Änderung)."""
    global _storage_config
    _storage_config = None
    _load_or_create()
