"""Podcast-Folgen: Download landet in der Ablage unter Podcasts/<Abo>/, Wiedergabe von dort, Löschen in den
Papierkorb."""

from __future__ import annotations

import uuid

import httpx

from backend.config import get_arbeit_dir
from backend.database import db_session
from backend.services.podcast import podcast_service


def _folge(abo: str, titel: str) -> int:
    with db_session() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO podcast_subscriptions (feed_url, title) VALUES (?, ?)",
                  (f"https://feed.test/{uuid.uuid4().hex}", abo))
        podcast_id = c.lastrowid
        c.execute("""INSERT INTO podcast_episodes (podcast_id, guid, title, audio_url, published_at)
                     VALUES (?, ?, ?, ?, ?)""",
                  (podcast_id, uuid.uuid4().hex, titel, "https://audio.test/folge.mp3?token=1", "2026-10-01 06:00:00"))
        return c.lastrowid


def _quelle(inhalt: bytes):
    def antwort(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "audio.test"
        return httpx.Response(200, content=inhalt)
    podcast_service.client = httpx.AsyncClient(transport=httpx.MockTransport(antwort))


async def test_download_landet_in_der_ablage(client, speicher):
    inhalt = bytes(range(256)) * 40
    _quelle(inhalt)
    episode_id = _folge("Zeitfragen: Wissen", "Folge 1: Anfang?")
    ergebnis = await podcast_service.download_episode(episode_id)
    assert ergebnis["success"], ergebnis
    pfad = "Podcasts/Zeitfragen Wissen/2026-10-01 Folge 1 Anfang.mp3"
    assert ergebnis["path"] == pfad and speicher.dateien[pfad] == inhalt
    assert not any(get_arbeit_dir("downloads").iterdir())
    episode = await podcast_service.get_episode(episode_id)
    assert episode["is_downloaded"] == 1 and episode["local_path"] == pfad and episode["file_size"] == len(inhalt)

    wieder = await podcast_service.download_episode(episode_id)
    assert wieder.get("already_downloaded") is True

    teil = client.get(f"/api/podcasts/episodes/{episode_id}/play", headers={"Range": "bytes=0-9"})
    assert teil.status_code == 206 and teil.content == inhalt[:10]

    dateien = client.get("/api/files/podcasts").json()
    ordner = next(f for f in dateien["folders"] if f["name"] == "Zeitfragen Wissen")
    assert ordner["orphaned"] is False and ordner["files"][0]["path"] == pfad

    assert client.delete(f"/api/podcasts/episodes/{episode_id}/download").status_code == 200
    assert pfad in speicher.papierkorb
    assert (await podcast_service.get_episode(episode_id))["is_downloaded"] == 0


async def test_gleicher_name_bekommt_einen_zaehler(speicher):
    _quelle(b"a" * 100)
    erste = await podcast_service.download_episode(_folge("Doppelt", "Gleich"))
    zweite_id = _folge("Doppelt", "Gleich")
    zweite = await podcast_service.download_episode(zweite_id)
    assert erste["path"] == "Podcasts/Doppelt/2026-10-01 Gleich.mp3"
    assert zweite["path"] == "Podcasts/Doppelt/2026-10-01 Gleich (2).mp3"


async def test_gehoerte_downloads_loeschen(speicher):
    _quelle(b"b" * 100)
    episode_id = _folge("Gehört", "Schon gehört")
    pfad = (await podcast_service.download_episode(episode_id))["path"]
    await podcast_service.mark_played(episode_id)
    with db_session() as conn:
        podcast_id = conn.execute("SELECT podcast_id FROM podcast_episodes WHERE id = ?", (episode_id,)).fetchone()[0]
    assert await podcast_service.delete_played_downloads(podcast_id) == 1
    assert pfad in speicher.papierkorb
