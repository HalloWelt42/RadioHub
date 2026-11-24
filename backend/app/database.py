"""Datenbank des RadioHub (`radiohub.db`): Sender, Favoriten, Filter und Sperren, Aufnahmen, Abos und Folgen, Wecker.

Das Schema kommt in Stufen über die Datenbank des Appkerns (`appkern.datenbank`, Baustein `radiohub`): `einrichten`
spielt beim Start nur die noch fehlenden Stufen ein und merkt sich den Stand in der Tabelle `appkern_schema`. Stufe 1
ist der Bestand bis Fassung 0.15.6, wie ihn der frühere Start mit `CREATE ... IF NOT EXISTS` und Nachträgen per `ALTER`
in `try/except` anlegte. Eine Datenbank aus dieser Zeit wird ohne Umbau übernommen: sie bekommt nur die Stufe gesetzt
(`bestand_uebernehmen`). Nur einem älteren Bestand, dem Spalten fehlen, die der frühere Start nachgetragen hätte, trägt
die Übernahme genau diese nach (`NACHTRAEGE`); nichts wird gelöscht. Jede weitere Änderung am Schema ist eine neue Stufe
am Ende von `STUFEN`, nie eine Änderung an einer alten.

Die Senderquelle (RAD-7) liest und schreibt über die Datenbank des Appkerns (`oeffnen`, `lesen`, `schreiben`): ein
Vorrat an Leseverbindungen neben einer schreibenden, alles in Fäden, die Ereignisschleife wartet nie auf die Platte.
Die übrigen Dienste lesen und schreiben bis zu ihrem Umbau über `get_db` und `db_session`.
"""
from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from appkern.datenbank import Datenbank

from .config import DB_PATH, DATA_DIR

log = logging.getLogger("radiohub.datenbank")

# === Konfiguration ===
DB_TIMEOUT = 30.0
BAUSTEIN = "radiohub"           # Name der Stufen in appkern_schema


