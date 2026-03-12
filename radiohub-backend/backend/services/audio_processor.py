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

# Qualitaets-Presets pro Format
QUALITY_PRESETS = {
    "mp3": {
        "low": {"bitrate": "64k", "label": "64 kbps (Sprache)"},
        "medium": {"bitrate": "128k", "label": "128 kbps (Standard)"},
        "high": {"bitrate": "192k", "label": "192 kbps (Gut)"},
        "best": {"bitrate": "320k", "label": "320 kbps (Maximal)"},
    },
    "ogg": {
        "low": {"quality": "2", "label": "Q2 (~96 kbps, Sprache)"},
        "medium": {"quality": "5", "label": "Q5 (~160 kbps, Standard)"},
        "high": {"quality": "7", "label": "Q7 (~224 kbps, Gut)"},
        "best": {"quality": "9", "label": "Q9 (~320 kbps, Maximal)"},
    },
    "aac": {
        "low": {"bitrate": "64k", "label": "64 kbps (Sprache)"},
        "medium": {"bitrate": "128k", "label": "128 kbps (Standard)"},
        "high": {"bitrate": "192k", "label": "192 kbps (Gut)"},
        "best": {"bitrate": "256k", "label": "256 kbps (Maximal)"},
    },
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
    """FFmpeg-basierte Audio-Verarbeitung fuer Aufnahmen."""

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
        """Pass 1: LUFS-Analyse einer Audiodatei. Gibt loudnorm-Messwerte zurueck."""
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
        EBU R128 Normalisierung (zwei Durchlaeufe).
        Ersetzt die Originaldatei.
        """
        logger.info("Normalisierung: %s", audio_path.name)
        loudnorm_data = await self._analyze_lufs(audio_path, target_lufs)
        result = await self._apply_loudnorm(audio_path, loudnorm_data, target_lufs)
        logger.info("Normalisierung abgeschlossen: %s", audio_path.name)
        return result

    async def normalize_segments(self, segment_paths: list[Path],
                                  target_lufs: float = -16.0,
                                  on_progress=None) -> list[Path]:
        """
        EBU R128 Normalisierung ueber mehrere Segmente.
        Pass 1: Gemeinsame Analyse via ffmpeg concat (ein Messwert fuer alle).
        Pass 2: Gleicher Gain auf jedes Segment einzeln.
        on_progress(step, total, message) fuer Fortschritt.
        """
        if not segment_paths:
            return []

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
            # Timeout: 60s pro Segment (grosszuegig fuer Pi)
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

    async def convert(
        self,
        audio_path: Path,
        target_format: str,
        quality: str = "medium",
        mono: bool = False,
    ) -> Path:
        """
        Audio in ein anderes Format konvertieren.
        Gibt den Pfad der neuen Datei zurueck.
        """
        if target_format not in FORMAT_CODECS:
            raise ValueError(f"Unbekanntes Format: {target_format}")

        preset = QUALITY_PRESETS.get(target_format, {}).get(quality)
        if not preset:
            raise ValueError(f"Unbekannte Qualitaet: {quality}")

        target_ext = FORMAT_EXTENSIONS[target_format]
        output_path = audio_path.with_suffix(target_ext)

        # Falls Ziel = Quelle und gleiches Format, temp-Datei nutzen
        if output_path == audio_path:
            output_path = audio_path.with_suffix(f".conv{target_ext}")

        codec = FORMAT_CODECS[target_format]
        cmd = ["ffmpeg", "-y", "-i", str(audio_path)]

        # Codec + Qualitaet
        cmd.extend(["-c:a", codec])
        if "bitrate" in preset:
            cmd.extend(["-b:a", preset["bitrate"]])
        elif "quality" in preset:
            cmd.extend(["-q:a", preset["quality"]])

        # Mono
        if mono:
            cmd.extend(["-ac", "1"])

        cmd.append(str(output_path))

        logger.info(
            "Konvertierung: %s -> %s (%s%s)",
            audio_path.name, target_format, quality,
            ", mono" if mono else ""
        )
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

        if proc.returncode != 0 or not output_path.exists():
            if output_path.exists():
                output_path.unlink()
            logger.error(
                "Konvertierung fehlgeschlagen: %s",
                stderr.decode()[-500:]
            )
            raise RuntimeError("Konvertierung fehlgeschlagen")

        # Falls gleicher Dateiname: Original loeschen und umbenennen
        if output_path.name.startswith(audio_path.stem + ".conv"):
            final_path = audio_path.with_suffix(target_ext)
            audio_path.unlink(missing_ok=True)
            shutil.move(str(output_path), str(final_path))
            output_path = final_path

        logger.info(
            "Konvertierung abgeschlossen: %s (%.1f MB)",
            output_path.name, output_path.stat().st_size / 1024 / 1024
        )
        return output_path

    async def to_mono(self, audio_path: Path) -> Path:
        """Stereo -> Mono konvertieren. Ersetzt die Originaldatei."""
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

    def get_quality_presets(self) -> dict:
        """Alle verfuegbaren Qualitaets-Presets zurueckgeben."""
        return QUALITY_PRESETS

    def _get_codec_args_for_ext(self, ext: str) -> list:
        """Passende Codec-Argumente fuer eine Dateiendung."""
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
