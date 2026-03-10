"""
RadioHub v0.2.1 - ICY Metadata Logger

Liest ICY-Metadata (StreamTitle) aus dem Radio-Stream via Raw-TCP.
Loggt Titelwechsel mit Audio-Byte-Positionen in eine .meta.json Datei.

ICY-Protokoll:
- HTTP/1.0 GET mit "Icy-MetaData: 1" Header
- Server antwortet mit icy-metaint=N Header
- Alle N Audio-Bytes: 1 Byte Laenge, dann Laenge*16 Bytes Metadata
- Metadata: "StreamTitle='Artist - Song';"

Byte-Tracking:
- Kumulative Audio-Bytes werden pro Metadata-Zyklus gezaehlt
- Jeder Entry speichert 'b' (Byte-Position) + 't' (Wallclock-ms)
- Splitter nutzt Byte-Ratio fuer praezise Schnitt-Positionen:
  audio_pos = (entry_bytes / total_bytes) * total_duration
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class IcyMetadataLogger:
    def __init__(self):
        self.entries: list[dict] = []
        self._running = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._start_time: Optional[float] = None
        self._last_title: str = ""
        self._cumulative_bytes: int = 0
        self._metaint: int = 0

    async def run(self, stream_url: str, output_path: Path, timeout: float = 10.0):
        """Startet ICY-Metadata-Logging. Laeuft bis stop() aufgerufen wird."""
        self.entries = []
        self._running = True
        self._last_title = ""
        self._cumulative_bytes = 0
        self._metaint = 0

        parsed = urlparse(stream_url)
        host = parsed.hostname
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        if not host:
            print(f"  ICY: Ungueltige URL: {stream_url}")
            return

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
        except (asyncio.TimeoutError, OSError) as e:
            print(f"  ICY: Verbindung fehlgeschlagen: {e}")
            return

        # HTTP/1.0 Request mit ICY-Header
        request = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            f"Icy-MetaData: 1\r\n"
            f"User-Agent: RadioHub/0.2\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )

        try:
            self._writer.write(request.encode())
            await self._writer.drain()

            # Response-Header lesen
            metaint = await self._read_headers()
            if not metaint:
                print("  ICY: Kein icy-metaint Header, Stream unterstuetzt kein ICY")
                self._close()
                return

            self._metaint = metaint
            # Start-Time NACH Connection+Headers (naeher am Audio-Start)
            self._start_time = asyncio.get_event_loop().time()

            print(f"  ICY: Metadata-Interval: {metaint} Bytes")

            # Metadata-Loop
            await self._metadata_loop(metaint, output_path)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._running:
                print(f"  ICY: Fehler: {e}")
        finally:
            self._save(output_path)
            self._close()

    async def _read_headers(self) -> int:
        """Liest HTTP-Response-Header und gibt icy-metaint zurueck (0 wenn nicht vorhanden)."""
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
            # Audio-Bytes ueberspringen (exakt metaint Bytes pro Zyklus)
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

            # Metadata-Laenge lesen (1 Byte)
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
                elapsed_ms = int((asyncio.get_event_loop().time() - self._start_time) * 1000)
                self.entries.append({
                    "t": elapsed_ms,
                    "b": self._cumulative_bytes,
                    "title": title,
                    "raw": meta_str
                })
                self._last_title = title
                print(f"  ICY [{elapsed_ms/1000:.1f}s, {self._cumulative_bytes} bytes]: {title}")

                # Sofort speichern bei jedem Titelwechsel
                self._save(output_path)

    def _parse_stream_title(self, meta_str: str) -> str:
        """Extrahiert StreamTitle aus ICY-Metadata-String."""
        match = re.search(r"StreamTitle='([^']*)'", meta_str)
        if match:
            return match.group(1).strip()
        return ""

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

    def _close(self):
        """Schliesst die TCP-Verbindung."""
        self._running = False
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
        self._close()

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def total_audio_bytes(self) -> int:
        return self._cumulative_bytes
