"""
RadioHub v0.2.4 - Podcast Service

Podcast-Suche (iTunes + fyyd), Abonnements, Episoden, Downloads,
Cover-Art-Persistierung, erweiterte Filter/Sortierung, Statistiken.
"""
import httpx
import hashlib
import shutil
import re
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime
from dataclasses import dataclass
from typing import List, Optional
from xml.etree import ElementTree as ET

from ..database import db_session
from ..config import get_podcast_recordings_dir, DATA_DIR, PODCAST_RECORDINGS_DIR, AUDIO_MIMETYPES
from .config_service import config_service


def _sanitize_filename(name: str) -> str:
    """Dateinamen-sichere Version eines Strings"""
    name = re.sub(r'[^\w\s\-.]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name[:80] or "untitled"


@dataclass
class PodcastSearchResult:
    title: str
    author: str
    feed_url: str
    image_url: str
    description: str
    source: str  # "itunes" oder "fyyd"


class PodcastService:
    REFRESH_INTERVAL = 6 * 3600  # 6 Stunden (Fallback)

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self._next_refresh_at: Optional[datetime] = None
        self._downloading: set[int] = set()  # Aktive Downloads (episode_id)

    @property
    def refresh_interval(self) -> int:
        """Refresh-Intervall aus Config oder Fallback"""
        return config_service.get("podcast_refresh_interval", self.REFRESH_INTERVAL)

    @property
    def auto_refresh_enabled(self) -> bool:
        """Auto-Refresh aus Config"""
        return config_service.get("podcast_auto_refresh", True)

    def get_refresh_status(self) -> dict:
        """Refresh-Timer Status für Frontend"""
        interval = self.refresh_interval
        return {
            "next_refresh_at": self._next_refresh_at.isoformat() if self._next_refresh_at else None,
            "interval_hours": interval // 3600,
            "auto_refresh": self.auto_refresh_enabled
        }

    def set_next_refresh(self, dt: datetime):
        self._next_refresh_at = dt

    def reset_refresh_timer(self):
        from datetime import timedelta
        self._next_refresh_at = datetime.now() + timedelta(seconds=self.refresh_interval)

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.client:
            self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self.client

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    # =========================================================================
    # Suche
    # =========================================================================

    async def search(self, query: str, source: str = "all", limit: int = 20) -> List[PodcastSearchResult]:
        """Sucht Podcasts über iTunes und/oder fyyd"""
        results = []

        if source in ("all", "itunes"):
            results.extend(await self._search_itunes(query, limit))

        if source in ("all", "fyyd"):
            results.extend(await self._search_fyyd(query, limit))

        # Deduplizieren nach Feed-URL
        seen = set()
        unique = []
        for r in results:
            if r.feed_url not in seen:
                seen.add(r.feed_url)
                unique.append(r)

        return unique[:limit]

    async def _search_itunes(self, query: str, limit: int) -> List[PodcastSearchResult]:
        try:
            client = await self._get_client()
            itunes_url = config_service.get("service_itunes_search_url", "https://itunes.apple.com/search")
            resp = await client.get(
                itunes_url,
                params={"term": query, "media": "podcast", "limit": limit}
            )
            if resp.status_code != 200:
                return []

            results = []
            for item in resp.json().get("results", []):
                results.append(PodcastSearchResult(
                    title=item.get("collectionName", ""),
                    author=item.get("artistName", ""),
                    feed_url=item.get("feedUrl", ""),
                    image_url=item.get("artworkUrl600", item.get("artworkUrl100", "")),
                    description=item.get("collectionName", ""),
                    source="itunes"
                ))
            return results
        except Exception as e:
            print(f"iTunes search error: {e}")
            return []

    async def _search_fyyd(self, query: str, limit: int) -> List[PodcastSearchResult]:
        try:
            client = await self._get_client()
            fyyd_url = config_service.get("service_fyyd_search_url", "https://api.fyyd.de/0.2/search/podcast")
            resp = await client.get(
                fyyd_url,
                params={"title": query, "count": limit}
            )
            if resp.status_code != 200:
                return []

            results = []
            for item in resp.json().get("data", []):
                results.append(PodcastSearchResult(
                    title=item.get("title", ""),
                    author=item.get("author", ""),
                    feed_url=item.get("xmlURL", ""),
                    image_url=item.get("imgURL", ""),
                    description=item.get("description", "")[:500] if item.get("description") else "",
                    source="fyyd"
                ))
            return results
        except Exception as e:
            print(f"fyyd search error: {e}")
            return []

    # =========================================================================
    # Abonnements
    # =========================================================================

    async def subscribe(self, feed_url: str) -> Optional[dict]:
        """Podcast abonnieren + Cover-Art herunterladen"""
        feed_data = await self._parse_feed(feed_url)
        if not feed_data:
            return None

        with db_session() as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO podcast_subscriptions
                (feed_url, title, author, description, image_url, last_updated, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (feed_url, feed_data["title"], feed_data["author"],
                 feed_data["description"][:1000] if feed_data["description"] else "",
                 feed_data["image_url"], datetime.now().isoformat(),
                 datetime.now().isoformat()))

            podcast_id = c.lastrowid

            # Kategorien aus Feed speichern
            if feed_data.get("categories"):
                c.execute("UPDATE podcast_subscriptions SET categories = ? WHERE id = ?",
                          (",".join(feed_data["categories"]), podcast_id))

            # Episoden speichern
            for ep in feed_data.get("episodes", []):
                c.execute('''INSERT OR IGNORE INTO podcast_episodes
                    (podcast_id, guid, title, description, audio_url, duration,
                     published_at, image_url, transcript_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (podcast_id, ep["guid"], ep["title"],
                     ep["description"][:2000] if ep["description"] else "",
                     ep["audio_url"], ep.get("duration", 0),
                     ep.get("published_at"), ep.get("image_url", ""),
                     ep.get("transcript_url", "")))

        # Cover-Art async herunterladen
        if feed_data.get("image_url"):
            try:
                await self.download_image(feed_data["image_url"], podcast_id)
            except Exception as e:
                print(f"Cover-Art download fehlgeschlagen: {e}")

        return {"id": podcast_id, "title": feed_data["title"], "feed_url": feed_url}

    async def unsubscribe(self, podcast_id: int) -> bool:
        """Podcast-Abo entfernen (lokale Dateien bleiben erhalten)"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM podcast_episodes WHERE podcast_id = ?", (podcast_id,))
            c.execute("DELETE FROM podcast_subscriptions WHERE id = ?", (podcast_id,))
            return c.rowcount > 0

    async def get_subscriptions(self) -> List[dict]:
        """Alle Abos mit Episoden-Statistiken"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT ps.*,
                (SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ps.id) as episode_count,
                (SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ps.id AND is_downloaded = 1) as downloaded_count,
                (SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ps.id AND is_played = 0) as unplayed_count,
                (SELECT COALESCE(SUM(duration), 0) FROM podcast_episodes WHERE podcast_id = ps.id) as total_duration
                FROM podcast_subscriptions ps ORDER BY title''')
            return [dict(row) for row in c.fetchall()]

    async def get_subscription(self, podcast_id: int) -> Optional[dict]:
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT ps.*,
                (SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ps.id) as episode_count,
                (SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ps.id AND is_downloaded = 1) as downloaded_count,
                (SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ps.id AND is_played = 0) as unplayed_count,
                (SELECT COALESCE(SUM(duration), 0) FROM podcast_episodes WHERE podcast_id = ps.id) as total_duration
                FROM podcast_subscriptions ps WHERE ps.id = ?''', (podcast_id,))
            row = c.fetchone()
            return dict(row) if row else None

    async def refresh_podcast(self, podcast_id: int) -> dict:
        """Podcast-Feed neu laden, neue Episoden hinzufügen"""
        sub = await self.get_subscription(podcast_id)
        if not sub:
            return {"success": False, "error": "Podcast nicht gefunden"}

        feed_data = await self._parse_feed(sub["feed_url"])
        if not feed_data:
            return {"success": False, "error": "Feed nicht erreichbar"}

        new_episodes = 0
        with db_session() as conn:
            c = conn.cursor()

            # Podcast-Metadaten aktualisieren
            c.execute('''UPDATE podcast_subscriptions SET
                title = ?, author = ?, description = ?, image_url = ?, last_updated = ?
                WHERE id = ?''',
                (feed_data["title"], feed_data["author"],
                 feed_data["description"][:1000] if feed_data["description"] else "",
                 feed_data["image_url"], datetime.now().isoformat(), podcast_id))

            # Kategorien aktualisieren
            if feed_data.get("categories"):
                c.execute("UPDATE podcast_subscriptions SET categories = ? WHERE id = ?",
                          (",".join(feed_data["categories"]), podcast_id))

            # Neue Episoden einfügen
            for ep in feed_data.get("episodes", []):
                c.execute('''INSERT OR IGNORE INTO podcast_episodes
                    (podcast_id, guid, title, description, audio_url, duration,
                     published_at, image_url, transcript_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (podcast_id, ep["guid"], ep["title"],
                     ep["description"][:2000] if ep["description"] else "",
                     ep["audio_url"], ep.get("duration", 0),
                     ep.get("published_at"), ep.get("image_url", ""),
                     ep.get("transcript_url", "")))
                if c.rowcount > 0:
                    new_episodes += 1

        # Cover aktualisieren
        if feed_data.get("image_url"):
            try:
                await self.download_image(feed_data["image_url"], podcast_id)
            except Exception:
                pass

        # Auto-Download für neue Episoden
        if sub.get("auto_download") and new_episodes > 0:
            try:
                await self._auto_download_new(podcast_id)
            except Exception as e:
                print(f"Auto-Download fehlgeschlagen: {e}")

        return {"success": True, "new_episodes": new_episodes}

    async def refresh_all(self) -> dict:
        """Alle Feeds aktualisieren"""
        subs = await self.get_subscriptions()
        results = {"total": len(subs), "refreshed": 0, "new_episodes": 0, "errors": 0}

        for sub in subs:
            try:
                result = await self.refresh_podcast(sub["id"])
                if result.get("success"):
                    results["refreshed"] += 1
                    results["new_episodes"] += result.get("new_episodes", 0)
                else:
                    results["errors"] += 1
            except Exception:
                results["errors"] += 1

        return results

    async def update_subscription_categories(self, podcast_id: int, categories: str) -> bool:
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE podcast_subscriptions SET categories = ? WHERE id = ?",
                      (categories, podcast_id))
            return c.rowcount > 0

    async def set_auto_download(self, podcast_id: int, enabled: bool) -> bool:
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE podcast_subscriptions SET auto_download = ? WHERE id = ?",
                      (1 if enabled else 0, podcast_id))
            return c.rowcount > 0

    # =========================================================================
    # Episoden
    # =========================================================================

    async def get_episodes(self, podcast_id: int, limit: int = 50, offset: int = 0,
                           filter_status: str = "all", sort_by: str = "published_at",
                           sort_order: str = "desc") -> dict:
        """Episoden mit Filter und Sortierung"""
        allowed_sort = {"published_at", "title", "duration"}
        if sort_by not in allowed_sort:
            sort_by = "published_at"
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        where = "WHERE podcast_id = ?"
        params = [podcast_id]

        if filter_status == "unplayed":
            where += " AND is_played = 0"
        elif filter_status == "downloaded":
            where += " AND is_downloaded = 1"
        elif filter_status == "played":
            where += " AND is_played = 1"

        with db_session() as conn:
            c = conn.cursor()
            c.execute(f'''SELECT * FROM podcast_episodes
                {where} ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?''',
                params + [limit, offset])
            episodes = [dict(row) for row in c.fetchall()]

            c.execute(f"SELECT COUNT(*) FROM podcast_episodes {where}", params)
            total = c.fetchone()[0]

        return {"episodes": episodes, "total": total}

    async def get_all_episodes(self, limit: int = 50, offset: int = 0,
                               filter_status: str = "all", sort_by: str = "published_at",
                               sort_order: str = "desc", podcast_ids: Optional[List[int]] = None) -> dict:
        """Episoden über alle Abos, mit optionalem Podcast-Filter"""
        allowed_sort = {"published_at", "title", "duration"}
        if sort_by not in allowed_sort:
            sort_by = "published_at"
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        where_clauses = []
        params = []

        if podcast_ids:
            placeholders = ",".join("?" * len(podcast_ids))
            where_clauses.append(f"pe.podcast_id IN ({placeholders})")
            params.extend(podcast_ids)

        if filter_status == "unplayed":
            where_clauses.append("pe.is_played = 0")
        elif filter_status == "downloaded":
            where_clauses.append("pe.is_downloaded = 1")
        elif filter_status == "played":
            where_clauses.append("pe.is_played = 1")

        where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        with db_session() as conn:
            c = conn.cursor()
            c.execute(f'''SELECT pe.*, ps.title as podcast_title, ps.image_url as podcast_image_url
                FROM podcast_episodes pe
                JOIN podcast_subscriptions ps ON pe.podcast_id = ps.id
                {where} ORDER BY pe.{sort_by} {sort_order} LIMIT ? OFFSET ?''',
                params + [limit, offset])
            episodes = [dict(row) for row in c.fetchall()]

            c.execute(f'''SELECT COUNT(*) FROM podcast_episodes pe
                {("JOIN podcast_subscriptions ps ON pe.podcast_id = ps.id " + where) if where else ""}''',
                params)
            total = c.fetchone()[0]

        return {"episodes": episodes, "total": total}

    async def search_episodes(self, query: str, limit: int = 50, offset: int = 0,
                               search_in: str = "all") -> dict:
        """Volltextsuche über Episoden (Titel, Beschreibung, Transkript).
        search_in: 'all' | 'title' | 'description' | 'transcript'
        Gibt Ergebnisse mit Kontext-Snippets zurück.
        """
        if not query or len(query) < 2:
            return {"episodes": [], "total": 0}

        like_pattern = f"%{query}%"

        # Suchfelder je nach Scope
        fields = []
        if search_in in ("all", "title"):
            fields.append("pe.title LIKE ?")
        if search_in in ("all", "description"):
            fields.append("pe.description LIKE ?")
        if search_in in ("all", "transcript"):
            fields.append("pe.transcript LIKE ?")

        if not fields:
            fields = ["pe.title LIKE ?"]

        where_clause = " OR ".join(fields)
        params = [like_pattern] * len(fields)

        with db_session() as conn:
            c = conn.cursor()

            c.execute(f'''SELECT pe.*, ps.title as podcast_title, ps.image_url as podcast_image_url
                FROM podcast_episodes pe
                JOIN podcast_subscriptions ps ON pe.podcast_id = ps.id
                WHERE ({where_clause})
                ORDER BY pe.published_at DESC
                LIMIT ? OFFSET ?''',
                params + [limit, offset])
            episodes = [dict(row) for row in c.fetchall()]

            c.execute(f'''SELECT COUNT(*) FROM podcast_episodes pe
                JOIN podcast_subscriptions ps ON pe.podcast_id = ps.id
                WHERE ({where_clause})''', params)
            total = c.fetchone()[0]

        # Kontext-Snippets extrahieren
        for ep in episodes:
            ep["match_context"] = self._extract_match_context(ep, query)

        return {"episodes": episodes, "total": total}

    def _extract_match_context(self, episode: dict, query: str) -> dict:
        """Extrahiert Treffer-Kontext aus Titel, Beschreibung, Transkript."""
        context = {"title": False, "description": None, "transcript": None}
        q_lower = query.lower()

        if q_lower in (episode.get("title") or "").lower():
            context["title"] = True

        desc = episode.get("description") or ""
        if q_lower in desc.lower():
            # HTML-Tags entfernen für Snippet
            import re
            clean = re.sub(r'<[^>]+>', ' ', desc)
            clean = re.sub(r'\s+', ' ', clean).strip()
            idx = clean.lower().find(q_lower)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(clean), idx + len(query) + 80)
                snippet = clean[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(clean):
                    snippet = snippet + "..."
                context["description"] = snippet

        transcript = episode.get("transcript") or ""
        if q_lower in transcript.lower():
            idx = transcript.lower().find(q_lower)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(transcript), idx + len(query) + 80)
                snippet = transcript[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(transcript):
                    snippet = snippet + "..."
                context["transcript"] = snippet

        return context

    async def search_subscriptions(self, query: str) -> list:
        """Sucht in lokalen Podcast-Abos (Titel, Autor)."""
        if not query or len(query) < 2:
            return []
        like_pattern = f"%{query}%"
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM podcast_subscriptions
                WHERE title LIKE ? OR author LIKE ?
                ORDER BY title''',
                (like_pattern, like_pattern))
            return [dict(row) for row in c.fetchall()]

    async def get_episode(self, episode_id: int) -> Optional[dict]:
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT pe.*, ps.title as podcast_title, ps.image_url as podcast_image_url
                FROM podcast_episodes pe
                JOIN podcast_subscriptions ps ON pe.podcast_id = ps.id
                WHERE pe.id = ?''', (episode_id,))
            row = c.fetchone()
            return dict(row) if row else None

    async def update_episode_position(self, episode_id: int, position: int) -> bool:
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE podcast_episodes SET resume_position = ? WHERE id = ?",
                     (position, episode_id))
            return c.rowcount > 0

    async def mark_played(self, episode_id: int) -> bool:
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE podcast_episodes SET is_played = 1, resume_position = 0 WHERE id = ?",
                      (episode_id,))
            return c.rowcount > 0

    async def mark_unplayed(self, episode_id: int) -> bool:
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE podcast_episodes SET is_played = 0 WHERE id = ?",
                      (episode_id,))
            return c.rowcount > 0

    async def mark_all_played(self, podcast_id: int) -> int:
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE podcast_episodes SET is_played = 1, resume_position = 0 WHERE podcast_id = ?",
                      (podcast_id,))
            return c.rowcount

    # =========================================================================
    # Bild-Download
    # =========================================================================

    async def download_image(self, url: str, podcast_id: int, episode_id: int = None) -> Optional[str]:
        """Bild herunterladen und lokal speichern"""
        if not url:
            return None

        image_dir = PODCAST_RECORDINGS_DIR / "images" / str(podcast_id)
        image_dir.mkdir(parents=True, exist_ok=True)

        filename = "cover.jpg" if not episode_id else f"ep_{episode_id}.jpg"
        target = image_dir / filename

        try:
            client = await self._get_client()
            resp = await client.get(url)
            if resp.status_code != 200:
                return None

            # Dateiendung aus Content-Type ableiten
            content_type = resp.headers.get("content-type", "")
            if "png" in content_type:
                target = target.with_suffix(".png")
            elif "webp" in content_type:
                target = target.with_suffix(".webp")

            target.write_bytes(resp.content)
            local_path = str(target)

            # DB aktualisieren
            with db_session() as conn:
                c = conn.cursor()
                if episode_id:
                    c.execute("UPDATE podcast_episodes SET local_image_path = ? WHERE id = ?",
                              (local_path, episode_id))
                else:
                    c.execute("UPDATE podcast_subscriptions SET local_image_path = ? WHERE id = ?",
                              (local_path, podcast_id))

            return local_path
        except Exception as e:
            print(f"Bild-Download fehlgeschlagen ({url}): {e}")
            return None

    def get_image_path(self, podcast_id: int, episode_id: int = None) -> Optional[Path]:
        """Lokalen Bild-Pfad ermitteln"""
        image_dir = PODCAST_RECORDINGS_DIR / "images" / str(podcast_id)

        if episode_id:
            # Episode-Bild suchen
            for ext in (".jpg", ".png", ".webp"):
                path = image_dir / f"ep_{episode_id}{ext}"
                if path.exists():
                    return path

        # Podcast-Cover als Fallback
        for ext in (".jpg", ".png", ".webp"):
            path = image_dir / f"cover{ext}"
            if path.exists():
                return path

        return None

    # =========================================================================
    # Episode-Download
    # =========================================================================

    async def download_episode(self, episode_id: int) -> dict:
        """Episode herunterladen"""
        if episode_id in self._downloading:
            return {"success": False, "error": "Download läuft bereits"}

        episode = await self.get_episode(episode_id)
        if not episode:
            return {"success": False, "error": "Episode nicht gefunden"}

        if episode.get("is_downloaded") and episode.get("local_path"):
            local = Path(episode["local_path"])
            if local.exists():
                return {"success": True, "already_downloaded": True, "path": str(local)}

        audio_url = episode.get("audio_url")
        if not audio_url:
            return {"success": False, "error": "Keine Audio-URL"}

        # Zielverzeichnis
        audio_dir = PODCAST_RECORDINGS_DIR / "audio" / str(episode["podcast_id"])
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Dateiendung aus URL ableiten
        url_path = audio_url.split("?")[0]
        ext = Path(url_path).suffix.lower()
        if ext not in AUDIO_MIMETYPES:
            ext = ".mp3"

        safe_title = _sanitize_filename(episode.get("title", "episode"))
        filename = f"{episode_id}_{safe_title}{ext}"
        target = audio_dir / filename

        # Speicherplatz prüfen
        total, used, free = shutil.disk_usage(DATA_DIR)
        if free < 100 * 1024 * 1024:  # 100 MB Minimum
            return {"success": False, "error": "Nicht genug Speicherplatz"}

        self._downloading.add(episode_id)
        try:
            client = await self._get_client()
            async with client.stream("GET", audio_url) as resp:
                if resp.status_code != 200:
                    return {"success": False, "error": f"HTTP {resp.status_code}"}

                file_size = 0
                with open(target, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        file_size += len(chunk)

            # DB aktualisieren
            with db_session() as conn:
                c = conn.cursor()
                c.execute('''UPDATE podcast_episodes
                    SET is_downloaded = 1, local_path = ?, file_size = ?
                    WHERE id = ?''', (str(target), file_size, episode_id))

            return {"success": True, "path": str(target), "size": file_size}

        except Exception as e:
            # Aufräumen bei Fehler
            if target.exists():
                target.unlink(missing_ok=True)
            return {"success": False, "error": str(e)}
        finally:
            self._downloading.discard(episode_id)

    async def download_episodes_batch(self, episode_ids: List[int]) -> dict:
        """Mehrere Episoden herunterladen"""
        results = {"total": len(episode_ids), "success": 0, "failed": 0, "skipped": 0}

        for eid in episode_ids:
            result = await self.download_episode(eid)
            if result.get("success"):
                if result.get("already_downloaded"):
                    results["skipped"] += 1
                else:
                    results["success"] += 1
            else:
                results["failed"] += 1

        return results

    async def delete_episode_download(self, episode_id: int) -> bool:
        """Lokale Episode-Datei löschen"""
        episode = await self.get_episode(episode_id)
        if not episode:
            return False

        if episode.get("local_path"):
            path = Path(episode["local_path"])
            if path.exists():
                path.unlink(missing_ok=True)

        with db_session() as conn:
            c = conn.cursor()
            c.execute('''UPDATE podcast_episodes
                SET is_downloaded = 0, local_path = NULL, file_size = 0
                WHERE id = ?''', (episode_id,))
            # Auch aus podcast_saved_episodes entfernen
            c.execute("DELETE FROM podcast_saved_episodes WHERE episode_id = ?", (episode_id,))

        return True

    def get_episode_audio_path(self, episode_id: int) -> Optional[Path]:
        """Lokalen Audio-Pfad einer Episode ermitteln"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT local_path FROM podcast_episodes WHERE id = ? AND is_downloaded = 1",
                      (episode_id,))
            row = c.fetchone()
            if row and row[0]:
                path = Path(row[0])
                if path.exists():
                    return path
        return None

    async def _auto_download_new(self, podcast_id: int):
        """Neue (ungehörte, nicht heruntergeladene) Episoden automatisch laden"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT id FROM podcast_episodes
                WHERE podcast_id = ? AND is_downloaded = 0 AND is_played = 0
                ORDER BY published_at DESC''', (podcast_id,))
            episode_ids = [row[0] for row in c.fetchall()]

        if episode_ids:
            await self.download_episodes_batch(episode_ids)

    async def delete_played_downloads(self, podcast_id: int = None) -> int:
        """Gehörte Downloads löschen (Speicher freigeben)"""
        where = "WHERE is_downloaded = 1 AND is_played = 1"
        params = []
        if podcast_id:
            where += " AND podcast_id = ?"
            params.append(podcast_id)

        deleted = 0
        with db_session() as conn:
            c = conn.cursor()
            c.execute(f"SELECT id, local_path FROM podcast_episodes {where}", params)
            rows = c.fetchall()

            for row in rows:
                if row[1]:
                    path = Path(row[1])
                    if path.exists():
                        path.unlink(missing_ok=True)
                        deleted += 1

                c.execute('''UPDATE podcast_episodes
                    SET is_downloaded = 0, local_path = NULL, file_size = 0
                    WHERE id = ?''', (row[0],))

        return deleted

    # =========================================================================
    # Transkription
    # =========================================================================

    async def get_transcript(self, episode_id: int) -> Optional[str]:
        """Transkript einer Episode holen -- aus Cache oder von URL laden"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT transcript, transcript_url FROM podcast_episodes WHERE id = ?",
                      (episode_id,))
            row = c.fetchone()
            if not row:
                return None

            # Bereits gecacht
            if row[0]:
                return row[0]

            # Kein Transkript verfügbar
            transcript_url = row[1]
            if not transcript_url:
                return None

        # Von URL herunterladen und cachen
        try:
            client = await self._get_client()
            resp = await client.get(transcript_url)
            if resp.status_code != 200:
                return None

            content_type = resp.headers.get("content-type", "")
            text = resp.text

            # SRT/VTT zu reinem Text konvertieren
            if any(x in transcript_url.lower() for x in [".srt", ".vtt"]) or \
               any(x in content_type for x in ["srt", "vtt"]):
                text = self._subtitle_to_text(text)

            # HTML-Tags entfernen falls nötig
            if "<" in text and ">" in text:
                text = re.sub(r'<[^>]+>', '', text)

            text = text.strip()
            if not text:
                return None

            # In DB cachen
            with db_session() as conn:
                c = conn.cursor()
                c.execute("UPDATE podcast_episodes SET transcript = ? WHERE id = ?",
                          (text, episode_id))

            return text

        except Exception as e:
            print(f"Transkript-Download fehlgeschlagen: {e}")
            return None

    def _subtitle_to_text(self, content: str) -> str:
        """SRT/VTT Untertitel zu reinem Text konvertieren"""
        lines = content.strip().split("\n")
        text_lines = []
        for line in lines:
            line = line.strip()
            # Zeitstempel und Nummern überspringen
            if not line:
                continue
            if re.match(r'^\d+$', line):
                continue
            if re.match(r'[\d:.,\-\s>]+$', line):
                continue
            if line.startswith("WEBVTT") or line.startswith("NOTE"):
                continue
            # HTML-Tags entfernen
            line = re.sub(r'<[^>]+>', '', line)
            if line:
                text_lines.append(line)
        return "\n".join(text_lines)

    # =========================================================================
    # Statistiken
    # =========================================================================

    async def get_stats(self) -> dict:
        """Umfassende Podcast-Statistiken"""
        total, used, free = shutil.disk_usage(DATA_DIR)

        with db_session() as conn:
            c = conn.cursor()

            c.execute("SELECT COUNT(*) FROM podcast_subscriptions")
            sub_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM podcast_episodes")
            ep_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM podcast_episodes WHERE is_downloaded = 1")
            dl_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM podcast_episodes WHERE is_played = 0")
            unplayed_count = c.fetchone()[0]

            c.execute("SELECT COALESCE(SUM(file_size), 0) FROM podcast_episodes WHERE is_downloaded = 1")
            dl_size = c.fetchone()[0]

        return {
            "subscriptions": sub_count,
            "episodes": ep_count,
            "downloaded": dl_count,
            "unplayed": unplayed_count,
            "download_size_mb": round(dl_size / (1024 * 1024), 1) if dl_size else 0,
            "disk_free_gb": round(free / (1024**3), 2),
        }

    async def get_storage_stats(self) -> dict:
        """Speicher-Statistiken (Kompatibilität)"""
        stats = await self.get_stats()
        return {
            "disk_free_gb": stats["disk_free_gb"],
            "saved_episodes": stats["downloaded"],
            "saved_size_mb": stats["download_size_mb"],
        }

    # =========================================================================
    # Feed-Parser
    # =========================================================================

    async def _parse_feed(self, feed_url: str) -> Optional[dict]:
        """RSS-Feed parsen mit iTunes-Namespace-Support"""
        try:
            client = await self._get_client()
            resp = await client.get(feed_url, headers={"User-Agent": "RadioHub/0.2"})

            if resp.status_code != 200:
                return None

            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if channel is None:
                return None

            itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
            podcast_ns = "{https://podcastindex.org/namespace/1.0}"

            # Podcast-Info
            title = self._get_text(channel, "title")
            author = self._get_text(channel, "itunes:author") or self._get_text(channel, "author")
            description = self._get_text(channel, "description")

            # Bild
            image_url = ""
            itunes_image = channel.find(f"{itunes_ns}image")
            if itunes_image is not None:
                image_url = itunes_image.get("href", "")
            if not image_url:
                image_el = channel.find("image/url")
                if image_el is not None:
                    image_url = image_el.text or ""

            # Kategorien
            categories = []
            for cat in channel.findall(f"{itunes_ns}category"):
                cat_text = cat.get("text", "")
                if cat_text:
                    categories.append(cat_text)
                # Subkategorien
                for subcat in cat.findall(f"{itunes_ns}category"):
                    sub_text = subcat.get("text", "")
                    if sub_text:
                        categories.append(sub_text)

            # Episoden
            episodes = []
            for item in channel.findall("item"):
                enclosure = item.find("enclosure")
                if enclosure is None:
                    continue

                audio_url = enclosure.get("url", "")
                if not audio_url:
                    continue

                guid = self._get_text(item, "guid") or audio_url
                ep_title = self._get_text(item, "title")
                ep_desc = self._get_text(item, "description") or self._get_text(item, "itunes:summary")
                pub_date = self._parse_pub_date(self._get_text(item, "pubDate"))

                # Episode-Bild
                ep_image = ""
                ep_itunes_image = item.find(f"{itunes_ns}image")
                if ep_itunes_image is not None:
                    ep_image = ep_itunes_image.get("href", "")

                # Duration
                duration = 0
                dur_text = self._get_text(item, "itunes:duration")
                if dur_text:
                    duration = self._parse_duration(dur_text)

                # Transkript-URL (podcast:transcript oder podlove:transcript)
                transcript_url = ""
                for transcript_tag in item.findall(f"{podcast_ns}transcript"):
                    url = transcript_tag.get("url", "")
                    mime = transcript_tag.get("type", "")
                    # Bevorzuge text/plain, text/html, application/srt, text/vtt
                    if url and mime in ("text/plain", "text/html", "text/vtt",
                                        "application/srt", "application/x-subrip"):
                        transcript_url = url
                        break
                    elif url and not transcript_url:
                        transcript_url = url

                episodes.append({
                    "guid": guid,
                    "title": ep_title,
                    "description": ep_desc,
                    "audio_url": audio_url,
                    "duration": duration,
                    "published_at": pub_date,
                    "image_url": ep_image,
                    "transcript_url": transcript_url,
                })

            return {
                "title": title,
                "author": author,
                "description": description,
                "image_url": image_url,
                "categories": categories,
                "episodes": episodes,
            }

        except Exception as e:
            print(f"Feed parse error: {e}")
            return None

    def _get_text(self, element, tag: str) -> str:
        """Text aus XML-Element holen"""
        if ":" in tag:
            ns, local = tag.split(":")
            namespaces = {
                "itunes": "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
            }
            tag = namespaces.get(ns, "") + local

        el = element.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    def _parse_duration(self, duration_str: str) -> int:
        """Duration-String zu Sekunden"""
        try:
            parts = duration_str.split(":")
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            else:
                return int(parts[0])
        except:
            return 0

    def _parse_pub_date(self, date_str: str) -> str:
        """RFC 2822 pubDate nach ISO 8601 konvertieren für korrekte Sortierung."""
        if not date_str:
            return ""
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            # Fallback: Original-String zurückgeben
            return date_str


# Singleton
podcast_service = PodcastService()
