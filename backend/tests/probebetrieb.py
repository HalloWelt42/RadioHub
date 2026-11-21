"""Probebetrieb für Rauchtests der Oberfläche, nur am eigenen Rechner: die ganze App auf 127.0.0.1 mit einer KOPIE der
Daten, Ablage im Speicher und nachgestellter Kellerwolke wie in den Tests (conftest.py). Anmelden mit beliebiger
Kennung und dem Passwort "geheim"; ein echter Dienst wird nie gefragt. Damit Hören, Wellenform und Schnitt etwas zu
tun haben, bekommt jedes Stück der Aufnahmen in der Kopie einen erzeugten Ton in der Testablage, und die nachgestellte
Kellerwolke hat einige Ordner mit Audiodateien (RAD-17), die zuletzt gespeicherten Podcast-Folgen bekommen kurze Töne
(RAD-32); die Töne liegen zwischengespeichert im Datenordner.

    RADIOHUB_DATEN=/pfad/zur/kopie .venv/bin/python tests/probebetrieb.py [port]      (im Ordner backend, Vorgabe 9091)

Der Datenordner muss ausdrücklich angegeben sein und darf weder der Ordner des Repos noch der des Betriebs sein; so
landet keine Änderung des Rauchtests in echten Daten.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
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


def ton(ziel: Path, sekunden: float, frequenz: int) -> Path:
    """Ton mit wechselnder Lautstärke (die Wellenform zeigt etwas), Format nach der Endung; einmal erzeugt, dann gemerkt."""
    if not ziel.exists():
        ziel.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-f", "lavfi", "-i", f"sine=frequency={frequenz}:duration={sekunden:.1f}",
                        "-af", "volume='0.25+0.75*abs(sin(t/2.3))':eval=frame", "-b:a", "96k", str(ziel)], check=True)
    return ziel


WOLKE = {   # Pfad in der nachgestellten Kellerwolke: (Sekunden, Frequenz)
    "Musik/Konzerte/Probe im Keller.mp3": (95, 330), "Musik/Konzerte/Zugabe.mp3": (40, 440),
    "Musik/Mitschnitte 2025/Sommerfest.mp3": (150, 262), "Hörspiele/Die Kiste, Folge 1.mp3": (120, 196),
}


async def toene_hinlegen(speicher, wolke, daten: Path) -> None:
    """Jedem Stück der Aufnahmen und den Dateien der Kellerwolke einen Ton geben (nur in den Testablagen)."""
    lager = daten / "probetoene"
    with sqlite3.connect(daten / "radiohub.db") as db:
        stuecke = db.execute("SELECT id, file_path, duration_ms FROM segments WHERE file_path IS NOT NULL").fetchall()
        gespeichert = db.execute("SELECT id, local_path, duration FROM podcast_episodes WHERE is_downloaded = 1 AND local_path != '' "
                                 "ORDER BY id DESC LIMIT 20").fetchall()
    for kennung, pfad, dauer in stuecke:
        endung = Path(pfad).suffix or ".mp3"
        await speicher.ablegen(pfad, ton(lager / f"stueck_{kennung}{endung}", min(max((dauer or 10000) / 1000, 2), 600), 220 + kennung % 7 * 55))
    for kennung, pfad, dauer in gespeichert:          # gespeicherte Folgen (RAD-32): kurz, damit der Start schnell bleibt
        endung = Path(pfad).suffix or ".mp3"
        await speicher.ablegen(pfad, ton(lager / f"folge_{kennung}{endung}", min(max(dauer or 60, 20), 180), 180 + kennung % 5 * 70))
    for pfad, (sekunden, frequenz) in WOLKE.items():
        await wolke.ablegen(pfad, ton(lager / "wolke" / Path(pfad).name, sekunden, frequenz))
    nicht_audio = lager / "Brief.txt"
    nicht_audio.write_text("kein Ton")
    await wolke.ablegen("Dokumente/Brief.txt", nicht_audio)


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

    speicher, wolke = ablage.vorgeben(SpeicherAblage()), ablage.wolke_setzen(SpeicherAblage())
    asyncio.run(toene_hinlegen(speicher, wolke, daten))
    uvicorn.run(app_bauen(daten, transport=httpx.MockTransport(kellerwolke)), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
