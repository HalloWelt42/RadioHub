"""
RadioHub Storage Zone Manager v1.0.0

Verwaltet konfigurierbare Speicher-Zonen fuer verschiedene Datentypen.
Ermoeglicht es, Datenbank, Cache, Aufnahmen und Podcasts auf
verschiedene Laufwerke/Pfade zu verteilen.

Konfiguration: storage.json
Prioritaet: STORAGE_CONFIG Env > {DATA_PATH}/storage.json > Defaults

Zonen:
  database   - SQLite-Datei (SSD empfohlen)
  cache      - HLS-Buffer, temporaere Dateien (SSD empfohlen)
  recordings - Radio-Aufnahmen (HDD reicht)
  podcasts   - Podcast-Downloads + Cover (HDD reicht)
  config     - App-Einstellungen (SSD empfohlen)
"""
import os
import json
import shutil
from pathlib import Path
from typing import Optional


# === Basis-Datenverzeichnis (gleiche Logik wie bisheriges config.py) ===
_DATA_DIR = Path(os.getenv("DATA_PATH", str(Path(__file__).resolve().parent.parent / "data")))

# Standardstruktur (matcht bestehende Verzeichnisstruktur exakt)
_DEFAULT_ZONE_SUBDIRS = {
    "database": "",                     # radiohub.db liegt direkt in DATA_DIR
    "cache": "cache",                   # HLS-Buffer, Temp
    "recordings": "recordings/radio",   # Radio-Aufnahmen
    "podcasts": "recordings/podcasts",  # Podcast-Downloads + Cover
    "config": "",                       # App-Einstellungen (in DATA_DIR)
}

# Zone-Beschreibungen fuer die UI
ZONE_INFO = {
    "database": {
        "label": "Datenbank",
        "description": "SQLite-Datei, klein, braucht schnelle I/O",
        "icon": "fa-database",
        "recommended": "SSD",
    },
    "cache": {
        "label": "Cache / Buffer",
        "description": "HLS-Buffer, temporaere Dateien",
        "icon": "fa-bolt",
        "recommended": "SSD",
    },
    "recordings": {
        "label": "Aufnahmen",
        "description": "Radio-Aufnahmen, grosse Dateien",
        "icon": "fa-record-vinyl",
        "recommended": "HDD",
    },
    "podcasts": {
        "label": "Podcasts",
        "description": "Podcast-Downloads und Cover-Bilder",
        "icon": "fa-podcast",
        "recommended": "HDD",
    },
    "config": {
        "label": "Konfiguration",
        "description": "App-Einstellungen und Praeferenzen",
        "icon": "fa-gear",
        "recommended": "SSD",
    },
}

_storage_config: Optional[dict] = None


