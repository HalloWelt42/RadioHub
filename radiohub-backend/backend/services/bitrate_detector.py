"""
RadioHub - Bitrate Detector

Erkennt echte Stream-Bitrate via ffprobe.
Fallback: URL-Analyse fuer Bitrate/Codec-Hinweise.
Ergebnisse werden in detected_bitrates gecacht.
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Optional, List
from urllib.parse import unquote

from ..database import db_session


# Max gleichzeitige ffprobe-Prozesse
MAX_CONCURRENT = 5
# Timeout pro Stream in Sekunden
PROBE_TIMEOUT = 8.0

# Bekannte Bitrate-Werte fuer URL-Matching
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


def get_cached_bitrates(uuids: List[str]) -> dict:
    """Holt gecachte Bitrates + Codec fuer mehrere UUIDs."""
    if not uuids:
        return {}

    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(uuids))
        c.execute(
            f"SELECT uuid, bitrate, codec FROM detected_bitrates WHERE uuid IN ({placeholders})",
            uuids
        )
        return {row[0]: {"bitrate": row[1], "codec": row[2] or ""} for row in c.fetchall()}


def save_detected_bitrate(uuid: str, bitrate: int, codec: str = "", sample_rate: int = 0):
    """Speichert erkannte Bitrate in DB."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO detected_bitrates
               (uuid, bitrate, codec, sample_rate, detected_at)
               VALUES (?, ?, ?, ?, ?)""",
            (uuid, bitrate, codec, sample_rate, datetime.now().isoformat())
        )


def get_uuids_needing_probe(uuids: List[str]) -> List[str]:
    """Filtert UUIDs die noch nicht erfolgreich geprobt wurden.

    Uebersprungen werden nur UUIDs mit plausiblem Ergebnis:
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
    Probt Bitrate fuer eine Liste von Stationen im Hintergrund.
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

            result = await probe_bitrate(url)
            if result and result["bitrate"] > 0:
                save_detected_bitrate(
                    uuid,
                    result["bitrate"],
                    result.get("codec", ""),
                    result.get("sample_rate", 0)
                )
                print(f"  Bitrate erkannt: {station.get('name', uuid)} -> {result['bitrate']} kbps")
            else:
                save_detected_bitrate(uuid, 0)

    tasks = [probe_one(s) for s in stations]
    await asyncio.gather(*tasks, return_exceptions=True)
