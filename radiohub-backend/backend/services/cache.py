"""
RadioHub v0.1.9 - Cache Service

Lädt Sender von radio-browser.info und cached sie lokal.
Mit Sortierung nach name, country, bitrate, votes
"""
import json
import httpx
from datetime import datetime
from typing import List, Optional

from ..database import db_session

# Radio-Browser API Server
API_SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info"
]

CACHE_MAX_AGE_HOURS = 24


class CacheService:
    def __init__(self):
        self.api_base = API_SERVERS[0]
    
    async def sync_stations(self, force: bool = False) -> dict:
        """Synchronisiert Sender-Cache mit radio-browser.info"""
        
        # Prüfen ob Cache aktuell
        if not force:
            with db_session() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM cache_meta WHERE key='last_sync'")
                row = c.fetchone()
                if row:
                    last_sync = datetime.fromisoformat(row[0])
                    age_hours = (datetime.now() - last_sync).total_seconds() / 3600
                    if age_hours < CACHE_MAX_AGE_HOURS:
                        c.execute("SELECT COUNT(*) FROM stations")
                        count = c.fetchone()[0]
                        return {"status": "cached", "count": count, "age_hours": round(age_hours, 1)}
        
        # Sender laden
        stations = await self._fetch_stations()
        if not stations:
            return {"status": "error", "message": "Keine Sender geladen"}
        
        # In DB speichern
        count = self._save_stations(stations)
        
        # Timestamp speichern
        with db_session() as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
                     ("last_sync", datetime.now().isoformat()))
        
        return {"status": "synced", "count": count}
    
    async def _fetch_stations(self) -> List[dict]:
        """Laedt alle Sender von API in Batches (API-Limit ~20000 pro Request)"""
        BATCH_SIZE = 20000
        all_stations = []
        offset = 0

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                while True:
                    url = f"{self.api_base}/json/stations/search"
                    params = {
                        "limit": BATCH_SIZE,
                        "offset": offset,
                        "hidebroken": "true",
                        "order": "clickcount",
                        "reverse": "true"
                    }

                    resp = await client.get(url, params=params, headers={
                        "User-Agent": "RadioHub/0.1"
                    })

                    if resp.status_code != 200:
                        print(f"✗ API Fehler bei Offset {offset}: Status {resp.status_code}")
                        break

                    batch = resp.json()
                    if not batch:
                        break

                    all_stations.extend(batch)
                    print(f"  Batch geladen: {len(batch)} Sender (gesamt: {len(all_stations)})")

                    if len(batch) < BATCH_SIZE:
                        break

                    offset += BATCH_SIZE
        except Exception as e:
            print(f"✗ Fehler beim Laden bei Offset {offset}: {e}")

        print(f"✓ {len(all_stations)} Sender insgesamt geladen")
        return all_stations
    
    def _save_stations(self, stations: List[dict]) -> int:
        """Speichert Sender in DB mit last_seen Tracking"""
        now = datetime.now().isoformat()
        count = 0

        with db_session() as conn:
            c = conn.cursor()

            for s in stations:
                try:
                    c.execute('''INSERT OR REPLACE INTO stations
                        (uuid, name, url, url_resolved, favicon, country, countrycode,
                         language, tags, codec, bitrate, votes, clickcount, homepage,
                         lastcheck, cached_at, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (s.get("stationuuid"), s.get("name"), s.get("url"),
                         s.get("url_resolved"), s.get("favicon"), s.get("country"),
                         s.get("countrycode"), s.get("language"), s.get("tags"),
                         s.get("codec"), s.get("bitrate", 0), s.get("votes", 0),
                         s.get("clickcount", 0), s.get("homepage"), s.get("lastcheckok"),
                         now, now))
                    count += 1
                except Exception as e:
                    print(f"✗ Station speichern fehlgeschlagen: {e}")

        print(f"✓ {count} Sender gespeichert")
        return count
    
    def get_stats(self) -> dict:
        """Cache-Statistiken"""
        with db_session() as conn:
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) FROM stations")
            total = c.fetchone()[0]
            
            c.execute("SELECT value FROM cache_meta WHERE key='last_sync'")
            row = c.fetchone()
            last_sync = row[0] if row else None
            
            c.execute("SELECT COUNT(DISTINCT countrycode) FROM stations")
            countries = c.fetchone()[0]
            
            return {
                "total_stations": total,
                "countries": countries,
                "last_sync": last_sync
            }
    
    def get_filters(self) -> dict:
        """Holt Filter-Optionen (Länder, Genres, Bitraten, max_votes)"""
        with db_session() as conn:
            c = conn.cursor()
            
            # Top Länder (ohne geblockte Sender)
            c.execute('''SELECT countrycode, country, COUNT(*) as cnt
                        FROM stations WHERE countrycode != ''
                        AND uuid NOT IN (SELECT uuid FROM blocklist)
                        GROUP BY countrycode ORDER BY cnt DESC LIMIT 30''')
            countries = [{"code": r[0], "name": r[1], "count": r[2]} for r in c.fetchall()]
            
            # Top Tags/Genres (ohne geblockte Sender)
            c.execute("""SELECT tags FROM stations WHERE tags != ''
                        AND uuid NOT IN (SELECT uuid FROM blocklist)
                        LIMIT 10000""")
            tag_counts = {}
            for row in c.fetchall():
                for tag in row[0].split(","):
                    tag = tag.strip().lower()
                    if tag and len(tag) > 2:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:30]
            genres = [{"name": t[0], "count": t[1]} for t in top_tags]
            
            # Bitrate-Bereiche
            bitrates = [
                {"label": "< 64 kbps", "min": 0, "max": 64},
                {"label": "64-128 kbps", "min": 64, "max": 128},
                {"label": "128-192 kbps", "min": 128, "max": 192},
                {"label": "192-256 kbps", "min": 192, "max": 256},
                {"label": "> 256 kbps", "min": 256, "max": 9999}
            ]
            
            # Max Votes für logarithmische Skala (ohne geblockte)
            c.execute("SELECT MAX(votes) FROM stations WHERE uuid NOT IN (SELECT uuid FROM blocklist)")
            max_votes_row = c.fetchone()
            max_votes = max_votes_row[0] if max_votes_row and max_votes_row[0] else 100000
            
            return {
                "countries": countries,
                "genres": genres,
                "bitrates": bitrates,
                "max_votes": max_votes
            }
    
    def search_stations(self, q: str = None, countries: List[str] = None,
                       tags: List[str] = None, exclude_languages: List[str] = None,
                       exclude_tags: List[str] = None, bitrate_min: int = None,
                       bitrate_max: int = None, votes_min: int = None,
                       votes_max: int = None, sort_by: str = 'votes',
                       sort_order: str = 'desc', limit: int = 100,
                       offset: int = 0, favs_only: bool = False) -> List[dict]:
        """Sucht Sender mit Filtern und Sortierung (ohne blockierte Sender)"""
        
        # Mapping für Sortierfelder
        sort_field_map = {
            'name': 'name COLLATE NOCASE',
            'country': 'country COLLATE NOCASE',
            'bitrate': 'bitrate',
            'votes': 'votes'
        }
        
        sort_field = sort_field_map.get(sort_by, 'votes')
        order_dir = 'ASC' if sort_order == 'asc' else 'DESC'
        
        with db_session() as conn:
            c = conn.cursor()

            if favs_only:
                # Nur Favoriten mit Sortierung
                sql = f"SELECT * FROM favorites ORDER BY {sort_field} {order_dir}"
                c.execute(sql)
            else:
                # Normale Suche mit Sortierung
                conditions = ["uuid NOT IN (SELECT uuid FROM blocklist)"]
                params = []

                if q:
                    conditions.append("(name LIKE ? OR tags LIKE ?)")
                    params.extend([f"%{q}%", f"%{q}%"])

                if countries:
                    placeholders = ",".join("?" * len(countries))
                    conditions.append(f"countrycode IN ({placeholders})")
                    params.extend(countries)

                if tags:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("tags LIKE ?")
                        params.append(f"%{tag}%")
                    conditions.append(f"({' OR '.join(tag_conditions)})")

                if exclude_languages:
                    for lang in exclude_languages:
                        conditions.append("NOT (language LIKE ?)")
                        params.append(f"%{lang}%")

                if exclude_tags:
                    for tag in exclude_tags:
                        conditions.append("NOT (tags LIKE ?)")
                        params.append(f"%{tag}%")

                if bitrate_min is not None:
                    conditions.append("bitrate >= ?")
                    params.append(bitrate_min)

                if bitrate_max is not None:
                    conditions.append("bitrate <= ?")
                    params.append(bitrate_max)

                if votes_min is not None:
                    conditions.append("votes >= ?")
                    params.append(votes_min)

                if votes_max is not None:
                    conditions.append("votes <= ?")
                    params.append(votes_max)

                where = f"WHERE {' AND '.join(conditions)}"
                sql = f"SELECT * FROM stations {where} ORDER BY {sort_field} {order_dir} LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                c.execute(sql, params)

            results = [dict(row) for row in c.fetchall()]

            # Detected bitrates mergen (immer Vorrang vor API-Werten)
            if results:
                uuids = [s['uuid'] for s in results]
                placeholders = ",".join("?" * len(uuids))
                c.execute(
                    f"SELECT uuid, bitrate, codec FROM detected_bitrates WHERE uuid IN ({placeholders}) AND bitrate > 0",
                    uuids
                )
                detected = {row[0]: (row[1], row[2]) for row in c.fetchall()}
                for station in results:
                    det = detected.get(station['uuid'])
                    if det:
                        station['bitrate'] = det[0]
                        if det[1]:
                            station['codec'] = det[1]

            return results


# Singleton
cache_service = CacheService()
