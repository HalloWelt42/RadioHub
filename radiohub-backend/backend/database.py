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

    # Migration: last_seen Spalte hinzufuegen falls nicht vorhanden
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
        blocked_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # === Migration: hidden_stations -> blocklist ===
    # Daten uebernehmen, dann Tabelle loeschen
    try:
        c.execute("SELECT uuid, name, reason, hidden_at FROM hidden_stations")
        hidden_rows = c.fetchall()
        for row in hidden_rows:
            c.execute(
                "INSERT OR IGNORE INTO blocklist (uuid, name, reason, blocked_at) VALUES (?, ?, ?, ?)",
                (row[0], row[1], row[2], row[3])
            )
        if hidden_rows:
            print(f"  {len(hidden_rows)} Sender von hidden_stations nach blocklist migriert")
        c.execute("DROP TABLE IF EXISTS hidden_stations")
    except Exception:
        # Tabelle existiert nicht (mehr) -- OK
        pass

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
    
    # === Indices für Performance ===
    c.execute("CREATE INDEX IF NOT EXISTS idx_stations_votes ON stations(votes DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_stations_country ON stations(countrycode)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_stations_name ON stations(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_podcast_episodes_podcast ON podcast_episodes(podcast_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_podcast_episodes_published ON podcast_episodes(published_at DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blocklist_reason ON blocklist(reason)")
    
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
