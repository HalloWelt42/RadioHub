"""Eine Fassung: version.json im Wurzelordner ist die einzige Quelle; Server, Schnittstellenbeschreibung und /health
melden sie (RAD-5)."""

import json
from pathlib import Path

from app.fassung import FASSUNG, fassung_datei, fassung_lesen

WURZEL = Path(__file__).resolve().parents[2]


def test_fassung_kommt_aus_version_json_im_wurzelordner():
    assert fassung_datei() == WURZEL / "version.json"
    assert FASSUNG == json.loads((WURZEL / "version.json").read_text())["version"]


def test_naechste_version_json_oberhalb_gilt(tmp_path):
    (tmp_path / "version.json").write_text(json.dumps({"version": "9.8.7", "id": "abc123", "voll": "v9.8.7-abc123"}))
    paket = tmp_path / "backend"
    paket.mkdir()
    assert fassung_datei(paket) == tmp_path / "version.json"
    assert fassung_lesen(fassung_datei(paket)) == "9.8.7"


def test_server_meldet_die_fassung(client):
    assert client.get("/health").json()["version"] == FASSUNG
    assert client.get("/openapi.json").json()["info"]["version"] == FASSUNG
