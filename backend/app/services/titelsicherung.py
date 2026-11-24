"""Einen fertigen Titel aus dem Puffer sichern (RAD-132): sein Stück zwischen zwei Grenzen, genau wie der Puffer es zeigt, sofort
und unabhängig von einer laufenden Aufnahme. Er liegt danach als eigene Aufnahme mit einem Stück in der Ablage und trägt
Sendezeit und Titel. Wird er dort gelöscht, lässt er sich wieder sichern, solange er im Puffer ist.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from ..ablage import AblageFehler, orte
from ..config import get_active_recording_folder, get_arbeit_dir
from ..database import db_session
from .anhaengen import anhaengen, ziel_pruefen
from .aufnahmen import AufnahmeFehler, aufnahmen
from .audio_utils import probe_duration
from .empfang import Empfang
from .segment_splitter import splitter

logger = logging.getLogger("radiohub.titelsicherung")

ENDUNG = {"mp3": ".mp3", "aac": ".aac", "ogg": ".ogg", "flac": ".flac"}
#: so weit dürfen Anfang und Ende neben dem schon Gesicherten liegen (die Grenze rückt, wenn mehr Ton bekannt ist)
GLEICH_S = 3.0

_sperre = asyncio.Lock()


class SicherungFehler(Exception):
    """Der Titel lässt sich nicht sichern; die Meldung ist für Menschen lesbar."""


def gesichert(e: Empfang, von: float, bis: float) -> str:
    """Kennung der Aufnahme dieses Titels (Sekunden des Empfangs), leer wenn es keine (mehr) gibt."""
    kennung = next((k for v, b, k in e.gesichert if abs(v - von) <= GLEICH_S and abs(b - bis) <= GLEICH_S), "")
    return kennung if kennung and aufnahmen.sitzung(kennung) else ""


async def sichern(e: Empfang, von: float, bis: float, titel: str, ziel_id: str | None = None) -> str:
    """Legt den Titel ab und liefert die Kennung seiner Aufnahme; schon Gesichertes wird nicht doppelt abgelegt. Mit `ziel_id` kommt er
    an diese Aufnahme (RAD-145)."""
    async with _sperre:
        if kennung := gesichert(e, von, bis):
            return kennung
        try:
            ziel_pruefen(ziel_id, e.uuid)
        except AufnahmeFehler as f:
            raise SicherungFehler(str(f)) from f
        ton = e.ton_zwischen(von, bis)
        if not ton:
            raise SicherungFehler("Der Anfang des Titels ist nicht mehr im Puffer")
        kennung = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        beginn = datetime.now() - timedelta(seconds=max(0.0, e.jetzt_s - von))
        ordner = get_arbeit_dir("titel", kennung)
        try:
            await _ablegen(e, kennung, beginn, titel, ton, ordner / f"roh{_endung(e)}", ziel_id)
            e.gesichert.append((von, bis, kennung))
            if ziel_id:
                try:
                    await anhaengen(kennung)
                except (AufnahmeFehler, AblageFehler) as f:
                    logger.warning(f"{kennung} bleibt eine eigene Aufnahme: {f}")
            return kennung
        finally:
            shutil.rmtree(ordner, ignore_errors=True)


def _endung(e: Empfang) -> str:
    return ENDUNG.get((e.kopf.format if e.kopf else "") or "", ".mp3")


async def _ablegen(e: Empfang, kennung: str, beginn: datetime, titel: str, ton: bytes, roh: Path, ziel_id: str | None) -> None:
    roh.write_bytes(ton)
    datei = await splitter.zusammenfuegen([roh], roh.with_name(f"titel{roh.suffix}")) or roh      # Kopf mit der richtigen Länge
    dauer = await probe_duration(datei)
    if dauer <= 0:
        raise SicherungFehler("Der Ton lässt sich nicht lesen")
    ordnername, ordner_id = get_active_recording_folder()
    with db_session() as conn:
        conn.execute("""INSERT INTO sessions (id, station_uuid, station_name, stream_url, bitrate, start_time, end_time, duration, file_path,
                        status, codec, file_format, folder_id, ziel_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)""",
                     (kennung, e.uuid, e.name, e.adresse, round(e.bytes_je_sekunde * 8 / 1000), beginn.isoformat(),
                      (beginn + timedelta(seconds=dauer)).isoformat(), dauer, orte.aufnahmeordner(e.name, beginn, ordnername),
                      (e.kopf.format if e.kopf else None), datei.suffix, ordner_id, ziel_id))
    try:
        stueck = await aufnahmen.teil_ablegen(kennung, 0, titel or "Titel", 0, int(dauer * 1000), datei)
    except Exception:
        with db_session() as conn:                     # nichts Halbes: der Titel bleibt im Puffer und lässt sich erneut sichern
            conn.execute("DELETE FROM sessions WHERE id = ?", (kennung,))
        raise
    with db_session() as conn:
        conn.execute("UPDATE sessions SET file_size = ? WHERE id = ?", (stueck["size"], kennung))
