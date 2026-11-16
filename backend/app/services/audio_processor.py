"""
RadioHub - Audio Processor Service

FFmpeg-basierte Audio-Verarbeitung:
- Normalisierung (EBU R128 loudnorm)
- Format-Konvertierung (MP3, OGG, AAC)
- Mono-Konvertierung
"""

import asyncio
import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Verfügbare Bitraten pro Format (kbps)
FORMAT_BITRATES = {
    "mp3": [64, 96, 128, 160, 192, 224, 256, 320],
    "ogg": [64, 96, 128, 160, 192, 224, 256, 320],
    "aac": [64, 96, 128, 160, 192, 256],
}

FORMAT_EXTENSIONS = {
    "mp3": ".mp3",
    "ogg": ".ogg",
    "aac": ".m4a",
}

FORMAT_CODECS = {
    "mp3": "libmp3lame",
    "ogg": "libvorbis",
    "aac": "aac",
}


class AudioProcessor:
    """FFmpeg-basierte Audio-Verarbeitung für Aufnahmen."""

    def __init__(self):
        # Per-Pfad Locks: verhindert parallele Operationen auf derselben Datei
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def _get_lock(self, path: Path) -> asyncio.Lock:
        """Lock für einen bestimmten Dateipfad holen/erstellen."""
        key = str(path.resolve())
        async with self._locks_guard:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def get_audio_info(self, audio_path: Path) -> dict:
        """Audio-Metadaten via ffprobe auslesen."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(audio_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            return {}
        try:
            data = json.loads(stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])
            audio_stream = next(
                (s for s in streams if s.get("codec_type") == "audio"), {}
            )
            return {
                "duration": float(fmt.get("duration", 0)),
                "size_bytes": int(fmt.get("size", 0)),
                "bitrate": int(fmt.get("bit_rate", 0)) // 1000,
                "codec": audio_stream.get("codec_name", ""),
                "sample_rate": int(audio_stream.get("sample_rate", 0)),
                "channels": int(audio_stream.get("channels", 0)),
                "format": fmt.get("format_name", ""),
            }
        except Exception:
            return {}

    async def _analyze_lufs(self, audio_path: Path, target_lufs: float = -16.0,
                            timeout: int = 300) -> dict:
        """Pass 1: LUFS-Analyse einer Audiodatei. Gibt loudnorm-Messwerte zurück."""
        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
            "-f", "null", "-"
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        if proc.returncode != 0:
            raise RuntimeError(f"LUFS-Analyse fehlgeschlagen: {audio_path.name}")

        stderr_text = stderr.decode()
        json_start = stderr_text.rfind("{")
        json_end = stderr_text.rfind("}") + 1
        if json_start < 0 or json_end <= json_start:
            raise RuntimeError("Loudnorm-Daten nicht gefunden")

        return json.loads(stderr_text[json_start:json_end])

    async def _apply_loudnorm(self, audio_path: Path, loudnorm_data: dict,
                               target_lufs: float = -16.0, timeout: int = 300) -> Path:
        """Pass 2: Loudnorm-Korrektur auf eine Datei anwenden. Ersetzt das Original."""
        ext = audio_path.suffix
        temp_path = audio_path.with_suffix(f".norm{ext}")

        af_filter = (
            f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:"
            f"measured_I={loudnorm_data.get('input_i', '-24.0')}:"
            f"measured_TP={loudnorm_data.get('input_tp', '-1.0')}:"
            f"measured_LRA={loudnorm_data.get('input_lra', '11.0')}:"
            f"measured_thresh={loudnorm_data.get('input_thresh', '-34.0')}:"
            f"offset={loudnorm_data.get('target_offset', '0.0')}:linear=true"
        )

        codec_args = self._get_codec_args_for_ext(ext)

        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-af", af_filter,
            *codec_args,
            str(temp_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        if proc.returncode != 0 or not temp_path.exists():
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Normalisierung fehlgeschlagen: {audio_path.name}")

        shutil.move(str(temp_path), str(audio_path))
        return audio_path

    async def normalize(self, audio_path: Path, target_lufs: float = -16.0) -> Path:
        """
        EBU R128 Normalisierung (zwei Durchläufe).
        Ersetzt die Originaldatei.
        """
        lock = await self._get_lock(audio_path)
        async with lock:
            logger.info("Normalisierung: %s", audio_path.name)
            loudnorm_data = await self._analyze_lufs(audio_path, target_lufs)
            result = await self._apply_loudnorm(audio_path, loudnorm_data, target_lufs)
            logger.info("Normalisierung abgeschlossen: %s", audio_path.name)
            return result

    async def normalize_segments(self, segment_paths: list[Path],
                                  target_lufs: float = -16.0,
                                  on_progress=None) -> list[Path]:
        """
        EBU R128 Normalisierung über mehrere Segmente.
        Pass 1: Gemeinsame Analyse via ffmpeg concat (ein Messwert für alle).
        Pass 2: Gleicher Gain auf jedes Segment einzeln.
        on_progress(step, total, message) für Fortschritt.
        """
        if not segment_paths:
            return []

        # Locks für alle Segmente holen
        locks = [await self._get_lock(p) for p in segment_paths]
        for lk in locks:
            await lk.acquire()

        try:
            return await self._normalize_segments_locked(
                segment_paths, target_lufs, on_progress
            )
        finally:
            for lk in locks:
                lk.release()

    async def _normalize_segments_locked(self, segment_paths: list[Path],
                                          target_lufs: float,
                                          on_progress) -> list[Path]:
        """Interne Implementierung (Locks bereits gehalten)."""
        total_steps = len(segment_paths) + 1  # 1 Analyse + N Anwendungen

        # Pass 1: Concat-Liste erstellen, gemeinsam analysieren
        if on_progress:
            on_progress(0, total_steps, "Analyse aller Segmente...")

        concat_file = segment_paths[0].parent / "_normalize_concat.txt"
        try:
            with open(concat_file, "w") as f:
                for p in segment_paths:
                    # FFmpeg concat erwartet escaped Pfade
                    escaped = str(p).replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
                "-f", "null", "-"
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Timeout: 60s pro Segment (großzügig für Pi)
            _, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=60 * len(segment_paths)
            )

            if proc.returncode != 0:
                raise RuntimeError("LUFS-Analyse der Segmente fehlgeschlagen")

            stderr_text = stderr.decode()
            json_start = stderr_text.rfind("{")
            json_end = stderr_text.rfind("}") + 1
            if json_start < 0 or json_end <= json_start:
                raise RuntimeError("Loudnorm-Daten nicht gefunden")

            loudnorm_data = json.loads(stderr_text[json_start:json_end])
            logger.info(
                "Segment-Analyse: %d Segmente, LUFS=%s",
                len(segment_paths), loudnorm_data.get("input_i", "?")
            )
        finally:
            concat_file.unlink(missing_ok=True)

        # Pass 2: Gleiche Korrektur auf jedes Segment anwenden
        results = []
        for i, seg_path in enumerate(segment_paths):
            if on_progress:
                on_progress(i + 1, total_steps, f"Segment {i + 1}/{len(segment_paths)}...")
            logger.info("Normalisierung Segment %d/%d: %s",
                        i + 1, len(segment_paths), seg_path.name)
            result = await self._apply_loudnorm(seg_path, loudnorm_data, target_lufs,
                                                 timeout=120)
            results.append(result)

        if on_progress:
            on_progress(total_steps, total_steps, "Fertig")

        return results

    def _kbps_to_ogg_quality(self, kbps: int) -> str:
        """kbps-Wert auf OGG Vorbis Quality-Stufe (0-10) umrechnen."""
        if kbps <= 64:
            return "1"
        elif kbps <= 96:
            return "2"
        elif kbps <= 128:
            return "3"
        elif kbps <= 160:
            return "5"
        elif kbps <= 192:
            return "6"
        elif kbps <= 224:
            return "7"
        elif kbps <= 256:
            return "8"
        else:
            return "9"

    async def convert(
        self,
        audio_path: Path,
        target_format: str,
        bitrate_kbps: int = 192,
        mono: bool = False,
    ) -> Path:
        """
        Audio in ein anderes Format konvertieren.
        bitrate_kbps: Ziel-Bitrate in kbps (z.B. 64, 128, 192, 256, 320).
        Ersetzt die Originaldatei.
        """
        lock = await self._get_lock(audio_path)
        async with lock:
            if target_format not in FORMAT_CODECS:
                raise ValueError(f"Unbekanntes Format: {target_format}")

            target_ext = FORMAT_EXTENSIONS[target_format]
            temp_path = audio_path.with_suffix(f".conv{target_ext}")

            codec = FORMAT_CODECS[target_format]
            cmd = ["ffmpeg", "-y", "-i", str(audio_path)]

            # Codec + Bitrate
            cmd.extend(["-c:a", codec])
            if target_format == "ogg":
                # OGG Vorbis nutzt Quality statt Bitrate
                cmd.extend(["-q:a", self._kbps_to_ogg_quality(bitrate_kbps)])
            else:
                cmd.extend(["-b:a", f"{bitrate_kbps}k"])

            if mono:
                cmd.extend(["-ac", "1"])

            cmd.append(str(temp_path))

            logger.info(
                "Konvertierung: %s -> %s (%d kbps%s)",
                audio_path.name, target_format, bitrate_kbps,
                ", mono" if mono else ""
            )
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

            if proc.returncode != 0 or not temp_path.exists():
                if temp_path.exists():
                    temp_path.unlink()
                logger.error(
                    "Konvertierung fehlgeschlagen: %s",
                    stderr.decode()[-500:]
                )
                raise RuntimeError("Konvertierung fehlgeschlagen")

            # Sicher ersetzen: erst temp an Ziel bewegen, dann Original löschen
            final_path = audio_path.with_suffix(target_ext)
            shutil.move(str(temp_path), str(final_path))
            if final_path != audio_path and audio_path.exists():
                audio_path.unlink(missing_ok=True)

            logger.info(
                "Konvertierung abgeschlossen: %s (%.1f MB)",
                final_path.name, final_path.stat().st_size / 1024 / 1024
            )
            return final_path

    async def to_mono(self, audio_path: Path) -> Path:
        """Stereo -> Mono konvertieren. Ersetzt die Originaldatei."""
        lock = await self._get_lock(audio_path)
        async with lock:
            ext = audio_path.suffix
            temp_path = audio_path.with_suffix(f".mono{ext}")

            codec_args = self._get_codec_args_for_ext(ext)

            cmd = [
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ac", "1",
                *codec_args,
                str(temp_path)
            ]

            logger.info("Mono-Konvertierung: %s", audio_path.name)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            if proc.returncode != 0 or not temp_path.exists():
                if temp_path.exists():
                    temp_path.unlink()
                logger.error(
                    "Mono-Konvertierung fehlgeschlagen: %s",
                    stderr.decode()[-500:]
                )
                raise RuntimeError("Mono-Konvertierung fehlgeschlagen")

            shutil.move(str(temp_path), str(audio_path))
            logger.info("Mono-Konvertierung abgeschlossen: %s", audio_path.name)
            return audio_path

    def get_format_bitrates(self) -> dict:
        """Verfügbare Bitraten pro Format zurückgeben."""
        return FORMAT_BITRATES

    def _get_codec_args_for_ext(self, ext: str) -> list:
        """Passende Codec-Argumente für eine Dateiendung."""
        ext_lower = ext.lower()
        if ext_lower == ".mp3":
            return ["-c:a", "libmp3lame", "-b:a", "192k"]
        elif ext_lower in (".ogg", ".opus"):
            return ["-c:a", "libvorbis", "-q:a", "5"]
        elif ext_lower in (".aac", ".m4a"):
            return ["-c:a", "aac", "-b:a", "192k"]
        elif ext_lower == ".flac":
            return ["-c:a", "flac"]
        elif ext_lower == ".wav":
            return ["-c:a", "pcm_s16le"]
        else:
            return ["-c:a", "libmp3lame", "-b:a", "192k"]


# Singleton
audio_processor = AudioProcessor()
