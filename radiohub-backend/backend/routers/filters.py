"""
RadioHub - Filter Router

Massen-Filter für Sender: Sprachen, Tags, Min-Votes.
Alle Sperren landen in der einheitlichen blocklist-Tabelle.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from ..database import db_session
from ..services import filtersperren
from .. import sender_merkmale

router = APIRouter(prefix="/api/filters", tags=["filters"])


class FilterCriteria(BaseModel):
    excluded_languages: List[str] = []
    excluded_tags: List[str] = []
    min_votes: int = 0

    def kriterien(self) -> filtersperren.FilterKriterien:
        return filtersperren.FilterKriterien(
            sprachen=self.excluded_languages, tags=self.excluded_tags, mindeststimmen=self.min_votes)


class ReleaseRequest(BaseModel):
    uuids: Optional[List[str]] = None
    reason: Optional[str] = None
    all: bool = False


def _noch_frei(conn, kriterien: filtersperren.FilterKriterien) -> list[filtersperren.Sperre]:
    """Treffer der Kriterien, die noch nicht gesperrt sind (aus welchem Grund auch immer)."""
    gesperrt = {z[0] for z in conn.execute("SELECT uuid FROM blocklist")}
    return [s for s in filtersperren.treffer(conn, kriterien) if s.uuid not in gesperrt]


@router.post("/preview")
async def filter_preview(criteria: FilterCriteria):
    """Vorschau: Welche Sender würden zusätzlich ausgeblendet?"""
    with db_session() as conn:
        sperren = _noch_frei(conn, criteria.kriterien())
        if not sperren:
            return {"count": 0, "sample": []}
        uuids = [s.uuid for s in sperren]
        platz = ",".join("?" * len(uuids))
        sample = [dict(z) for z in conn.execute(
            f"SELECT uuid, name, country, language, tags, votes FROM stations WHERE uuid IN ({platz})"
            " ORDER BY votes DESC LIMIT 20", uuids)]
        return {"count": len(sperren), "sample": sample}


@router.post("/push")
async def filter_push(criteria: FilterCriteria):
    """Sender ausblenden, die die Kriterien treffen (kommt zu den bestehenden Sperren hinzu)."""
    with db_session() as conn:
        sperren = _noch_frei(conn, criteria.kriterien())
        jetzt = datetime.now().isoformat()
        conn.executemany(
            "INSERT OR IGNORE INTO blocklist (uuid, name, reason, category, blocked_at) VALUES (?, ?, ?, ?, ?)",
            [(s.uuid, s.name, s.grund, filtersperren.KATEGORIE, jetzt) for s in sperren])
        total = conn.execute("SELECT COUNT(*) FROM blocklist").fetchone()[0]
    return {"hidden_count": len(sperren), "total_hidden": total}


@router.get("/hidden")
async def get_hidden(reason: Optional[str] = None, category: Optional[str] = None):
    """Alle blockierten Sender, nach Kategorien gruppiert"""
    with db_session() as conn:
        c = conn.cursor()

        if reason:
            c.execute(
                "SELECT * FROM blocklist WHERE reason LIKE ? ORDER BY blocked_at DESC",
                (f"%{reason}%",)
            )
        elif category:
            c.execute(
                "SELECT * FROM blocklist WHERE category = ? ORDER BY blocked_at DESC",
                (category,)
            )
        else:
            c.execute("SELECT * FROM blocklist ORDER BY blocked_at DESC")

        stations = [dict(r) for r in c.fetchall()]

        # Nach Kategorien gruppieren
        categories = {}
        c.execute("""
            SELECT COALESCE(category, 'manual') as cat, reason, COUNT(*) as cnt
            FROM blocklist
            GROUP BY cat, reason
            ORDER BY cnt DESC
        """)
        for row in c.fetchall():
            cat = row[0] or 'manual'
            reason_key = row[1] or 'manual'
            if cat not in categories:
                categories[cat] = {'count': 0, 'reasons': {}}
            categories[cat]['count'] += row[2]
            categories[cat]['reasons'][reason_key] = row[2]

    return {
        "count": len(stations),
        "categories": categories,
        "stations": stations,
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
    """Verfügbare Sprachen mit Anzahl"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("""SELECT language FROM stations WHERE language != '' AND language IS NOT NULL""")

        lang_counts = {}
        for row in c.fetchall():
            # dieselbe Zerlegung wie beim Ausschließen, damit Liste und Vergleich übereinstimmen
            for lang in sender_merkmale.eintraege(row[0]):
                if len(lang) > 1:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

        sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
        languages = [{"name": name, "count": count} for name, count in sorted_langs]

    return {"languages": languages}


@router.get("/countries")
async def get_countries():
    """Verfügbare Länder mit Anzahl"""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT countrycode, country, COUNT(*) as cnt
            FROM stations
            WHERE countrycode != '' AND countrycode IS NOT NULL
            AND uuid NOT IN (SELECT uuid FROM blocklist)
            GROUP BY countrycode
            ORDER BY cnt DESC
        """)
        countries = [
            {"code": row[0], "name": row[1], "count": row[2]}
            for row in c.fetchall()
        ]

    return {"countries": countries}