def get_db() -> sqlite3.Connection:
    """Verbindung zur Datenbank mit den Einstellungen des RadioHub."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False,
        timeout=DB_TIMEOUT
    )
    conn.row_factory = sqlite3.Row

    # Optimale SQLite-Einstellungen
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA cache_size = -64000")  # 64MB Cache

    return conn


@contextmanager
def db_session():
    """Context Manager für DB-Sessions"""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except sqlite3.OperationalError as e:
        conn.rollback()
        if "locked" in str(e):
            log.warning("Datenbank gesperrt: %s", e)
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ----- Stufen ----------------------------------------------------------------------------------------------------------

# Stufe 1: der Bestand bis Fassung 0.15.6. Spalten stehen in der Reihenfolge, die der frühere Start ergab (Nachträge per
# ALTER hängten sich hinten an), damit ein frischer Bestand genauso aussieht wie ein übernommener.
STUFE_1 = """
CREATE TABLE IF NOT EXISTS stations (
    uuid TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    url_resolved TEXT,
    favicon TEXT,
    country TEXT,
    countrycode TEXT,
    language TEXT,
    tags TEXT,
    codec TEXT,
    bitrate INTEGER,
    votes INTEGER,
    clickcount INTEGER,
    homepage TEXT,
    lastcheck TEXT,
    cached_at TEXT,
    last_seen TEXT
);
CREATE TABLE IF NOT EXISTS favorites (
    uuid TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    url_resolved TEXT,
    favicon TEXT,
    country TEXT,
    countrycode TEXT,
    tags TEXT,
    bitrate INTEGER,
    added_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    station_uuid TEXT,
    station_name TEXT,
    stream_url TEXT,
    bitrate INTEGER,
    start_time TEXT,
    end_time TEXT,
    duration REAL DEFAULT 0,
    file_path TEXT,
    file_size INTEGER DEFAULT 0,
    status TEXT DEFAULT 'recording',
    codec TEXT,
    file_format TEXT,
    meta_file_path TEXT,
    rec_type TEXT DEFAULT 'direct',
    folder_id INTEGER REFERENCES recording_folders(id) ON DELETE SET NULL,
    quality_json TEXT
);
CREATE TABLE IF NOT EXISTS podcast_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_url TEXT UNIQUE NOT NULL,
    title TEXT,
    author TEXT,
    description TEXT,
    image_url TEXT,
    last_updated TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    auto_download INTEGER DEFAULT 0,
    last_auto_download TEXT,
    local_image_path TEXT,
    categories TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS podcast_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    podcast_id INTEGER REFERENCES podcast_subscriptions(id) ON DELETE CASCADE,
    guid TEXT,
    title TEXT,
    description TEXT,
    audio_url TEXT,
    duration INTEGER,
    published_at TEXT,
    resume_position INTEGER DEFAULT 0,
    is_downloaded INTEGER DEFAULT 0,
    local_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_played INTEGER DEFAULT 0,
    file_size INTEGER DEFAULT 0,
    image_url TEXT,
    local_image_path TEXT,
    transcript_url TEXT,
    transcript TEXT,
    UNIQUE(podcast_id, guid)
);
CREATE TABLE IF NOT EXISTS podcast_saved_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    podcast_id INTEGER REFERENCES podcast_subscriptions(id) ON DELETE CASCADE,
    episode_id INTEGER REFERENCES podcast_episodes(id) ON DELETE CASCADE,
    file_path TEXT,
    size_mb REAL DEFAULT 0,
    saved_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS filter_cache (
    type TEXT PRIMARY KEY,
    data TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS blocklist (
    uuid TEXT PRIMARY KEY,
    name TEXT,
    reason TEXT,
    category TEXT DEFAULT 'manual',
    blocked_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS detected_bitrates (
    uuid TEXT PRIMARY KEY,
    bitrate INTEGER,
    codec TEXT,
    sample_rate INTEGER,
    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    icy INTEGER DEFAULT 0,
    icy_quality TEXT
);
CREATE TABLE IF NOT EXISTS cache_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS station_ad_status (
    station_uuid TEXT PRIMARY KEY,
    stream_url TEXT,
    block_status TEXT DEFAULT 'clean',
    confidence REAL DEFAULT 0.0,
    reasons_json TEXT,
    detection_method TEXT,
    first_detected TEXT,
    last_checked TEXT,
    blocked_at TEXT,
    manually_set INTEGER DEFAULT 0,
    manual_note TEXT,
    user_action TEXT,
    ad_detections INTEGER DEFAULT 0,
    false_positives INTEGER DEFAULT 0,
    check_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ad_detections_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_uuid TEXT,
    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    method TEXT,
    reason_code TEXT,
    detail TEXT,
    confidence REAL DEFAULT 0.0,
    resolved INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS domain_blacklist (
    domain TEXT PRIMARY KEY,
    category TEXT,
    source TEXT DEFAULT 'builtin',
    confidence REAL DEFAULT 0.9,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS recording_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    segment_index INTEGER,
    title TEXT,
    start_ms INTEGER,
    end_ms INTEGER,
    duration_ms INTEGER,
    file_path TEXT,
    file_size INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, segment_index)
);
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT 'radio',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS category_stations (
    category_id INTEGER NOT NULL,
    station_uuid TEXT NOT NULL,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (category_id, station_uuid),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS category_podcasts (
    category_id INTEGER NOT NULL,
    podcast_id INTEGER NOT NULL,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (category_id, podcast_id),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    FOREIGN KEY (podcast_id) REFERENCES podcast_subscriptions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS category_sessions (
    category_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (category_id, session_id),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS wecker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aktiv INTEGER DEFAULT 1,
    zeit TEXT NOT NULL,
    tage TEXT NOT NULL DEFAULT '[1,2,3,4,5]',
    quelle TEXT NOT NULL DEFAULT 'sender',
    sender_json TEXT,
    podcast_id INTEGER,
    lautstaerke INTEGER DEFAULT 60,
    anstieg_s INTEGER DEFAULT 60,
    schlummern_min INTEGER DEFAULT 9,
    herkunft TEXT
);
CREATE TABLE IF NOT EXISTS icy_title_ignore (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT UNIQUE NOT NULL,
    match_type TEXT DEFAULT 'exact',
    source TEXT DEFAULT 'user',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO icy_title_ignore (pattern, match_type, source) VALUES
    ('THIS STATION WILL CONTINUE AFTER THIS BREAK', 'exact', 'builtin'),
    ('ADBREAK', 'contains', 'builtin'),
    ('AD BREAK', 'contains', 'builtin');
CREATE TABLE IF NOT EXISTS station_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_uuid TEXT NOT NULL,
    tag_key TEXT NOT NULL,
    tag_value TEXT NOT NULL DEFAULT 'true',
    source TEXT NOT NULL DEFAULT 'user',
    confidence REAL DEFAULT 1.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(station_uuid, tag_key, source)
);
CREATE TABLE IF NOT EXISTS station_custom_urls (
    station_uuid TEXT PRIMARY KEY,
    custom_url TEXT NOT NULL,
    original_url TEXT NOT NULL,
    original_url_resolved TEXT,
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_stations_votes ON stations(votes DESC);
CREATE INDEX IF NOT EXISTS idx_stations_country ON stations(countrycode);
CREATE INDEX IF NOT EXISTS idx_stations_name ON stations(name);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_podcast_episodes_podcast ON podcast_episodes(podcast_id);
CREATE INDEX IF NOT EXISTS idx_podcast_episodes_published ON podcast_episodes(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_blocklist_reason ON blocklist(reason);
CREATE INDEX IF NOT EXISTS idx_blocklist_category ON blocklist(category);
CREATE INDEX IF NOT EXISTS idx_ad_status_block ON station_ad_status(block_status);
CREATE INDEX IF NOT EXISTS idx_ad_log_station ON ad_detections_log(station_uuid);
CREATE INDEX IF NOT EXISTS idx_domain_blacklist_cat ON domain_blacklist(category);
CREATE INDEX IF NOT EXISTS idx_segments_session ON segments(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_folder ON sessions(folder_id);
CREATE INDEX IF NOT EXISTS idx_rec_folders_active ON recording_folders(is_active);
CREATE INDEX IF NOT EXISTS idx_categories_sort ON categories(sort_order);
CREATE INDEX IF NOT EXISTS idx_categories_scope ON categories(scope);
CREATE INDEX IF NOT EXISTS idx_cat_stations_uuid ON category_stations(station_uuid);
CREATE INDEX IF NOT EXISTS idx_cat_stations_cat ON category_stations(category_id);
CREATE INDEX IF NOT EXISTS idx_cat_podcasts_pod ON category_podcasts(podcast_id);
CREATE INDEX IF NOT EXISTS idx_cat_podcasts_cat ON category_podcasts(category_id);
CREATE INDEX IF NOT EXISTS idx_cat_sessions_ses ON category_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_cat_sessions_cat ON category_sessions(category_id);
CREATE INDEX IF NOT EXISTS idx_station_tags_uuid ON station_tags(station_uuid);
CREATE INDEX IF NOT EXISTS idx_station_tags_key ON station_tags(tag_key);
CREATE INDEX IF NOT EXISTS idx_podcast_episodes_downloaded ON podcast_episodes(is_downloaded);
CREATE INDEX IF NOT EXISTS idx_podcast_episodes_played ON podcast_episodes(is_played);
"""

# Stufe 2 (RAD-7, Etappe 3 Filterung): nur dazu, nichts umgebaut oder geleert. Die Felder des Verzeichnisses, die der
# frühere Abgleich verwarf, kommen als Spalten an stations; was der Senderdaten-Baustein daraus macht, steht in eigenen
# Tabellen (sender_*), ebenso die lebenden Regeln, ihre Treffer, Einzelsperren und Freigaben. Die Sperrliste blocklist
# bleibt unverändert stehen: bis zur Überführung (python -m app.werkzeuge.regeln_ueberfuehren) gilt sie über die Regel
# "altbestand", die es nur gibt, wenn die Sperrliste Einträge hat.
STUFE_2 = """
ALTER TABLE stations ADD COLUMN languagecodes TEXT;
ALTER TABLE stations ADD COLUMN iso_3166_2 TEXT;
ALTER TABLE stations ADD COLUMN state TEXT;
ALTER TABLE stations ADD COLUMN geo_lat REAL;
ALTER TABLE stations ADD COLUMN geo_long REAL;
ALTER TABLE stations ADD COLUMN hls INTEGER;
ALTER TABLE stations ADD COLUMN ssl_error INTEGER;
ALTER TABLE stations ADD COLUMN clicktrend INTEGER;
ALTER TABLE stations ADD COLUMN lastcheckok INTEGER;
ALTER TABLE stations ADD COLUMN lastcheckoktime TEXT;
ALTER TABLE stations ADD COLUMN lastchangetime TEXT;
ALTER TABLE stations ADD COLUMN has_extended_info INTEGER;
ALTER TABLE stations ADD COLUMN verschwunden_am TEXT;
UPDATE stations SET lastcheckok = CASE WHEN lastcheck IN ('1', 'true') THEN 1 ELSE 0 END;
CREATE INDEX IF NOT EXISTS idx_stations_last_seen ON stations(last_seen);
CREATE TABLE sender_index (
    nr INTEGER PRIMARY KEY,
    uuid TEXT NOT NULL UNIQUE,
    name_klein TEXT NOT NULL DEFAULT '',
    land TEXT NOT NULL DEFAULT '',
    codec TEXT NOT NULL DEFAULT 'unbekannt',
    kbps INTEGER NOT NULL DEFAULT 0,
    kbps_gemessen INTEGER,
    qualitaet TEXT NOT NULL DEFAULT 'unbekannt',
    qualitaet_rang INTEGER NOT NULL DEFAULT 0,
    stimmen INTEGER NOT NULL DEFAULT 0,
    erreichbar INTEGER NOT NULL DEFAULT 0,
    gruppe TEXT NOT NULL DEFAULT '',
    sprachen TEXT NOT NULL DEFAULT '[]',
    genres TEXT NOT NULL DEFAULT '[]',
    verschwunden INTEGER NOT NULL DEFAULT 0,
    favorit INTEGER NOT NULL DEFAULT 0,
    freigegeben INTEGER NOT NULL DEFAULT 0,
    werbe_stufe INTEGER NOT NULL DEFAULT 0,
    getroffen INTEGER NOT NULL DEFAULT 0,
    sichtbar INTEGER NOT NULL DEFAULT 1,
    vertreter INTEGER NOT NULL DEFAULT 1,
    varianten INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX sender_index_stimmen ON sender_index (sichtbar, vertreter, stimmen DESC, uuid, erreichbar, favorit);
CREATE INDEX sender_index_name ON sender_index (sichtbar, vertreter, name_klein, uuid, erreichbar, favorit);
CREATE INDEX sender_index_qualitaet ON sender_index (sichtbar, vertreter, qualitaet_rang DESC, kbps DESC, uuid, erreichbar,
                                                     favorit);
CREATE INDEX sender_index_bitrate ON sender_index (sichtbar, vertreter, kbps DESC, uuid, erreichbar, favorit);
CREATE INDEX sender_index_land ON sender_index (land, sichtbar, vertreter, stimmen DESC, uuid, erreichbar, favorit);
CREATE INDEX sender_index_stufe ON sender_index (sichtbar, vertreter, qualitaet, erreichbar, favorit);
CREATE INDEX sender_index_codec ON sender_index (sichtbar, vertreter, codec, erreichbar, favorit);
CREATE INDEX sender_index_favorit ON sender_index (favorit, sichtbar, stimmen DESC) WHERE favorit = 1;
CREATE INDEX sender_index_gruppe ON sender_index (gruppe);
CREATE TABLE sender_genre (genre TEXT NOT NULL, nr INTEGER NOT NULL, PRIMARY KEY (genre, nr)) WITHOUT ROWID;
CREATE INDEX sender_genre_nr ON sender_genre (nr, genre);
CREATE TABLE sender_sprache (schluessel TEXT NOT NULL, nr INTEGER NOT NULL, PRIMARY KEY (schluessel, nr)) WITHOUT ROWID;
CREATE TABLE sender_spracheintrag (eintrag TEXT NOT NULL, nr INTEGER NOT NULL, PRIMARY KEY (eintrag, nr)) WITHOUT ROWID;
CREATE TABLE sender_tag (tag TEXT NOT NULL, nr INTEGER NOT NULL, PRIMARY KEY (tag, nr)) WITHOUT ROWID;
CREATE VIRTUAL TABLE sender_suche USING fts5(text, content='', tokenize='trigram remove_diacritics 1');
CREATE TABLE regel (
    id TEXT PRIMARY KEY,
    art TEXT NOT NULL,
    wert TEXT NOT NULL DEFAULT '{}',
    an INTEGER NOT NULL DEFAULT 1,
    herkunft TEXT NOT NULL DEFAULT 'nutzer',
    angelegt_am TEXT NOT NULL,
    geaendert_am TEXT NOT NULL
);
CREATE TABLE sender_ausblendung (
    regel TEXT NOT NULL REFERENCES regel(id) ON DELETE CASCADE,
    nr INTEGER NOT NULL,
    PRIMARY KEY (regel, nr)
) WITHOUT ROWID;
CREATE INDEX sender_ausblendung_nr ON sender_ausblendung (nr, regel);
CREATE TABLE sender_sperre (
    uuid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    herkunft TEXT NOT NULL DEFAULT 'auge',
    angelegt_am TEXT NOT NULL
);
CREATE TABLE sender_freigabe (uuid TEXT PRIMARY KEY, angelegt_am TEXT NOT NULL);
INSERT INTO regel (id, art, wert, an, herkunft, angelegt_am, geaendert_am)
    VALUES ('einzelsperren', 'einzeln', '{}', 1, 'bestand', datetime('now'), datetime('now'));
INSERT INTO regel (id, art, wert, an, herkunft, angelegt_am, geaendert_am)
    SELECT 'altbestand', 'altsperren', '{}', 1, 'bestand', datetime('now'), datetime('now')
    WHERE EXISTS (SELECT 1 FROM blocklist);
"""

# Stufe 3 (RAD-15): jeder Wecker hat seinen Weckton; die Töne selbst entstehen im Gerät (frontend lib/telefon/wecktoene.js)
STUFE_3 = """
ALTER TABLE wecker ADD COLUMN weckton TEXT NOT NULL DEFAULT 'doppelpiep';
"""

# Stufe 4 (RAD-17): ein Abo lässt sich oben anheften und merkt sich die Sortierung seiner Folgen (leer: die der Ansicht)
STUFE_4 = """
ALTER TABLE podcast_subscriptions ADD COLUMN angeheftet INTEGER NOT NULL DEFAULT 0;
ALTER TABLE podcast_subscriptions ADD COLUMN sortierung TEXT NOT NULL DEFAULT '';
"""

# Stufe 5 (RAD-23): eigene Ordner der Abos (Gruppierung); ein Ordner zu löschen nimmt nur die Gruppierung (die Abos stehen
# danach lose), die Abos bleiben
STUFE_5 = """
CREATE TABLE podcast_ordner (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    reihenfolge INTEGER NOT NULL DEFAULT 0,
    offen INTEGER NOT NULL DEFAULT 1,
    angelegt_am TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE podcast_subscriptions ADD COLUMN ordner_id TEXT REFERENCES podcast_ordner(id) ON DELETE SET NULL;
"""

# RAD-17: Schritte des Schnitts je Gegenstand ("sitzung:<id>" oder "datei:<pfad>"), damit Rückgängig auch nach dem
# Neuladen geht; `daten` sagt, wie (Sitzung: Ordner mit der vorigen Fassung und die Titel; Datei: neue Dateien)
STUFE_6 = """
CREATE TABLE schnitt_schritte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gegenstand TEXT NOT NULL,
    was TEXT NOT NULL,
    daten TEXT NOT NULL DEFAULT '{}',
    zeit TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_schnitt_schritte_gegenstand ON schnitt_schritte(gegenstand, id);
"""

# RAD-32: Werbestellen je Folge (Sekunden) mit Herkunft; verworfen heißt "keine Werbung" (vom Nutzer), damit eine
# neue Suche sie nicht wieder einträgt. Je Abo: überspringen und neue Folgen von selbst prüfen; je Folge die Adresse
# der Kapitel aus dem Feed (podcast:chapters)
STUFE_7 = """
CREATE TABLE werbestellen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folge_id INTEGER NOT NULL REFERENCES podcast_episodes(id) ON DELETE CASCADE,
    von REAL NOT NULL,
    bis REAL NOT NULL,
    herkunft TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    verworfen INTEGER NOT NULL DEFAULT 0,
    angelegt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_werbestellen_folge ON werbestellen(folge_id, von);
ALTER TABLE podcast_episodes ADD COLUMN chapters_url TEXT NOT NULL DEFAULT '';
ALTER TABLE podcast_subscriptions ADD COLUMN werbung_ueberspringen INTEGER NOT NULL DEFAULT 1;
ALTER TABLE podcast_subscriptions ADD COLUMN werbung_pruefen INTEGER NOT NULL DEFAULT 0;
"""

# Stufe 8 (RAD-33): Werbung aus den Sendedaten. Spots, die Sender in ihren Sendedaten ankündigen (je Sender, Format
# und Kennung einmal, mit Zähler), und je Sender, ob angekündigte Werbung übersprungen wird (ohne Zeile: ja)
STUFE_8 = """
CREATE TABLE werbespots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_uuid TEXT NOT NULL,
    format TEXT NOT NULL,
    kennung TEXT NOT NULL,
    werbender TEXT NOT NULL DEFAULT '',
    titel TEXT NOT NULL DEFAULT '',
    dauer_ms INTEGER,
    beim_verbinden INTEGER NOT NULL DEFAULT 0,
    anzahl INTEGER NOT NULL DEFAULT 1,
    zuerst TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    zuletzt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sender_uuid, format, kennung)
);
CREATE INDEX idx_werbespots_sender ON werbespots(sender_uuid, zuletzt);
CREATE TABLE sender_werbung (
    uuid TEXT PRIMARY KEY,
    ueberspringen INTEGER NOT NULL DEFAULT 1
);
"""

# Stufe 9 (RAD-33, Schritt 7): Werbestellen gehören zu einer Quelle, einer Folge oder einer Aufnahme (genau einer).
# SQLite ändert keine Spalte: die Tabelle wird mit denselben Zeilen und Kennungen neu angelegt
STUFE_9 = """
CREATE TABLE werbestellen_neu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folge_id INTEGER REFERENCES podcast_episodes(id) ON DELETE CASCADE,
    aufnahme_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    von REAL NOT NULL,
    bis REAL NOT NULL,
    herkunft TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    verworfen INTEGER NOT NULL DEFAULT 0,
    angelegt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((folge_id IS NULL) <> (aufnahme_id IS NULL))
);
INSERT INTO werbestellen_neu (id, folge_id, von, bis, herkunft, text, verworfen, angelegt)
    SELECT id, folge_id, von, bis, herkunft, text, verworfen, angelegt FROM werbestellen;
DROP TABLE werbestellen;
ALTER TABLE werbestellen_neu RENAME TO werbestellen;
CREATE INDEX idx_werbestellen_folge ON werbestellen(folge_id, von);
CREATE INDEX idx_werbestellen_aufnahme ON werbestellen(aufnahme_id, von);
"""

# Stufe 10 (RAD-59): ein Sender mit bekannten Spots trägt die Marke Werbung, bis man sie entfernt; entfernt bleibt sie
# weg, auch wenn der Sender später wieder Werbung ankündigt
STUFE_10 = """
CREATE TABLE werbemarke_aus (
    uuid TEXT PRIMARY KEY,
    seit TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# Stufe 11 (HELF-256): wie lange ein Sender je Tag lief, damit der Lernlauf nachts das hört, was man selbst hört
STUFE_11 = """
CREATE TABLE hoerverlauf (
    uuid TEXT NOT NULL,
    tag TEXT NOT NULL,
    sekunden INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (uuid, tag)
) WITHOUT ROWID;
CREATE INDEX hoerverlauf_tag ON hoerverlauf(tag);
"""

# Stufe 12 (RAD-26): vertonte Fassungen einer Folge (je Sprache eine) und welche man hört (leer: das Original). Ton und Text
# liegen als Begleitdateien neben der Folge in der Ablage, hier steht nur, was es gibt
STUFE_12 = """
CREATE TABLE podcast_fassungen (
    folge_id INTEGER NOT NULL REFERENCES podcast_episodes(id) ON DELETE CASCADE,
    sprache TEXT NOT NULL,
    pfad TEXT NOT NULL,
    stimme TEXT NOT NULL DEFAULT '',
    angelegt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (folge_id, sprache)
) WITHOUT ROWID;
ALTER TABLE podcast_episodes ADD COLUMN fassung TEXT NOT NULL DEFAULT '';
"""

STUFEN: list[str] = [STUFE_1, STUFE_2, STUFE_3, STUFE_4, STUFE_5, STUFE_6, STUFE_7, STUFE_8, STUFE_9, STUFE_10, STUFE_11, STUFE_12]

# Spalten, die der frühere Start einem älteren Bestand per ALTER nachgetragen hat (Tabelle, Spalte, Festlegung).
NACHTRAEGE: list[tuple[str, str, str]] = [
    ("stations", "last_seen", "TEXT"),
    ("blocklist", "category", "TEXT DEFAULT 'manual'"),
    ("station_ad_status", "user_action", "TEXT"),
    ("detected_bitrates", "icy", "INTEGER DEFAULT 0"),
    ("detected_bitrates", "icy_quality", "TEXT"),
    ("sessions", "codec", "TEXT"),
    ("sessions", "file_format", "TEXT"),
    ("sessions", "meta_file_path", "TEXT"),
    ("sessions", "rec_type", "TEXT DEFAULT 'direct'"),
    ("sessions", "folder_id", "INTEGER REFERENCES recording_folders(id) ON DELETE SET NULL"),
    ("sessions", "quality_json", "TEXT"),
    ("categories", "scope", "TEXT NOT NULL DEFAULT 'radio'"),
    ("podcast_subscriptions", "local_image_path", "TEXT"),
    ("podcast_subscriptions", "categories", "TEXT DEFAULT ''"),
    ("podcast_subscriptions", "sort_order", "INTEGER DEFAULT 0"),
    ("podcast_episodes", "is_played", "INTEGER DEFAULT 0"),
    ("podcast_episodes", "file_size", "INTEGER DEFAULT 0"),
    ("podcast_episodes", "image_url", "TEXT"),
    ("podcast_episodes", "local_image_path", "TEXT"),
    ("podcast_episodes", "transcript_url", "TEXT"),
    ("podcast_episodes", "transcript", "TEXT"),
]


class FremderBestand(RuntimeError):
    """Die Datei sieht nicht wie eine Datenbank des RadioHub aus; sie wird nicht angefasst."""


@dataclass(frozen=True)
class Einrichtung:
    """Ergebnis von `einrichten`: Stand der Stufen und was mit dem Bestand geschah."""

    stufe: int
    bestand: str            # "neu", "übernommen", "nachgetragen", "vorhanden"
    nachgetragen: tuple[str, ...] = ()

    def satz(self) -> str:
        if self.bestand == "übernommen":
            return f"Bestand ohne Änderung als Stufe 1 übernommen, Stand Stufe {self.stufe}"
        if self.bestand == "nachgetragen":
            return (f"älterer Bestand als Stufe 1 übernommen, nachgetragen: {', '.join(self.nachgetragen)}; "
                    f"Stand Stufe {self.stufe}")
        if self.bestand == "neu":
            return f"neu angelegt, Stand Stufe {self.stufe}"
        return f"Stand Stufe {self.stufe}"


def _spalten(v: sqlite3.Connection, tabelle: str) -> set[str]:
    return {z[1] for z in v.execute(f"PRAGMA table_info({tabelle})")}


def bestand_uebernehmen(v: sqlite3.Connection) -> tuple[str, tuple[str, ...]]:
    """Übernimmt einen Bestand ohne Stufe als Stufe 1 (läuft in einer Transaktion). Ein Bestand ist eine Datei, in der
    der frühere Start die Tabelle `stations` angelegt hat. Fehlen ihm Spalten, die der frühere Start nachgetragen hätte,
    kommen genau diese dazu (wie dort, mit der Einordnung der Sperren beim Nachtrag von `blocklist.category`); dazu
    fehlende Tabellen und Indizes aus Stufe 1 (ohne die Einträge der Ignorierliste). Liefert ("vorhanden" | "neu" |
    "übernommen" | "nachgetragen", nachgetragene Spalten)."""
    if v.execute("SELECT 1 FROM appkern_schema WHERE baustein=?", (BAUSTEIN,)).fetchone():
        return "vorhanden", ()
    if not v.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='stations'").fetchone():
        _fremd_pruefen(v)
        return "neu", ()
    nachgetragen: list[str] = []
    for tabelle, spalte, festlegung in NACHTRAEGE:
        vorhanden = _spalten(v, tabelle)
        if vorhanden and spalte not in vorhanden:
            v.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte} {festlegung}")
            nachgetragen.append(f"{tabelle}.{spalte}")
            if (tabelle, spalte) == ("blocklist", "category"):
                v.execute("UPDATE blocklist SET category = 'ad' WHERE reason LIKE 'ad:%'")
                v.execute("""UPDATE blocklist SET category = 'filter'
                             WHERE category = 'manual'
                             AND (reason LIKE '%language:%' OR reason LIKE '%country:%'
                                  OR reason LIKE '%tag:%' OR reason LIKE '%votes<%')""")
    vorher = {z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'index')")}
    for satz in _anlegen_saetze():
        v.execute(satz)
    dazu = {z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'index')")} - vorher
    nachgetragen += sorted(dazu)
    v.execute("INSERT INTO appkern_schema (baustein, stufe) VALUES (?, 1)", (BAUSTEIN,))
    return ("nachgetragen" if nachgetragen else "übernommen"), tuple(nachgetragen)


def _fremd_pruefen(v: sqlite3.Connection) -> None:
    """Tabellen ohne Senderliste und ohne Stufe: das ist keine Datenbank des RadioHub."""
    if v.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='stations'").fetchone():
        return
    if v.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                 "AND name != 'appkern_schema'").fetchone():
        raise FremderBestand("Tabellen vorhanden, aber keine Senderliste: keine Datenbank des RadioHub")


def _vorab_pruefen(pfad: Path) -> None:
    """Vor dem Öffnen, nur lesend: eine fremde Datei bekommt nicht einmal die Tabelle der Stufen."""
    if not pfad.is_file() or pfad.stat().st_size == 0:
        return
    v = sqlite3.connect(f"{pfad.resolve().as_uri()}?mode=ro", uri=True)
    try:
        if not v.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='appkern_schema'").fetchone():
            _fremd_pruefen(v)
    finally:
        v.close()


def _anlegen_saetze() -> list[str]:
    """Die Sätze von Stufe 1, die nur anlegen, was fehlt (ohne Einträge)."""
    saetze, puffer = [], ""
    for zeile in STUFE_1.splitlines(keepends=True):
        puffer += zeile
        if sqlite3.complete_statement(puffer):
            satz = puffer.strip()
            if satz.upper().startswith("CREATE"):
                saetze.append(satz)
            puffer = ""
    return saetze


async def einrichten(pfad: Path | str = DB_PATH) -> Einrichtung:
    """Bringt die Datenbank auf den Stand der Stufen (beim Start, vor jedem anderen Zugriff)."""
    _vorab_pruefen(Path(pfad))
    async with Datenbank(pfad) as db:
        bestand, nachgetragen = await db.transaktion(bestand_uebernehmen)
        stufe = await db.einrichten(BAUSTEIN, STUFEN)
    return Einrichtung(stufe, bestand, nachgetragen)


# ----- Datenbank des Appkerns für die Senderquelle --------------------------------------------------------------------

T = TypeVar("T")
_offen: Datenbank | None = None


async def oeffnen(pfad: Path | str = DB_PATH) -> Datenbank:
    """Öffnet die Datenbank des Radios für die Senderquelle (beim Start nach `einrichten`, in Werkzeugen selbst)."""
    global _offen
    if _offen is None:
        _offen = await Datenbank(pfad).oeffnen()
    return _offen


async def schliessen() -> None:
    global _offen
    if _offen is not None:
        await _offen.schliessen()
        _offen = None


def radio_db() -> Datenbank:
    if _offen is None:
        raise RuntimeError("Datenbank des Radios ist nicht geöffnet")
    return _offen


async def lesen(arbeit: Callable[[sqlite3.Connection], T]) -> T:
    """Mehrere Abfragen in einem Lesestand, in einer der Leseverbindungen (nur lesend). Offene Frage an den Appkern:
    `Datenbank` bietet das bisher nur intern an (`_lesen`); sobald es öffentlich ist, ruft diese eine Stelle es dort."""
    return await radio_db()._lesen(arbeit)


async def schreiben(arbeit: Callable[[sqlite3.Connection], T]) -> T:
    """`arbeit` in einer Transaktion über die schreibende Verbindung (alles oder nichts)."""
    return await radio_db().transaktion(arbeit)


# ----- Prüfen ----------------------------------------------------------------------------------------------------------

def datenbank_erreichbar() -> dict:
    """Leichte Probe für /health (alle 30 Sekunden vom Docker-Healthcheck): öffnet die Datenbank und fragt SELECT 1.
    Die volle Prüfung über die ganze Datei steht in datenbank_pruefen."""
    try:
        with db_session() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def datenbank_pruefen() -> dict:
    """Volle Prüfung (PRAGMA integrity_check über die ganze Datei, dauert bei der großen Datenbank lange) und WAL-Modus;
    nur auf ausdrücklichen Aufruf (GET /api/datenbank/pruefung)."""
    result = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
    try:
        with db_session() as conn:
            c = conn.cursor()
            c.execute("PRAGMA integrity_check")
            result["integrity"] = c.fetchone()[0] == "ok"
            c.execute("PRAGMA journal_mode")
            result["wal_mode"] = c.fetchone()[0] == "wal"
            if not result["integrity"]:
                result["status"] = "unhealthy"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result
