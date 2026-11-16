"""RAD-2: Ausschlüsse vergleichen ganze Einträge, Filtersperren lassen sich mit Vorschau neu berechnen,
erneutes Abonnieren behält die Folgen."""

from __future__ import annotations

import uuid

import pytest

from backend import sender_merkmale
from backend.database import db_session
from backend.services import filtersperren
from backend.services.cache import cache_service
from backend.services.podcast import podcast_service

PRAEFIX = "rad2-"


def _sender(name: str, sprache: str = "", tags: str = "", stimmen: int = 10) -> str:
    kennung = PRAEFIX + uuid.uuid4().hex
    with db_session() as conn:
        conn.execute(
            "INSERT INTO stations (uuid, name, url, language, tags, votes, countrycode) VALUES (?, ?, ?, ?, ?, ?, 'XX')",
            (kennung, name, "https://example.invalid/" + kennung, sprache, tags, stimmen))
    return kennung


def _sperren(kennungen) -> dict[str, tuple[str, str]]:
    platz = ",".join("?" * len(kennungen))
    with db_session() as conn:
        return {z["uuid"]: (z["category"], z["reason"]) for z in conn.execute(
            f"SELECT uuid, category, reason FROM blocklist WHERE uuid IN ({platz})", list(kennungen))}


@pytest.fixture(autouse=True)
def _aufraeumen():
    yield
    with db_session() as conn:
        conn.execute("DELETE FROM blocklist WHERE uuid LIKE ?", (PRAEFIX + "%",))
        conn.execute("DELETE FROM favorites WHERE uuid LIKE ?", (PRAEFIX + "%",))
        conn.execute("DELETE FROM stations WHERE uuid LIKE ?", (PRAEFIX + "%",))


def test_eintraege_werden_ganz_verglichen():
    assert sender_merkmale.eintraege(" German, swiss german ,,ENGLISH") == {"german", "swiss german", "english"}
    gesucht = sender_merkmale.liste_als_parameter(["ger", " English "])
    assert sender_merkmale.trifft("german", gesucht) == 0
    assert sender_merkmale.trifft("german,english", gesucht) == 1
    assert sender_merkmale.trifft(None, gesucht) == 0


def test_suche_schliesst_kuerzel_nicht_als_wortteil_aus():
    deutsch = _sender(PRAEFIX + "Deutsch", sprache="german")
    kuerzel = _sender(PRAEFIX + "Kürzel", sprache="ger")
    treffer = cache_service.search_stations(q=PRAEFIX, exclude_languages=["ger"], limit=50)
    gefunden = {s["uuid"] for s in treffer}
    assert deutsch in gefunden
    assert kuerzel not in gefunden


def test_neu_berechnen_gibt_frei_und_laesst_hand_und_werbung_in_ruhe():
    deutsch = _sender(PRAEFIX + "Deutsch", sprache="german")
    russisch = _sender(PRAEFIX + "Russisch", sprache="russian,english")
    hand = _sender(PRAEFIX + "Hand", sprache="german")
    werbung = _sender(PRAEFIX + "Werbung", sprache="russian")
    with db_session() as conn:
        # Altbestand: Wortteil-Sperren mit der ganzen Liste als Grund
        for kennung in (deutsch, russisch):
            conn.execute("INSERT INTO blocklist (uuid, name, reason, category) VALUES (?, 'x', ?, 'filter')",
                         (kennung, "language:ger, language:russian"))
        conn.execute("INSERT INTO blocklist (uuid, name, reason, category) VALUES (?, 'x', 'manual', 'manual')", (hand,))
        conn.execute("INSERT INTO blocklist (uuid, name, reason, category) VALUES (?, 'x', 'ad', 'ad')", (werbung,))
        conn.execute("INSERT INTO favorites (uuid, name, url) VALUES (?, ?, 'https://example.invalid')",
                     (deutsch, PRAEFIX + "Deutsch"))

    kriterien = filtersperren.FilterKriterien(sprachen=["ger", "russian"])
    with db_session() as conn:
        vorschau = filtersperren.abgleichen(conn, kriterien)
    assert deutsch in {s.uuid for s in vorschau.frei}
    assert PRAEFIX + "Deutsch" in vorschau.favoriten_frei
    assert _sperren([deutsch])[deutsch][0] == "filter", "Vorschau ändert nichts"

    with db_session() as conn:
        filtersperren.anwenden(conn, kriterien)
    sperren = _sperren([deutsch, russisch, hand, werbung])
    assert deutsch not in sperren
    assert sperren[russisch] == ("filter", "language:russian")
    assert sperren[hand] == ("manual", "manual")
    assert sperren[werbung] == ("ad", "ad")


def test_vorschau_und_ausblenden_ueber_die_schnittstelle(client):
    deutsch = _sender(PRAEFIX + "Deutsch", sprache="german")
    kuerzel = _sender(PRAEFIX + "Kürzel", sprache="ger")
    kriterien = {"excluded_languages": ["ger"], "excluded_tags": [], "min_votes": 0}
    vorschau = client.post("/api/filters/preview", json=kriterien).json()
    assert kuerzel in {s["uuid"] for s in vorschau["sample"]}
    assert deutsch not in {s["uuid"] for s in vorschau["sample"]}
    client.post("/api/filters/push", json=kriterien)
    sperren = _sperren([deutsch, kuerzel])
    assert sperren == {kuerzel: ("filter", "language:ger")}


async def test_erneutes_abonnieren_behaelt_folgen(monkeypatch):
    feed_url = "https://example.invalid/" + PRAEFIX + uuid.uuid4().hex + ".xml"
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


def test_fruehere_ausschluesse_bleiben_beim_neu_berechnen():
    fernsehen = _sender(PRAEFIX + "Fernsehen", sprache="german", tags="tv,news")
    deutsch = _sender(PRAEFIX + "Deutsch", sprache="german", tags="news")
    with db_session() as conn:
        for kennung in (fernsehen, deutsch):
            conn.execute("INSERT INTO blocklist (uuid, name, reason, category) VALUES (?, 'x', ?, 'filter')",
                         (kennung, "language:ger, tag:tv, votes<3"))
        aus_sperren = filtersperren.kriterien_aus_sperren(conn)
        assert {"ger"} <= set(aus_sperren.sprachen) and "tv" in aus_sperren.tags and aus_sperren.mindeststimmen >= 3
        kriterien = filtersperren.FilterKriterien(sprachen=["russian"]).vereinigt(
            filtersperren.FilterKriterien(sprachen=["ger"], tags=["tv"]))
        filtersperren.anwenden(conn, kriterien)
    sperren = _sperren([fernsehen, deutsch])
    assert sperren == {fernsehen: ("filter", "tag:tv")}
