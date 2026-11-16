"""
RadioHub - Ad-Detection Router (Phase 2)

API-Endpoints für Werbeerkennung:
Check, Report, False-Positive, Suspects, Decide, Summary, Scan-Stream, Batch-Status.
"""
import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from ..database import db_session
from ..services.ad_detector import (
    check_station_ads, report_ad_manual, report_ad_mark_only, mark_false_positive,
    get_ad_status, get_ad_summary, get_suspects, decide_station_ad
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


class DecideRequest(BaseModel):
    uuid: str
    action: str  # "block" oder "allow"


class ScanRequest(BaseModel):
    batch_size: int = 50


@router.post("/scan")
async def scan_batch(req: ScanRequest):
    """Batch-Scan: Prüft N zufällige, noch nicht gecheckte Sender."""
    batch_size = min(req.batch_size, 200)

    with db_session() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT uuid, url_resolved, url, name FROM stations
            WHERE uuid NOT IN (SELECT station_uuid FROM station_ad_status)
            AND uuid NOT IN (SELECT uuid FROM blocklist)
            AND (url_resolved IS NOT NULL OR url IS NOT NULL)
            ORDER BY RANDOM()
            LIMIT ?
        """, (batch_size,))
        candidates = c.fetchall()

    checked = 0
    new_suspects = 0
    for row in candidates:
        stream_url = row[1] or row[2]
        if not stream_url:
            continue
        try:
            result = await check_station_ads(row[0], stream_url, row[3])
            checked += 1
            if result.get('status') in ('suspect', 'confirmed_ad'):
                new_suspects += 1
        except Exception:
            pass

    summary = get_ad_summary()
    return {
        'checked': checked,
        'new_suspects': new_suspects,
        'total_checked': summary['total_checked'],
        'remaining': _count_unchecked(),
    }


def _count_unchecked() -> int:
    with db_session() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM stations
            WHERE uuid NOT IN (SELECT station_uuid FROM station_ad_status)
            AND uuid NOT IN (SELECT uuid FROM blocklist)
        """)
        return c.fetchone()[0]


@router.get("/scan-stream")
async def scan_stream(batch_size: int = Query(default=50, le=200)):
    """SSE-Stream: Prüft Sender und sendet Fortschritt pro Sender."""

    with db_session() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT uuid, url_resolved, url, name FROM stations
            WHERE uuid NOT IN (SELECT station_uuid FROM station_ad_status)
            AND uuid NOT IN (SELECT uuid FROM blocklist)
            AND (url_resolved IS NOT NULL OR url IS NOT NULL)
            ORDER BY RANDOM()
            LIMIT ?
        """, (batch_size,))
        candidates = c.fetchall()

    async def event_generator():
        total = len(candidates)
        checked = 0
        new_suspects = 0

        for i, row in enumerate(candidates):
            stream_url = row[1] or row[2]
            if not stream_url:
                continue
            name = row[3] or row[0][:8]
            status = "skipped"
            try:
                result = await check_station_ads(row[0], stream_url, row[3])
                checked += 1
                status = result.get('status', 'unknown')
                if status in ('suspect', 'confirmed_ad'):
                    new_suspects += 1
            except Exception:
                status = "error"

            event = json.dumps({
                "progress": i + 1,
                "total": total,
                "current": name,
                "status": status,
            })
            yield f"data: {event}\n\n"
            await asyncio.sleep(0)

        done = json.dumps({
            "done": True,
            "checked": checked,
            "new_suspects": new_suspects,
            "total_checked": get_ad_summary().get('total_checked', 0),
            "remaining": _count_unchecked(),
        })
        yield f"data: {done}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class BatchStatusRequest(BaseModel):
    uuids: List[str]


@router.post("/batch-status")
async def batch_status(req: BatchStatusRequest):
    """Ad-Status für mehrere Sender auf einmal abfragen."""
    if not req.uuids:
        return {}

    placeholders = ",".join("?" for _ in req.uuids)
    with db_session() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT station_uuid, block_status, confidence, user_action
            FROM station_ad_status
            WHERE station_uuid IN ({placeholders})
        """, req.uuids)
        rows = c.fetchall()

    result = {}
    for row in rows:
        result[row[0]] = {
            "status": row[1],
            "confidence": row[2],
            "user_action": row[3],
        }
    return result


@router.get("/suspects")
async def suspects(min_confidence: float = Query(default=0.0)):
    """Verdächtige Sender über Schwellwert, User hat noch nicht entschieden"""
    return get_suspects(min_confidence)


@router.post("/decide")
async def decide(req: DecideRequest):
    """User entscheidet über verdächtigen Sender: block oder allow"""
    return decide_station_ad(req.uuid, req.action)


@router.get("/summary/overview")
async def summary():
    """Übersicht: Wie viele Sender in welchem Ad-Status"""
    data = get_ad_summary()
    data['remaining'] = _count_unchecked()
    return data


@router.get("/{uuid}")
async def get_station_ad_status(uuid: str):
    """Ad-Status für einen Sender"""
    status = get_ad_status(uuid)
    if not status:
        return {"uuid": uuid, "status": "unknown", "confidence": 0.0}
    return status


@router.post("/check")
async def check_ads(req: CheckRequest):
    """Sender auf Werbung prüfen (URL + Header-Check)"""
    result = await check_station_ads(req.uuid, req.stream_url, req.name)
    return result


@router.post("/report")
async def report_ad(req: ReportRequest):
    """Werbung manuell melden: Sender wird als Werbesender markiert und blockiert"""
    result = report_ad_manual(req.uuid, req.stream_url, req.name, req.note)
    return result


@router.post("/report-mark")
async def report_ad_mark(req: ReportRequest):
    """Werbung markieren ohne zu blockieren: Nur Ad-Status setzen"""
    result = report_ad_mark_only(req.uuid, req.stream_url, req.name, req.note)
    return result


@router.post("/false-positive")
async def false_positive(req: FalsePositiveRequest):
    """Fehlalarm markieren: Sender wird freigegeben"""
    result = mark_false_positive(req.uuid)
    return result
