"""
RadioHub - Ad Detector (Phase 2)

Werbeerkennung fuer Radiosender:
- Schicht 1: URL/Domain Pattern-Matching (kein I/O)
- Schicht 2: HTTP-Header-Analyse (1 HEAD-Request)

Ergebnisse werden in station_ad_status + ad_detections_log gespeichert.
KEIN automatisches Blocken -- User entscheidet ueber /api/ad-detection/decide.
"""
import json
import re
import httpx
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
    # URL-Methoden
    'URL_KNOWN_AD_NETWORK': 0.95,
    'URL_SSAI_DOMAIN': 0.90,
    'URL_AD_PATH_PATTERN': 0.85,
    'URL_TRACKING_REDIRECT': 0.80,
    'URL_AGGREGATOR_RELAY': 0.75,
    'URL_SUSPICIOUSLY_LONG': 0.35,
    'URL_CDN_MISMATCH': 0.40,
    'DOMAIN_BLACKLIST_MATCH': 0.90,
    # Header-Methoden
    'HEADER_SSAI_MARKER': 0.95,
    'HEADER_AD_SERVER_SIGNATURE': 0.85,
    'HEADER_TARGETING_COOKIES': 0.75,
    'HEADER_VARY_USERAGENT': 0.60,
    'HEADER_SUSPICIOUSLY_SHORT_TTL': 0.50,
    'HEADER_NO_ICY_NAME': 0.35,
    # Redirect-Methoden
    'REDIRECT_AD_INTERMEDIATE': 0.90,
    'REDIRECT_EXCESSIVE_HOPS': 0.50,
    # Manuell
    'MANUAL_USER_BLOCKED': 1.0,
    'MANUAL_CORRECTED_FALSE_POSITIVE': 0.0,
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


async def analyze_headers(url: str) -> list:
    """
    HTTP-Header-Analyse: HEAD-Request an Stream-URL.
    Erkennt SSAI-Header, Ad-Server-Signaturen, Redirect-Chains, Cache-TTL.
    """
    if not url:
        return []

    results = []
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.head(url, headers={
                'User-Agent': 'VLC/3.0 LibVLC/3.0',
                'Icy-MetaData': '1'
            })

            headers = {k.lower(): v for k, v in resp.headers.items()}

            # Check 1: SSAI-spezifische Header
            ssai_prefixes = [
                'x-triton-session', 'x-adswizz-', 'x-targetspot-',
                'x-stream-session', 'x-ad-', 'x-adserver',
            ]
            for prefix in ssai_prefixes:
                for h in headers:
                    if h.startswith(prefix):
                        results.append({
                            'reason': 'HEADER_SSAI_MARKER',
                            'confidence': METHOD_WEIGHTS['HEADER_SSAI_MARKER'],
                            'detail': f'Header: {h}: {headers[h][:100]}'
                        })
                        break
                if results and results[-1]['reason'] == 'HEADER_SSAI_MARKER':
                    break  # Ein SSAI-Header reicht

            # Check 2: Server-Signatur
            server = headers.get('server', '').lower()
            powered = headers.get('x-powered-by', '').lower()
            ad_signatures = ['adswizz', 'triton', 'streamguys', 'targeting', 'adserver']
            for sig in ad_signatures:
                if sig in server or sig in powered:
                    results.append({
                        'reason': 'HEADER_AD_SERVER_SIGNATURE',
                        'confidence': METHOD_WEIGHTS['HEADER_AD_SERVER_SIGNATURE'],
                        'detail': f'Server: {server}, X-Powered-By: {powered}'
                    })
                    break

            # Check 3: Vary: User-Agent (Ad-Targeting)
            vary = headers.get('vary', '').lower()
            if 'user-agent' in vary:
                results.append({
                    'reason': 'HEADER_VARY_USERAGENT',
                    'confidence': METHOD_WEIGHTS['HEADER_VARY_USERAGENT'],
                    'detail': f'Vary: {headers.get("vary", "")}'
                })

            # Check 4: Cache-Control TTL < 5s
            cc = headers.get('cache-control', '')
            max_age_match = re.search(r'max-age=(\d+)', cc)
            if max_age_match and int(max_age_match.group(1)) < 5:
                results.append({
                    'reason': 'HEADER_SUSPICIOUSLY_SHORT_TTL',
                    'confidence': METHOD_WEIGHTS['HEADER_SUSPICIOUSLY_SHORT_TTL'],
                    'detail': f'Cache-Control max-age={max_age_match.group(1)}'
                })

            # Check 5: Fehlender icy-name bei Audio-Stream
            content_type = headers.get('content-type', '').lower()
            if 'audio/' in content_type:
                if not headers.get('icy-name') and not headers.get('ice-name'):
                    results.append({
                        'reason': 'HEADER_NO_ICY_NAME',
                        'confidence': METHOD_WEIGHTS['HEADER_NO_ICY_NAME'],
                        'detail': f'Audio-Stream ({content_type}) ohne ICY-Name-Header'
                    })

            # Check 6: Redirect-Chain analysieren
            if resp.history:
                redirect_count = len(resp.history)
                if redirect_count > 2:
                    results.append({
                        'reason': 'REDIRECT_EXCESSIVE_HOPS',
                        'confidence': min(0.3 + redirect_count * 0.1, 0.70),
                        'detail': f'{redirect_count} Redirects'
                    })

                # Redirects ueber Ad-Domains?
                for r in resp.history:
                    rd = _extract_domain(str(r.url))
                    for ad_d in AD_NETWORK_DOMAINS:
                        if rd == ad_d or rd.endswith('.' + ad_d):
                            results.append({
                                'reason': 'REDIRECT_AD_INTERMEDIATE',
                                'confidence': METHOD_WEIGHTS['REDIRECT_AD_INTERMEDIATE'],
                                'detail': f'Redirect ueber Ad-Domain: {rd}'
                            })
                            break
                    if results and results[-1]['reason'] == 'REDIRECT_AD_INTERMEDIATE':
                        break

    except Exception as e:
        # Timeout, Connection refused etc. -- kein Fehler, nur kein Header-Check
        pass

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


