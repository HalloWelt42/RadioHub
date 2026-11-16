"""
RadioHub Backend - HLS Timeshift Buffer

Internet Radio & Podcast Player mit HLS-basiertem Time-Shift
© HalloWelt42 - Nur für private Nutzung
"""
import os
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import DATA_DIR, VERSION, erlaubte_urspruenge
from .database import init_db, datenbank_erreichbar, datenbank_pruefen

# DB-Schema VOR Service-Imports initialisieren -- einige Service-Singletons
# greifen bereits im Konstruktor auf DB-Tabellen zu (config, sessions ...).
DATA_DIR.mkdir(parents=True, exist_ok=True)
init_db()

from .storage import get_all_zones
from .routers import stations_router, favorites_router, recording_router, recordings_router, podcasts_router, stream_router, config_router, blocklist_router, buffer_router, hls_router, filters_router, ad_detection_router, categories_router, file_explorer_router, recording_folders_router, storage_router, services_router, favicons_router, peaks_router, audio_processing_router, station_tags_router, station_custom_urls_router, wecker_router, zeitansage_router
from .services import rec_manager, podcast_service, buffer_manager, timeshift_buffer, hls_buffer, get_config_service
from .services.hls_recorder import hls_recorder
from .services.ad_detector import seed_domain_blacklist
from .services.aufnahmen import AufnahmeFehler, aufnahmen
from .services.durchleiter import DurchleiterFehler
from . import ablage as ablage_paket
from .ablage import AblageFehler, Belegt, NichtEingerichtet, NichtErreichbar, NichtGefunden


async def _podcast_refresh_loop():
    """Periodischer Feed-Refresh für alle Podcast-Abos"""
    podcast_service.set_next_refresh(datetime.now() + timedelta(seconds=60))
    await asyncio.sleep(60)  # 1 Min nach Start warten
    while True:
        if podcast_service.auto_refresh_enabled:
            try:
                result = await podcast_service.refresh_all()
                print(f"✓ Podcast-Refresh: {result.get('refreshed', 0)}/{result.get('total', 0)} Feeds, "
                      f"{result.get('new_episodes', 0)} neue Episoden")
            except Exception as e:
                print(f"✗ Podcast-Refresh fehlgeschlagen: {e}")
        podcast_service.reset_refresh_timer()
        await asyncio.sleep(podcast_service.refresh_interval)


