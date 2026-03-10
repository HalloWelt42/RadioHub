"""
RadioHub - Bitrate Detector

Erkennt echte Stream-Bitrate via ffprobe.
ICY-Metadata-Support via Raw-TCP HEAD-Check.
Fallback: URL-Analyse für Bitrate/Codec-Hinweise.
Ergebnisse werden in detected_bitrates gecacht.
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Optional, List
from urllib.parse import unquote, urlparse

from ..database import db_session


# Max gleichzeitige ffprobe-Prozesse
MAX_CONCURRENT = 5
# Timeout pro Stream in Sekunden
PROBE_TIMEOUT = 8.0

# Bekannte Bitrate-Werte für URL-Matching
KNOWN_BITRATES = {24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320}


def parse_url_hints(url: str) -> Optional[dict]:
    """Extrahiert Bitrate/Codec-Hinweise aus der Stream-URL.

    Erkennt Muster wie:
    - audio=128000, audio%3d128000 (bps -> kbps)
    - /128/, _128., -128k, 128kbps
    - .mp3, .aac, .ogg, .opus, .m3u8
    """
    decoded = unquote(url).lower()
    bitrate = 0
    codec = ""

    # 1. audio=NNNNNN (bps, z.B. audio=128000 -> 128 kbps)
    m = re.search(r'audio[=:](\d{4,6})\b', decoded)
    if m:
        bps = int(m.group(1))
        kbps = bps // 1000
        if kbps in KNOWN_BITRATES:
            bitrate = kbps

    # 2. Bitrate im Pfad: /128/, _128., -128k, 128kbps
    if not bitrate:
        m = re.search(r'[/_\-.](\d{2,3})(?:k(?:bps)?)?[/_\-.]', decoded)
        if m:
            val = int(m.group(1))
            if val in KNOWN_BITRATES:
                bitrate = val

    # 3. Codec aus Dateiendung
    if decoded.endswith('.mp3') or '/mp3/' in decoded or '.mp3?' in decoded:
        codec = "mp3"
    elif decoded.endswith('.aac') or '/aac/' in decoded or '.aac?' in decoded:
        codec = "aac"
    elif decoded.endswith('.ogg') or '/ogg/' in decoded:
        codec = "ogg"
    elif decoded.endswith('.opus') or '/opus/' in decoded:
        codec = "opus"
    elif '.m3u8' in decoded:
        codec = "aac"  # HLS ist fast immer AAC

    if not bitrate and not codec:
        return None

    return {"bitrate": bitrate, "codec": codec, "sample_rate": 0}


async def probe_bitrate(stream_url: str, timeout: float = PROBE_TIMEOUT) -> Optional[dict]:
    """
    Erkennt Bitrate eines Streams via ffprobe.
    Fallback: URL-Analyse wenn ffprobe scheitert.

    Returns:
        dict mit bitrate (kbps), codec, sample_rate oder None bei Fehler
    """
    # 1. Versuch: ffprobe
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "a:0",
            stream_url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            stdout = None

        if process.returncode == 0 and stdout:
            data = json.loads(stdout.decode())
            streams = data.get("streams", [])

            if streams:
                stream = streams[0]
                bitrate_raw = stream.get("bit_rate", "0")
                bitrate = int(bitrate_raw) // 1000 if bitrate_raw else 0

                if bitrate > 0:
                    return {
                        "bitrate": bitrate,
                        "codec": stream.get("codec_name", ""),
                        "sample_rate": int(stream.get("sample_rate", 0))
                    }

    except Exception as e:
        print(f"  ffprobe Fehler: {e}")

    # 2. Fallback: URL-Analyse
    hints = parse_url_hints(stream_url)
    if hints:
        print(f"  URL-Hinweis: {stream_url[:60]}... -> {hints['bitrate']}kbps/{hints['codec']}")
    return hints


async def check_icy_support(stream_url: str, timeout: float = 5.0) -> bool:
    """Prueft via Raw-TCP ob ein Stream ICY-Metadata unterstuetzt.

    Sendet HTTP GET mit Icy-MetaData:1 und prueft ob icy-metaint
    im Response-Header vorkommt.
    """
    try:
        parsed = urlparse(stream_url)
        host = parsed.hostname
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        if not host:
            return False

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )

        request = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            f"Icy-MetaData: 1\r\n"
            f"User-Agent: RadioHub/0.2\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        writer.write(request.encode())
        await writer.drain()

        # Nur Header lesen (max 4KB)
        header_data = await asyncio.wait_for(reader.read(4096), timeout=timeout)
        header_str = header_data.decode("utf-8", errors="replace").lower()

        writer.close()

        return "icy-metaint" in header_str

    except Exception:
        return False


async def fetch_icy_title(stream_url: str, timeout: float = 8.0) -> Optional[str]:
    """Holt den aktuellen ICY-StreamTitle via One-Shot Raw-TCP.

    Verbindet sich, liest Header fuer metaint, dann genau einen
    Metadata-Block, und schliesst sofort. Gibt den Titel zurueck
    oder None bei Fehler / kein ICY.
    """
    reader = None
    writer = None
    try:
        parsed = urlparse(stream_url)
        host = parsed.hostname
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        if not host:
            return None

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )

        request = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            f"Icy-MetaData: 1\r\n"
            f"User-Agent: RadioHub/0.2\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        writer.write(request.encode())
        await writer.drain()

        # Header lesen, metaint extrahieren
        metaint = 0
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            line_str = line.decode("utf-8", errors="replace").strip()
            if not line_str:
                break
            if line_str.lower().startswith("icy-metaint:"):
                try:
                    metaint = int(line_str.split(":", 1)[1].strip())
                except ValueError:
                    pass

        if not metaint:
            return None

        # Audio-Bytes ueberspringen bis zum ersten Metadata-Block
        remaining = metaint
        while remaining > 0:
            chunk = await asyncio.wait_for(reader.read(min(remaining, 8192)), timeout=timeout)
            if not chunk:
                return None
            remaining -= len(chunk)

        # Metadata-Laenge (1 Byte)
        length_byte = await asyncio.wait_for(reader.readexactly(1), timeout=timeout)
        meta_length = length_byte[0] * 16

        if meta_length == 0:
            return None  # Kein Titel in diesem Block

        # Metadata lesen und StreamTitle parsen
        meta_data = await asyncio.wait_for(reader.readexactly(meta_length), timeout=timeout)
        meta_str = meta_data.decode("utf-8", errors="replace").rstrip("\x00")

        match = re.search(r"StreamTitle='([^']*)'", meta_str)
        if match:
            title = match.group(1).strip()
            return title if title else None

        return None

    except Exception:
        return None
    finally:
        if writer:
            try:
                writer.close()
            except Exception:
                pass


def get_cached_bitrates(uuids: List[str]) -> dict:
    """Holt gecachte Bitrates + Codec + ICY + icy_quality fuer mehrere UUIDs."""
    if not uuids:
        return {}

    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(uuids))
        c.execute(
            f"SELECT uuid, bitrate, codec, icy, icy_quality FROM detected_bitrates WHERE uuid IN ({placeholders})",
            uuids
        )
        return {row[0]: {"bitrate": row[1], "codec": row[2] or "", "icy": bool(row[3]), "icy_quality": row[4]} for row in c.fetchall()}


def save_detected_bitrate(uuid: str, bitrate: int, codec: str = "", sample_rate: int = 0, icy: bool = False):
    """Speichert erkannte Bitrate + ICY-Status in DB."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO detected_bitrates
               (uuid, bitrate, codec, sample_rate, icy, detected_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (uuid, bitrate, codec, sample_rate, int(icy), datetime.now().isoformat())
        )


