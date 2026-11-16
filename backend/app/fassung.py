"""Fassung der App aus version.json, der einzigen Quelle ({version, id, voll}, gezählt vom Git-Haken).

Gesucht wird die nächste version.json oberhalb dieses Pakets: im Repo liegt sie im Wurzelordner, im Abbild des Backends
neben dem Paket (/app/version.json, siehe Dockerfile).
"""

import json
from pathlib import Path


def fassung_datei(start: Path = Path(__file__).resolve().parent) -> Path:
    for ordner in (start, *start.parents):
        datei = ordner / "version.json"
        if datei.is_file():
            return datei
    raise FileNotFoundError(f"version.json fehlt oberhalb von {start}")


def fassung_lesen(datei: Path | None = None) -> str:
    return json.loads((datei or fassung_datei()).read_text(encoding="utf-8"))["version"]


FASSUNG: str = fassung_lesen()
