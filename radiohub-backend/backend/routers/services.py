"""
RadioHub Services API Router

Übersicht aller externen Dienste und Datenquellen.
Ermöglicht Transparenz über Datenflüsse und konfigurierbare Endpunkte.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.config_service import config_service

router = APIRouter(prefix="/api/services", tags=["services"])


# Statische Dienst-Definitionen
SERVICE_DEFINITIONS = [
    {
        "id": "radio_browser",
        "name": "Radio-Browser",
        "description": "Sender-Datenbank mit über 30.000 Internetradio-Stationen",
        "icon": "fa-solid fa-tower-broadcast",
        "direction": "eingehend",
        "category": "radio",
        "config_key": "service_radio_browser_servers",
        "url_type": "multi",
    },
    {
        "id": "itunes_search",
        "name": "iTunes Search",
        "description": "Podcast-Suche über Apple iTunes Verzeichnis",
        "icon": "fa-brands fa-apple",
        "direction": "eingehend",
        "category": "podcast",
        "config_key": "service_itunes_search_url",
        "url_type": "single",
    },
    {
        "id": "fyyd_search",
        "name": "fyyd",
        "description": "Podcast-Suche über fyyd.de - deutsches Podcast-Verzeichnis",
        "icon": "fa-solid fa-podcast",
        "direction": "eingehend",
        "category": "podcast",
        "config_key": "service_fyyd_search_url",
        "url_type": "single",
    },
    {
        "id": "podcast_rss",
        "name": "Podcast RSS Feeds",
        "description": "Abruf von Episoden und Metadaten über RSS/Atom Feeds der abonnierten Podcasts",
        "icon": "fa-solid fa-rss",
        "direction": "eingehend",
        "category": "podcast",
        "config_key": None,
        "url_type": "dynamic",
        "note": "URLs aus den Podcast-Abonnements",
    },
    {
        "id": "icy_metadata",
        "name": "ICY Metadata",
        "description": "Titel- und Interpretenanzeige direkt aus den Audiostreams (Shoutcast/Icecast Protokoll)",
        "icon": "fa-solid fa-music",
        "direction": "eingehend",
        "category": "radio",
        "config_key": None,
        "url_type": "dynamic",
        "note": "Metadaten aus den jeweiligen Stream-URLs",
    },
    {
        "id": "ad_detection",
        "name": "Werbeerkennung",
        "description": "Lokale Domain-Blacklist zur Erkennung von Werbe-Redirects in Streams",
        "icon": "fa-solid fa-shield-halved",
        "direction": "lokal",
        "category": "radio",
        "config_key": None,
        "url_type": "none",
        "note": "Kein externer Dienst - Domain-Muster werden lokal geprüft",
    },
]


class ServiceUrlUpdate(BaseModel):
    value: object  # str oder list[str]


@router.get("")
async def list_services():
    """Alle externen Dienste mit aktuellen Endpunkten"""
    services = []

    for svc in SERVICE_DEFINITIONS:
        entry = {
            "id": svc["id"],
            "name": svc["name"],
            "description": svc["description"],
            "icon": svc["icon"],
            "direction": svc["direction"],
            "category": svc["category"],
            "url_type": svc["url_type"],
            "configurable": svc["config_key"] is not None,
        }

        # Aktuelle URL(s) aus Config laden
        if svc["config_key"]:
            entry["urls"] = config_service.get(svc["config_key"])
            entry["config_key"] = svc["config_key"]
        else:
            entry["urls"] = None

        # Zusätzliche Hinweise
        if "note" in svc:
            entry["note"] = svc["note"]

        services.append(entry)

    return {"services": services}


@router.put("/{service_id}")
async def update_service_url(service_id: str, body: ServiceUrlUpdate):
    """Endpunkt-URL eines Dienstes ändern"""
    # Service finden
    svc = next((s for s in SERVICE_DEFINITIONS if s["id"] == service_id), None)
    if not svc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dienst '{service_id}' nicht gefunden")

    if not svc["config_key"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Dieser Dienst ist nicht konfigurierbar")

    config_service.set(svc["config_key"], body.value)

    return {
        "success": True,
        "service_id": service_id,
        "value": body.value
    }


@router.post("/{service_id}/reset")
async def reset_service_url(service_id: str):
    """Endpunkt eines Dienstes auf Standard zurücksetzen"""
    from ..services.config_service import DEFAULT_CONFIG

    svc = next((s for s in SERVICE_DEFINITIONS if s["id"] == service_id), None)
    if not svc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Dienst '{service_id}' nicht gefunden")

    if not svc["config_key"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Dieser Dienst ist nicht konfigurierbar")

    default_value = DEFAULT_CONFIG.get(svc["config_key"])
    if default_value is not None:
        config_service.set(svc["config_key"], default_value)

    return {
        "success": True,
        "service_id": service_id,
        "value": default_value
    }
