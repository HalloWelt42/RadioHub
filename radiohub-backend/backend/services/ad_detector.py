"""
RadioHub - Ad Detector (Phase 1)

URL/Domain-basierte Werbeerkennung fuer Radiosender.
Erkennt bekannte Werbenetzwerke, SSAI-Domains, Ad-Pfad-Muster.
Ergebnisse werden in station_ad_status + ad_detections_log gespeichert.
Bei hoher Konfidenz: automatische Blockierung via blocklist.
"""
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional

from ..database import db_session


# === Bekannte Werbenetzwerk-Domains ===

AD_NETWORK_DOMAINS = [
    # AdsWizz
    'adswizz.com', 'deliveryengine.adswizz.com', 'cdn.adswizz.com',
    'delivery-cdn-cf.adswizz.com', 'attribution.adswizz.com',
    'synchrobox.adswizz.com', 'second-screen.adswizz.com',
    'trackingengine-us-west-2.adswizz.com', 'kriteria.adswizz.com',
    'zc.adswizz.com', 'audiogo.adswizz.com',

    # Triton Digital / StreamTheWorld
    'tritondigital.com', 'streamtheworld.com', 'live.streamtheworld.com',
    'cmod.live.streamtheworld.com', 'cmod-world.live.streamtheworld.com',
    'ondemand-ad-server.tritondigital.com',
    'na.ondemand-ad-server.tritondigital.com',
    'ondemand-impression.tritondigital.com',
    'creative-tracker.tritondigital.com',
    'playerservices.streamtheworld.com',
    'iadsrv.tritondigital.com',

    # StreamGuys
    'streamguys.com', 'streamguys1.com', 'sgcaster.com',

    # Omny Studio / Spotify
    'omny.fm', 'omnystudio.com', 'megaphone.fm',

    # Targetspot / AudioGO / DAX
    'targetspot.com', 'audiogo.com', 'dax.io', 'global-audio.net',

    # AdTonos
    'adtonos.com', 'play.adtonos.com',

    # Nimble Advertizer / Softvelum
    'nimblestreamer.com',

    # Podcast / DAI Tracking
    'podsights.com', 'podscribe.com', 'chartable.com',
    'podtrac.com', 'podcorn.com', 'blubrry.com', 'transistor.fm',

    # Audio Ad Tracking allgemein
    'audio.ad', 'audiads.com', 'audiomatic.in',
    'spotxchange.com', 'spotx.tv', 'lijit.com',
]

SSAI_DOMAINS = {
    'adswizz.com', 'tritondigital.com', 'streamtheworld.com',
    'live.streamtheworld.com', 'cmod.live.streamtheworld.com',
}

AD_PATH_PATTERNS = [
    r'/ad[s]?/',
    r'/preroll[s]?/',
    r'/midroll[s]?/',
    r'/postroll[s]?/',
    r'/vast\.xml',
    r'/daast\.xml',
    r'[?&]ad[Tt]ype=',
    r'[?&]adid=',
    r'[?&]adUnit=',
    r'cmod',
    r'/inventory/',
    r'/targeting/',
    r'[?&]stationId=.*[?&]',
]

AGGREGATOR_RELAY_DOMAINS = [
    'radionomy.com', 'securenet.fm', 'hostingbaby.com',
    'streambrothers.com', 'radiostreamz.net',
    'myradiostream.com', 'radiohoster.de', 'stream-server.eu',
]

# Konfidenz-Gewichte pro Reason-Code
METHOD_WEIGHTS = {
    'URL_KNOWN_AD_NETWORK': 0.95,
    'URL_SSAI_DOMAIN': 0.90,
    'URL_AD_PATH_PATTERN': 0.85,
    'URL_TRACKING_REDIRECT': 0.80,
    'URL_AGGREGATOR_RELAY': 0.75,
    'URL_SUSPICIOUSLY_LONG': 0.35,
    'URL_CDN_MISMATCH': 0.40,
    'MANUAL_USER_BLOCKED': 1.0,
    'MANUAL_CORRECTED_FALSE_POSITIVE': 0.0,
    'DOMAIN_BLACKLIST_MATCH': 0.90,
}


# === Hilfsfunktionen ===

