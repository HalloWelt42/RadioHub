"""Probebetrieb für Rauchtests der Oberfläche, nur am eigenen Rechner: die ganze App auf 127.0.0.1 mit einer KOPIE der
Daten, Ablage im Speicher und nachgestellter Kellerwolke wie in den Tests (conftest.py). Anmelden mit beliebiger
Kennung und dem Passwort "geheim"; ein echter Dienst wird nie gefragt.

    RADIOHUB_DATEN=/pfad/zur/kopie .venv/bin/python tests/probebetrieb.py [port]      (im Ordner backend, Vorgabe 9091)

Der Datenordner muss ausdrücklich angegeben sein und darf weder der Ordner des Repos noch der des Betriebs sein; so
landet keine Änderung des Rauchtests in echten Daten.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

SITZUNG = "sitzung-probebetrieb"
PASSWORT = "geheim"
KONTO = {"id": "1", "name": "probe", "rolle": "mitglied", "aktiv": True}


def kellerwolke(request: httpx.Request) -> httpx.Response:
    """Kellerwolke zum Schein: der App-Schlüssel gehört dem Konto probe, angemeldet ist, wer `SITZUNG` mitbringt."""
    pfad = request.url.path
    if pfad == "/api/v1/ablage/ich":
        return httpx.Response(200, json={"app": "RadioHub", "konto": "probe", "rechte": []})
    if pfad == "/api/v1/auth/login":
        if json.loads(request.content)["passwort"] != PASSWORT:
            return httpx.Response(401, json={"detail": "Anmeldung fehlgeschlagen"})
        return httpx.Response(200, json={"token": SITZUNG, "benutzer": KONTO})
    if pfad == "/api/v1/auth/status":
        ok = request.headers.get("x-kellerwolke-sitzung") == SITZUNG
        return httpx.Response(200, json={"angemeldet": ok, "benutzer": KONTO if ok else None})
    return httpx.Response(404, json={"detail": "nicht da"})


def datenordner() -> Path:
    wert = os.environ.get("RADIOHUB_DATEN", "")
    if not wert:
        raise SystemExit("RADIOHUB_DATEN fehlt: nur mit einer Kopie der Daten starten")
    daten = Path(wert).resolve()
    if daten == (HIER.parents[1] / "data").resolve() or str(daten).startswith("/mnt/"):
        raise SystemExit(f"{daten} ist kein Probeordner")
    return daten


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9091
    daten = datenordner()
    os.environ["RADIOHUB_SICHERUNGEN"] = str(daten / "sicherungen")
    os.environ["RADIOHUB_KELLERWOLKE_ADRESSE"] = "https://kellerwolke.test"
    os.environ["RADIOHUB_KELLERWOLKE_SCHLUESSEL"] = "kw_app_probe"
    for name in ("DATA_PATH", "STORAGE_CONFIG", "RADIOHUB_ERLAUBTE_URSPRUENGE", "ALLOWED_ORIGINS"):
        os.environ.pop(name, None)

    import uvicorn

    from app import ablage
    from app.ablage import SpeicherAblage
    from app.main import app_bauen

    ablage.vorgeben(SpeicherAblage())
    uvicorn.run(app_bauen(daten, transport=httpx.MockTransport(kellerwolke)), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
