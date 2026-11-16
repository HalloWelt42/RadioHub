"""
RadioHub v0.4.0 - Segment Splitter

Schneidet lokale Audio-Dateien in Stücke (Stream-Copy, kein Re-Encoding) und fügt Stücke wieder zusammen.
Arbeitet nur mit lokalen Dateien im Arbeitsordner; Ablegen und Datenbank übernimmt `services.aufnahmen`.

Schnitt nach Titelliste: Audio-Byte-Positionen (nicht Wallclock) für präzise Schnitte. Carry-Forward: Einträge mit
ignored=True haben denselben Titel wie ihr Vorgänger und erzeugen keinen eigenen Schnitt.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Stueck:
    """Ein geschnittenes Stück im Arbeitsordner, noch nicht abgelegt."""

    titel: str
    start_ms: int
    end_ms: int
    datei: Path

    @property
    def dauer_ms(self) -> int:
        return self.end_ms - self.start_ms


def titel_eintraege(titelliste: dict | list | None) -> list[dict]:
    """Einträge einer Titelliste (neues Format: dict mit entries, alt: flache Liste)."""
    if isinstance(titelliste, dict):
        return titelliste.get("entries", [])
    return titelliste or []


async def _ffmpeg(cmd: list[str], timeout: float) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL,
                                                stderr=asyncio.subprocess.PIPE)
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, "Zeitüberschreitung"
    return proc.returncode == 0, stderr.decode("utf-8", errors="replace")[-200:]


class SegmentSplitter:

    def __init__(self):
        # Aktive Schnitte je Quelle (verhindert Doppel-Schnitte)
        self._aktiv: set[str] = set()

    async def _schneiden(self, audio: Path, start_sec: float, dauer_sec: float, ziel: Path) -> bool:
        ok, fehler = await _ffmpeg(["ffmpeg", "-y", "-i", str(audio), "-ss", f"{start_sec:.3f}",
                                    "-t", f"{dauer_sec:.3f}", "-c:a", "copy", str(ziel)], timeout=120)
        if not ok:
            print(f"  Split: FFmpeg-Fehler bei {ziel.name}, übersprungen: {fehler}")
            ziel.unlink(missing_ok=True)
        return ok and ziel.exists()

    async def nach_titelliste(self, audio: Path, titelliste: dict | list, total_duration: float, endung: str,
                              ziel_dir: Path) -> list[Stueck]:
        """Schneidet an den Titelwechseln der Titelliste. Leer, wenn es nichts zu schneiden gibt."""
        eintraege = titel_eintraege(titelliste)
        total_audio_bytes = titelliste.get("total_audio_bytes", 0) if isinstance(titelliste, dict) else 0
        total_ms = int(total_duration * 1000)
        if not eintraege or total_ms <= 0 or not audio.exists():
            return []

        wirksam = [e for e in eintraege if not e.get("ignored", False)] or [eintraege[0]]
        nach_bytes = total_audio_bytes > 0 and "b" in wirksam[0]
        grenzen: list[tuple[str, int, int]] = []
        for i, eintrag in enumerate(wirksam):
            if nach_bytes:
                start_ms = int(eintrag.get("b", 0) / total_audio_bytes * total_ms)
                end_ms = (int(wirksam[i + 1].get("b", 0) / total_audio_bytes * total_ms)
                          if i + 1 < len(wirksam) else total_ms)
            else:
                start_ms = eintrag.get("t", 0)
                end_ms = wirksam[i + 1]["t"] if i + 1 < len(wirksam) else total_ms
            if end_ms > start_ms:
                grenzen.append((eintrag.get("title", "") or f"Teil {len(grenzen) + 1}", start_ms, end_ms))
        return await self._schneiden_alle(audio, grenzen, endung, ziel_dir)

    async def an_zeiten(self, audio: Path, zeiten: list[float], total_duration: float, endung: str,
                        ziel_dir: Path, titel: list[dict] | None = None) -> list[Stueck]:
        """Schneidet an Zeitpunkten (Sekunden); ergibt len(zeiten) + 1 Stücke. Titel aus der Titelliste, wenn da."""
        punkte = [0.0] + sorted({t for t in zeiten if 0 < t < total_duration}) + [total_duration]
        grenzen: list[tuple[str, int, int]] = []
        for i in range(len(punkte) - 1):
            start_sec, end_sec = punkte[i], punkte[i + 1]
            if end_sec - start_sec <= 0.01:
                continue
            name = f"Teil {i + 1}"
            for eintrag in reversed(titel or []):
                if eintrag.get("t", 0) / 1000.0 <= start_sec:
                    name = eintrag.get("title", name) or name
                    break
            grenzen.append((name, int(start_sec * 1000), int(end_sec * 1000)))
        return await self._schneiden_alle(audio, grenzen, endung, ziel_dir)

    async def _schneiden_alle(self, audio: Path, grenzen: list[tuple[str, int, int]], endung: str,
                              ziel_dir: Path) -> list[Stueck]:
        schluessel = str(audio)
        if schluessel in self._aktiv:
            print(f"  Split: {audio.name} wird bereits geschnitten")
            return []
        self._aktiv.add(schluessel)
        try:
            ziel_dir.mkdir(parents=True, exist_ok=True)
            endung = endung if endung.startswith(".") else f".{endung}"
            stuecke: list[Stueck] = []
            for i, (titel, start_ms, end_ms) in enumerate(grenzen):
                ziel = ziel_dir / f"teil_{i:03d}{endung}"
                if await self._schneiden(audio, start_ms / 1000.0, (end_ms - start_ms) / 1000.0, ziel):
                    stuecke.append(Stueck(titel, start_ms, end_ms, ziel))
            print(f"  Split: {len(stuecke)} von {len(grenzen)} Stücken aus {audio.name}")
            return stuecke
        finally:
            self._aktiv.discard(schluessel)

    async def zusammenfuegen(self, dateien: list[Path], ziel: Path) -> Optional[Path]:
        """Fügt Stücke per concat-Demuxer zu einer Datei zusammen (Stream-Copy)."""
        vorhanden = [d for d in dateien if d.exists()]
        if not vorhanden:
            return None
        liste = ziel.with_name(f"{ziel.stem}_concat.txt")
        with open(liste, "w", encoding="utf-8") as f:
            for datei in vorhanden:
                f.write("file '{}'\n".format(str(datei).replace("'", "'\\''")))
        try:
            ok, fehler = await _ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
                                        "-c:a", "copy", str(ziel)], timeout=300)
        finally:
            liste.unlink(missing_ok=True)
        if not ok:
            print(f"  Concat: FFmpeg-Fehler: {fehler}")
            ziel.unlink(missing_ok=True)
            return None
        return ziel


# Singleton
splitter = SegmentSplitter()
