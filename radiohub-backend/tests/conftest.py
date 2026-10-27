"""Gemeinsame Vorbereitung: eigener Datenordner (nie der echte), Testablage im Speicher, Ton aus ffmpeg.

Mit RADIOHUB_PROBE_KELLERWOLKE=1 und den Einstellungen der Ablage (RADIOHUB_KELLERWOLKE_ADRESSE, ..._SCHLUESSEL,
..._WURZEL, ..._CA) laufen die Prüfungen der Schnittstelle zusätzlich gegen eine echte Kellerwolke (nur in einem
eigenen Probeordner als Wurzel, der danach in den Papierkorb geht).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

_DATEN = Path(tempfile.mkdtemp(prefix="radiohub-test-"))
os.environ["DATA_PATH"] = str(_DATEN)
os.environ.pop("STORAGE_CONFIG", None)

import backend.main  # noqa: E402,F401  legt die Datenbank im Testordner an, bevor Dienste sie lesen
from backend import ablage as ablage_paket  # noqa: E402
from backend.ablage import SpeicherAblage  # noqa: E402


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_DATEN, ignore_errors=True)


@pytest.fixture
def speicher() -> SpeicherAblage:
    """Frische Testablage, die für App und Dienste gilt."""
    return ablage_paket.vorgeben(SpeicherAblage())


@pytest.fixture
def client(speicher):
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


def ton(ziel: Path, sekunden: float = 6.0, frequenz: int = 440) -> Path:
    """Kurzer Sinuston als MP3."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-f", "lavfi", "-i", f"sine=frequency={frequenz}:duration={sekunden}",
                    "-c:a", "libmp3lame", "-b:a", "64k", str(ziel)], check=True)
    return ziel


@pytest.fixture
def tonquelle(tmp_path) -> Path:
    return ton(tmp_path / "quelle.mp3")
