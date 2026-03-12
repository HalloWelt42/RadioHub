"""RadioHub Routers"""
from .stations import router as stations_router
from .favorites import router as favorites_router
from .recording import router as recording_router
from .recordings import router as recordings_router
from .podcasts import router as podcasts_router
from .stream import router as stream_router
from .config import router as config_router
from .blocklist import router as blocklist_router
from .buffer import router as buffer_router
from .hls import router as hls_router
from .filters import router as filters_router
from .ad_detection import router as ad_detection_router
from .categories import router as categories_router
from .file_explorer import router as file_explorer_router
from .recording_folders import router as recording_folders_router
from .storage import router as storage_router
from .services import router as services_router
from .favicons import router as favicons_router
from .peaks import router as peaks_router
from .audio_processing import router as audio_processing_router

__all__ = [
    "stations_router",
    "favorites_router",
    "recording_router",
    "recordings_router",
    "podcasts_router",
    "stream_router",
    "config_router",
    "blocklist_router",
    "buffer_router",
    "hls_router",
    "filters_router",
    "ad_detection_router",
    "categories_router",
    "file_explorer_router",
    "recording_folders_router",
    "storage_router",
    "services_router",
    "favicons_router",
    "peaks_router",
    "audio_processing_router",
]
