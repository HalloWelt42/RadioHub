"""
RadioHub v0.1.6 - Podcast Service

Podcast-Suche (iTunes + fyyd), Abonnements, Episoden, Downloads
"""
import httpx
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from xml.etree import ElementTree as ET

from ..database import db_session
from ..config import get_podcast_recordings_dir, DATA_DIR


@dataclass
class PodcastSearchResult:
    title: str
    author: str
    feed_url: str
    image_url: str
    description: str
    source: str  # "itunes" oder "fyyd"


class PodcastService:
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if not self.client:
            self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self.client
    
    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
    
    # === Suche ===
    
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
        """iTunes Podcast-Suche"""
        try:
            client = await self._get_client()
            url = "https://itunes.apple.com/search"
            params = {
                "term": query,
                "media": "podcast",
                "limit": limit
            }
            
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            results = []
            
            for item in data.get("results", []):
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
        """fyyd Podcast-Suche"""
        try:
            client = await self._get_client()
            url = f"https://api.fyyd.de/0.2/search/podcast"
            params = {"title": query, "count": limit}
            
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            results = []
            
            for item in data.get("data", []):
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
    
    # === Abonnements ===
    
    async def subscribe(self, feed_url: str) -> Optional[dict]:
        """Podcast abonnieren"""
        # Feed laden und parsen
        feed_data = await self._parse_feed(feed_url)
        if not feed_data:
            return None
        
        # In DB speichern
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
            
            # Episoden speichern
            for ep in feed_data.get("episodes", [])[:100]:  # Max 100 Episoden
                c.execute('''INSERT OR IGNORE INTO podcast_episodes 
                    (podcast_id, guid, title, description, audio_url, duration, published_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (podcast_id, ep["guid"], ep["title"],
                     ep["description"][:1000] if ep["description"] else "",
                     ep["audio_url"], ep.get("duration", 0), ep.get("published_at")))
        
        return {"id": podcast_id, "title": feed_data["title"], "feed_url": feed_url}
    
    async def unsubscribe(self, podcast_id: int) -> bool:
        """Podcast-Abo entfernen"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM podcast_subscriptions WHERE id = ?", (podcast_id,))
            return c.rowcount > 0
    
    async def get_subscriptions(self) -> List[dict]:
        """Alle Abos holen"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT ps.*, 
                (SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ps.id) as episode_count
                FROM podcast_subscriptions ps ORDER BY title''')
            return [dict(row) for row in c.fetchall()]
    
    async def get_subscription(self, podcast_id: int) -> Optional[dict]:
        """Einzelnes Abo holen"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM podcast_subscriptions WHERE id = ?", (podcast_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    async def refresh_podcast(self, podcast_id: int) -> bool:
        """Podcast-Feed neu laden"""
        sub = await self.get_subscription(podcast_id)
        if not sub:
            return False
        
        feed_data = await self._parse_feed(sub["feed_url"])
        if not feed_data:
            return False
        
        with db_session() as conn:
            c = conn.cursor()
            
            # Podcast aktualisieren
            c.execute('''UPDATE podcast_subscriptions SET 
                title = ?, author = ?, description = ?, image_url = ?, last_updated = ?
                WHERE id = ?''',
                (feed_data["title"], feed_data["author"],
                 feed_data["description"][:1000] if feed_data["description"] else "",
                 feed_data["image_url"], datetime.now().isoformat(), podcast_id))
            
            # Neue Episoden hinzufügen
            for ep in feed_data.get("episodes", [])[:100]:
                c.execute('''INSERT OR IGNORE INTO podcast_episodes 
                    (podcast_id, guid, title, description, audio_url, duration, published_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (podcast_id, ep["guid"], ep["title"],
                     ep["description"][:1000] if ep["description"] else "",
                     ep["audio_url"], ep.get("duration", 0), ep.get("published_at")))
        
        return True
    
    # === Episoden ===
    
    async def get_episodes(self, podcast_id: int, limit: int = 50, offset: int = 0) -> dict:
        """Episoden eines Podcasts"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM podcast_episodes 
                WHERE podcast_id = ? ORDER BY published_at DESC LIMIT ? OFFSET ?''',
                (podcast_id, limit, offset))
            episodes = [dict(row) for row in c.fetchall()]
            
            c.execute("SELECT COUNT(*) FROM podcast_episodes WHERE podcast_id = ?", (podcast_id,))
            total = c.fetchone()[0]
        
        return {"episodes": episodes, "total": total}
    
    async def get_episode(self, episode_id: int) -> Optional[dict]:
        """Einzelne Episode"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM podcast_episodes WHERE id = ?", (episode_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    async def update_episode_position(self, episode_id: int, position: int) -> bool:
        """Resume-Position speichern"""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE podcast_episodes SET resume_position = ? WHERE id = ?",
                     (position, episode_id))
            return c.rowcount > 0
    
    # === Storage ===
    
    async def get_storage_stats(self) -> dict:
        """Speicher-Statistiken für Podcasts"""
        podcast_dir = get_podcast_recordings_dir()
        
        total, used, free = shutil.disk_usage(DATA_DIR)
        
        # Gespeicherte Episoden zählen
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*), COALESCE(SUM(size_mb), 0) FROM podcast_saved_episodes")
            row = c.fetchone()
            saved_count = row[0]
            saved_size = row[1]
        
        return {
            "disk_free_gb": round(free / (1024**3), 2),
            "saved_episodes": saved_count,
            "saved_size_mb": round(saved_size, 2)
        }
    
    # === Feed Parser ===
    
    async def _parse_feed(self, feed_url: str) -> Optional[dict]:
        """RSS-Feed parsen"""
        try:
            client = await self._get_client()
            resp = await client.get(feed_url, headers={"User-Agent": "RadioHub/0.1"})
            
            if resp.status_code != 200:
                return None
            
            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if channel is None:
                return None
            
            # Podcast-Info
            title = self._get_text(channel, "title")
            author = self._get_text(channel, "itunes:author") or self._get_text(channel, "author")
            description = self._get_text(channel, "description")
            
            # Bild
            image_url = ""
            itunes_image = channel.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
            if itunes_image is not None:
                image_url = itunes_image.get("href", "")
            if not image_url:
                image_el = channel.find("image/url")
                if image_el is not None:
                    image_url = image_el.text or ""
            
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
                pub_date = self._get_text(item, "pubDate")
                
                # Duration parsen
                duration = 0
                dur_text = self._get_text(item, "itunes:duration")
                if dur_text:
                    duration = self._parse_duration(dur_text)
                
                episodes.append({
                    "guid": guid,
                    "title": ep_title,
                    "description": ep_desc,
                    "audio_url": audio_url,
                    "duration": duration,
                    "published_at": pub_date
                })
            
            return {
                "title": title,
                "author": author,
                "description": description,
                "image_url": image_url,
                "episodes": episodes
            }
            
        except Exception as e:
            print(f"Feed parse error: {e}")
            return None
    
    def _get_text(self, element, tag: str) -> str:
        """Text aus XML-Element holen"""
        # Namespace-Handling
        if ":" in tag:
            ns, local = tag.split(":")
            namespaces = {
                "itunes": "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
            }
            tag = namespaces.get(ns, "") + local
        
        el = element.find(tag)
        return el.text.strip() if el is not None and el.text else ""
    
    def _parse_duration(self, duration_str: str) -> int:
        """Duration-String zu Sekunden parsen"""
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


# Singleton
podcast_service = PodcastService()
