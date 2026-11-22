"""Podcast-Folgen: Download landet in der Ablage unter Podcasts/<Abo>/, Wiedergabe von dort, Löschen in den
Papierkorb."""

from __future__ import annotations

import uuid

import httpx

from app.config import get_arbeit_dir
from app.database import db_session
from app.services.podcast import podcast_service


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


async def test_erneutes_abonnieren_behaelt_folgen(monkeypatch):
    """RAD-2: erneutes Abonnieren frischt nur die Angaben des Feeds auf und behält Folgen mit Hörstand."""
    feed_url = "https://example.invalid/rad2-" + uuid.uuid4().hex + ".xml"
    feed = {"title": "Probe", "author": "A", "description": "", "image_url": "", "categories": [],
            "episodes": [{"guid": "f1", "title": "Folge 1", "description": "", "audio_url": "https://example.invalid/1.mp3"}]}

    async def lesen(url):
        return feed

    monkeypatch.setattr(podcast_service, "_parse_feed", lesen)
    erst = await podcast_service.subscribe(feed_url)
    with db_session() as conn:
        conn.execute("UPDATE podcast_episodes SET resume_position = 123 WHERE podcast_id = ?", (erst["id"],))

    feed["title"] = "Probe neu"
    wieder = await podcast_service.subscribe(feed_url)
    try:
        assert wieder["id"] == erst["id"]
        with db_session() as conn:
            titel = conn.execute("SELECT title FROM podcast_subscriptions WHERE id = ?", (erst["id"],)).fetchone()[0]
            stand = conn.execute("SELECT resume_position FROM podcast_episodes WHERE podcast_id = ?",
                                 (erst["id"],)).fetchone()[0]
        assert titel == "Probe neu"
        assert stand == 123
    finally:
        with db_session() as conn:
            conn.execute("DELETE FROM podcast_subscriptions WHERE id = ?", (erst["id"],))


def test_abo_anheften_und_sortierung_merken(client):
    with db_session() as conn:
        ids = [conn.execute("INSERT INTO podcast_subscriptions (feed_url, title, sort_order) VALUES (?, ?, ?)",
                            (f"https://feed.test/{uuid.uuid4().hex}", titel, n)).lastrowid for n, titel in enumerate(["Erst", "Zweit", "Dritt"])]
    assert client.put(f"/api/podcasts/{ids[2]}/anheften", json={"an": True}).status_code == 200
    assert client.put(f"/api/podcasts/{ids[1]}/sortierung", json={"sortierung": "alt"}).status_code == 200
    assert client.put(f"/api/podcasts/{ids[1]}/sortierung", json={"sortierung": "boese"}).status_code == 422
    assert client.put("/api/podcasts/999999/anheften", json={"an": True}).status_code == 404
    abos = [a for a in client.get("/api/podcasts/subscriptions").json()["subscriptions"] if a["id"] in ids]
    assert [a["title"] for a in abos] == ["Dritt", "Erst", "Zweit"]                       # angeheftet zuerst
    assert {a["title"]: (a["angeheftet"], a["sortierung"]) for a in abos} == {"Dritt": (1, ""), "Erst": (0, ""), "Zweit": (0, "alt")}


async def test_folge_als_datei_aufs_geraet(client, speicher, monkeypatch):
    inhalt = b"c" * 300
    _quelle(inhalt)
    gespeichert = _folge("Datei", "Gespeichert?")
    await podcast_service.download_episode(gespeichert)
    antwort = client.get(f"/api/podcasts/episodes/{gespeichert}/datei")
    assert antwort.status_code == 200 and antwort.content == inhalt
    assert antwort.headers["content-disposition"] == "attachment; filename*=UTF-8''2026-10-01%20Gespeichert.mp3"

    from app.routers import podcasts as router_podcasts
    gesehen = {}

    async def durchleiten(adresse, bereich=None, zusatz=None):
        gesehen.update(adresse=adresse, zusatz=zusatz)
        from fastapi.responses import Response
        return Response(b"x", headers=zusatz)

    monkeypatch.setattr(router_podcasts.durchleiter, "durchleiten", durchleiten)
    nur_im_netz = _folge("Datei", "Nur im Netz")
    antwort = client.get(f"/api/podcasts/episodes/{nur_im_netz}/datei")
    assert antwort.status_code == 200 and gesehen["adresse"] == "https://audio.test/folge.mp3?token=1"
    assert gesehen["zusatz"]["Content-Disposition"] == "attachment; filename*=UTF-8''2026-10-01%20Nur%20im%20Netz.mp3"
    assert client.get("/api/podcasts/episodes/999999/datei").status_code == 404


