"""
RadioHub v0.1.1 - Datenbank

SQLite mit WAL-Modus für bessere Concurrency.
Nur Core-Tabellen (keine Alarms, Export, Waveform).
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from .config import DB_PATH, DATA_DIR

# === Konfiguration ===
DB_TIMEOUT = 30.0


def get_db() -> sqlite3.Connection:
    """Erstellt Datenbankverbindung mit optimalen Einstellungen"""
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
            print("⚠️ DB Lock erkannt")
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Erstellt alle Tabellen"""
    conn = get_db()
    c = conn.cursor()
    
    # === Stations Cache ===
    c.execute('''CREATE TABLE IF NOT EXISTS stations (
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
    )''')

    # Migration: last_seen Spalte hinzufügen falls nicht vorhanden
    try:
        c.execute("ALTER TABLE stations ADD COLUMN last_seen TEXT")
    except Exception:
        pass  # Spalte existiert bereits
    
    # === Favorites ===
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
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
    )''')
    
    # === Recording Sessions ===
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
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
        status TEXT DEFAULT 'recording'
    )''')
    
    # === Podcast Subscriptions ===
    c.execute('''CREATE TABLE IF NOT EXISTS podcast_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feed_url TEXT UNIQUE NOT NULL,
        title TEXT,
        author TEXT,
        description TEXT,
        image_url TEXT,
        last_updated TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        auto_download INTEGER DEFAULT 0,
        download_schedule TEXT DEFAULT 'daily',
        download_time TEXT DEFAULT '08:00',
        download_day INTEGER DEFAULT 1,
        max_episodes INTEGER DEFAULT 100,
        max_size_mb INTEGER DEFAULT 5000,
        auto_delete_old INTEGER DEFAULT 1,
        last_auto_download TEXT
    )''')
    
    # === Podcast Episodes ===
    c.execute('''CREATE TABLE IF NOT EXISTS podcast_episodes (
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
        UNIQUE(podcast_id, guid)
    )''')
    
    # === Saved Episodes (Downloads) ===
    c.execute('''CREATE TABLE IF NOT EXISTS podcast_saved_episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        podcast_id INTEGER REFERENCES podcast_subscriptions(id) ON DELETE CASCADE,
        episode_id INTEGER REFERENCES podcast_episodes(id) ON DELETE CASCADE,
        file_path TEXT,
        size_mb REAL DEFAULT 0,
        saved_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # === Filter Cache ===
    c.execute('''CREATE TABLE IF NOT EXISTS filter_cache (
        type TEXT PRIMARY KEY,
        data TEXT,
        updated_at TEXT
    )''')
    
    # === Config ===
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # === Blocklist (Negativliste für Sender) ===
    c.execute('''CREATE TABLE IF NOT EXISTS blocklist (
        uuid TEXT PRIMARY KEY,
        name TEXT,
        reason TEXT,
        category TEXT DEFAULT 'manual',
        blocked_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # === Migration: category-Spalte hinzufuegen (idempotent) ===
    try:
        c.execute("ALTER TABLE blocklist ADD COLUMN category TEXT DEFAULT 'manual'")
        # Bestehende Eintraege migrieren
        c.execute("UPDATE blocklist SET category = 'ad' WHERE reason LIKE 'ad:%'")
        ad_count = c.rowcount
        c.execute("""UPDATE blocklist SET category = 'filter'
                     WHERE category = 'manual'
                     AND (reason LIKE '%language:%' OR reason LIKE '%country:%'
                          OR reason LIKE '%tag:%' OR reason LIKE '%votes<%')""")
        filter_count = c.rowcount
        if ad_count or filter_count:
            print(f"  Blocklist-Migration: {ad_count} ad, {filter_count} filter kategorisiert")
    except Exception:
        pass  # Spalte existiert bereits

    # === Detected Bitrates (ffprobe-Ergebnisse) ===
    c.execute('''CREATE TABLE IF NOT EXISTS detected_bitrates (
        uuid TEXT PRIMARY KEY,
        bitrate INTEGER,
        codec TEXT,
        sample_rate INTEGER,
        detected_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # === Cache Meta ===
    c.execute('''CREATE TABLE IF NOT EXISTS cache_meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # === Ad-Detection: Sender-Status ===
    c.execute('''CREATE TABLE IF NOT EXISTS station_ad_status (
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
    )''')

    # Migration: user_action Spalte (idempotent)
    try:
        c.execute("ALTER TABLE station_ad_status ADD COLUMN user_action TEXT")
    except Exception:
        pass

    # === Ad-Detection: Erkennungs-Log ===
    c.execute('''CREATE TABLE IF NOT EXISTS ad_detections_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        station_uuid TEXT,
        detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
        method TEXT,
        reason_code TEXT,
        detail TEXT,
        confidence REAL DEFAULT 0.0,
        resolved INTEGER DEFAULT 0
    )''')

    # === Ad-Detection: Domain-Blacklist ===
    c.execute('''CREATE TABLE IF NOT EXISTS domain_blacklist (
        domain TEXT PRIMARY KEY,
        category TEXT,
        source TEXT DEFAULT 'builtin',
        confidence REAL DEFAULT 0.9,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # === Indices für Performance ===
    c.execute("CREATE INDEX IF NOT EXISTS idx_stations_votes ON stations(votes DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_stations_country ON stations(countrycode)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_stations_name ON stations(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_podcast_episodes_podcast ON podcast_episodes(podcast_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_podcast_episodes_published ON podcast_episodes(published_at DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blocklist_reason ON blocklist(reason)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blocklist_category ON blocklist(category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ad_status_block ON station_ad_status(block_status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ad_log_station ON ad_detections_log(station_uuid)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_domain_blacklist_cat ON domain_blacklist(category)")

    conn.commit()
    conn.close()
    print("✓ Datenbank initialisiert")


def check_db_health() -> dict:
    """Prüft Datenbank-Gesundheit"""
    result = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        with db_session() as conn:
            c = conn.cursor()
            
            # Integrity Check
            c.execute("PRAGMA integrity_check")
            integrity = c.fetchone()[0]
            result["integrity"] = integrity == "ok"
            
            # WAL-Modus aktiv?
            c.execute("PRAGMA journal_mode")
            result["wal_mode"] = c.fetchone()[0] == "wal"
            
            if not result["integrity"]:
                result["status"] = "unhealthy"
                
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result
