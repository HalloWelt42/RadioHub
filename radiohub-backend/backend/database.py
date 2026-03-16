"""
RadioHub v0.1.1 - Datenbank

SQLite mit WAL-Modus für bessere Concurrency.
Nur Core-Tabellen (keine Alarms, Export, Waveform).
"""
import sqlite3
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

    # === Migration: category-Spalte hinzufügen (idempotent) ===
    try:
        c.execute("ALTER TABLE blocklist ADD COLUMN category TEXT DEFAULT 'manual'")
        # Bestehende Einträge migrieren
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

    # === Recording Folders (Ordner für Aufnahmen) ===
    c.execute('''CREATE TABLE IF NOT EXISTS recording_folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        path TEXT NOT NULL UNIQUE,
        is_active INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # === Segments (atomare Audio-Segmente pro Session) ===
    c.execute('''CREATE TABLE IF NOT EXISTS segments (
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
    )''')

    # === Migration: detected_bitrates um icy-Spalte erweitern ===
    try:
        c.execute("ALTER TABLE detected_bitrates ADD COLUMN icy INTEGER DEFAULT 0")
    except Exception:
        pass

    # === Migration: detected_bitrates um icy_quality erweitern ===
    # Werte: NULL=nicht bewertet, 'good'=genaue Cuts, 'poor'=ungenaue Cuts
    try:
        c.execute("ALTER TABLE detected_bitrates ADD COLUMN icy_quality TEXT")
    except Exception:
        pass

    # === Migration: Sessions-Tabelle erweitern ===
    for col, typedef in [
        ("codec", "TEXT"),
        ("file_format", "TEXT"),
        ("meta_file_path", "TEXT"),
        ("rec_type", "TEXT DEFAULT 'direct'"),
        ("folder_id", "INTEGER REFERENCES recording_folders(id) ON DELETE SET NULL"),
        ("quality_json", "TEXT"),  # JSON: {gaps, codec_changes, stalls, rating}
    ]:
        try:
            c.execute(f"ALTER TABLE sessions ADD COLUMN {col} {typedef}")
        except Exception:
            pass  # Spalte existiert bereits

    # === Benutzerdefinierte Kategorien ===
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        tags TEXT NOT NULL DEFAULT '',
        scope TEXT NOT NULL DEFAULT 'radio',
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # === Kategorie-Sender-Zuordnung ===
    c.execute('''CREATE TABLE IF NOT EXISTS category_stations (
        category_id INTEGER NOT NULL,
        station_uuid TEXT NOT NULL,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (category_id, station_uuid),
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
    )''')

    # === Kategorie-Podcast-Zuordnung ===
    c.execute('''CREATE TABLE IF NOT EXISTS category_podcasts (
        category_id INTEGER NOT NULL,
        podcast_id INTEGER NOT NULL,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (category_id, podcast_id),
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
        FOREIGN KEY (podcast_id) REFERENCES podcast_subscriptions(id) ON DELETE CASCADE
    )''')

    # === Kategorie-Aufnahme-Zuordnung ===
    c.execute('''CREATE TABLE IF NOT EXISTS category_sessions (
        category_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (category_id, session_id),
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )''')

    # === Migration: categories scope-Spalte (idempotent) ===
    try:
        c.execute("ALTER TABLE categories ADD COLUMN scope TEXT NOT NULL DEFAULT 'radio'")
    except Exception:
        pass  # Spalte existiert bereits

    # === Migration: podcast_subscriptions erweitern ===
    for col, typedef in [
        ("local_image_path", "TEXT"),
        ("categories", "TEXT DEFAULT ''"),
        ("sort_order", "INTEGER DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE podcast_subscriptions ADD COLUMN {col} {typedef}")
        except Exception:
            pass

    # === Migration: podcast_episodes erweitern ===
    for col, typedef in [
        ("is_played", "INTEGER DEFAULT 0"),
        ("file_size", "INTEGER DEFAULT 0"),
        ("image_url", "TEXT"),
        ("local_image_path", "TEXT"),
        ("transcript_url", "TEXT"),
        ("transcript", "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE podcast_episodes ADD COLUMN {col} {typedef}")
        except Exception:
            pass

    # === ICY-Titel Ignorier-Liste ===
    c.execute('''CREATE TABLE IF NOT EXISTS icy_title_ignore (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern TEXT UNIQUE NOT NULL,
        match_type TEXT DEFAULT 'exact',
        source TEXT DEFAULT 'user',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Builtin-Eintraege (idempotent)
    for pattern, mtype in [
        ("THIS STATION WILL CONTINUE AFTER THIS BREAK", "exact"),
        ("ADBREAK", "contains"),
        ("AD BREAK", "contains"),
    ]:
        c.execute(
            "INSERT OR IGNORE INTO icy_title_ignore (pattern, match_type, source) VALUES (?, ?, 'builtin')",
            (pattern, mtype)
        )

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
    c.execute("CREATE INDEX IF NOT EXISTS idx_segments_session ON segments(session_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_folder ON sessions(folder_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rec_folders_active ON recording_folders(is_active)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_categories_sort ON categories(sort_order)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_categories_scope ON categories(scope)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cat_stations_uuid ON category_stations(station_uuid)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cat_stations_cat ON category_stations(category_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cat_podcasts_pod ON category_podcasts(podcast_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cat_podcasts_cat ON category_podcasts(category_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cat_sessions_ses ON category_sessions(session_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cat_sessions_cat ON category_sessions(category_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_podcast_episodes_downloaded ON podcast_episodes(is_downloaded)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_podcast_episodes_played ON podcast_episodes(is_played)")

    # === Migration: published_at RFC 2822 -> ISO 8601 ===
    try:
        from email.utils import parsedate_to_datetime
        rows = c.execute("SELECT id, published_at FROM podcast_episodes WHERE published_at LIKE '%,%'").fetchall()
        for row in rows:
            try:
                dt = parsedate_to_datetime(row[1])
                iso = dt.strftime("%Y-%m-%dT%H:%M:%S")
                c.execute("UPDATE podcast_episodes SET published_at = ? WHERE id = ?", (iso, row[0]))
            except Exception:
                pass
        if rows:
            print(f"  → {len(rows)} Episoden-Daten auf ISO 8601 migriert")
    except Exception:
        pass

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
