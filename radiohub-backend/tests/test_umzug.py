"""Umzug des Altbestands mit der Testablage: heutiges RadioHub und altes Radio, Trockenlauf, Abbruch und Wiederaufnahme,
keine Doppel, Aufräumen nur nach vollständigem Lauf."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest

from backend.ablage import SpeicherAblage, vorgeben
from backend.config import DATA_DIR, get_cache_dir
from backend.database import db_session
from backend.umzug.__main__ import main
from conftest import ton

PYRADIO_SCHEMA = """
CREATE TABLE favorites (uuid TEXT PRIMARY KEY, name TEXT, url TEXT, url_resolved TEXT, favicon TEXT, country TEXT,
    countrycode TEXT, tags TEXT, bitrate INTEGER, added_at TEXT);
CREATE TABLE podcast_subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, feed_url TEXT UNIQUE NOT NULL, title TEXT,
    author TEXT, description TEXT, image_url TEXT, last_updated TEXT, created_at TEXT, auto_download INTEGER DEFAULT 0,
    last_auto_download TEXT);
CREATE TABLE podcast_episodes (id INTEGER PRIMARY KEY AUTOINCREMENT, podcast_id INTEGER, guid TEXT, title TEXT,
    description TEXT, audio_url TEXT, duration INTEGER, published_at TEXT, resume_position INTEGER DEFAULT 0,
    is_downloaded INTEGER DEFAULT 0, local_path TEXT, UNIQUE(podcast_id, guid));
CREATE TABLE alarms (id INTEGER PRIMARY KEY, enabled INTEGER, time TEXT, days TEXT, mode TEXT, station_uuid TEXT,
    station_name TEXT, volume INTEGER);
CREATE TABLE podcast_saved_episodes (id INTEGER PRIMARY KEY AUTOINCREMENT, podcast_id INTEGER, episode_id INTEGER,
    file_path TEXT, size_mb REAL DEFAULT 0, saved_at TEXT);