async def _liegengebliebene_ablegen():
    """Aufnahmen, die ein Neustart oder eine fehlende Ablage im Arbeitsordner gelassen hat, nachträglich ablegen."""
    try:
        anzahl = await aufnahmen.liegengebliebene_ablegen()
        if anzahl:
            print(f"✓ Ablage: {anzahl} liegengebliebene Stücke nachgeholt")
    except AblageFehler as e:
        print(f"✗ Ablage: Nachholen nicht möglich: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App Lifecycle"""
    # Startup -- init_db() lief bereits beim Modul-Import (s.o.)
    ablage = ablage_paket.starten()
    hls_recorder.startup()  # Verwaiste HLS-REC-Sessions aufräumen
    get_config_service()  # Config initialisieren
    seed_domain_blacklist()  # Ad-Detection Domain-Blacklist befüllen

    # Periodischer Podcast-Refresh
    refresh_task = asyncio.create_task(_podcast_refresh_loop())

    # Ablage: Stand melden, liegengebliebene Aufnahmen nachholen, alte Arbeitskopien räumen
    zustand = await ablage.zustand()
    print(f"{'✓' if zustand.get('verbunden') else '✗'} Ablage: {zustand.get('meldung')}")
    aufnahmen.aufraeumen()
    nachholen_task = asyncio.create_task(_liegengebliebene_ablegen())

    print(f"✓ RadioHub Backend v{VERSION} gestartet")
    print(f"✓ Daten-Verzeichnis: {DATA_DIR}")
    zones = get_all_zones()
    for name, info in zones.items():
        writable = "OK" if info["writable"] else "FEHLER"
        print(f"  Zone {name}: {info['path']} [{writable}]")
    print(f"✓ HLS Buffer verfügbar: /api/hls/")
    refresh_h = podcast_service.refresh_interval // 3600
    refresh_status = "aktiv" if podcast_service.auto_refresh_enabled else "deaktiviert"
    print(f"✓ Podcast-Refresh alle {refresh_h}h {refresh_status}")

    yield

    # Shutdown
    refresh_task.cancel()
    nachholen_task.cancel()
    if hls_recorder.active_session:
        await hls_recorder.stop()
    if rec_manager.active_session:
        await rec_manager.stop()
    await buffer_manager.stop_buffering()
    await timeshift_buffer.stop_buffering()
    await hls_buffer.stop()  # HLS Buffer stoppen
    await podcast_service.close()
    await ablage.schliessen()
    print(f"✓ RadioHub Backend v{VERSION} gestoppt")


app = FastAPI(
    title="RadioHub API",
    version=VERSION,
    description="Internet Radio & Podcast Player mit HLS Time-Shift - © HalloWelt42",
    lifespan=lifespan
)

# CORS: die Oberfläche spricht /api über denselben Ursprung (im Betrieb nginx hinter dem Vorschaltdienst, beim Entwickeln
# der Proxy von Vite); fremde Ursprünge nur, wenn ALLOWED_ORIGINS sie ausdrücklich nennt (nie "*")
_urspruenge = erlaubte_urspruenge(os.getenv("ALLOWED_ORIGINS", ""))
if _urspruenge:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_urspruenge,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Fehler der Ablage und der Aufnahmen als HTTP-Status mit lesbarer Meldung
_ABLAGE_STATUS = ((NichtGefunden, 404), (Belegt, 409), (NichtEingerichtet, 503), (NichtErreichbar, 503))


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


# Router einbinden
app.include_router(stations_router)
app.include_router(favorites_router)
app.include_router(recording_router)
app.include_router(recordings_router)
app.include_router(podcasts_router)
app.include_router(stream_router)
app.include_router(config_router)
app.include_router(blocklist_router)
app.include_router(buffer_router)
app.include_router(hls_router)  # HLS Buffer
app.include_router(filters_router)
app.include_router(ad_detection_router)  # Ad-Detection
app.include_router(categories_router)  # Kategorien
app.include_router(file_explorer_router)  # File Explorer
app.include_router(recording_folders_router)  # Aufnahme-Ordner
app.include_router(storage_router)  # Storage-Zonen
app.include_router(services_router)  # Externe Dienste
app.include_router(favicons_router)  # Sender-Favicons
app.include_router(peaks_router)  # Waveform-Peaks
app.include_router(audio_processing_router)  # Audio-Nachbearbeitung
app.include_router(station_tags_router)  # Sender-Bewertungen
app.include_router(station_custom_urls_router)  # Custom Stream URLs
app.include_router(wecker_router)  # Wecker und Ort für Sonnenzeiten
app.include_router(zeitansage_router)  # Bausteine der Zeitansage


@app.get("/")
async def root():
    """API Info"""
    return {
        "name": "RadioHub API",
        "version": VERSION,
        "author": "HalloWelt42",
        "docs": "/docs",
        "health": "/health",
        "hls": "/api/hls/status"
    }


@app.get("/health")
async def health():
    """Health Check für Docker/Monitoring: Fassung und ob die Datenbank antwortet (SELECT 1, keine volle Prüfung)"""
    db_health = datenbank_erreichbar()
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "version": VERSION,
        "database": db_health["status"]
    }


@app.get("/api/datenbank/pruefung")
async def datenbank_pruefung():
    """Volle Prüfung der Datenbank (integrity_check über die ganze Datei); läuft neben der Ereignisschleife"""
    return await asyncio.to_thread(datenbank_pruefen)
