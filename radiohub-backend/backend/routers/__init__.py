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
    "hls_router"
]
