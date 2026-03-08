"""
RadioHub - Bitrate Detector

Erkennt echte Stream-Bitrate via ffprobe.
Ergebnisse werden in detected_bitrates gecacht.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, List

from ..database import db_session


# Max gleichzeitige ffprobe-Prozesse
MAX_CONCURRENT = 5
# Timeout pro Stream in Sekunden
PROBE_TIMEOUT = 8.0


async def probe_bitrate(stream_url: str, timeout: float = PROBE_TIMEOUT) -> Optional[dict]:
    """
    Erkennt Bitrate eines Streams via ffprobe.

    Returns:
        dict mit bitrate (kbps), codec, sample_rate oder None bei Fehler
    """
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
            return None

        if process.returncode != 0 or not stdout:
            return None

        data = json.loads(stdout.decode())
        streams = data.get("streams", [])

        if not streams:
            return None

        stream = streams[0]
        bitrate_raw = stream.get("bit_rate", "0")
        bitrate = int(bitrate_raw) // 1000 if bitrate_raw else 0

        return {
            "bitrate": bitrate,
            "codec": stream.get("codec_name", ""),
            "sample_rate": int(stream.get("sample_rate", 0))
        }

    except Exception as e:
        print(f"  ffprobe Fehler: {e}")
        return None


def get_cached_bitrates(uuids: List[str]) -> dict:
    """Holt gecachte Bitrates fuer mehrere UUIDs."""
    if not uuids:
        return {}

    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(uuids))
        c.execute(
            f"SELECT uuid, bitrate FROM detected_bitrates WHERE uuid IN ({placeholders})",
            uuids
        )
        return {row[0]: row[1] for row in c.fetchall()}


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
    """Filtert UUIDs die noch nicht geprobt wurden."""
    if not uuids:
        return []

    with db_session() as conn:
        c = conn.cursor()
        placeholders = ",".join("?" * len(uuids))
        c.execute(
            f"SELECT uuid FROM detected_bitrates WHERE uuid IN ({placeholders})",
            uuids
        )
        already_probed = {row[0] for row in c.fetchall()}
        return [u for u in uuids if u not in already_probed]


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
