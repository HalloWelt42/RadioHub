"""Datenbank in Stufen (RAD-6): ein Bestand im alten Schema wird ohne Umbau als Stufe 1 übernommen, ein frischer
Bestand sieht genauso aus, ein älterer bekommt nur die früheren Nachträge, eine fremde Datei bleibt unberührt."""

import sqlite3
from pathlib import Path

import pytest

from altes_schema import alt_anlegen
from app import database, sender_merkmale


def _alt(pfad: Path) -> Path:
    """Eine Kopie im alten Schema mit Daten, wie sie auf dem Pi liegt (WAL, Tabellen des früheren Starts)."""
    v = sqlite3.connect(pfad)
    v.execute("PRAGMA journal_mode=WAL")
    alt_anlegen(v)
    v.execute("INSERT INTO stations (uuid, name, url, language, tags, votes) VALUES ('s1', 'Probe', 'http://x', 'german', 'pop', 7)")
    v.execute("INSERT INTO favorites (uuid, name, url) VALUES ('s1', 'Probe', 'http://x')")
    v.execute("INSERT INTO config (key, value) VALUES ('podcast_refresh_interval', '7200'), ('language', '\"de\"')")
    v.execute("INSERT INTO wecker (zeit, tage, lautstaerke) VALUES ('06:30', '[1,2,3,4,5]', 40)")
    v.execute("DELETE FROM icy_title_ignore WHERE pattern = 'ADBREAK'")    # vom Nutzer entfernt: bleibt entfernt
    v.commit()
    v.close()
    return pfad


def _schema(pfad: Path) -> dict:
    """Schema (ohne appkern_schema) und Inhalt jeder Tabelle."""
    v = sqlite3.connect(pfad)
    try:
        tabellen = [z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                                            "AND name != 'appkern_schema' ORDER BY name")]
        return {
            "sql": sorted(tuple(z) for z in v.execute("SELECT type, name, sql FROM sqlite_master WHERE tbl_name != 'appkern_schema'")),
            "inhalt": {t: sorted(map(repr, v.execute(f"SELECT * FROM {t}"))) for t in tabellen},
        }
    finally:
        v.close()


def _aufbau(pfad: Path) -> dict:
    """Spalten, Indizes und Fremdschlüssel je Tabelle (vergleichbar zwischen frisch angelegt und übernommen)."""
    v = sqlite3.connect(pfad)
    try:
        tabellen = [z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                                            "AND name != 'appkern_schema' ORDER BY name")]
        return {t: {"spalten": list(v.execute(f"PRAGMA table_info({t})")),
                    "indizes": sorted((z[1], z[2], z[3]) for z in v.execute(f"PRAGMA index_list({t})") if not z[1].startswith("sqlite_")),
                    "eindeutig": sorted(z[2] for z in v.execute(f"PRAGMA index_list({t})") if z[1].startswith("sqlite_")),
                    "fremd": sorted(tuple(z[2:]) for z in v.execute(f"PRAGMA foreign_key_list({t})"))}
                for t in tabellen}
    finally:
        v.close()


def _stufe(pfad: Path) -> int | None:
    v = sqlite3.connect(pfad)
    try:
        z = v.execute("SELECT stufe FROM appkern_schema WHERE baustein = ?", (database.BAUSTEIN,)).fetchone()
        return z[0] if z else None
    finally:
        v.close()


async def test_bestand_im_alten_schema_wird_ohne_umbau_stufe_1(tmp_path):
    pfad = _alt(tmp_path / "radiohub.db")
    vorher = _schema(pfad)
    einrichtung = await database.einrichten(pfad)
    assert (einrichtung.bestand, einrichtung.stufe, einrichtung.nachgetragen) == ("übernommen", 1, ())
    assert _schema(pfad) == vorher                    # kein Umbau, keine Daten geändert, die entfernte Zeile bleibt weg
    assert _stufe(pfad) == 1
    zweite = await database.einrichten(pfad)
    assert (zweite.bestand, zweite.stufe) == ("vorhanden", 1) and _schema(pfad) == vorher


async def test_frischer_bestand_gleicht_dem_alten_schema(tmp_path):
    frisch = tmp_path / "frisch.db"
    einrichtung = await database.einrichten(frisch)
    assert (einrichtung.bestand, einrichtung.stufe) == ("neu", 1)
    alt = tmp_path / "alt.db"
    v = sqlite3.connect(alt)
    alt_anlegen(v)
    v.close()
    assert _aufbau(frisch) == _aufbau(alt)
    v = sqlite3.connect(frisch)
    assert v.execute("SELECT COUNT(*) FROM icy_title_ignore WHERE source = 'builtin'").fetchone()[0] == 3
    v.close()


async def test_aelterer_bestand_bekommt_nur_die_frueheren_nachtraege(tmp_path):
    pfad = tmp_path / "radiohub.db"
    v = sqlite3.connect(pfad)
    v.execute("CREATE TABLE stations (uuid TEXT PRIMARY KEY, name TEXT, url TEXT, url_resolved TEXT, favicon TEXT, country TEXT, "
              "countrycode TEXT, language TEXT, tags TEXT, codec TEXT, bitrate INTEGER, votes INTEGER, clickcount INTEGER, "
              "homepage TEXT, lastcheck TEXT, cached_at TEXT)")
    v.execute("CREATE TABLE blocklist (uuid TEXT PRIMARY KEY, name TEXT, reason TEXT, blocked_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    v.execute("INSERT INTO stations (uuid, name) VALUES ('s1', 'Alt')")
    v.execute("INSERT INTO blocklist (uuid, name, reason) VALUES ('a', 'A', 'ad: domain'), ('b', 'B', 'language:german'), "
              "('c', 'C', 'von Hand')")
    v.commit()
    v.close()
    einrichtung = await database.einrichten(pfad)
    assert einrichtung.bestand == "nachgetragen" and einrichtung.stufe == 1
    assert {"stations.last_seen", "blocklist.category", "sessions", "wecker"} <= set(einrichtung.nachgetragen)
    v = sqlite3.connect(pfad)
    assert v.execute("SELECT name FROM stations").fetchall() == [("Alt",)]
    assert dict(v.execute("SELECT uuid, category FROM blocklist")) == {"a": "ad", "b": "filter", "c": "manual"}
    v.close()
    alt = tmp_path / "alt.db"
    v = sqlite3.connect(alt)
    alt_anlegen(v)
    v.close()
    # Spalten, die per ALTER dazukamen, stehen hinten wie beim früheren Start; die Menge stimmt überein
    assert {t: sorted(s[1] for s in a["spalten"]) for t, a in _aufbau(pfad).items()} == \
        {t: sorted(s[1] for s in a["spalten"]) for t, a in _aufbau(alt).items()}


async def test_fremde_datei_bleibt_unberuehrt(tmp_path):
    pfad = tmp_path / "fremd.db"
    v = sqlite3.connect(pfad)
    v.execute("CREATE TABLE etwas (x)")
    v.commit()
    v.close()
    with pytest.raises(database.FremderBestand):
        await database.einrichten(pfad)
    v = sqlite3.connect(pfad)
    assert [z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type='table'")] == ["etwas"]
    v.close()


def test_verbindungen_kennen_merkmal_trifft():
    with database.db_session() as conn:
        liste = sender_merkmale.liste_als_parameter(["German"])
        assert conn.execute("SELECT merkmal_trifft('german,english', ?)", (liste,)).fetchone()[0] == 1
        assert conn.execute("SELECT merkmal_trifft('germanic', ?)", (liste,)).fetchone()[0] == 0
