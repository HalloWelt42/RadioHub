"""
RadioHub Backend v0.2.0 - HLS Timeshift Buffer

Internet Radio & Podcast Player mit HLS-basiertem Time-Shift
© HalloWelt42 - Nur für private Nutzung
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import DATA_DIR, VERSION
from .database import init_db, check_db_health
from .routers import stations_router, favorites_router, recording_router, recordings_router, podcasts_router, stream_router, config_router, blocklist_router, buffer_router, hls_router, filters_router, ad_detection_router, categories_router
from .services import rec_manager, podcast_service, buffer_manager, timeshift_buffer, hls_buffer, get_config_service
from .services.hls_recorder import hls_recorder
from .services.ad_detector import seed_domain_blacklist


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App Lifecycle"""
    # Startup
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    get_config_service()  # Config initialisieren
    seed_domain_blacklist()  # Ad-Detection Domain-Blacklist befuellen
    print(f"✓ RadioHub Backend v{VERSION} gestartet")
    print(f"✓ Daten-Verzeichnis: {DATA_DIR}")
    print(f"✓ HLS Buffer verfügbar: /api/hls/")
    
    yield
    
    # Shutdown
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
