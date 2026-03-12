"""
RadioHub v0.1.1 - Peaks Generator

Erzeugt Waveform-Peaks aus Audio-Dateien via FFmpeg.
Berechnet max(abs(sample)) pro 10ms-Fenster aus Full-Rate PCM.
Ergebnis: 1 Float32 pro 10ms, normalisiert auf [0.0, 1.0].
Wird als .peaks-Datei gecacht.
"""
import asyncio
import struct
from pathlib import Path


SAMPLE_RATE = 100  # Peaks pro Sekunde (= 10ms-Fenster)
BYTES_PER_SAMPLE = 4  # float32
INTERMEDIATE_RATE = 44100  # PCM-Rate für korrekte Peak-Berechnung
WINDOW_SIZE = INTERMEDIATE_RATE // SAMPLE_RATE  # 441 Samples pro Fenster
READ_CHUNK = 65536  # 64 KB Leseblöcke aus FFmpeg-Pipe


class PeaksGenerator:

    async def generate_peaks(self, audio_path: Path, force: bool = False) -> Path | None:
        """Generiert komplette Peaks-Datei neben der Audio-Datei.

        Liest Full-Rate PCM (44100 Hz Mono) und berechnet pro 10ms-Fenster
        den maximalen Absolutwert. Das ergibt die echte Amplituden-Hüllkurve,
        unabhängig von der Frequenz des Audioinhalts.

        Args:
            audio_path: Pfad zur Audio-Datei
            force: Cache ignorieren und neu generieren

        Returns: Pfad zur .peaks-Datei oder None bei Fehler.
        """
        peaks_path = audio_path.with_suffix(".peaks")
        if not force and peaks_path.exists() and peaks_path.stat().st_size > 0:
            return peaks_path

        # Full-Rate Mono PCM via FFmpeg-Pipe
        cmd = [
            "ffmpeg", "-y", "-v", "quiet",
            "-i", str(audio_path),
            "-ac", "1",
            "-ar", str(INTERMEDIATE_RATE),
            "-f", "f32le",
            "-acodec", "pcm_f32le",
            "pipe:1"
        ]

        window_bytes = WINDOW_SIZE * BYTES_PER_SAMPLE  # 441 * 4 = 1764

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )

            peaks = []
            max_peak = 0.0
            buf = b""

            # Stückweise lesen, pro Fenster Peak berechnen
            while True:
                block = await asyncio.wait_for(
                    proc.stdout.read(READ_CHUNK), timeout=30
                )
                if not block:
                    break
                buf += block

                # Ganze Fenster verarbeiten
                while len(buf) >= window_bytes:
                    window_data = buf[:window_bytes]
                    buf = buf[window_bytes:]
                    samples = struct.unpack(f"<{WINDOW_SIZE}f", window_data)
                    peak = max(abs(s) for s in samples)
                    peaks.append(peak)
                    if peak > max_peak:
                        max_peak = peak

            # Restliche Samples (letztes unvollständiges Fenster)
            remaining = len(buf) // BYTES_PER_SAMPLE
            if remaining > 0:
                samples = struct.unpack(
                    f"<{remaining}f", buf[:remaining * BYTES_PER_SAMPLE]
                )
                peak = max(abs(s) for s in samples)
                peaks.append(peak)
                if peak > max_peak:
                    max_peak = peak

            await proc.wait()

            if proc.returncode != 0 or len(peaks) == 0:
                print(f"  Peaks: FFmpeg Fehler (rc={proc.returncode}) für {audio_path.name}")
                return None

            # Normalisieren auf [0.0, 1.0]
            if max_peak < 1e-6:
                max_peak = 1.0
            normalized = [p / max_peak for p in peaks]
            raw = struct.pack(f"<{len(normalized)}f", *normalized)

            peaks_path.write_bytes(raw)
            print(f"  Peaks: {len(peaks)} Samples generiert für {audio_path.name}")
            return peaks_path

        except asyncio.TimeoutError:
            print(f"  Peaks: Timeout für {audio_path.name}")
            try:
                proc.kill()
            except Exception:
                pass
            return None
        except Exception as e:
            print(f"  Peaks: Fehler: {e}")
            return None

    def get_peaks_chunk(self, peaks_path: Path, start_sec: float,
                        duration_sec: float) -> bytes:
        """Liefert Peaks-Daten für einen Zeitbereich als raw bytes.

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
        """Gesamtdauer in Sekunden basierend auf Peaks-Dateigröße."""
        if not peaks_path.exists():
            return 0.0
        total_samples = peaks_path.stat().st_size // BYTES_PER_SAMPLE
        return total_samples / SAMPLE_RATE

    def has_cache(self, audio_path: Path) -> bool:
        """Prüft ob Peaks-Cache existiert."""
        peaks_path = audio_path.with_suffix(".peaks")
        return peaks_path.exists() and peaks_path.stat().st_size > 0


# Singleton
peaks_gen = PeaksGenerator()
