"""RadioHub Routers"""
from .stations import router as stations_router
from .favorites import router as favorites_router
from .recording import router as recording_router
from .recordings import router as recordings_router
from .podcasts import router as podcasts_router
from .podcast_ordner import router as podcast_ordner_router
from .wolke import router as wolke_router
from .schnitt import router as schnitt_router
from .werbung import router as werbung_router
from .sendewerbung import router as sendewerbung_router
from .stream import router as stream_router
from .config import router as config_router
from .blocklist import router as blocklist_router
from .buffer import router as buffer_router
from .hls import router as hls_router
from .filters import router as filters_router
from .ad_detection import router as ad_detection_router
from .categories import router as categories_router
from .recording_folders import router as recording_folders_router
from .storage import router as storage_router
from .services import router as services_router
from .favicons import router as favicons_router
from .station_tags import router as station_tags_router
from .station_custom_urls import router as station_custom_urls_router
from .wecker import router as wecker_router
from .zeitansage import router as zeitansage_router
from .lernlauf import router as lernlauf_router
from .radio import router as radio_router

# In dieser Reihenfolge eingebunden (main.app_bauen), alle hinter der Anmeldung
ALLE = [
    stations_router, favorites_router, recording_router, recordings_router, podcasts_router, podcast_ordner_router, wolke_router, schnitt_router, werbung_router, sendewerbung_router, stream_router,
    config_router, blocklist_router, buffer_router, hls_router, filters_router, ad_detection_router, categories_router,
    recording_folders_router, storage_router, services_router, favicons_router,
    station_tags_router, station_custom_urls_router, wecker_router, zeitansage_router,
    radio_router, lernlauf_router,
]

__all__ = [
    "ALLE",
    "lernlauf_router",
    "radio_router",
    "stations_router",
    "favorites_router",
    "recording_router",
    "recordings_router",
    "podcasts_router",
    "podcast_ordner_router", "wolke_router", "schnitt_router", "werbung_router", "sendewerbung_router",
    "stream_router",
    "config_router",
    "blocklist_router",
    "buffer_router",
    "hls_router",
    "filters_router",
    "ad_detection_router",
    "categories_router",
    "recording_folders_router",
    "storage_router",
    "services_router",
    "favicons_router",
    "station_tags_router",
    "station_custom_urls_router",
    "wecker_router",
    "zeitansage_router",
]
