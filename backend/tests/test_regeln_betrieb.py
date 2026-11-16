"""Die harten Regeln (architektur/regeln.toml) greifen, und der Betrieb ist abgesichert (RAD-5): Muster der verbotenen
Regeln an Beispielzeilen, Compose-Dateien veröffentlichen nur den Vorschaltdienst, Container nicht als root, nginx
ohne CORS-Köpfe. Die Schichtenregeln prüft der Appkern selbst (python -m appkern.werkzeuge regeln)."""

import re
import tomllib
from pathlib import Path

import pytest
import yaml

WURZEL = Path(__file__).resolve().parents[2]
REGELN = {r["kennung"]: r for r in tomllib.loads((WURZEL / "architektur/regeln.toml").read_text(encoding="utf-8"))["regel"]}

# Regel: (Zeilen, die anschlagen müssen, Zeilen, die durchgehen)
BEISPIELE = {
    "G1": (['<link href="https://fonts.googleapis.com/css2?family=Barlow">', "import x from 'https://unpkg.com/x';"],
           ["import '@fontsource/barlow';"]),
    "G2": (["alert('x');", "if (window.confirm('Löschen?')) {", "const n = prompt('Name');"],
           ["actions.confirm('x');", "onConfirm(true);", "zeigePrompt()"]),
    "G3": (['VERSION = "0.8.0"', "version: '1.2.3',", '"version": "0.14.3",'],
           ["VERSION = FASSUNG", "version: FASSUNG,"]),
    "B1": (["return `${b}/api/stream/proxy?url=${u}`;", "api.getStreamProxyUrl(url)", '@router.get("/stream/proxy")'],
           ["api.getStationStreamUrl(station.uuid)", '@router.get("/stream/sender/{uuid}")']),
    "B2": (["httpx.AsyncClient(verify=False)", "ctx.check_hostname = False", "ssl._create_unverified_context()"],
           ["httpx.AsyncClient(verify=tls_pruefung(ca))", "ssl.create_default_context()"]),
    "B3": (["fetch('https://raw.githubusercontent.com/x/y/main/package.json')", "fetch('https://api.github.com/repos/x')"],
           ['<a href="https://github.com/HalloWelt42/RadioHub">']),
    "B4": (["      - ALLOWED_ORIGINS=*", "    add_header Access-Control-Allow-Origin *;", 'allow_origins=["*"],', "    cors: true,"],
           ["      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-}", "allow_origins=_urspruenge,"]),
    "B5": (['      - "9091:8000"', '      - "127.0.0.1:9092:8080"', "      - 9092:80"],
           ['      - "9093:9093"', '      - "8000"', '      - "127.0.0.1:${PROBE_PORT:?}:9093"']),
}


@pytest.mark.parametrize("kennung", sorted(BEISPIELE))
def test_verbotene_muster_greifen(kennung):
    muster = re.compile(REGELN[kennung]["muster"])
    treffer, frei = BEISPIELE[kennung]
    assert all(muster.search(z) for z in treffer), kennung
    assert not any(muster.search(z) for z in frei), kennung


def test_jede_verbotene_regel_hat_beispiele():
    assert {k for k, r in REGELN.items() if r["art"] == "verboten"} == set(BEISPIELE)


@pytest.mark.parametrize("datei", ["compose.pi.yml", "docker-compose.yml"])
def test_nur_der_vorschaltdienst_ist_veroeffentlicht(datei):
    dienste = yaml.safe_load((WURZEL / datei).read_text(encoding="utf-8"))["services"]
    assert [n for n, d in dienste.items() if d.get("ports")] == ["vorne"]
    assert [p.split(":")[-1] for p in dienste["vorne"]["ports"]] == ["9093"]
    assert dienste["radiohub-backend"]["expose"] == ["8000"] and dienste["radiohub-frontend"]["expose"] == ["8080"]
    for name in ("radiohub-backend", "radiohub-frontend", "vorne"):
        assert "no-new-privileges:true" in dienste[name]["security_opt"]


def test_container_nicht_als_root():
    backend = (WURZEL / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^USER 1000:1000$", backend, re.MULTILINE)
    oberflaeche = (WURZEL / "radiohub-frontend/Dockerfile").read_text(encoding="utf-8")
    letzte_stufe = oberflaeche.rsplit("\nFROM ", 1)[1]
    assert letzte_stufe.startswith("nginxinc/nginx-unprivileged:")


def test_nginx_ohne_cors_und_vorschaltdienst_auf_8080():
    nginx = (WURZEL / "radiohub-frontend/nginx.conf").read_text(encoding="utf-8")
    assert "Access-Control-" not in nginx and "listen 8080;" in nginx
    assert "reverse_proxy radiohub-frontend:8080" in (WURZEL / "deploy/Caddyfile").read_text(encoding="utf-8")
