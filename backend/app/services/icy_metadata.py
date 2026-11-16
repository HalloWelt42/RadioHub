"""
RadioHub v0.4.0 - ICY Metadata Logger

Liest ICY-Metadata (StreamTitle) aus dem Radio-Stream via Raw-TCP.
Loggt Titelwechsel mit Audio-Byte-Positionen in eine .meta.json Datei.
Mit Reconnect-Logik bei Verbindungsabbruch.
Optional: on_title_change Callback fuer Live-Split bei Titelwechsel.

ICY-Protokoll:
- HTTP/1.0 GET mit "Icy-MetaData: 1" Header
- Server antwortet mit icy-metaint=N Header
- Alle N Audio-Bytes: 1 Byte Länge, dann Länge*16 Bytes Metadata
- Metadata: "StreamTitle='Artist - Song';"

Byte-Tracking:
- Kumulative Audio-Bytes werden pro Metadata-Zyklus gezählt
- Jeder Entry speichert 'b' (Byte-Position) + 't' (Wallclock-ms)
- Splitter nutzt Byte-Ratio für präzise Schnitt-Positionen:
  audio_pos = (entry_bytes / total_bytes) * total_duration
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse


ICY_MAX_RECONNECTS = 10       # Maximale Reconnect-Versuche
ICY_RECONNECT_DELAY = 5       # Sekunden zwischen Versuchen


class IcyMetadataLogger:
    def __init__(self, ignore_rules: list[dict] | None = None,
                 on_title_change: Optional[Callable] = None):
        self.entries: list[dict] = []
        self._running = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._start_time: Optional[float] = None
        self._last_title: str = ""
        self._last_valid_title: str = ""  # Carry-Forward: letzter nicht-ignorierter Titel
        self._cumulative_bytes: int = 0
        self._metaint: int = 0
        self._reconnect_count: int = 0
        # Sperr-Liste: [{pattern, match_type}, ...]
        self._ignore_rules = ignore_rules or []
        # Live-Split Callback: async fn(title, elapsed_ms, audio_bytes)
        self._on_title_change = on_title_change

    async def _connect(self, host: str, port: int, path: str,
                       timeout: float = 10.0) -> int:
        """Verbindet zum Stream und gibt metaint zurück (0 bei Fehler)."""
        self._close_connection()

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
        except (asyncio.TimeoutError, OSError) as e:
            print(f"  ICY: Verbindung fehlgeschlagen: {e}")
            return 0

        request = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            f"Icy-MetaData: 1\r\n"
            f"User-Agent: RadioHub/0.2\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )

        self._writer.write(request.encode())
        await self._writer.drain()

        metaint = await self._read_headers()
        return metaint

    async def run(self, stream_url: str, output_path: Path, timeout: float = 10.0):
        """Startet ICY-Metadata-Logging mit Reconnect. Läuft bis stop()."""
        self.entries = []
        self._running = True
        self._last_title = ""
        self._last_valid_title = ""
        self._cumulative_bytes = 0
        self._metaint = 0
        self._reconnect_count = 0

        parsed = urlparse(stream_url)
        host = parsed.hostname
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        if not host:
            print(f"  ICY: Ungültige URL: {stream_url}")
            return

        try:
            metaint = await self._connect(host, port, path, timeout)
            if not metaint:
                print("  ICY: Kein icy-metaint Header, Stream ohne ICY")
                return

            self._metaint = metaint
            self._start_time = asyncio.get_event_loop().time()
            print(f"  ICY: Metadata-Interval: {metaint} Bytes")

            # Metadata-Loop mit Reconnect
            while self._running:
                try:
                    await self._metadata_loop(metaint, output_path)
                    # Sauberes Ende der Loop = Stream beendet
                    if not self._running:
                        break

                    # Reconnect-Versuch
                    self._reconnect_count += 1
                    if self._reconnect_count > ICY_MAX_RECONNECTS:
                        print(f"  ICY: Max Reconnects erreicht ({ICY_MAX_RECONNECTS})")
                        break

                    print(f"  ICY: Stream unterbrochen, "
                          f"Reconnect {self._reconnect_count}/{ICY_MAX_RECONNECTS} "
                          f"in {ICY_RECONNECT_DELAY}s...")
                    await asyncio.sleep(ICY_RECONNECT_DELAY)

                    if not self._running:
                        break

                    new_metaint = await self._connect(host, port, path, timeout)
                    if not new_metaint:
                        print(f"  ICY: Reconnect fehlgeschlagen")
                        # Nächsten Versuch abwarten
                        continue

                    metaint = new_metaint
                    print(f"  ICY: Reconnect erfolgreich "
                          f"({self._reconnect_count}/{ICY_MAX_RECONNECTS})")
                    self._reconnect_count = 0

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    if self._running:
                        print(f"  ICY: Loop-Fehler: {e}")
                        self._reconnect_count += 1
                        if self._reconnect_count > ICY_MAX_RECONNECTS:
                            break
                        await asyncio.sleep(ICY_RECONNECT_DELAY)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._running:
                print(f"  ICY: Fehler: {e}")
        finally:
            self._save(output_path)
            self._close_connection()

    async def _read_headers(self) -> int:
        """Liest HTTP-Response-Header und gibt icy-metaint zurück (0 wenn nicht vorhanden)."""
        metaint = 0
        while True:
            line = await asyncio.wait_for(self._reader.readline(), timeout=10)
            line_str = line.decode("utf-8", errors="replace").strip()

            if not line_str:
                break  # Leere Zeile = Header-Ende

            # icy-metaint Header suchen
            if line_str.lower().startswith("icy-metaint:"):
                try:
                    metaint = int(line_str.split(":", 1)[1].strip())
                except ValueError:
                    pass

        return metaint

    async def _metadata_loop(self, metaint: int, output_path: Path):
        """Liest Audio-Chunks und extrahiert Metadata mit Byte-Tracking."""
        while self._running:
            # Audio-Bytes überspringen (exakt metaint Bytes pro Zyklus)
            remaining = metaint
            while remaining > 0:
                chunk_size = min(remaining, 8192)
                data = await asyncio.wait_for(
                    self._reader.read(chunk_size),
                    timeout=30
                )
                if not data:
                    print("  ICY: Stream beendet")
                    return
                remaining -= len(data)

            # Kumulative Audio-Bytes nach diesem Chunk
            self._cumulative_bytes += metaint

            # Metadata-Länge lesen (1 Byte)
            length_byte = await asyncio.wait_for(
                self._reader.readexactly(1),
                timeout=10
            )
            meta_length = length_byte[0] * 16

            if meta_length == 0:
                continue  # Kein Metadata in diesem Block

            # Metadata lesen
            meta_data = await asyncio.wait_for(
                self._reader.readexactly(meta_length),
                timeout=10
            )
            meta_str = meta_data.decode("utf-8", errors="replace").rstrip("\x00")

            # StreamTitle parsen
            title = self._parse_stream_title(meta_str)
            if title and title != self._last_title:
                self._last_title = title
                ignored = self._is_ignored(title)
                elapsed_ms = int((asyncio.get_event_loop().time() - self._start_time) * 1000)

                if ignored:
                    # Carry-Forward: Letzten gültigen Titel beibehalten
                    display_title = self._last_valid_title or title
                    print(f"  ICY [{elapsed_ms/1000:.1f}s] Sperrtext: {title} -> behalte: {display_title}")
                else:
                    display_title = title
                    self._last_valid_title = title
                    print(f"  ICY [{elapsed_ms/1000:.1f}s, {self._cumulative_bytes} bytes]: {title}")

                self.entries.append({
                    "t": elapsed_ms,
                    "b": self._cumulative_bytes,
                    "title": display_title,
                    "raw_title": title,
                    "ignored": ignored,
                    "raw": meta_str
                })

                # Sofort speichern bei jedem Titelwechsel
                self._save(output_path)

                # Live-Split Callback (nur bei echten Titelwechseln, nicht Sperrtexten)
                if not ignored and self._on_title_change:
                    try:
                        await self._on_title_change(
                            display_title, elapsed_ms, self._cumulative_bytes
                        )
                    except Exception as e:
                        print(f"  ICY: Callback-Fehler: {e}")

    def _parse_stream_title(self, meta_str: str) -> str:
        """Extrahiert StreamTitle aus ICY-Metadata-String."""
        match = re.search(r"StreamTitle='([^']*)'", meta_str)
        if match:
            return match.group(1).strip()

    def _is_ignored(self, title: str) -> bool:
        """Prueft ob ein ICY-Titel auf der Ignorier-Liste steht."""
        upper = title.upper()
        for rule in self._ignore_rules:
            pattern = rule.get("pattern", "").upper()
            if not pattern:
                continue
            if rule.get("match_type") == "contains":
                if pattern in upper:
                    return True
            else:  # exact
                if upper == pattern:
                    return True
        return False

    def _save(self, output_path: Path):
        """Speichert Metadata als strukturiertes JSON mit Byte-Positionen."""
        if not self.entries:
            return
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            meta = {
                "metaint": self._metaint,
                "total_audio_bytes": self._cumulative_bytes,
                "entries": self.entries
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  ICY: Speichern fehlgeschlagen: {e}")

    def _close_connection(self):
        """Schließt die TCP-Verbindung (ohne _running zu ändern)."""
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass
            self._writer = None
        self._reader = None

    def stop(self):
        """Stoppt den Logger."""
        self._running = False
        self._close_connection()

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def total_audio_bytes(self) -> int:
        return self._cumulative_bytes