def _find_config_path() -> Optional[Path]:
    """Sucht storage.json in Prioritaetsreihenfolge"""
    # 1. STORAGE_CONFIG Env-Variable
    env_path = os.getenv("STORAGE_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    # 2. {DATA_PATH}/storage.json
    data_path = _DATA_DIR / "storage.json"
    if data_path.exists():
        return data_path
    return None


def _load_or_create() -> dict:
    """Laedt oder erstellt Storage-Konfiguration"""
    global _storage_config
    if _storage_config is not None:
        return _storage_config

    config_path = _find_config_path()

    if config_path:
        with open(config_path, "r") as f:
            _storage_config = json.load(f)
        # Fehlende Zonen mit Defaults ergaenzen
        zones = _storage_config.setdefault("zones", {})
        for zone, subdir in _DEFAULT_ZONE_SUBDIRS.items():
            if zone not in zones:
                default_path = str(_DATA_DIR / subdir) if subdir else str(_DATA_DIR)
                zones[zone] = {"path": default_path}
    else:
        # Neue Default-Config erstellen
        _storage_config = {
            "version": 1,
            "zones": {},
        }
        for zone, subdir in _DEFAULT_ZONE_SUBDIRS.items():
            default_path = str(_DATA_DIR / subdir) if subdir else str(_DATA_DIR)
            _storage_config["zones"][zone] = {"path": default_path}
        _save_config()

    # Verzeichnisse erstellen
    for zone_info in _storage_config["zones"].values():
        try:
            Path(zone_info["path"]).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Pfad evtl. nicht erreichbar (Docker-Volume noch nicht gemounted)

    return _storage_config


def _save_config():
    """Speichert storage.json"""
    if _storage_config is None:
        return

    env_path = os.getenv("STORAGE_CONFIG")
    save_path = Path(env_path) if env_path else _DATA_DIR / "storage.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(save_path, "w") as f:
        json.dump(_storage_config, f, indent=2, ensure_ascii=False)


# ============================================================
#  Oeffentliche API
# ============================================================

def get_zone_path(zone: str) -> Path:
    """Gibt den Pfad einer Storage-Zone zurueck.

    Args:
        zone: Name der Zone (database, cache, recordings, podcasts, config)

    Returns:
        Path-Objekt zum Zone-Verzeichnis
    """
    config = _load_or_create()
    zones = config.get("zones", {})
    if zone not in zones:
        raise ValueError(f"Unbekannte Storage-Zone: {zone}")
    return Path(zones[zone]["path"])


def get_all_zones() -> dict:
    """Alle Zonen mit Pfad, Speicherplatz, Status und Meta-Info."""
    config = _load_or_create()
    result = {}

    for zone_name, zone_conf in config.get("zones", {}).items():
        path = Path(zone_conf["path"])
        meta = ZONE_INFO.get(zone_name, {})

        data = {
            "path": str(path),
            "label": meta.get("label", zone_name),
            "description": meta.get("description", ""),
            "icon": meta.get("icon", "fa-folder"),
            "recommended": meta.get("recommended", ""),
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

            # Dateien in Zone zaehlen
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


def update_zone(zone: str, new_path: str) -> dict:
    """Zone-Pfad aendern.

    WICHTIG: Verschiebt keine Daten! Der alte Pfad bleibt erhalten.
    Der Nutzer muss Daten selbst verschieben oder den
    "Daten verschieben"-Button nutzen (wenn implementiert).

    Args:
        zone: Name der Zone
        new_path: Neuer absoluter Pfad

    Returns:
        Aktualisierte Zone-Info

    Raises:
        ValueError: Unbekannte Zone
        PermissionError: Pfad nicht beschreibbar
    """
    config = _load_or_create()
    zones = config.get("zones", {})

    if zone not in zones:
        raise ValueError(f"Unbekannte Zone: {zone}")

    path = Path(new_path)
    path.mkdir(parents=True, exist_ok=True)

    if not os.access(path, os.W_OK):
        raise PermissionError(f"Pfad nicht beschreibbar: {new_path}")

    zones[zone]["path"] = str(path.resolve())
    _save_config()

    return {"path": str(path.resolve()), "zone": zone}


def validate_path(path: str) -> dict:
    """Prueft ob ein Pfad als Zone-Speicher geeignet ist.

    Args:
        path: Zu pruefender Pfad

    Returns:
        Dict mit exists, writable, free_bytes, total_bytes, error
    """
    p = Path(path)
    result = {
        "path": str(p),
        "exists": p.exists(),
        "writable": False,
        "free_bytes": 0,
        "total_bytes": 0,
    }
    try:
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            result["created"] = True
        result["exists"] = True
        result["writable"] = os.access(p, os.W_OK)
        total, used, free = shutil.disk_usage(p)
        result["free_bytes"] = free
        result["total_bytes"] = total
    except OSError as e:
        result["error"] = str(e)
    return result


def get_data_dir() -> Path:
    """Basis-Datenverzeichnis (fuer Abwaertskompatibilitaet)."""
    return _DATA_DIR


def reload():
    """Konfiguration neu laden (z.B. nach API-Aenderung)."""
    global _storage_config
    _storage_config = None
    _load_or_create()
