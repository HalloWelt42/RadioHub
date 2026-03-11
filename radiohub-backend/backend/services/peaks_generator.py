"""
RadioHub v0.1.0 - Peaks Generator

Erzeugt Waveform-Peaks aus Audio-Dateien via FFmpeg.
Mono-Mixdown bei 100 Hz Samplerate -> 1 Float32 pro 10ms.
Ergebnis wird als .peaks-Datei gecacht.
"""
import asyncio
import struct
from pathlib import Path


SAMPLE_RATE = 100  # Peaks pro Sekunde
BYTES_PER_SAMPLE = 4  # float32


class PeaksGenerator:

    async def generate_peaks(self, audio_path: Path) -> Path | None:
        """Generiert komplette Peaks-Datei neben der Audio-Datei.

        Returns: Pfad zur .peaks-Datei oder None bei Fehler.
        """
        peaks_path = audio_path.with_suffix(".peaks")
        if peaks_path.exists() and peaks_path.stat().st_size > 0:
            return peaks_path

        cmd = [
            "ffmpeg", "-y", "-v", "quiet",
            "-i", str(audio_path),
            "-ac", "1",
            "-ar", str(SAMPLE_RATE),
            "-f", "f32le",
            "-acodec", "pcm_f32le",
            "pipe:1"
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=120
            )

            if proc.returncode != 0 or not stdout:
                err = stderr.decode("utf-8", errors="replace")[-200:]
                print(f"  Peaks: FFmpeg Fehler: {err}")
                return None

            # Normalisieren auf [-1.0, 1.0]
            num_samples = len(stdout) // BYTES_PER_SAMPLE
            if num_samples == 0:
                return None

            samples = struct.unpack(f"<{num_samples}f", stdout[:num_samples * BYTES_PER_SAMPLE])
            max_val = max(abs(s) for s in samples) or 1.0
            normalized = [s / max_val for s in samples]
            raw = struct.pack(f"<{len(normalized)}f", *normalized)

            peaks_path.write_bytes(raw)
            print(f"  Peaks: {num_samples} Samples generiert fuer {audio_path.name}")
            return peaks_path

        except asyncio.TimeoutError:
            print(f"  Peaks: Timeout fuer {audio_path.name}")
            return None
        except Exception as e:
            print(f"  Peaks: Fehler: {e}")
            return None

    def get_peaks_chunk(self, peaks_path: Path, start_sec: float,
                        duration_sec: float) -> bytes:
        """Liefert Peaks-Daten fuer einen Zeitbereich als raw bytes.

        Returns: Raw float32 bytes (Little Endian).
        """
        if not peaks_path.exists():
            return b""

        file_size = peaks_path.stat().st_size
        total_samples = file_size // BYTES_PER_SAMPLE

        start_sample = int(start_sec * SAMPLE_RATE)
        num_samples = int(duration_sec * SAMPLE_RATE)

        # Clamp
        start_sample = max(0, min(start_sample, total_samples))
        end_sample = min(start_sample + num_samples, total_samples)
        actual_count = end_sample - start_sample

        if actual_count <= 0:
            return b""

        offset = start_sample * BYTES_PER_SAMPLE
        length = actual_count * BYTES_PER_SAMPLE

        with open(peaks_path, "rb") as f:
            f.seek(offset)
            return f.read(length)

    def get_total_duration(self, peaks_path: Path) -> float:
        """Gesamtdauer in Sekunden basierend auf Peaks-Dateigroesse."""
        if not peaks_path.exists():
            return 0.0
        total_samples = peaks_path.stat().st_size // BYTES_PER_SAMPLE
        return total_samples / SAMPLE_RATE

    def has_cache(self, audio_path: Path) -> bool:
        """Prueft ob Peaks-Cache existiert."""
        peaks_path = audio_path.with_suffix(".peaks")
        return peaks_path.exists() and peaks_path.stat().st_size > 0


# Singleton
peaks_gen = PeaksGenerator()
