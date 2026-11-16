"""RadioHub: Internetradio, Podcasts, Aufnahmen und Wecker. Backend auf dem Gerüst des Appkerns (RAD-6).

    uvicorn app.main:app --port 9091          (im Ordner backend)

Das Gerüst bringt Einstellungen, Protokoll, Aufträge, Anmeldung mit dem Konto der Kellerwolke, Sicherung und die
Auslieferung der gebauten Oberfläche mit; der Betrieb des Radios hängt als Begleiter daran (`betrieb.Radiobetrieb`).
Alle Wege unter /api brauchen eine Anmeldung, außer denen, die das Gerüst freigibt (Fassung und Zustand unter
/api/v1/app, Anmeldung, erste Einrichtung); frei ist dazu nur die Gesundheitsprobe /health. Ton, Bilder und
Ereignisströme, die der Browser ohne eigenen Kopf holt, kommen mit dem Lesezugang (Keks des Gerüsts, gilt unter /api).

© HalloWelt42 - Nur für private Nutzung
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from appkern.app import Geruest
from appkern.app.sicherung import RegelmaessigeSicherung, regel_aus
from appkern.sicherung import Ablage as Sicherungsablage

from . import einstellungen, ort, uebergang
from .ablage import AblageFehler, Belegt, NichtEingerichtet, NichtErreichbar, NichtGefunden
from .betrieb import Radiobetrieb
from .config import DB_PATH, VERSION, erlaubte_urspruenge
from .database import datenbank_erreichbar, datenbank_pruefen
from .einstellungen import KENNUNG, AppEinstellungen
from .routers import ALLE
from .services import rec_manager
from .services.aufnahmen import AufnahmeFehler
from .services.durchleiter import DurchleiterFehler
from .services.hls_recorder import hls_recorder

OBERFLAECHE = ort.WURZEL / "radiohub-frontend" / "dist"
LESEZUGANG = "/api"        # unter diesem Pfad gilt der Keks des Lesezugangs (Ton, Bilder, Ereignisströme)

# Fehler der Ablage als HTTP-Status mit lesbarer Meldung
_ABLAGE_STATUS = ((NichtGefunden, 404), (Belegt, 409), (NichtEingerichtet, 503), (NichtErreichbar, 503))


def _fehler_behandeln(app: FastAPI) -> None:
    @app.exception_handler(AblageFehler)
    async def _ablage_fehler(request: Request, fehler: AblageFehler):
        status = next((code for art, code in _ABLAGE_STATUS if isinstance(fehler, art)), 502)
        return JSONResponse(status_code=status, content={"detail": str(fehler)})

    @app.exception_handler(AufnahmeFehler)
    async def _aufnahme_fehler(request: Request, fehler: AufnahmeFehler):
        return JSONResponse(status_code=fehler.status, content={"detail": str(fehler)})

    @app.exception_handler(DurchleiterFehler)
    async def _durchleiter_fehler(request: Request, fehler: DurchleiterFehler):
        return JSONResponse(status_code=fehler.status, content={"detail": str(fehler)})


def _log_einrichten() -> None:
    """Das Log des Radios (Logger radiohub.*) auf die Standardausgabe des Containers (docker compose logs), ab Stufe
    info; Uvicorn und Appkern melden über die Wurzel nur Warnungen. Wichtige Ereignisse stehen zusätzlich im
    Protokoll der App (Seite Protokoll, /api/v1/protokoll)."""
    radio = logging.getLogger("radiohub")
    if not radio.handlers:
        ausgabe = logging.StreamHandler(sys.stdout)
        ausgabe.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        radio.addHandler(ausgabe)
        radio.setLevel(logging.INFO)
        radio.propagate = False


def app_bauen(daten: Path, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    """`daten`: Datenordner (das Gerüst hält seins im Unterordner appkern). `transport` nur für Tests (Kellerwolke
    nachgestellt)."""
    _log_einrichten()
    uebergang.alte_umgebung_uebernehmen(daten=daten)
    geruest = Geruest(name="RadioHub", kennung=KENNUNG, rolle="spielt Radio und Podcasts, nimmt auf und weckt",
                      symbol="fa-radio", symbolbild="/favicon.svg", farbe="#222222", fassung=VERSION,
                      daten=ort.geruest_ordner(daten), einstellungen=AppEinstellungen, oberflaeche=OBERFLAECHE,
                      sicherungen=ort.sicherungen_ordner() / ort.GERUEST, seiten=(LESEZUGANG,), transport=transport)
    betrieb = Radiobetrieb(geruest)
    # die große Datenbank des Radios nach derselben Regel wie die des Gerüsts, im Ordner, in den auch das Ausrollen sichert
    radio_sicherung = RegelmaessigeSicherung(Sicherungsablage(DB_PATH, ort.sicherungen_ordner(), KENNUNG),
                                             lambda: regel_aus(geruest.einstellungen.stand))
    geruest.begleiter_anmelden(betrieb, radio_sicherung)

    app = geruest.fastapi()
    app.state.geruest = geruest
    app.state.betrieb = betrieb
    _fehler_behandeln(app)
    # Kein CORS: die Oberfläche spricht /api über denselben Ursprung; fremde Ursprünge nur, wenn die Einstellung
    # erlaubte_urspruenge sie ausdrücklich nennt (nie "*"), gelesen beim Start
    urspruenge = erlaubte_urspruenge(",".join(einstellungen.stand().erlaubte_urspruenge))
    if urspruenge:
        app.add_middleware(CORSMiddleware, allow_origins=urspruenge, allow_credentials=True, allow_methods=["*"],
                           allow_headers=["*"])
    for router in ALLE:
        app.include_router(router, dependencies=[geruest.lesen])

    @app.get("/health")
    async def health():
        """Gesundheitsprobe für Docker und Ausrollen (ohne Anmeldung): Fassung, ob die Datenbank antwortet (SELECT 1,
        keine volle Prüfung) und ob gerade eine Aufnahme läuft (das Ausrollen wartet sie ab, nur ja oder nein)."""
        db = {"status": "error", "error": betrieb.datenbank_fehler} if betrieb.datenbank_fehler \
            else await asyncio.to_thread(datenbank_erreichbar)
        aufnahme = bool(rec_manager.get_status().get("recording") or hls_recorder.get_status().get("recording"))
        return {"status": "healthy" if db["status"] == "healthy" else "degraded", "version": VERSION,
                "database": db["status"], "aufnahme": aufnahme}

    @app.get("/api/datenbank/pruefung", dependencies=[geruest.pflicht])
    async def datenbank_pruefung():
        """Volle Prüfung der Datenbank (integrity_check über die ganze Datei); läuft neben der Ereignisschleife"""
        return await asyncio.to_thread(datenbank_pruefen)

    geruest.oberflaeche_ausliefern(app)
    return app


app = app_bauen(ort.daten_ordner())