def _extract_domain(url: str) -> str:
    """Extrahiert Domain aus URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().split(':')[0]
    except Exception:
        return ""


def check_url(url: str) -> list:
    """
    Reine URL/Domain Pattern-Erkennung. Kein I/O, kein Netzwerk.
    Returns: Liste von Detection-Dicts {reason, confidence, detail}
    """
    if not url:
        return []

    results = []
    domain = _extract_domain(url)
    parsed = urlparse(url)

    # Check 1: Bekannte Ad-Netzwerk-Domains (exact + subdomain)
    for ad_domain in AD_NETWORK_DOMAINS:
        if domain == ad_domain or domain.endswith('.' + ad_domain):
            reason = 'URL_SSAI_DOMAIN' if ad_domain in SSAI_DOMAINS else 'URL_KNOWN_AD_NETWORK'
            conf = METHOD_WEIGHTS.get(reason, 0.90)
            results.append({
                'reason': reason,
                'confidence': conf,
                'detail': f'Domain: {domain} matches {ad_domain}'
            })
            break  # Ein Domain-Match reicht

    # Check 2: Aggregator-Relay-Domains
    for relay_domain in AGGREGATOR_RELAY_DOMAINS:
        if domain == relay_domain or domain.endswith('.' + relay_domain):
            results.append({
                'reason': 'URL_AGGREGATOR_RELAY',
                'confidence': METHOD_WEIGHTS['URL_AGGREGATOR_RELAY'],
                'detail': f'Aggregator-Relay: {domain} matches {relay_domain}'
            })
            break

    # Check 3: Pfad-Pattern
    path = parsed.path.lower()
    query = parsed.query.lower()
    full_path = path + '?' + query if query else path
    for pattern in AD_PATH_PATTERNS:
        if re.search(pattern, full_path):
            results.append({
                'reason': 'URL_AD_PATH_PATTERN',
                'confidence': METHOD_WEIGHTS['URL_AD_PATH_PATTERN'],
                'detail': f'Pattern: {pattern}'
            })
            break  # Ein Pattern-Match reicht

    # Check 4: Zu viele Query-Parameter (Ad-Targeting)
    params = parsed.query.split('&') if parsed.query else []
    if len(params) > 5:
        results.append({
            'reason': 'URL_SUSPICIOUSLY_LONG',
            'confidence': METHOD_WEIGHTS['URL_SUSPICIOUSLY_LONG'],
            'detail': f'{len(params)} Query-Parameter'
        })

    return results


def check_domain_blacklist(url: str) -> list:
    """Prueft URL gegen domain_blacklist Tabelle in der DB."""
    domain = _extract_domain(url)
    if not domain:
        return []

    results = []
    with db_session() as conn:
        c = conn.cursor()
        # Exakter Match oder Subdomain-Match
        c.execute(
            "SELECT domain, category, confidence FROM domain_blacklist"
        )
        for row in c.fetchall():
            bl_domain = row[0]
            if domain == bl_domain or domain.endswith('.' + bl_domain):
                results.append({
                    'reason': 'DOMAIN_BLACKLIST_MATCH',
                    'confidence': row[2] or 0.90,
                    'detail': f'Blacklist: {domain} -> {bl_domain} (Kategorie: {row[1]})'
                })
                break

    return results


def calculate_confidence(detections: list) -> float:
    """
    Noisy-OR-Kombination: Mehrere schwache Signale ergeben zusammen starkes Signal.
    Formel: P(ad) = 1 - Pi(1 - p_i) fuer alle p_i
    """
    if not detections:
        return 0.0
    p_not_ad = 1.0
    for d in detections:
        p_not_ad *= (1.0 - d['confidence'])
    return round(1.0 - p_not_ad, 4)


def determine_block_status(confidence: float, reasons: list, manually_set: bool = False) -> dict:
    """
    Entscheidet ueber Block-Status basierend auf Konfidenz.
    Returns: {status, action}
    """
    if manually_set:
        return {'status': 'manual_blocked', 'action': 'block'}

    # Direkte Blockierung bei Single-High-Confidence-Reason
    for r in reasons:
        if r['confidence'] >= 0.90:
            return {'status': 'auto_blocked', 'action': 'block'}

    # Kombinierte Konfidenz
    if confidence >= 0.80:
        return {'status': 'confirmed_ad', 'action': 'block'}
    elif confidence >= 0.40:
        return {'status': 'suspect', 'action': 'flag'}
    else:
        return {'status': 'clean', 'action': 'monitor'}


# === Hauptfunktionen ===

def check_station_ads(uuid: str, stream_url: str, name: Optional[str] = None) -> dict:
    """
    Orchestrator: Prueft einen Sender auf Werbung (Phase 1: nur URL-Check).
    - Ruft check_url() auf
    - Prueft domain_blacklist
    - Berechnet Konfidenz
    - Schreibt station_ad_status + ad_detections_log
    - Bei confidence >= 0.80: Schreibt in blocklist mit reason "ad:REASON_CODE"
    """
    all_detections = []

    # Schicht 1: URL-Pattern (sofort, kein Netzwerk)
    all_detections.extend(check_url(stream_url))

    # Schicht 2: Domain-Blacklist aus DB
    all_detections.extend(check_domain_blacklist(stream_url))

    # Konfidenz berechnen
    confidence = calculate_confidence(all_detections)
    block_result = determine_block_status(confidence, all_detections)

    now = datetime.now().isoformat()

    with db_session() as conn:
        c = conn.cursor()

        # Vorherigen Status pruefen (manually_set nicht ueberschreiben)
        c.execute("SELECT manually_set, check_count, ad_detections FROM station_ad_status WHERE station_uuid = ?", (uuid,))
        existing = c.fetchone()

        if existing and existing[0]:
            # Manuell gesetzt -- nicht ueberschreiben, nur check_count erhoehen
            c.execute(
                "UPDATE station_ad_status SET last_checked = ?, check_count = check_count + 1 WHERE station_uuid = ?",
                (now, uuid)
            )
            return {
                'uuid': uuid,
                'status': 'manual_blocked',
                'confidence': 1.0,
                'detections': all_detections,
                'action': 'skip_manual',
                'message': 'Manuell gesetzt, nicht ueberschrieben'
            }

        check_count = (existing[1] + 1) if existing else 1
        prev_ad_count = (existing[2] or 0) if existing else 0
        ad_count = prev_ad_count + (len(all_detections) if all_detections else 0)

        reasons_json = json.dumps(all_detections) if all_detections else None
        primary_method = all_detections[0]['reason'] if all_detections else None

        # station_ad_status upsert
        c.execute("""
            INSERT INTO station_ad_status
                (station_uuid, stream_url, block_status, confidence, reasons_json,
                 detection_method, first_detected, last_checked, blocked_at,
                 ad_detections, check_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(station_uuid) DO UPDATE SET
                stream_url = excluded.stream_url,
                block_status = excluded.block_status,
                confidence = excluded.confidence,
                reasons_json = excluded.reasons_json,
                detection_method = excluded.detection_method,
                last_checked = excluded.last_checked,
                blocked_at = CASE WHEN excluded.block_status IN ('auto_blocked', 'confirmed_ad')
                             THEN COALESCE(station_ad_status.blocked_at, excluded.blocked_at)
                             ELSE station_ad_status.blocked_at END,
                ad_detections = excluded.ad_detections,
                check_count = excluded.check_count
        """, (
            uuid, stream_url, block_result['status'], confidence, reasons_json,
            primary_method,
            now if not existing else None,  # first_detected nur beim ersten Mal
            now,
            now if block_result['action'] == 'block' else None,
            ad_count, check_count
        ))

        # Detections ins Log schreiben
        for det in all_detections:
            c.execute("""
                INSERT INTO ad_detections_log (station_uuid, detected_at, method, reason_code, detail, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (uuid, now, 'url_check', det['reason'], det.get('detail', ''), det['confidence']))

        # Bei hoher Konfidenz: blocklist
        if block_result['action'] == 'block' and all_detections:
            primary_reason = f"ad:{all_detections[0]['reason']}"
            c.execute(
                "INSERT OR IGNORE INTO blocklist (uuid, name, reason, blocked_at) VALUES (?, ?, ?, ?)",
                (uuid, name or '', primary_reason, now)
            )

    return {
        'uuid': uuid,
        'status': block_result['status'],
        'confidence': confidence,
        'detections': all_detections,
        'action': block_result['action'],
    }


def report_ad_manual(uuid: str, stream_url: str, name: str, note: Optional[str] = None) -> dict:
    """
    Manuell Werbung melden: User markiert Sender als Werbesender.
    Schreibt station_ad_status mit MANUAL_USER_BLOCKED + confidence 1.0.
    Schreibt in blocklist mit reason "ad:manual".
    """
    now = datetime.now().isoformat()

    with db_session() as conn:
        c = conn.cursor()

        # station_ad_status
        c.execute("""
            INSERT INTO station_ad_status
                (station_uuid, stream_url, block_status, confidence, reasons_json,
                 detection_method, first_detected, last_checked, blocked_at,
                 manually_set, manual_note, ad_detections, check_count)
            VALUES (?, ?, 'manual_blocked', 1.0, ?, 'manual', ?, ?, ?, 1, ?, 1, 1)
            ON CONFLICT(station_uuid) DO UPDATE SET
                block_status = 'manual_blocked',
                confidence = 1.0,
                reasons_json = excluded.reasons_json,
                detection_method = 'manual',
                last_checked = excluded.last_checked,
                blocked_at = excluded.blocked_at,
                manually_set = 1,
                manual_note = excluded.manual_note,
                ad_detections = station_ad_status.ad_detections + 1
        """, (
            uuid, stream_url,
            json.dumps([{'reason': 'MANUAL_USER_BLOCKED', 'confidence': 1.0, 'detail': note or 'Manuell gemeldet'}]),
            now, now, now, note
        ))

        # Detection-Log
        c.execute("""
            INSERT INTO ad_detections_log (station_uuid, detected_at, method, reason_code, detail, confidence)
            VALUES (?, ?, 'manual', 'MANUAL_USER_BLOCKED', ?, 1.0)
        """, (uuid, now, note or 'Manuell gemeldet'))

        # Blocklist
        c.execute(
            "INSERT OR IGNORE INTO blocklist (uuid, name, reason, blocked_at) VALUES (?, ?, 'ad:manual', ?)",
            (uuid, name, now)
        )

    return {
        'uuid': uuid,
        'status': 'manual_blocked',
        'confidence': 1.0,
        'message': 'Sender als Werbung gemeldet und blockiert'
    }


def mark_false_positive(uuid: str) -> dict:
    """
    Fehlalarm markieren: Setzt Status auf clean, entfernt ad:-Eintraege aus blocklist.
    """
    now = datetime.now().isoformat()

    with db_session() as conn:
        c = conn.cursor()

        # Status zuruecksetzen
        c.execute("""
            UPDATE station_ad_status
            SET block_status = 'clean', confidence = 0.0,
                manually_set = 0, manual_note = NULL,
                false_positives = false_positives + 1,
                last_checked = ?
            WHERE station_uuid = ?
        """, (now, uuid))

        updated = c.rowcount

        # Log-Eintraege als resolved markieren
        c.execute(
            "UPDATE ad_detections_log SET resolved = 1 WHERE station_uuid = ? AND resolved = 0",
            (uuid,)
        )

        # Aus blocklist entfernen wo reason mit "ad:" anfaengt
        c.execute(
            "DELETE FROM blocklist WHERE uuid = ? AND reason LIKE 'ad:%'",
            (uuid,)
        )
        removed = c.rowcount

    return {
        'uuid': uuid,
        'status': 'clean',
        'updated': updated > 0,
        'blocklist_removed': removed,
        'message': 'Fehlalarm markiert, Sender freigegeben'
    }


def get_ad_status(uuid: str) -> Optional[dict]:
    """Holt Ad-Status fuer einen einzelnen Sender."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM station_ad_status WHERE station_uuid = ?", (uuid,))
        row = c.fetchone()
        if not row:
            return None
        return dict(row)


def get_ad_summary() -> dict:
    """Uebersicht: Wie viele Sender in welchem Status."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT block_status, COUNT(*) as cnt
            FROM station_ad_status
            GROUP BY block_status
        """)
        counts = {row[0]: row[1] for row in c.fetchall()}

        c.execute("SELECT COUNT(*) FROM station_ad_status")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM domain_blacklist")
        domains = c.fetchone()[0]

    return {
        'total_checked': total,
        'clean': counts.get('clean', 0),
        'suspect': counts.get('suspect', 0),
        'confirmed_ad': counts.get('confirmed_ad', 0),
        'auto_blocked': counts.get('auto_blocked', 0),
        'manual_blocked': counts.get('manual_blocked', 0),
        'domain_blacklist_count': domains,
    }


def seed_domain_blacklist():
    """
    Befuellt domain_blacklist mit Builtin-Domains beim ersten Start.
    Wird nur einmal ausgefuehrt (idempotent via INSERT OR IGNORE).
    """
    now = datetime.now().isoformat()

    entries = []

    for domain in AD_NETWORK_DOMAINS:
        cat = 'ssai' if domain in SSAI_DOMAINS else 'ad_network'
        entries.append((domain, cat, 'builtin', 0.90, now))

    for domain in AGGREGATOR_RELAY_DOMAINS:
        entries.append((domain, 'relay', 'builtin', 0.75, now))

    with db_session() as conn:
        c = conn.cursor()
        c.executemany(
            "INSERT OR IGNORE INTO domain_blacklist (domain, category, source, confidence, added_at) VALUES (?, ?, ?, ?, ?)",
            entries
        )
        inserted = c.rowcount

    if inserted > 0:
        print(f"  {inserted} Domains in Blacklist eingetragen")
