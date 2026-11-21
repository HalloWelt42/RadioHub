"""Stillenwächter einer Aufnahme (RAD-45): ein eigener FFmpeg, der den ganzen Ton ohne Unterbrechung auf Stille prüft.

Dazu misst er die Lautheit alle 100 ms (EBU R128, Momentanwert über 400 ms): viele Sender blenden über und haben am
Liedwechsel keine digitale Stille, aber ein Pegeltal (gemessen an FFH, Antenne Bayern, OLDIE ANTENNE: 15 bis 30 dB unter
dem Umfeld). Der Feinschnitt nimmt es, wo keine Stille ist.

Die Stücke schreibt der Aufnehmer mit je einem FFmpeg, der beim Titelwechsel neu startet. Prüfte der auch die Stille,
zerfiele jede Pause, die über den Wechsel reicht, und gerade die Pausen zwischen zwei Liedern gingen verloren (gemessen
an Mangoradio 21.11.2026). Der Wächter bekommt denselben Ton, läuft aber von der ersten bis zur letzten Sekunde durch;
seine Zeiten sind die Sekunden des aufgenommenen Tons. Er ändert nichts am Ton und schreibt keine Datei.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from typing import Optional

from ..sendewerbung.angaben import regeln as werberegeln

logger = logging.getLogger("radiohub.stillenwaechter")

PEGEL = re.compile(r"\bt:\s*([\d.]+)\s+TARGET.*?\bM:\s*(-?[\d.]+)")


class Stillenwaechter:
    def __init__(self, eingang_format: Optional[str], bei_zeile: Callable[[str], None],
                 bei_pegel: Optional[Callable[[float, float], None]] = None) -> None:
        """`bei_zeile`: jede Zeile, die FFmpeg zur Stille meldet (silence_start, silence_end). `bei_pegel`: je 100 ms
        Zeit (Ende des Messfensters) und Momentanlautheit in LUFS."""
        self._format = eingang_format
        self._bei_zeile = bei_zeile
        self._bei_pegel = bei_pegel
        self._prozess: Optional[asyncio.subprocess.Process] = None
        self._leser: Optional[asyncio.Task] = None
        self.kaputt = False

    def befehl(self) -> list[str]:
        g = werberegeln().grenze
        return ["ffmpeg", "-hide_banner", "-loglevel", "info", "-nostats",
                *(["-f", self._format] if self._format else []), "-i", "pipe:0",
                "-af", f"silencedetect=noise={g.stille_db}dB:duration={g.stille_mindestens_s}"
                       + (",ebur128=framelog=info" if self._bei_pegel else ""), "-f", "null", "-"]

    async def starten(self) -> None:
        self._prozess = await asyncio.create_subprocess_exec(
            *self.befehl(), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        self._leser = asyncio.create_task(self._lesen())

    async def ton(self, daten: bytes) -> None:
        """Den nächsten Block Ton prüfen lassen; fällt der Wächter aus, läuft die Aufnahme ohne ihn weiter."""
        p = self._prozess
        if self.kaputt or not p or not p.stdin or p.stdin.is_closing():
            return
        try:
            p.stdin.write(daten)
            await p.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as f:
            self.kaputt = True
            logger.warning(f"Stillenwächter ausgefallen: {f}")

    async def beenden(self, zeitgrenze_s: float = 20.0) -> None:
        """Ende des Tons: FFmpeg meldet die letzten Stillen und endet; danach sind alle Zeilen gelesen."""
        p = self._prozess
        if not p:
            return
        try:
            if p.stdin and not p.stdin.is_closing():
                p.stdin.close()
            await asyncio.wait_for(p.wait(), zeitgrenze_s)
            if self._leser:
                await asyncio.wait_for(self._leser, zeitgrenze_s)
        except asyncio.TimeoutError:
            logger.warning("Stillenwächter endet nicht, wird beendet")
            p.kill()
        finally:
            self._prozess = None

    async def _lesen(self) -> None:
        p = self._prozess
        assert p and p.stderr
        while line := await p.stderr.readline():
            text = line.decode("utf-8", errors="replace").strip()
            if "silence_" in text:
                self._bei_zeile(text)
            elif self._bei_pegel and (m := PEGEL.search(text)):
                self._bei_pegel(float(m.group(1)), float(m.group(2)))
