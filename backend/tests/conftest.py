"""Gemeinsame Vorbereitung: eigener Datenordner (nie der echte), Testablage im Speicher, Ton aus ffmpeg, eine
nachgestellte Kellerwolke für Einrichtung und Anmeldung (RAD-6: alle Wege unter /api brauchen eine Anmeldung).

`client` ist angemeldet (Kopf X-Kellerwolke-Sitzung mit `SITZUNG`), `anonym` nicht; beide starten die ganze App mit
ihrem Betrieb (Datenbank in Stufen, Ablage, Dienste).

Mit RADIOHUB_PROBE_KELLERWOLKE=1 und den Einstellungen der Kellerwolke (RADIOHUB_KELLERWOLKE_ADRESSE, ..._SCHLUESSEL,
..._WURZEL, RADIOHUB_CA_DATEI) laufen die Prüfungen der Ablage zusätzlich gegen eine echte Kellerwolke (nur in einem
eigenen Probeordner als Wurzel, der danach in den Papierkorb geht).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx
import pytest

PROBE = os.environ.get("RADIOHUB_PROBE_KELLERWOLKE") == "1"
SITZUNG = "sitzung-probe"
KELLERWOLKE = "https://kellerwolke.test"
APP_SCHLUESSEL = "kw_app_probe"

_DATEN = Path(tempfile.mkdtemp(prefix="radiohub-test-"))
os.environ["RADIOHUB_DATEN"] = str(_DATEN)
os.environ["RADIOHUB_SICHERUNGEN"] = str(_DATEN / "sicherungen")
for _name in ("DATA_PATH", "STORAGE_CONFIG", "ALLOWED_ORIGINS", "RADIOHUB_ERLAUBTE_URSPRUENGE"):
    os.environ.pop(_name, None)
for _name in [n for n in os.environ if n.startswith("RADIOHUB_FEST_")]:
    os.environ.pop(_name)
if not PROBE:
    os.environ["RADIOHUB_KELLERWOLKE_ADRESSE"] = KELLERWOLKE
    os.environ["RADIOHUB_KELLERWOLKE_SCHLUESSEL"] = APP_SCHLUESSEL

from app import database, ort  # noqa: E402
from app import ablage as ablage_paket  # noqa: E402
from app.ablage import SpeicherAblage  # noqa: E402

asyncio.run(database.einrichten())   # legt die Datenbank im Testordner an, bevor Dienste sie lesen


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_DATEN, ignore_errors=True)


def kellerwolke(request: httpx.Request) -> httpx.Response:
    """Kellerwolke zum Schein: der App-Schlüssel gehört dem Konto probe, angemeldet ist, wer `SITZUNG` mitbringt."""
    pfad = request.url.path
    if pfad == "/api/v1/ablage/ich":
        return httpx.Response(200, json={"app": "RadioHub", "konto": "probe", "rechte": []})
    if pfad == "/api/v1/auth/login":
        if json.loads(request.content)["passwort"] != "geheim":
            return httpx.Response(401, json={"detail": "Anmeldung fehlgeschlagen"})
        return httpx.Response(200, json={"token": SITZUNG, "benutzer": {"id": "1", "name": "probe", "rolle": "mitglied",
                                                                        "aktiv": True}})
    if pfad == "/api/v1/auth/status":
        ok = request.headers.get("x-kellerwolke-sitzung") == SITZUNG
        return httpx.Response(200, json={"angemeldet": ok, "benutzer": {"id": "1", "name": "probe", "rolle": "mitglied",
                                                                        "aktiv": True} if ok else None})
    return httpx.Response(404, json={"detail": "nicht da"})


def app_bauen():
    from app.main import app_bauen as bauen
    return bauen(ort.daten_ordner(), transport=httpx.MockTransport(kellerwolke))


@pytest.fixture
def speicher() -> SpeicherAblage:
    """Frische Testablage, die für App und Dienste gilt."""
    return ablage_paket.vorgeben(SpeicherAblage())


@pytest.fixture
def client(speicher):
    from fastapi.testclient import TestClient
    with TestClient(app_bauen(), headers={"X-Kellerwolke-Sitzung": SITZUNG}) as c:
        yield c


@pytest.fixture
def anonym(speicher):
    from fastapi.testclient import TestClient
    with TestClient(app_bauen()) as c:
        yield c


def ton(ziel: Path, sekunden: float = 6.0, frequenz: int = 440) -> Path:
    """Kurzer Sinuston als MP3."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-f", "lavfi", "-i", f"sine=frequency={frequenz}:duration={sekunden}",
                    "-c:a", "libmp3lame", "-b:a", "64k", str(ziel)], check=True)
    return ziel


@pytest.fixture
def tonquelle(tmp_path) -> Path:
    return ton(tmp_path / "quelle.mp3")
