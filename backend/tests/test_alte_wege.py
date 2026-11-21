"""RAD-7: die alten Wege der heutigen Oberfläche (/api/stations/search, /api/filters/*, /api/blocklist, Werbung) laufen
auf der neuen Sichtbarkeit: eine Wahrheit, Ausschlüsse als lebende Regeln, Sperren als Einzelsperre, Freigeben ohne
Löschen. Die Ausschlüsse vergleichen ganze Einträge (RAD-2: "ger" traf "german")."""

from __future__ import annotations

import uuid as uuid_modul

import pytest

from app.database import db_session
from app.services.senderquelle import dienst

PRAEFIX = "rad7a-"
NAME = "Rad7Alt"


def _sender(name: str, sprache: str = "german", tags: str = "", stimmen: int = 10) -> str:
    kennung = PRAEFIX + uuid_modul.uuid4().hex
    with db_session() as conn:
        conn.execute("INSERT INTO stations (uuid, name, url, language, tags, votes, countrycode, lastcheckok) "
                     "VALUES (?, ?, ?, ?, ?, ?, 'XX', 1)",
                     (kennung, f"{NAME} {name}", "https://example.invalid/" + kennung, sprache, tags, stimmen))
    return kennung


@pytest.fixture
def alt(client):
    yield client
    with db_session() as conn:
        for tabelle, spalte in (("stations", "uuid"), ("favorites", "uuid"), ("sender_sperre", "uuid"),
                                ("sender_freigabe", "uuid"), ("station_ad_status", "station_uuid")):
            conn.execute(f"DELETE FROM {tabelle} WHERE {spalte} LIKE ?", (PRAEFIX + "%",))
        conn.execute("DELETE FROM regel WHERE herkunft = 'nutzer'")
    client.portal.call(dienst.aufbereiten)


def _suche(c, **mehr) -> set[str]:
    antwort = c.post("/api/stations/search", json={"q": NAME, "limit": 100, **mehr})
    assert antwort.status_code == 200
    return {s["uuid"] for s in antwort.json()["stations"]}


def test_vorschau_und_ausblenden_vergleichen_ganze_eintraege(alt):
    deutsch = _sender("Deutsch", sprache="german")
    kuerzel = _sender("Kürzel", sprache="ger")
    alt.portal.call(dienst.aufbereiten)
    kriterien = {"excluded_languages": ["ger"], "excluded_tags": [], "min_votes": 0}
    vorschau = alt.post("/api/filters/preview", json=kriterien).json()
    assert {s["uuid"] for s in vorschau["sample"]} >= {kuerzel} and deutsch not in {s["uuid"] for s in vorschau["sample"]}
    assert _suche(alt) == {deutsch, kuerzel}, "Vorschau ändert nichts"
    ergebnis = alt.post("/api/filters/push", json=kriterien).json()
    assert ergebnis["hidden_count"] >= 1
    assert _suche(alt) == {deutsch}
    # erneutes Ausblenden mit derselben Liste legt keine zweite Regel an
    assert alt.post("/api/filters/push", json=kriterien).json()["hidden_count"] == 0
    regeln = [r for r in alt.get("/api/radio/regeln").json()["regeln"] if r["art"] == "sprache"]
    assert len(regeln) == 1 and regeln[0]["entwurf"]["eintraege"] == ["ger"]
    # die Ausschlüsse der Anfrage gelten nicht mehr eigens (die Regel ist die Wahrheit)
    assert _suche(alt, exclude_languages=["german"]) == {deutsch}


def test_ausgeblendete_liste_und_freigeben_ohne_loeschen(alt):
    hand = _sender("Hand")
    fernsehen = _sender("Fernsehen", tags="tv")
    alt.portal.call(dienst.aufbereiten)
    assert alt.post("/api/blocklist", json={"uuid": hand, "name": "x", "reason": "manual"}).json()["success"]
    alt.post("/api/filters/push", json={"excluded_languages": [], "excluded_tags": ["tv"], "min_votes": 0})
    assert _suche(alt) == set()
    verborgen = {s["uuid"]: s for s in alt.get("/api/filters/hidden").json()["stations"]}
    assert verborgen[hand]["category"] == "manual" and verborgen[hand]["reason"] == "Einzeln ausgeblendet"
    assert verborgen[fernsehen]["category"] == "filter" and verborgen[fernsehen]["reason"] == "Tag ist tv"
    assert alt.get(f"/api/blocklist/check/{hand}").json()["blocked"]

    assert alt.post("/api/filters/release", json={"uuids": [fernsehen]}).json()["released_count"] == 1
    assert _suche(alt) == {fernsehen}                                  # als Ausnahme freigegeben
    assert alt.post("/api/filters/release", json={"reason": "Tag ist tv"}).json()["released_count"] == 0
    assert alt.delete(f"/api/blocklist/{hand}").json()["success"]
    assert _suche(alt) == {hand, fernsehen}
    assert alt.delete(f"/api/blocklist/{hand}").status_code == 404
    with db_session() as conn:
        assert conn.execute("SELECT COUNT(*) FROM regel WHERE art = 'tag'").fetchone()[0] == 1, "nichts gelöscht"


def test_nur_favoriten_wirkt_mit_den_anderen_filtern(alt):
    favorit = _sender("Favorit", stimmen=500)
    _sender("Kein Favorit", stimmen=600)
    leise = _sender("Leiser Favorit", stimmen=1)
    with db_session() as conn:
        for kennung in (favorit, leise):
            conn.execute("INSERT INTO favorites (uuid, name, url) VALUES (?, 'f', 'https://example.invalid')", (kennung,))
    alt.portal.call(dienst.aufbereiten)
    assert _suche(alt, favs_only=True, votes_min=100, sort_by="votes") == {favorit}   # früher: SQL-Fehler, Filter weg


def test_werbung_als_entscheidung_statt_sperrliste(alt):
    werbung = _sender("Werbung")
    alt.portal.call(dienst.aufbereiten)
    alt.post("/api/radio/regeln", json={"art": "werbung", "stufe": "eigene"})
    alt.post("/api/blocklist", json={"uuid": werbung, "name": "x", "reason": "ad:manual"})
    assert _suche(alt) == set()
    with db_session() as conn:
        assert conn.execute("SELECT user_action FROM station_ad_status WHERE station_uuid = ?", (werbung,)).fetchone()[0] \
            == "blocked"
        assert conn.execute("SELECT COUNT(*) FROM blocklist WHERE uuid = ?", (werbung,)).fetchone()[0] == 0
    assert alt.post("/api/ad-detection/false-positive", json={"uuid": werbung}).status_code == 200
    assert _suche(alt) == {werbung}
    # geprüft wird nur ein bekannter Sender über seine Kennung
    assert alt.post("/api/ad-detection/check", json={"uuid": "rad7a-gibt-es-nicht",
                                                      "stream_url": "http://192.168.0.1/"}).status_code == 404


def test_sprachen_und_laender_der_filter_einstellungen(alt):
    _sender("A", sprache="swiss german,german")
    alt.portal.call(dienst.aufbereiten)
    sprachen = {s["name"]: s["count"] for s in alt.get("/api/filters/languages").json()["languages"]}
    assert sprachen["swiss german"] >= 1 and sprachen["german"] >= 1
    laender = {l["code"] for l in alt.get("/api/filters/countries").json()["countries"]}
    assert "XX" in laender
