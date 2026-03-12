"""
RadioHub - Audio-Hilfsfunktionen

Gemeinsame Funktionen für Audio-Verarbeitung (ffprobe etc.).
"""
import asyncio
import json
from pathlib import Path


async def probe_duration(file_path: Path) -> float:
    """Ermittelt die echte Audio-Dauer per ffprobe.

    Args:
        file_path: Pfad zur Audio-Datei.

    Returns:
        Dauer in Sekunden (float), 0.0 bei Fehler.
    """
    if not file_path or not file_path.exists():
        return 0.0
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(file_path)
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        data = json.loads(stdout)
        dur = float(data.get("format", {}).get("duration", 0))
        if dur > 0:
            return dur
    except Exception as e:
        print(f"  ffprobe Duration-Fehler: {e}")
    return 0.0