"""


class StoerAblage(SpeicherAblage):
    """Bricht beim Ablegen bestimmter Dateien ab (wie eine fehlende Kellerwolke mitten im Lauf)."""

    def __init__(self):
        super().__init__()
        self.stoeren: set[str] = set()

    async def ablegen(self, pfad, quelle):
        if quelle.name in self.stoeren:
            raise ConnectionError("Kellerwolke nicht erreichbar")
        return await super().ablegen(pfad, quelle)


@pytest.fixture
def bestand(tmp_path):
    """Heutiges RadioHub mit lokalen Pfaden und ein altes Radio, beide mit eigenen Kennungen."""
    k = uuid.uuid4().hex[:6]
    rec = DATA_DIR / "recordings"
    with db_session() as c:
        heute_abo = c.execute("INSERT INTO podcast_subscriptions (feed_url, title) VALUES (?, ?)",
                              (f"https://heute.test/{k}/feed/", f"Heute {k}")).lastrowid
        folge = ton(rec / "podcasts" / "audio" / str(heute_abo) / "7_folge.mp3", 2)
        heute_folge = c.execute("""INSERT INTO podcast_episodes (podcast_id, guid, title, published_at, is_downloaded,
                                   local_path) VALUES (?, 'g1', 'Erste Folge', '2026-03-01 06:00:00', 1, ?)""",
                                (heute_abo, str(folge))).lastrowid
        ton(rec / "podcasts" / "audio" / str(heute_abo) / "9_ohne_eintrag.mp3", 1)
        bild = rec / "podcasts" / "images" / str(heute_abo) / "cover.jpg"
        bild.parent.mkdir(parents=True, exist_ok=True)
        bild.write_bytes(b"jpg")
        stueck = ton(rec / "radio" / f"rec_{k}" / "seg_000.mp3", 2)
        c.execute("""INSERT INTO sessions (id, station_name, start_time, file_path, status, meta_file_path)
                     VALUES (?, ?, '2026-03-13T01:15:14', ?, 'completed', ?)""",
                  (f"rec_{k}", f"Heutefunk {k}", str(stueck.parent), str(rec / "radio" / "fehlt.meta.json")))
        c.execute("""INSERT INTO segments (session_id, segment_index, title, start_ms, end_ms, duration_ms, file_path)
                     VALUES (?, 0, 'Lied', 0, 2000, 2000, ?)""", (f"rec_{k}", str(stueck)))
        c.execute("INSERT OR IGNORE INTO favorites (uuid, name, url) VALUES ('fav-da', 'Da', 'http://da.test/stream')")

    alt = tmp_path / "pyradio-daten"
    (alt / "recordings").mkdir(parents=True)
    db = sqlite3.connect(alt / "pyradio.db")
    db.executescript(PYRADIO_SCHEMA)
    db.execute("INSERT INTO favorites (uuid, name, url) VALUES ('fav-da-anders', 'Da', 'http://da.test/stream')")
    db.execute(f"INSERT INTO favorites (uuid, name, url) VALUES ('fav-neu-{k}', 'Neu', 'http://neu.test/{k}')")
    db.execute("INSERT INTO podcast_subscriptions (id, feed_url, title) VALUES (1, ?, 'Heute doppelt')",
               (f"http://heute.test/{k}/feed",))
    db.execute("INSERT INTO podcast_subscriptions (id, feed_url, title) VALUES (2, ?, ?)",
               (f"https://alt.test/{k}", f"Alt {k}"))
    db.execute("INSERT INTO podcast_episodes (id, podcast_id, guid, title, published_at) VALUES (1, 1, 'g1', 'x', '')")
    db.execute("""INSERT INTO podcast_episodes (id, podcast_id, guid, title, published_at, resume_position)
                  VALUES (2, 2, 'a1', 'Alte Folge', '2025-12-24 08:00:00', 42)""")
    ton(alt / "recordings" / "podcasts" / f"Alt {k}" / "Alte Folge.mp3", 1)
    db.execute("INSERT INTO podcast_saved_episodes (podcast_id, episode_id, file_path) VALUES (2, 2, ?)",
               (f"/data/recordings/podcasts/Alt {k}/Alte Folge.mp3",))
    ton(alt / "recordings" / "radio" / f"rec_20260110_021304_{k}.mp3", 1)
    db.execute("INSERT INTO alarms VALUES (1, 1, '06:45', '[0,6]', 'radio', ?, 'Neu', 55)", (f"fav-neu-{k}",))
    db.execute("INSERT INTO alarms VALUES (2, 0, '07:00', '[1]', 'wave', NULL, NULL, 70)")
    db.commit()
    db.close()
    return {"k": k, "alt": alt, "heute_abo": heute_abo, "heute_folge": heute_folge, "stueck": stueck}


def _zeile(sql, *werte):
    with db_session() as c:
        return c.execute(sql, werte).fetchone()


def test_trockenlauf_aendert_nichts(bestand, capsys):
    vorgeben(SpeicherAblage())
    favoriten = _zeile("SELECT COUNT(*) FROM favorites")[0]
    assert main(["--altes-radio", str(bestand["alt"]), "--probe"]) == 0
    aus = capsys.readouterr().out
    assert "Altes Radio: Favoriten neu: 1" in aus and "Altes Radio: Abos neu: 1" in aus
    assert "Altes Radio: gemerkte Folgen" in aus and "RadioHub: Podcast-Folgen" in aus
    assert _zeile("SELECT COUNT(*) FROM favorites")[0] == favoriten
    assert _zeile("SELECT local_path FROM podcast_episodes WHERE id = ?", bestand["heute_folge"])[0].startswith("/")


def test_umzug_mit_abbruch_und_wiederaufnahme(bestand, capsys):
    k = bestand["k"]
    ablage = vorgeben(StoerAblage())
    ablage.stoeren = {"Alte Folge.mp3"}
    assert main(["--altes-radio", str(bestand["alt"])]) == 1  # ein Fehler, Rest ist durch

    folge = f"Podcasts/Heute {k}/2026-03-01 Erste Folge.mp3"
    assert _zeile("SELECT local_path FROM podcast_episodes WHERE id = ?", bestand["heute_folge"])[0] == folge
    assert folge in ablage.dateien and f"Podcasts/Heute {k}/9_ohne_eintrag.mp3" in ablage.dateien
    sitzung = _zeile("SELECT file_path, meta_file_path FROM sessions WHERE id = ?", f"rec_{k}")
    assert sitzung[0] == f"Aufnahmen/Heutefunk {k}/2026-03-13 01-15-14" and sitzung[1] is None
    assert _zeile("SELECT file_path FROM segments WHERE session_id = ?", f"rec_{k}")[0] == \
        f"Aufnahmen/Heutefunk {k}/2026-03-13 01-15-14/001 Lied.mp3"
    assert (get_cache_dir() / "podcast-bilder" / str(bestand["heute_abo"]) / "cover.jpg").exists()
    assert bestand["stueck"].exists()  # Quellen bleiben unangetastet

    ablage.stoeren = set()
    versionen = dict(ablage.versionen)
    assert main(["--altes-radio", str(bestand["alt"])]) == 0
    assert "1 abgelegt" in capsys.readouterr().out
    assert all(ablage.versionen[p] == v for p, v in versionen.items())  # nichts doppelt geschrieben

    alt = _zeile("""SELECT e.* FROM podcast_episodes e JOIN podcast_subscriptions s ON s.id = e.podcast_id
                    WHERE s.feed_url = ? AND e.guid = 'a1'""", f"https://alt.test/{k}")
    assert alt["is_downloaded"] == 1 and alt["resume_position"] == 42
    assert alt["local_path"] == f"Podcasts/Alt {k}/2025-12-24 Alte Folge.mp3" and alt["local_path"] in ablage.dateien
    assert _zeile("SELECT COUNT(*) FROM podcast_saved_episodes WHERE episode_id = ?", alt["id"])[0] == 1
    assert _zeile("SELECT COUNT(*) FROM podcast_subscriptions WHERE feed_url LIKE ?", f"%heute.test/{k}%")[0] == 1
    assert _zeile("SELECT COUNT(*) FROM favorites WHERE url = 'http://da.test/stream'")[0] == 1
    assert _zeile("SELECT COUNT(*) FROM favorites WHERE uuid = ?", f"fav-neu-{k}")[0] == 1
    aufnahme = _zeile("SELECT * FROM sessions WHERE id = ?", f"alt_rec_20260110_021304_{k}")
    assert aufnahme["station_name"] == "Altes Radio" and aufnahme["file_path"] == "Aufnahmen/Altes Radio/2026-01-10 02-13-04"
    assert _zeile("SELECT file_path FROM segments WHERE session_id = ?", aufnahme["id"])[0] in ablage.dateien

    wecker = _zeile("SELECT * FROM wecker WHERE herkunft = 'pyradio:1' AND sender_json LIKE ?", f"%fav-neu-{k}%")
    assert wecker["zeit"] == "06:45" and wecker["tage"] == "[6, 7]" and wecker["lautstaerke"] == 55
    assert _zeile("SELECT COUNT(*) FROM wecker WHERE herkunft = 'pyradio:2'")[0] == 0

    # Dritter Lauf: nichts mehr offen, nichts doppelt
    assert main(["--altes-radio", str(bestand["alt"]), "--probe"]) == 0
    assert "0 offen" in capsys.readouterr().out
    assert main(["--altes-radio", str(bestand["alt"])]) == 0
    assert _zeile("SELECT COUNT(*) FROM favorites WHERE uuid = ?", f"fav-neu-{k}")[0] == 1


def test_aufraeumen_nur_nach_vollstaendigem_lauf(bestand, tmp_path, capsys):
    ablage = vorgeben(StoerAblage())
    papierkorb = tmp_path / "papierkorb"
    ablage.stoeren = {"7_folge.mp3"}
    assert main(["--altes-radio", str(bestand["alt"])]) == 1
    assert main(["--altes-radio", str(bestand["alt"]), "--aufraeumen", "--papierkorb", str(papierkorb)]) == 1
    assert (DATA_DIR / "recordings").exists() and not papierkorb.exists()

    ablage.stoeren = set()
    assert main(["--altes-radio", str(bestand["alt"])]) == 0
    assert main(["--altes-radio", str(bestand["alt"]), "--aufraeumen", "--papierkorb", str(papierkorb)]) == 0
    ziel = next(papierkorb.glob("papierkorb-radiohub-*"))
    assert (ziel / "radiohub-recordings" / "radio" / f"rec_{bestand['k']}" / "seg_000.mp3").exists()
    assert (ziel / "altes-radio-recordings" / "radio").exists()
    assert not (DATA_DIR / "recordings").exists() and (bestand["alt"] / "pyradio.db").exists()