def test_ordner_gruppieren_und_loesen(client):
    with db_session() as conn:
        abos = [conn.execute("INSERT INTO podcast_subscriptions (feed_url, title) VALUES (?, ?)",
                             (f"https://feed.test/{uuid.uuid4().hex}", t)).lastrowid for t in ("Eins", "Zwei")]
    a = client.post("/api/podcast-ordner", json={"name": " Nachrichten "}).json()
    b = client.post("/api/podcast-ordner", json={"name": "Wissen"}).json()
    assert a["name"] == "Nachrichten" and len(a["id"]) == 32 and b["reihenfolge"] == a["reihenfolge"] + 1
    assert client.post("/api/podcast-ordner", json={"name": ""}).status_code == 422
    assert client.put(f"/api/podcast-ordner/abo/{abos[0]}", json={"ordner_id": a["id"]}).status_code == 200
    assert client.put(f"/api/podcast-ordner/abo/{abos[1]}", json={"ordner_id": "gibtsnicht"}).status_code == 404
    assert client.put(f"/api/podcast-ordner/{a['id']}", json={"name": "Nachrichten am Morgen", "offen": False}).json()["offen"] is False
    client.put("/api/podcast-ordner/reihenfolge", json={"ids": [b["id"], a["id"]]})
    namen = [o["name"] for o in client.get("/api/podcast-ordner").json()["ordner"] if o["id"] in (a["id"], b["id"])]
    assert namen == ["Wissen", "Nachrichten am Morgen"]
    subs = {x["id"]: x for x in client.get("/api/podcasts/subscriptions").json()["subscriptions"]}
    assert subs[abos[0]]["ordner_id"] == a["id"] and subs[abos[1]]["ordner_id"] is None
    assert client.delete(f"/api/podcast-ordner/{a['id']}").json() == {"success": True, "geloest": 1}
    subs = {x["id"]: x for x in client.get("/api/podcasts/subscriptions").json()["subscriptions"]}
    assert subs[abos[0]]["ordner_id"] is None and subs[abos[0]]["title"] == "Eins"           # das Abo bleibt
    assert client.delete(f"/api/podcast-ordner/{a['id']}").status_code == 404
    client.delete(f"/api/podcast-ordner/{b['id']}")


def test_suche_mit_abo_wahl_und_filter(client):
    """RAD-44: die Suche gilt innerhalb der gewählten Abos und des Filters, wie die Liste ohne Suchtext."""
    spektrum = _folge("Spektrum", "Hugging-Face-Vorfall: Wie gefährlich ist KI?")
    bits = _folge("Bits und so", "Hugging Face in der Praxis")
    andere = _folge("Bits und so", "Neue Macs")
    with db_session() as conn:
        abo_bits = conn.execute("SELECT podcast_id FROM podcast_episodes WHERE id = ?", (bits,)).fetchone()[0]
        conn.execute("UPDATE podcast_episodes SET podcast_id = ? WHERE id = ?", (abo_bits, andere))
        conn.execute("UPDATE podcast_episodes SET is_downloaded = 1 WHERE id = ?", (bits,))
    ids = lambda **p: [e["id"] for e in client.get("/api/podcasts/episodes/all", params=p).json()["episodes"]]
    assert set(ids(q="hugging")) >= {spektrum, bits}
    assert ids(q="hugging", podcast_ids=str(abo_bits)) == [bits]
    assert ids(q="hugging", podcast_ids=str(abo_bits), filter_status="unplayed") == [bits]
    assert ids(q="macs", podcast_ids=str(abo_bits), filter_status="downloaded") == []
    assert client.get("/api/podcasts/episodes/all", params={"q": "h"}).status_code == 422


def test_abo_nennt_ob_ein_cover_da_ist(monkeypatch, tmp_path):
    """RAD-85: ohne Cover im Zwischenspeicher meldet das Abo hat_bild False, die Oberfläche fragt dann kein Bild an"""
    from pathlib import Path
    from app.services.podcast import podcast_service
    monkeypatch.setattr(podcast_service, "get_image_path", lambda pid, episode_id=None: Path(tmp_path / "cover.jpg") if pid == 1 else None)
    assert podcast_service._mit_bildangabe({"id": 1})["hat_bild"] is True
    assert podcast_service._mit_bildangabe({"id": 2})["hat_bild"] is False
