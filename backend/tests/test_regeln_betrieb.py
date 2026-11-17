"""Die harten Regeln (architektur/regeln.toml) greifen, und der Betrieb ist abgesichert (RAD-5, RAD-6): Muster der
verbotenen Regeln an Beispielzeilen, Compose-Dateien veröffentlichen nur den Vorschaltdienst, ein Container für die App
nicht als root, Vorschaltdienst ohne CORS-Köpfe. Die Schichtenregeln prüft der Appkern selbst (python -m appkern.werkzeuge
regeln)."""

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
    "P1": (["print(f'Start {x}')", "        print(\"fertig\")"],
           ["logger.info('Start %s', x)", "self.print_queue()", "blueprint(x)"]),
    "K1": (["os.environ.get('RADIOHUB_ZEITSTIMME')", "x = os.getenv('DATA_PATH')", "from os import getenv; getenv('X')"],
           ["einstellungen.stand().zeitstimme", "ort.daten_ordner()"]),
    "D1": (["c.execute('ALTER TABLE stations ADD COLUMN x TEXT')", "alter table blocklist add column y"],
           ["CREATE TABLE IF NOT EXISTS x (a)", "# die Spalte kommt mit Stufe 2"]),
    "D2": (["with db_session() as conn:", "c.execute('SELECT 1')", '"SELECT uuid FROM blocklist WHERE x"',
            "conn.execute(sql)", "DELETE FROM blocklist WHERE uuid = ?"],
           ["return await dienst.abfragen(q)", '"""Sender, die die Regel trifft (SELECT der Datenschicht)."""',
            "await senderquelle.sperren(uuid)"]),
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
    assert sorted(dienste) == ["radiohub", "vorne"]                  # ein Container für die App (RAD-6)
    assert dienste["radiohub"]["expose"] == ["8000"] and dienste["radiohub"]["user"] == "1000:1000"
    for name in ("radiohub", "vorne"):
        assert "no-new-privileges:true" in dienste[name]["security_opt"]
    assert "./data:/data" in dienste["radiohub"]["volumes"]               # die Daten bleiben, wo sie sind


def test_container_nicht_als_root():
    abbild = (WURZEL / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^USER 1000:1000$", abbild, re.MULTILINE)
    assert "ffmpeg" in abbild and "FROM python:3.12-slim" in abbild


def test_vorschaltdienst_ohne_cors_vor_der_app():
    caddy = (WURZEL / "deploy/Caddyfile").read_text(encoding="utf-8")
    assert "Access-Control-" not in caddy and "reverse_proxy radiohub:8000" in caddy