def determine_block_status(confidence: float, reasons: list, manually_set: bool = False,
                           threshold: float = 0.80) -> dict:
    """
    Bewertet Konfidenz und gibt Empfehlung (KEIN automatisches Blocken).
    Returns: {status, action}
    action ist nur eine Empfehlung -- User entscheidet ueber /decide.
    """
    if manually_set:
        return {'status': 'manual_blocked', 'action': 'recommend_block'}

    # Single-High-Confidence
    for r in reasons:
        if r['confidence'] >= 0.90:
            return {'status': 'confirmed_ad', 'action': 'recommend_block'}

    # Kombinierte Konfidenz
    if confidence >= threshold:
        return {'status': 'confirmed_ad', 'action': 'recommend_block'}
    elif confidence >= 0.40:
        return {'status': 'suspect', 'action': 'recommend_review'}
    else:
        return {'status': 'clean', 'action': 'monitor'}


# === Config-Hilfsfunktion ===

def _get_ad_config() -> dict:
    """Laedt Ad-Detection-Einstellungen aus Config-Tabelle."""
    defaults = {
        'ad_detection_enabled': True,
        'ad_detection_methods': ['url_check', 'header_check'],
        'ad_detection_threshold': 0.80,
    }
    try:
        with db_session() as conn:
            c = conn.cursor()
            for key in defaults:
                c.execute("SELECT value FROM config WHERE key = ?", (key,))
                row = c.fetchone()
                if row and row[0] is not None:
                    val = row[0]
                    if key == 'ad_detection_enabled':
                        defaults[key] = val.lower() in ('true', '1', 'yes')
                    elif key == 'ad_detection_methods':
                        defaults[key] = json.loads(val) if isinstance(val, str) else val
                    elif key == 'ad_detection_threshold':
                        defaults[key] = float(val)
    except Exception:
        pass
    return defaults


# === Hauptfunktionen ===

