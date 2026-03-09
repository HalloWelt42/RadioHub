"""
RadioHub - Ad-Detection Router

API-Endpoints fuer Werbeerkennung: Check, Report, False-Positive, Summary.
"""
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.ad_detector import (
    check_station_ads, report_ad_manual, mark_false_positive,
    get_ad_status, get_ad_summary
)

router = APIRouter(prefix="/api/ad-detection", tags=["ad-detection"])


class CheckRequest(BaseModel):
    uuid: str
    stream_url: str
    name: Optional[str] = None


class ReportRequest(BaseModel):
    uuid: str
    stream_url: str
    name: str
    note: Optional[str] = None


class FalsePositiveRequest(BaseModel):
    uuid: str


@router.get("/{uuid}")
async def get_station_ad_status(uuid: str):
    """Ad-Status fuer einen Sender"""
    status = get_ad_status(uuid)
    if not status:
        return {"uuid": uuid, "status": "unknown", "confidence": 0.0}
    return status


@router.post("/check")
async def check_ads(req: CheckRequest):
    """URL-Check ausfuehren: Prueft Sender auf Werbe-Domains/Patterns"""
    result = check_station_ads(req.uuid, req.stream_url, req.name)
    return result


@router.post("/report")
async def report_ad(req: ReportRequest):
    """Werbung manuell melden: Sender wird als Werbesender markiert und blockiert"""
    result = report_ad_manual(req.uuid, req.stream_url, req.name, req.note)
    return result


@router.post("/false-positive")
async def false_positive(req: FalsePositiveRequest):
    """Fehlalarm markieren: Sender wird freigegeben"""
    result = mark_false_positive(req.uuid)
    return result


@router.get("/summary/overview")
async def summary():
    """Uebersicht: Wie viele Sender in welchem Ad-Status"""
    return get_ad_summary()
