"""
Senderliste der heutigen Oberfläche (bis Etappe 3b): Statistik, Filterlisten und Suche über die Tabelle stations.

Sichtbar ist, was die Senderquelle sichtbar nennt (sender_index.sichtbar, RAD-7): lebende Regeln, Einzelsperren,
Freigaben und Favoriten als Ausnahme; die Ausschlüsse der früheren Filter-Einstellungen sind Regeln geworden und werden
hier nicht mehr eigens angewendet. Den Abgleich mit dem Senderverzeichnis macht der Auftrag sender_abgleich
(nächtlich, services/senderquelle/abgleich.py); "Aktualisieren" lädt nur die Liste (Vorgabe 4).
"""
import logging
from typing import List

from ..database import db_session

logger = logging.getLogger("radiohub.cache")

# sichtbar und, wie früher (das Verzeichnis lieferte nur erreichbare), erreichbar; Favoriten immer
SICHTBAR = "uuid IN (SELECT uuid FROM sender_index WHERE sichtbar = 1 AND (erreichbar = 1 OR favorit = 1))"


class CacheService:
    async def sync_stations(self, force: bool = False) -> dict:
        """Früher: Abgleich mit dem Verzeichnis. Jetzt nur der Stand der Liste; der Abgleich ist ein Auftrag."""
        stand = self.get_stats()
        return {"status": "cached", "count": stand["total_stations"], "last_sync": stand["last_sync"]}

    def get_stats(self) -> dict:
        """Cache-Statistiken"""
        with db_session() as conn:
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) FROM stations")
            total = c.fetchone()[0]
            
            c.execute("SELECT value FROM cache_meta WHERE key IN ('abgleich_zuletzt', 'last_sync') ORDER BY key LIMIT 1")
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
            c.execute(f'''SELECT countrycode, country, COUNT(*) as cnt
                        FROM stations WHERE countrycode != ''
                        AND {SICHTBAR}
                        GROUP BY countrycode ORDER BY cnt DESC LIMIT 30''')
            countries = [{"code": r[0], "name": r[1], "count": r[2]} for r in c.fetchall()]
            
            # Top Tags/Genres (ohne geblockte Sender)
            c.execute(f"""SELECT tags FROM stations WHERE tags != ''
                        AND {SICHTBAR}
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
            c.execute(f"SELECT MAX(votes) FROM stations WHERE {SICHTBAR}")
            max_votes_row = c.fetchone()
            max_votes = max_votes_row[0] if max_votes_row and max_votes_row[0] else 100000
            
            return {
                "countries": countries,
                "genres": genres,
                "bitrates": bitrates,
                "max_votes": max_votes
            }
    
    def get_tags(self, limit: int = 100) -> list:
        """Holt alle verfügbaren Tags mit Counts (für Kategorie-Verwaltung)."""
        with db_session() as conn:
            c = conn.cursor()
            c.execute(f"""SELECT tags FROM stations WHERE tags != ''
                        AND {SICHTBAR}
                        LIMIT 20000""")
            tag_counts = {}
            for row in c.fetchall():
                for tag in row[0].split(","):
                    tag = tag.strip().lower()
                    if tag and len(tag) > 2:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1

            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"name": t[0], "count": t[1]} for t in top_tags]

    def search_stations(self, q: str = None, countries: List[str] = None,
                       tags: List[str] = None, exclude_languages: List[str] = None,
                       exclude_tags: List[str] = None, bitrate_min: int = None,
                       bitrate_max: int = None, votes_min: int = None,
                       votes_max: int = None, sort_by: str = 'votes',
                       sort_order: str = 'desc', limit: int = 100,
                       offset: int = 0, favs_only: bool = False,
                       category_ids: List[int] = None) -> List[dict]:
        """Sucht sichtbare Sender mit Filtern und Sortierung. "Nur Favoriten" wirkt zusammen mit allen anderen
        Filtern (Vorgabe 2). `exclude_languages` und `exclude_tags` gelten nicht mehr: die Ausschlüsse sind lebende
        Regeln und stecken schon in der Sichtbarkeit (eine Wahrheit, RAD-7)."""
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
            conditions = [SICHTBAR]
            params: list = []
            if favs_only:
                conditions.append("uuid IN (SELECT uuid FROM favorites)")
            if q:
                conditions.append("(name LIKE ? OR tags LIKE ?)")
                params.extend([f"%{q}%", f"%{q}%"])
            if countries:
                conditions.append(f"countrycode IN ({','.join('?' * len(countries))})")
                params.extend(countries)
            if tags:
                conditions.append("(" + " OR ".join("tags LIKE ?" for _ in tags) + ")")
                params.extend(f"%{tag}%" for tag in tags)
            for spalte, zeichen, wert in (("bitrate", ">=", bitrate_min), ("bitrate", "<=", bitrate_max),
                                          ("votes", ">=", votes_min), ("votes", "<=", votes_max)):
                if wert is not None:
                    conditions.append(f"{spalte} {zeichen} ?")
                    params.append(wert)
            if category_ids:
                conditions.append(f"uuid IN (SELECT station_uuid FROM category_stations WHERE category_id IN "
                                  f"({','.join('?' * len(category_ids))}))")
                params.extend(category_ids)

            sql = (f"SELECT * FROM stations WHERE {' AND '.join(conditions)} "
                   f"ORDER BY {sort_field} {order_dir}, uuid LIMIT ? OFFSET ?")
            c.execute(sql, [*params, limit, offset])
            results = [dict(row) for row in c.fetchall()]

            # Erkannte Bitraten (immer Vorrang vor den Angaben des Verzeichnisses)
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
