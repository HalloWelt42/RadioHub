"""
RadioHub v0.2.2 - Segment Splitter

Schneidet Aufnahmen anhand von ICY-Metadata in atomare Segmente.
Nutzt Audio-Byte-Positionen (nicht Wallclock) fuer praezise Schnitte.
Stream-Copy (kein Re-Encoding). Reassembly via FFmpeg concat demuxer.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Optional

from ..database import db_session
from ..config import get_radio_recordings_dir, get_cache_dir


# Dateiendung -> MIME-Type (wiederverwendet aus recorder.py)
EXTENSION_MIMETYPES = {
    ".mp3": "audio/mpeg",
    ".aac": "audio/aac",
    ".opus": "audio/opus",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".wav": "audio/wav",
}


def _safe_filename(title: str, max_len: int = 80) -> str:
    """Erzeugt einen sicheren Dateinamen aus einem Titel."""
    safe = re.sub(r'[^\w\s\-]', '_', title)
    safe = re.sub(r'\s+', '_', safe).strip('_')
    return safe[:max_len] if safe else "segment"


class SegmentSplitter:

    async def split_session(self, session_id: str, audio_path: Path,
                            meta_path: Path, total_duration: float,
                            file_format: str) -> list[dict]:
        """Schneidet Audio anhand .meta.json in Segmente.

        Returns: Liste der erstellten Segmente (leer wenn kein Split moeglich).
        """
        if not audio_path or not audio_path.exists():
            print(f"  Split: Audio-Datei nicht gefunden: {audio_path}")
            return []

        if not meta_path or not meta_path.exists():
            return []

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                raw_meta = json.load(f)
        except Exception as e:
            print(f"  Split: Meta-JSON Fehler: {e}")
            return []

        # Neues Format (dict mit entries) vs Legacy (flache Liste)
        if isinstance(raw_meta, dict):
            entries = raw_meta.get("entries", [])
            total_audio_bytes = raw_meta.get("total_audio_bytes", 0)
        else:
            entries = raw_meta
            total_audio_bytes = 0

        if not entries or len(entries) == 0:
            return []

        total_ms = int(total_duration * 1000)
        if total_ms <= 0:
            print("  Split: Keine gueltige Gesamtdauer")
            return []

        # Byte-Ratio verfuegbar?
        use_byte_ratio = total_audio_bytes > 0 and "b" in entries[0]
        if use_byte_ratio:
            print(f"  Split: Byte-Ratio Modus ({total_audio_bytes} total bytes)")
        else:
            print("  Split: Wallclock-Fallback (Legacy-Metadata)")

        # Session-Verzeichnis anlegen
        session_dir = get_radio_recordings_dir() / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        ext = file_format if file_format.startswith(".") else f".{file_format}"
        segments = []
        failed = False

        for i, entry in enumerate(entries):
            if use_byte_ratio:
                # Praezise Position via Byte-Ratio
                entry_bytes = entry.get("b", 0)
                start_ms = int((entry_bytes / total_audio_bytes) * total_ms)
                if i + 1 < len(entries):
                    next_bytes = entries[i + 1].get("b", 0)
                    end_ms = int((next_bytes / total_audio_bytes) * total_ms)
                else:
                    end_ms = total_ms
            else:
                # Legacy: Wallclock-Timestamps
                start_ms = entry.get("t", 0)
                end_ms = entries[i + 1]["t"] if i + 1 < len(entries) else total_ms
            duration_ms = end_ms - start_ms

            if duration_ms <= 0:
                continue

            title = entry.get("title", f"Segment {i}")
            safe_title = _safe_filename(title)
            segment_file = session_dir / f"{i:03d}_{safe_title}{ext}"

            # FFmpeg Stream-Copy Cut
            start_sec = start_ms / 1000.0
            duration_sec = duration_ms / 1000.0

            cmd = [
                "ffmpeg", "-y",
                "-i", str(audio_path),
                "-ss", f"{start_sec:.3f}",
                "-t", f"{duration_sec:.3f}",
                "-c:a", "copy",
                str(segment_file)
            ]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

                if proc.returncode != 0:
                    err = stderr.decode("utf-8", errors="replace")[-200:]
                    print(f"  Split: FFmpeg Fehler bei Segment {i}: {err}")
                    failed = True
                    break

                file_size = segment_file.stat().st_size if segment_file.exists() else 0

                segments.append({
                    "session_id": session_id,
                    "segment_index": i,
                    "title": title,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "duration_ms": duration_ms,
                    "file_path": str(segment_file),
                    "file_size": file_size
                })

            except asyncio.TimeoutError:
                print(f"  Split: Timeout bei Segment {i}")
                failed = True
                break
            except Exception as e:
                print(f"  Split: Fehler bei Segment {i}: {e}")
                failed = True
                break

        if failed or len(segments) == 0:
            # Cleanup bei Fehler
            self._cleanup_dir(session_dir)
            return []

        # Segmente in DB speichern
        with db_session() as conn:
            c = conn.cursor()
            for seg in segments:
                c.execute('''INSERT INTO segments
                    (session_id, segment_index, title, start_ms, end_ms,
                     duration_ms, file_path, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (seg["session_id"], seg["segment_index"], seg["title"],
                     seg["start_ms"], seg["end_ms"], seg["duration_ms"],
                     seg["file_path"], seg["file_size"]))

        # Originaldatei loeschen
        try:
            audio_path.unlink()
            print(f"  Split: Originaldatei geloescht: {audio_path.name}")
        except Exception as e:
            print(f"  Split: Originaldatei nicht loeschbar: {e}")

        # Session file_path auf Verzeichnis updaten (Marker fuer Segmente)
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE sessions SET file_path = ? WHERE id = ?",
                      (str(session_dir), session_id))

        print(f"  Split: {len(segments)} Segmente erstellt fuer {session_id}")
        return segments

    async def concat_session(self, session_id: str) -> Optional[Path]:
        """Reassembliert alle Segmente einer Session zu einer Datei.

        Returns: Pfad zur zusammengebauten Datei (in CACHE_DIR) oder None.
        """
        segments = self.get_segments(session_id)
        if not segments:
            return None

        # Pruefen ob alle Dateien existieren
        for seg in segments:
            fp = Path(seg["file_path"])
            if not fp.exists():
                print(f"  Concat: Segment-Datei fehlt: {fp}")
                return None

        cache_dir = get_cache_dir()
        ext = Path(segments[0]["file_path"]).suffix

        # Concat-Listdatei schreiben
        concat_file = cache_dir / f"{session_id}_concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for seg in segments:
                # Pfade mit einfachen Anfuehrungszeichen escapen
                safe_path = seg["file_path"].replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        output_file = cache_dir / f"{session_id}_full{ext}"

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "copy",
            str(output_file)
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="replace")[-200:]
                print(f"  Concat: FFmpeg Fehler: {err}")
                return None

        except asyncio.TimeoutError:
            print("  Concat: Timeout")
            return None
        except Exception as e:
            print(f"  Concat: Fehler: {e}")
            return None
        finally:
            # Concat-Liste aufraeumen
            if concat_file.exists():
                concat_file.unlink()

        print(f"  Concat: {output_file.name} erstellt ({len(segments)} Segmente)")
        return output_file

    def get_segments(self, session_id: str) -> list[dict]:
        """Alle Segmente einer Session aus DB."""
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM segments
                WHERE session_id = ? ORDER BY segment_index''', (session_id,))
            return [dict(row) for row in c.fetchall()]

    def get_all_segments(self) -> list[dict]:
        """Alle Segmente aller Sessions aus DB, sortiert nach Session und Index."""
        with db_session() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM segments ORDER BY session_id DESC, segment_index''')
            return [dict(row) for row in c.fetchall()]

    def get_segment(self, segment_id: int) -> Optional[dict]:
        """Einzelnes Segment aus DB."""
        with db_session() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM segments WHERE id = ?", (segment_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def delete_segment(self, session_id: str, segment_id: int) -> bool:
        """Loescht ein einzelnes Segment (Datei + DB).

        Falls keine Segmente mehr: Session wird ebenfalls geloescht.
        Returns: True bei Erfolg.
        """
        segment = self.get_segment(segment_id)
        if not segment or segment["session_id"] != session_id:
            return False

        # Datei loeschen
        fp = Path(segment["file_path"])
        if fp.exists():
            fp.unlink()

        # DB-Eintrag loeschen
        with db_session() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM segments WHERE id = ?", (segment_id,))

        # Verbleibende Segmente re-indexieren
        remaining = self.get_segments(session_id)
        if remaining:
            with db_session() as conn:
                c = conn.cursor()
                for new_idx, seg in enumerate(remaining):
                    if seg["segment_index"] != new_idx:
                        c.execute("UPDATE segments SET segment_index = ? WHERE id = ?",
                                  (new_idx, seg["id"]))
        else:
            # Keine Segmente mehr -> Session-Verzeichnis und Session loeschen
            session_dir = get_radio_recordings_dir() / session_id
            self._cleanup_dir(session_dir)

            with db_session() as conn:
                c = conn.cursor()
                # Meta-Datei loeschen
                c.execute("SELECT meta_file_path FROM sessions WHERE id = ?", (session_id,))
                row = c.fetchone()
                if row and row[0]:
                    mp = Path(row[0])
                    if mp.exists():
                        mp.unlink()
                c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

            print(f"  Segment: Letztes Segment geloescht, Session {session_id} entfernt")

        return True

    def _cleanup_dir(self, dir_path: Path):
        """Loescht ein Verzeichnis und seinen Inhalt."""
        if not dir_path.exists() or not dir_path.is_dir():
            return
        for f in dir_path.iterdir():
            if f.is_file():
                f.unlink()
        try:
            dir_path.rmdir()
        except Exception:
            pass


# Singleton
splitter = SegmentSplitter()
