"""Wo das RadioHub seine Dateien hält: die einzige Stelle, die Orte aus der Umgebung liest (alle übrigen Einstellungen
kommen aus `einstellungen`, RAD-6).

    RADIOHUB_DATEN          Datenordner (im Container /data); früher DATA_PATH, das weiter gilt
    RADIOHUB_SICHERUNGEN    Ordner der Sicherungen (im Container /sicherungen)
    STORAGE_CONFIG          Datei der Speicherzonen außerhalb des Datenordners (nur bei mehreren Laufwerken)

Ohne Angabe liegen Daten und Sicherungen in `data/` und `sicherungen/` im Wurzelordner des Repos (beim Entwickeln).
Was das Gerüst des Appkerns hält (Einstellungen, Protokoll, Aufträge, Einrichtungscode), liegt im Unterordner
`appkern` des Datenordners, getrennt von `radiohub.db`.
"""
from __future__ import annotations

import os
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
GERUEST = "appkern"


def daten_ordner() -> Path:
    return Path(os.environ.get("RADIOHUB_DATEN") or os.environ.get("DATA_PATH") or WURZEL / "data")


def sicherungen_ordner() -> Path:
    return Path(os.environ.get("RADIOHUB_SICHERUNGEN") or WURZEL / "sicherungen")


def geruest_ordner(daten: Path | None = None) -> Path:
    """Datenordner des Gerüsts (seine Datenbank heißt dort radiohub.sqlite)."""
    return (daten or daten_ordner()) / GERUEST


def speicherzonen_datei() -> Path | None:
    wert = os.environ.get("STORAGE_CONFIG")
    return Path(wert) if wert else None
