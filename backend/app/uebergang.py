"""Übergang auf die Einstellungen des Appkerns (RAD-6): was vor Fassung 0.16 anders hieß oder anders stand, gilt
weiter, ohne dass auf dem Pi etwas umgestellt werden muss.

Umgebung (`alte_umgebung_uebernehmen`, beim Start vor dem Gerüst):

    RADIOHUB_KELLERWOLKE_SCHLUESSEL  nannte den Pfad einer Datei mit dem App-Schlüssel; steht dort ein Pfad statt eines
                                     Schlüssels, gilt der Inhalt der Datei
    (kein Schlüssel angegeben)       die frühere Vorgabe <Datenordner>/kellerwolke.schluessel, wenn es sie gibt
    RADIOHUB_KELLERWOLKE_CA          heißt jetzt RADIOHUB_CA_DATEI (gilt für Kellerwolke und Leitstelle)
    ALLOWED_ORIGINS                  heißt jetzt RADIOHUB_ERLAUBTE_URSPRUENGE (Liste als JSON statt durch Komma getrennt)

Ein Schlüssel, den das Ausrollen fest setzt (RADIOHUB_FEST_KELLERWOLKE_SCHLUESSEL), geht allem vor. Das Gerüst liest
die Umgebung bei jeder Änderung der Einstellungen neu; darum schreibt der Übergang die neuen Namen in die Umgebung
dieses Vorgangs (nie in eine Datei).

Tabelle config (`config_uebernehmen`, einmal beim ersten Start): Werte der Felder, die jetzt Einstellungen sind
(`einstellungen.CONFIG_FELDER`), gehen in die Einstellungen, sofern dort nicht schon einer gespeichert oder fest ist.
Die Zeilen der Tabelle bleiben stehen; gelesen werden diese Schlüssel danach nur noch aus den Einstellungen.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import MutableMapping
from pathlib import Path

from pydantic import ValidationError

from . import ort

log = logging.getLogger("radiohub.uebergang")

APP_PRAEFIX = "kw_app_"
SCHLUESSEL = "RADIOHUB_KELLERWOLKE_SCHLUESSEL"
FEST_SCHLUESSEL = "RADIOHUB_FEST_KELLERWOLKE_SCHLUESSEL"
ALTE_SCHLUESSELDATEI = "kellerwolke.schluessel"
UMBENANNT = {"RADIOHUB_KELLERWOLKE_CA": "RADIOHUB_CA_DATEI"}
URSPRUENGE = "RADIOHUB_ERLAUBTE_URSPRUENGE"


def _datei_lesen(pfad: Path) -> str | None:
    try:
        return pfad.expanduser().read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def alte_umgebung_uebernehmen(umgebung: MutableMapping[str, str] | None = None, daten: Path | None = None) -> list[str]:
    """Bringt die früheren Namen und Formen in die heutigen; liefert, was geschah (ohne Schlüssel). Mehrfach aufrufbar."""
    u = os.environ if umgebung is None else umgebung
    getan: list[str] = []
    for alt, neu in UMBENANNT.items():
        if u.get(alt, "").strip() and not u.get(neu, "").strip():
            u[neu] = u[alt].strip()
            getan.append(f"{alt} gilt als {neu}")
    urspruenge = [w.strip() for w in u.get("ALLOWED_ORIGINS", "").split(",") if w.strip()]
    if urspruenge and not u.get(URSPRUENGE, "").strip():
        u[URSPRUENGE] = json.dumps(urspruenge)
        getan.append(f"ALLOWED_ORIGINS gilt als {URSPRUENGE}")
    wert = u.get(SCHLUESSEL, "").strip()
    if wert and not wert.startswith(APP_PRAEFIX):
        inhalt = _datei_lesen(Path(wert))
        if inhalt is None:
            del u[SCHLUESSEL]
            getan.append(f"{SCHLUESSEL} nennt die Datei {wert}, die sich nicht lesen lässt; ohne Schlüssel weiter")
        else:
            u[SCHLUESSEL] = inhalt
            getan.append(f"{SCHLUESSEL}: Schlüssel aus der Datei {wert}")
    elif not wert and not u.get(FEST_SCHLUESSEL, "").strip():
        datei = (daten or ort.daten_ordner()) / ALTE_SCHLUESSELDATEI
        inhalt = _datei_lesen(datei)
        if inhalt is not None:
            u[SCHLUESSEL] = inhalt
            getan.append(f"Schlüssel der Kellerwolke aus der früheren Datei {datei}")
    for zeile in getan:
        log.info("Übergang: %s", zeile)
    return getan


def alte_config_lesen(db_pfad: Path, felder: frozenset[str]) -> dict[str, object]:
    """Die Werte der Tabelle config für `felder` (JSON wie früher; nicht lesbare Werte als Text)."""
    if not db_pfad.is_file():
        return {}
    v = sqlite3.connect(f"{db_pfad.resolve().as_uri()}?mode=ro", uri=True)
    try:
        if not v.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='config'").fetchone():
            return {}
        werte: dict[str, object] = {}
        for schluessel, roh in v.execute("SELECT key, value FROM config"):
            if schluessel in felder:
                try:
                    werte[schluessel] = json.loads(roh)
                except (TypeError, ValueError):
                    werte[schluessel] = roh
        return werte
    finally:
        v.close()


async def config_uebernehmen(einstellungen, db_pfad: Path, felder: frozenset[str]) -> tuple[list[str], list[str]]:
    """Übernimmt die Werte aus der Tabelle config in `einstellungen` (appkern.einstellungen.Einstellungen), je Feld
    einzeln: ein ungültiger Wert hält die übrigen nicht auf. Liefert (übernommen, übergangen mit Grund)."""
    uebernommen: list[str] = []
    uebergangen: list[str] = []
    for name, wert in sorted(alte_config_lesen(db_pfad, felder).items()):
        if einstellungen.herkunft(name) in ("gespeichert", "fest"):
            continue
        try:
            await einstellungen.aendern({name: wert})
        except (ValidationError, ValueError) as f:
            uebergangen.append(f"{name}: {f}".splitlines()[0])
            continue
        uebernommen.append(name)
    return uebernommen, uebergangen
