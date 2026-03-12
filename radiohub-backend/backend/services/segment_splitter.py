"""
RadioHub v0.2.2 - Segment Splitter

Schneidet Aufnahmen anhand von ICY-Metadata in atomare Segmente.
Nutzt Audio-Byte-Positionen (nicht Wallclock) für präzise Schnitte.
Stream-Copy (kein Re-Encoding). Reassembly via FFmpeg concat demuxer.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Optional

from ..database import db_session
from ..config import get_cache_dir, RADIO_RECORDINGS_DIR


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

    def __init__(self):
        # Aktive Split-Operationen tracken (verhindert Doppel-Splits)
        self._active_splits: set[str] = set()

    async def split_session(self, session_id: str, audio_path: Path,
                            meta_path: Path, total_duration: float,
                            file_format: str) -> list[dict]:
        """Schneidet Audio anhand .meta.json in Segmente.

        Returns: Liste der erstellten Segmente (leer wenn kein Split möglich).
        """
        if session_id in self._active_splits:
            print(f"  Split: Session {session_id} wird bereits gesplittet")
            return []
        self._active_splits.add(session_id)

        try:
            return await self._split_session_impl(
                session_id, audio_path, meta_path, total_duration, file_format
            )
        finally:
            self._active_splits.discard(session_id)

    async def _split_session_impl(self, session_id: str, audio_path: Path,
                                   meta_path: Path, total_duration: float,
                                   file_format: str) -> list[dict]:
        """Interne Split-Implementierung (Guard bereits gesetzt)."""
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
            print("  Split: Keine gültige Gesamtdauer")
            return []

        # Byte-Ratio verfügbar?
        use_byte_ratio = total_audio_bytes > 0 and "b" in entries[0]
        if use_byte_ratio:
            print(f"  Split: Byte-Ratio Modus ({total_audio_bytes} total bytes)")
        else:
            print("  Split: Wallclock-Fallback (Legacy-Metadata)")

        # Session-Verzeichnis anlegen (im selben Ordner wie die Audio-Datei)
        session_dir = audio_path.parent / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        ext = file_format if file_format.startswith(".") else f".{file_format}"
        segments = []
        failed = False

        for i, entry in enumerate(entries):
            if use_byte_ratio:
                # Präzise Position via Byte-Ratio
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

        # Originaldatei löschen
        try:
            audio_path.unlink()
            print(f"  Split: Originaldatei gelöscht: {audio_path.name}")
        except Exception as e:
            print(f"  Split: Originaldatei nicht löschbar: {e}")

        # Session file_path auf Verzeichnis updaten (Marker für Segmente)
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE sessions SET file_path = ? WHERE id = ?",
                      (str(session_dir), session_id))

        print(f"  Split: {len(segments)} Segmente erstellt für {session_id}")
        return segments

    async def split_at_times(self, session_id: str, audio_path: Path,
                              cut_times: list[float], total_duration: float,
                              file_format: str,
                              meta_entries: list[dict] | None = None) -> list[dict]:
        """Schneidet Audio an expliziten Zeitpunkten (Sekunden).

        cut_times: Sortierte Liste von Schnittpunkten (z.B. [30.0, 120.5, 300.0]).
        Erzeugt len(cut_times) + 1 Segmente.
        Falls meta_entries vorhanden: Titel aus ICY-Metadata zuordnen.
        Returns: Liste der erstellten Segmente.
        """
        if session_id in self._active_splits:
            print(f"  CustomSplit: Session {session_id} wird bereits gesplittet")
            return []
        self._active_splits.add(session_id)

        try:
            return await self._split_at_times_impl(
                session_id, audio_path, cut_times, total_duration,
                file_format, meta_entries
            )
        finally:
            self._active_splits.discard(session_id)

    async def _split_at_times_impl(self, session_id: str, audio_path: Path,
                                    cut_times: list[float], total_duration: float,
                                    file_format: str,
                                    meta_entries: list[dict] | None = None) -> list[dict]:
        """Interne Split-Implementierung (Guard bereits gesetzt)."""
        if not audio_path or not audio_path.exists():
            print(f"  CustomSplit: Audio-Datei nicht gefunden: {audio_path}")
            return []

        # Bestehende Segmente löschen
        existing = self.get_segments(session_id)
        if existing:
            for seg in existing:
                fp = Path(seg["file_path"])
                if fp.exists():
                    fp.unlink()
            with db_session() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM segments WHERE session_id = ?", (session_id,))

        # Session-Verzeichnis im Recordings-Ordner anlegen (nicht im Cache)
        session_dir = RADIO_RECORDINGS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        ext = file_format if file_format.startswith(".") else f".{file_format}"

        # Zeitpunkte normalisieren: 0 am Anfang, total_duration am Ende
        times = [0.0] + sorted(set(t for t in cut_times if 0 < t < total_duration)) + [total_duration]

        segments = []
        failed = False

        for i in range(len(times) - 1):
            start_sec = times[i]
            end_sec = times[i + 1]
            duration_sec = end_sec - start_sec

            if duration_sec <= 0.01:
                continue

            # Titel aus Metadata ermitteln
            title = f"Teil {i + 1}"
            if meta_entries:
                for entry in reversed(meta_entries):
                    entry_sec = (entry.get("t", 0)) / 1000.0
                    if entry_sec <= start_sec:
                        title = entry.get("title", title)
                        break

            safe_title = _safe_filename(title)
            segment_file = session_dir / f"{i:03d}_{safe_title}{ext}"

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
                    print(f"  CustomSplit: FFmpeg Fehler bei Segment {i}: {err}")
                    failed = True
                    break

                file_size = segment_file.stat().st_size if segment_file.exists() else 0
                start_ms = int(start_sec * 1000)
                end_ms = int(end_sec * 1000)

                segments.append({
                    "session_id": session_id,
                    "segment_index": i,
                    "title": title,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "duration_ms": end_ms - start_ms,
                    "file_path": str(segment_file),
                    "file_size": file_size
                })

            except asyncio.TimeoutError:
                print(f"  CustomSplit: Timeout bei Segment {i}")
                failed = True
                break
            except Exception as e:
                print(f"  CustomSplit: Fehler bei Segment {i}: {e}")
                failed = True
                break

        if failed or len(segments) == 0:
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

        # Originaldatei löschen
        try:
            audio_path.unlink()
            print(f"  CustomSplit: Originaldatei gelöscht: {audio_path.name}")
        except Exception as e:
            print(f"  CustomSplit: Originaldatei nicht löschbar: {e}")

        # Session file_path auf Verzeichnis updaten
        with db_session() as conn:
            c = conn.cursor()
            c.execute("UPDATE sessions SET file_path = ? WHERE id = ?",
                      (str(session_dir), session_id))

        print(f"  CustomSplit: {len(segments)} Segmente erstellt für {session_id}")
        return segments

    async def concat_session(self, session_id: str) -> Optional[Path]:
        """Reassembliert alle Segmente einer Session zu einer Datei.

        Returns: Pfad zur zusammengebauten Datei (in CACHE_DIR) oder None.
        """
        segments = self.get_segments(session_id)
        if not segments:
            return None

        # Prüfen ob alle Dateien existieren
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
                # Pfade mit einfachen Anführungszeichen escapen
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
            # Concat-Liste aufräumen
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
        """Löscht ein einzelnes Segment (Datei + DB).

        Falls keine Segmente mehr: Session wird ebenfalls gelöscht.
        Returns: True bei Erfolg.
        """
        segment = self.get_segment(segment_id)
        if not segment or segment["session_id"] != session_id:
            return False

        # Datei löschen
        fp = Path(segment["file_path"])
        if fp.exists():
            fp.unlink()

        # DB-Eintrag löschen
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
            # Keine Segmente mehr -> Session-Verzeichnis und Session löschen
            # Verzeichnis aus dem Segment-Pfad ableiten (parent = session_dir)
            session_dir = Path(segment["file_path"]).parent
            self._cleanup_dir(session_dir)

            with db_session() as conn:
                c = conn.cursor()
                # Meta-Datei löschen
                c.execute("SELECT meta_file_path FROM sessions WHERE id = ?", (session_id,))
                row = c.fetchone()
                if row and row[0]:
                    mp = Path(row[0])
                    if mp.exists():
                        mp.unlink()
                c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

            print(f"  Segment: Letztes Segment gelöscht, Session {session_id} entfernt")

        return True

    def _cleanup_dir(self, dir_path: Path):
        """Löscht ein Verzeichnis und seinen Inhalt."""
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