def set_icy_quality(uuid: str, quality: Optional[str]):
    """Setzt die ICY-Qualitaetsbewertung fuer einen Sender.

    quality: 'good', 'poor', oder None (zuruecksetzen)
    Legt ggf. einen Minimal-Eintrag an falls der Sender noch nicht geprobt wurde.
    """
    with db_session() as conn:
        c = conn.cursor()
        # Erst versuchen bestehenden Eintrag zu updaten
        c.execute(
            "UPDATE detected_bitrates SET icy_quality = ? WHERE uuid = ?",
            (quality, uuid)
        )
        if c.rowcount == 0:
            # Kein Eintrag vorhanden -> Minimal-Eintrag anlegen
            c.execute(
                """INSERT INTO detected_bitrates (uuid, bitrate, codec, sample_rate, icy, icy_quality, detected_at)
                   VALUES (?, 0, '', 0, 1, ?, ?)""",
                (uuid, quality, datetime.now().isoformat())
            )


def get_uuids_needing_probe(uuids: List[str]) -> List[str]:
    """Filtert UUIDs die noch nicht erfolgreich geprobt wurden.

    Übersprungen werden nur UUIDs mit plausiblem Ergebnis:
    - Bitrate zwischen 8 und 512 kbps
    - Codec bekannt (nicht leer, nicht UNKNOWN)

    Alles andere (nie geprobt, fehlgeschlagen, implausibel) wird (erneut) geprobt.
    """
    if not uuids:
        return []

    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(uuids))
        c.execute(
            f"""SELECT uuid FROM detected_bitrates
                WHERE uuid IN ({placeholders})
                AND bitrate >= 8 AND bitrate <= 512
                AND codec IS NOT NULL AND codec != '' AND UPPER(codec) != 'UNKNOWN'""",
            uuids
        )
        plausible = {row[0] for row in c.fetchall()}
        return [u for u in uuids if u not in plausible]


async def probe_stations(stations: List[dict]):
    """
    Probt Bitrate für eine Liste von Stationen im Hintergrund.
    Begrenzt auf MAX_CONCURRENT gleichzeitige Probes.

    stations: Liste mit dicts die mindestens uuid und url_resolved enthalten
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def probe_one(station):
        async with semaphore:
            uuid = station.get("uuid")
            url = station.get("url_resolved") or station.get("url")
            if not url:
                save_detected_bitrate(uuid, 0)
                return

            # Bitrate + ICY parallel pruefen
            bitrate_task = probe_bitrate(url)
            icy_task = check_icy_support(url)
            result, has_icy = await asyncio.gather(bitrate_task, icy_task)

            if result and (result["bitrate"] > 0 or result.get("codec")):
                save_detected_bitrate(
                    uuid,
                    result["bitrate"],
                    result.get("codec", ""),
                    result.get("sample_rate", 0),
                    icy=has_icy
                )
                icy_tag = " [ICY]" if has_icy else ""
                print(f"  Bitrate erkannt: {station.get('name', uuid)} -> {result['bitrate']}kbps/{result.get('codec', '?')}{icy_tag}")
            else:
                save_detected_bitrate(uuid, 0, icy=has_icy)

    tasks = [probe_one(s) for s in stations]
    await asyncio.gather(*tasks, return_exceptions=True)
