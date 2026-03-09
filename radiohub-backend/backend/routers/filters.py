"""
RadioHub - Filter Router

Massen-Filter fuer Sender: Sprachen, Tags, Min-Votes.
Alle Sperren landen in der einheitlichen blocklist-Tabelle.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from ..database import db_session

router = APIRouter(prefix="/api/filters", tags=["filters"])


class FilterCriteria(BaseModel):
    excluded_languages: List[str] = []
    excluded_tags: List[str] = []
    min_votes: int = 0


class ReleaseRequest(BaseModel):
    uuids: Optional[List[str]] = None
    reason: Optional[str] = None
    all: bool = False


def _build_filter_query(criteria: FilterCriteria):
    """Baut SQL-Bedingungen fuer Filter-Kriterien"""
    conditions = []
    params = []

    for lang in criteria.excluded_languages:
        conditions.append("language LIKE ?")
        params.append(f"%{lang}%")

    for tag in criteria.excluded_tags:
        conditions.append("tags LIKE ?")
        params.append(f"%{tag}%")

    if criteria.min_votes > 0:
        conditions.append("votes < ?")
        params.append(criteria.min_votes)

    return conditions, params


@router.post("/preview")
async def filter_preview(criteria: FilterCriteria):
    """Vorschau: Welche Sender wuerden blockiert?"""
    conditions, params = _build_filter_query(criteria)

    if not conditions:
        return {"count": 0, "sample": []}

    with db_session() as conn:
        c = conn.cursor()

        where = " OR ".join(conditions)
        sql = f"""
            SELECT uuid, name, country, language, tags, votes
            FROM stations
            WHERE ({where})
            AND uuid NOT IN (SELECT uuid FROM blocklist)
            ORDER BY votes DESC
        """
        c.execute(sql, params)
        rows = c.fetchall()

        sample = [dict(r) for r in rows[:20]]
        return {"count": len(rows), "sample": sample}


@router.post("/push")
async def filter_push(criteria: FilterCriteria):
    """Sender blockieren (kumulativ) -- alles in blocklist"""
    conditions, params = _build_filter_query(criteria)

    if not conditions:
        return {"hidden_count": 0, "total_hidden": 0}

    # Grund-Strings fuer jede Kategorie
    reasons = []
    for lang in criteria.excluded_languages:
        reasons.append(f"language:{lang}")
    for tag in criteria.excluded_tags:
        reasons.append(f"tag:{tag}")
    if criteria.min_votes > 0:
        reasons.append(f"votes<{criteria.min_votes}")
    reason_str = ", ".join(reasons)

    with db_session() as conn:
        c = conn.cursor()

        where = " OR ".join(conditions)
        sql = f"""
            SELECT uuid, name FROM stations
            WHERE ({where})
            AND uuid NOT IN (SELECT uuid FROM blocklist)
        """
        c.execute(sql, params)
        to_block = c.fetchall()

        now = datetime.now().isoformat()
        for row in to_block:
            c.execute(
                "INSERT OR IGNORE INTO blocklist (uuid, name, reason, blocked_at) VALUES (?, ?, ?, ?)",
                (row["uuid"], row["name"], reason_str, now)
            )

        c.execute("SELECT COUNT(*) FROM blocklist")
        total = c.fetchone()[0]

    return {"hidden_count": len(to_block), "total_hidden": total}


@router.get("/hidden")
async def get_hidden(reason: Optional[str] = None):
    """Alle blockierten Sender (manual + filter)"""
    with db_session() as conn:
        c = conn.cursor()

        if reason:
            c.execute(
                "SELECT * FROM blocklist WHERE reason LIKE ? ORDER BY blocked_at DESC",
                (f"%{reason}%",)
            )
        else:
            c.execute("SELECT * FROM blocklist ORDER BY blocked_at DESC")

        stations = [dict(r) for r in c.fetchall()]

        # Gruende aggregieren
        reason_counts = {}
        c.execute("SELECT reason, COUNT(*) as cnt FROM blocklist GROUP BY reason ORDER BY cnt DESC")
        for row in c.fetchall():
            reason_counts[row["reason"] or "manual"] = row["cnt"]

    return {
        "count": len(stations),
        "stations": stations,
        "reasons": reason_counts
    }


@router.post("/release")
async def release_stations(req: ReleaseRequest):
    """Sender freigeben (aus blocklist entfernen)"""
    with db_session() as conn:
        c = conn.cursor()

        if req.all:
            c.execute("DELETE FROM blocklist")
        elif req.reason:
            if req.reason == "manual":
                c.execute("DELETE FROM blocklist WHERE reason IS NULL OR reason = 'manual'")
            else:
                c.execute("DELETE FROM blocklist WHERE reason LIKE ?", (f"%{req.reason}%",))
        elif req.uuids:
            placeholders = ",".join("?" * len(req.uuids))
            c.execute(f"DELETE FROM blocklist WHERE uuid IN ({placeholders})", req.uuids)
        else:
            return {"released_count": 0}

        released = c.rowcount

    return {"released_count": released}


@router.get("/languages")
async def get_languages():
    """Verfuegbare Sprachen mit Anzahl"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT language FROM stations WHERE language != '' AND language IS NOT NULL")

        lang_counts = {}
        for row in c.fetchall():
            for lang in row[0].split(","):
                lang = lang.strip().lower()
                if lang and len(lang) > 1:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

        sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
        languages = [{"name": name, "count": count} for name, count in sorted_langs]

    return {"languages": languages}