async def check_station_ads(uuid: str, stream_url: str, name: Optional[str] = None) -> dict:
    """
    Orchestrator: Prueft einen Sender auf Werbung.
    - Schicht 1: URL-Pattern (kein I/O)
    - Schicht 2: HTTP-Header-Analyse (1 HEAD-Request)
    - Berechnet Konfidenz, schreibt station_ad_status + ad_detections_log
    - KEIN automatisches Blocken -- nur Empfehlung.
    """
    config = _get_ad_config()

    # Master-Schalter
    if not config['ad_detection_enabled']:
        return {
            'uuid': uuid,
            'status': 'disabled',
            'confidence': 0.0,
            'detections': [],
            'action': 'disabled',
        }

    all_detections = []
    methods_used = []

    # Schicht 1: URL-Pattern (sofort, kein Netzwerk)
    if 'url_check' in config['ad_detection_methods']:
        all_detections.extend(check_url(stream_url))
        all_detections.extend(check_domain_blacklist(stream_url))
        methods_used.append('url_check')

    # Schicht 2: HTTP-Header-Analyse (1 HEAD-Request)
    if 'header_check' in config['ad_detection_methods']:
        header_results = await analyze_headers(stream_url)
        all_detections.extend(header_results)
        if header_results:
            methods_used.append('header_check')

    # Konfidenz berechnen
    confidence = calculate_confidence(all_detections)
    threshold = config['ad_detection_threshold']
    block_result = determine_block_status(confidence, all_detections, threshold=threshold)

    now = datetime.now().isoformat()

    with db_session() as conn:
        c = conn.cursor()

        # Vorherigen Status pruefen
        c.execute("SELECT manually_set, check_count, ad_detections, user_action FROM station_ad_status WHERE station_uuid = ?", (uuid,))
        existing = c.fetchone()

        # User hat bereits entschieden (blocked oder allowed) -> nur check_count erhoehen
        if existing and existing[3] in ('blocked', 'allowed'):
            c.execute(
                "UPDATE station_ad_status SET last_checked = ?, check_count = check_count + 1, confidence = ?, reasons_json = ? WHERE station_uuid = ?",
                (now, confidence, json.dumps(all_detections) if all_detections else None, uuid)
            )
            return {
                'uuid': uuid,
                'status': existing[3],
                'confidence': confidence,
                'detections': all_detections,
                'action': 'skip_decided',
                'message': f'User hat bereits entschieden: {existing[3]}'
            }

        # Manuell gesetzt -> nicht ueberschreiben
        if existing and existing[0]:
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
            }

        check_count = (existing[1] + 1) if existing else 1
        prev_ad_count = (existing[2] or 0) if existing else 0
        ad_count = prev_ad_count + (len(all_detections) if all_detections else 0)

        reasons_json = json.dumps(all_detections) if all_detections else None
        primary_method = ','.join(methods_used) if methods_used else None

        # station_ad_status upsert (OHNE blocklist!)
        c.execute("""
            INSERT INTO station_ad_status
                (station_uuid, stream_url, block_status, confidence, reasons_json,
                 detection_method, first_detected, last_checked,
                 ad_detections, check_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(station_uuid) DO UPDATE SET
                stream_url = excluded.stream_url,
                block_status = excluded.block_status,
                confidence = excluded.confidence,
                reasons_json = excluded.reasons_json,
                detection_method = excluded.detection_method,
                last_checked = excluded.last_checked,
                ad_detections = excluded.ad_detections,
                check_count = excluded.check_count
        """, (
            uuid, stream_url, block_result['status'], confidence, reasons_json,
            primary_method,
            now if not existing else None,
            now,
            ad_count, check_count
        ))

        # Detections ins Log schreiben
        for det in all_detections:
            det_method = 'header_check' if det['reason'].startswith('HEADER_') or det['reason'].startswith('REDIRECT_') else 'url_check'
            c.execute("""
                INSERT INTO ad_detections_log (station_uuid, detected_at, method, reason_code, detail, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (uuid, now, det_method, det['reason'], det.get('detail', ''), det['confidence']))

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

        # Blocklist mit category
        c.execute(
            "INSERT OR IGNORE INTO blocklist (uuid, name, reason, category, blocked_at) VALUES (?, ?, 'ad:manual', 'ad', ?)",
            (uuid, name, now)
        )

    return {
        'uuid': uuid,
        'status': 'manual_blocked',
        'confidence': 1.0,
        'message': 'Sender als Werbung gemeldet und blockiert'
    }


def report_ad_mark_only(uuid: str, stream_url: str, name: str, note: Optional[str] = None) -> dict:
    """
    Werbung melden ohne zu blockieren: Markiert Sender als confirmed_ad
    in station_ad_status, schreibt NICHT in blocklist.
    """
    now = datetime.now().isoformat()

    with db_session() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO station_ad_status
                (station_uuid, stream_url, block_status, confidence, reasons_json,
                 detection_method, first_detected, last_checked,
                 manually_set, manual_note, ad_detections, check_count)
            VALUES (?, ?, 'confirmed_ad', 1.0, ?, 'manual', ?, ?,
                    1, ?, 1, 1)
            ON CONFLICT(station_uuid) DO UPDATE SET
                block_status = 'confirmed_ad',
                confidence = 1.0,
                reasons_json = excluded.reasons_json,
                detection_method = 'manual',
                last_checked = excluded.last_checked,
                manually_set = 1,
                manual_note = excluded.manual_note,
                ad_detections = station_ad_status.ad_detections + 1
        """, (
            uuid, stream_url,
            json.dumps([{'reason': 'MANUAL_USER_REPORTED', 'confidence': 1.0, 'detail': note or 'Manuell als Werbung markiert'}]),
            now, now, note
        ))

        c.execute("""
            INSERT INTO ad_detections_log (station_uuid, detected_at, method, reason_code, detail, confidence)
            VALUES (?, ?, 'manual', 'MANUAL_USER_REPORTED', ?, 1.0)
        """, (uuid, now, note or 'Manuell als Werbung markiert'))

    return {
        'uuid': uuid,
        'status': 'confirmed_ad',
        'confidence': 1.0,
        'message': 'Sender als Werbung markiert'
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
                user_action = 'allowed',
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


def get_suspects(min_confidence: float = 0.0) -> list:
    """
    Verdaechtige Sender: confidence > min_confidence, user_action noch nicht gesetzt,
    und nicht in blocklist.
    """
    threshold = max(min_confidence, 0.01)
    with db_session() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT s.station_uuid, st.name, s.stream_url, s.block_status,
                   s.confidence, s.reasons_json, s.detection_method, s.last_checked
            FROM station_ad_status s
            LEFT JOIN stations st ON st.uuid = s.station_uuid
            WHERE s.confidence >= ?
              AND (s.user_action IS NULL OR s.user_action = '')
              AND s.manually_set = 0
              AND s.station_uuid NOT IN (SELECT uuid FROM blocklist)
            ORDER BY s.confidence DESC
            LIMIT 100
        """, (threshold,))
        results = []
        for row in c.fetchall():
            results.append({
                'uuid': row[0],
                'name': row[1] or '',
                'stream_url': row[2],
                'status': row[3],
                'confidence': row[4],
                'reasons': json.loads(row[5]) if row[5] else [],
                'method': row[6],
                'last_checked': row[7],
            })
        return results


def decide_station_ad(uuid: str, action: str) -> dict:
    """
    User entscheidet: 'block' oder 'allow'.
    - block: In blocklist mit category='ad', Gruende aus station_ad_status
    - allow: user_action='allowed', wird nicht mehr gefragt
    """
    now = datetime.now().isoformat()

    with db_session() as conn:
        c = conn.cursor()

        # Status laden
        c.execute("SELECT stream_url, reasons_json, confidence FROM station_ad_status WHERE station_uuid = ?", (uuid,))
        row = c.fetchone()
        if not row:
            return {'uuid': uuid, 'success': False, 'message': 'Kein Ad-Status vorhanden'}

        stream_url, reasons_json, confidence = row[0], row[1], row[2]

        if action == 'block':
            # Reason aus Detection-Gruenden bauen
            reasons = json.loads(reasons_json) if reasons_json else []
            primary_reason = f"ad:{reasons[0]['reason']}" if reasons else 'ad:USER_CONFIRMED'

            # Sendername laden
            c.execute("SELECT name FROM stations WHERE uuid = ?", (uuid,))
            name_row = c.fetchone()
            name = name_row[0] if name_row else ''

            # In blocklist mit category
            c.execute(
                "INSERT OR IGNORE INTO blocklist (uuid, name, reason, category, blocked_at) VALUES (?, ?, ?, 'ad', ?)",
                (uuid, name, primary_reason, now)
            )

            # user_action setzen
            c.execute(
                "UPDATE station_ad_status SET user_action = 'blocked', blocked_at = ? WHERE station_uuid = ?",
                (now, uuid)
            )

            return {'uuid': uuid, 'success': True, 'action': 'blocked', 'reason': primary_reason}

        elif action == 'allow':
            c.execute(
                "UPDATE station_ad_status SET user_action = 'allowed', block_status = 'clean' WHERE station_uuid = ?",
                (uuid,)
            )
            return {'uuid': uuid, 'success': True, 'action': 'allowed'}

        return {'uuid': uuid, 'success': False, 'message': f'Unbekannte Aktion: {action}'}


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
