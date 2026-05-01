"""
RadioHub Backend v0.3.0 - HLS Timeshift Buffer

Internet Radio & Podcast Player mit HLS-basiertem Time-Shift
© HalloWelt42 - Nur für private Nutzung
"""
import os
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import DATA_DIR, VERSION
from .database import init_db, check_db_health

# DB-Schema VOR Service-Imports initialisieren -- einige Service-Singletons
# greifen bereits im Konstruktor auf DB-Tabellen zu (config, sessions ...).
DATA_DIR.mkdir(parents=True, exist_ok=True)
init_db()

from .storage import get_all_zones
from .routers import stations_router, favorites_router, recording_router, recordings_router, podcasts_router, stream_router, config_router, blocklist_router, buffer_router, hls_router, filters_router, ad_detection_router, categories_router, file_explorer_router, recording_folders_router, storage_router, services_router, favicons_router, peaks_router, audio_processing_router, station_tags_router, station_custom_urls_router
from .services import rec_manager, podcast_service, buffer_manager, timeshift_buffer, hls_buffer, get_config_service
from .services.hls_recorder import hls_recorder
from .services.ad_detector import seed_domain_blacklist


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App Lifecycle"""
    # Startup -- init_db() lief bereits beim Modul-Import (s.o.)
    hls_recorder.startup()  # Verwaiste HLS-REC-Sessions aufräumen
    get_config_service()  # Config initialisieren
    seed_domain_blacklist()  # Ad-Detection Domain-Blacklist befüllen

    # Periodischer Podcast-Refresh
    refresh_task = asyncio.create_task(_podcast_refresh_loop())

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
    if hls_recorder.active_session:
        await hls_recorder.stop()
    if rec_manager.active_session:
        await rec_manager.stop()
    await buffer_manager.stop_buffering()
    await timeshift_buffer.stop_buffering()
    await hls_buffer.stop()  # HLS Buffer stoppen
    await podcast_service.close()
    print(f"✓ RadioHub Backend v{VERSION} gestoppt")


app = FastAPI(
    title="RadioHub API",
    version=VERSION,
    description="Internet Radio & Podcast Player mit HLS Time-Shift - © HalloWelt42",
    lifespan=lifespan
)

# CORS - erlaubt Zugriff von separatem Frontend
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """Health Check für Docker/Monitoring"""
    db_health = check_db_health()
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "version": VERSION,
        "database": db_health["status"]
    }
