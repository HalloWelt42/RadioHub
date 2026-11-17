"""RAD-7: Überführung der heutigen Sperren in lebende Regeln: die Vorschau ändert nichts und nennt jede Änderung der
Sichtbarkeit mit Grund; angewendet bleiben dieselben Sender sichtbar (Favoriten als Ausnahme), die Sperrliste bleibt
stehen, ein zweiter Lauf lehnt ab."""

from __future__ import annotations

import json
import uuid as uuid_modul

import pytest

from app import database
from app.database import db_session
from app.services.senderquelle import dienst, ueberfuehrung
from app.werkzeuge import regeln_ueberfuehren

PRAEFIX = "rad7u-"


def _sender(name: str, sprache: str = "german", tags: str = "", stimmen: int = 10) -> str:
    kennung = PRAEFIX + uuid_modul.uuid4().hex
    with db_session() as conn:
        conn.execute("INSERT INTO stations (uuid, name, url, language, tags, votes, countrycode, lastcheckok) "
                     "VALUES (?, ?, ?, ?, ?, ?, 'XX', 1)", (kennung, name, "https://example.invalid/" + kennung, sprache,
                                                           tags, stimmen))
    return kennung


@pytest.fixture
def bestand():
    with db_session() as conn:
        config = dict(conn.execute("SELECT key, value FROM config WHERE key LIKE 'filter_%'").fetchall())
        regeln_vorher = {z[0] for z in conn.execute("SELECT id FROM regel")}
    yield
    with db_session() as conn:
        for tabelle, spalte in (("stations", "uuid"), ("favorites", "uuid"), ("blocklist", "uuid"),
                                ("sender_sperre", "uuid"), ("station_ad_status", "station_uuid")):
            conn.execute(f"DELETE FROM {tabelle} WHERE {spalte} LIKE ?", (PRAEFIX + "%",))
        conn.execute("DELETE FROM regel WHERE id NOT IN (SELECT value FROM json_each(?))", (json.dumps(sorted(regeln_vorher)),))
        conn.execute("DELETE FROM config WHERE key LIKE 'filter_%'")
        conn.executemany("INSERT INTO config (key, value) VALUES (?, ?)", list(config.items()))
        conn.execute("DELETE FROM cache_meta WHERE key = ?", (ueberfuehrung.UEBERFUEHRT,))


async def _aufbereiten() -> None:
    await database.oeffnen()
    try:
        await dienst.aufbereiten()
    finally:
        await database.schliessen()


async def test_vorschau_aendert_nichts_und_anwenden_haelt_die_sichtbarkeit(bestand):
    deutsch = _sender("Deutsch", sprache="german")
    kuerzel = _sender("Kürzel", sprache="deu")                 # genauer Eintrag, nicht ganz Deutsch
    fernsehen = _sender("Fernsehen", tags="webcam")
    hand = _sender("Hand")
    werbung = _sender("Werbung")
    favorit = _sender("Favorit gesperrt")
    with db_session() as conn:
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('filter_excluded_languages', ?)",
                     (json.dumps(["deu"]),))
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('filter_excluded_tags', '[]')")
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('filter_min_votes', '0')")
        conn.executemany("INSERT INTO blocklist (uuid, name, reason, category) VALUES (?, ?, ?, ?)", [
            (fernsehen, "Fernsehen", "tag:webcam", "filter"), (hand, "Hand", "manual", "manual"),
            (werbung, "Werbung", "ad:URL_SSAI_DOMAIN", "ad"), (favorit, "Favorit", "manual", "manual")])
        conn.execute("INSERT INTO favorites (uuid, name, url) VALUES (?, 'Favorit gesperrt', 'https://example.invalid')",
                     (favorit,))
        regeln_vorher = conn.execute("SELECT COUNT(*) FROM regel").fetchone()[0]
    await _aufbereiten()

    vorschau = await regeln_ueberfuehren.lauf(anwenden=False)
    assert not vorschau.angewendet
    assert vorschau.plan.sprachgruppen == {"Deutsch": ["deu"]} and "webcam" in vorschau.plan.tags
    assert sum(vorschau.neu_ausgeblendet.values()) == 0
    assert vorschau.favoriten_neu_sichtbar == ["Favorit gesperrt"]
    assert sum(vorschau.neu_sichtbar.values()) == 1
    with db_session() as conn:
        assert conn.execute("SELECT COUNT(*) FROM regel").fetchone()[0] == regeln_vorher, "Vorschau ändert nichts"
        assert conn.execute("SELECT COUNT(*) FROM sender_sperre WHERE uuid LIKE ?", (PRAEFIX + "%",)).fetchone()[0] == 0

    bericht = await regeln_ueberfuehren.lauf(anwenden=True)
    assert bericht.nachher_sichtbar - bericht.vorher_sichtbar == 1
    text = regeln_ueberfuehren.text(bericht)
    assert "Favorit trotz Sperre von Hand" in text and "Werbeverdacht eigene Entscheidung" in text
    with db_session() as conn:
        sichtbar = {z[0] for z in conn.execute("SELECT uuid FROM sender_index WHERE sichtbar = 1 AND uuid LIKE ?",
                                               (PRAEFIX + "%",))}
        assert sichtbar == {deutsch, favorit}
        assert conn.execute("SELECT user_action FROM station_ad_status WHERE station_uuid = ?", (werbung,)).fetchone()[0] \
            == "blocked"
        assert conn.execute("SELECT COUNT(*) FROM blocklist WHERE uuid LIKE ?", (PRAEFIX + "%",)).fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM regel WHERE id = 'altbestand'").fetchone()[0] == 0
    assert kuerzel not in sichtbar
    with pytest.raises(SystemExit):
        await regeln_ueberfuehren.lauf(anwenden=True)
