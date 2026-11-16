"""Datenbank des RadioHub (`radiohub.db`): Sender, Favoriten, Filter und Sperren, Aufnahmen, Abos und Folgen, Wecker.

Das Schema kommt in Stufen über die Datenbank des Appkerns (`appkern.datenbank`, Baustein `radiohub`): `einrichten`
spielt beim Start nur die noch fehlenden Stufen ein und merkt sich den Stand in der Tabelle `appkern_schema`. Stufe 1
ist der Bestand bis Fassung 0.15.6, wie ihn der frühere Start mit `CREATE ... IF NOT EXISTS` und Nachträgen per `ALTER`
in `try/except` anlegte. Eine Datenbank aus dieser Zeit wird ohne Umbau übernommen: sie bekommt nur die Stufe gesetzt
(`bestand_uebernehmen`). Nur einem älteren Bestand, dem Spalten fehlen, die der frühere Start nachgetragen hätte, trägt
die Übernahme genau diese nach (`NACHTRAEGE`); nichts wird gelöscht. Jede weitere Änderung am Schema ist eine neue Stufe
am Ende von `STUFEN`, nie eine Änderung an einer alten.

Gelesen und geschrieben wird bis zur Datenschicht (Etappe 3) über `get_db` und `db_session`: jede Verbindung meldet die
SQL-Funktion `merkmal_trifft` an (`sender_merkmale`).
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from appkern.datenbank import Datenbank

from .config import DB_PATH, DATA_DIR
from . import sender_merkmale

log = logging.getLogger("radiohub.datenbank")

# === Konfiguration ===
DB_TIMEOUT = 30.0
BAUSTEIN = "radiohub"           # Name der Stufen in appkern_schema


def get_db() -> sqlite3.Connection:
    """Verbindung zur Datenbank mit den Einstellungen des RadioHub und der SQL-Funktion `merkmal_trifft`."""
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
    sender_merkmale.anmelden(conn)

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

STUFEN: list[str] = [STUFE_1]

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
