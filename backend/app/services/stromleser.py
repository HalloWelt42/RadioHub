"""Stromleser (RAD-33): eine Verbindung zum Sender für Ton und Sendedaten.

Bisher holte ffmpeg den Ton und ein zweiter Leser die Titel. Jede Verbindung bekam ihre eigene Werbung beim Verbinden
und ihre eigenen Stellen, die Angaben passten also nicht zum gehörten Ton; Sender über https bekamen gar keine Titel.
Der Stromleser verbindet sich einmal (http und https, auch Server, die mit "ICY 200 OK" antworten), folgt
Weiterleitungen, trennt Ton und Sendedaten, reicht den reinen Ton an ein Ziel weiter (etwa ffmpeg über stdin) und
meldet jede Angabe mit ihrer Stelle im Ton. Bricht der Strom ab, verbindet er neu und zählt weiter; das Ziel merkt
davon nur eine Lücke.

Die Stelle einer Angabe ist die Zahl der Ton-Bytes davor; in Sekunden umgerechnet über die Bitrate des Stroms (Kopf
icy-br, sonst die vom Aufrufer erkannte). Für Ströme mit fester Bitrate ist das genau, bei wechselnder eine Näherung.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional
from urllib.parse import urljoin, urlsplit

import certifi

from .messung import messung

logger = logging.getLogger("radiohub.stromleser")

KENNUNG = "RadioHub/1.0"
HOECHSTENS_WEITERLEITUNGEN = 5
VERBINDEN_S = 10.0
LESEN_S = 30.0
NEU_VERBINDEN_VERSUCHE = 10
NEU_VERBINDEN_PAUSE_S = 5.0
BLOCK_OHNE_ANGABEN = 16384

#: Zertifikate wie bei httpx (certifi), damit https überall gleich geprüft wird, auch ohne Zertifikate des Systems
TLS = ssl.create_default_context(cafile=certifi.where())

#: Antworten, hinter denen kein Ton, sondern eine Liste weiterer Adressen steht (die übernimmt ffmpeg selbst)
WIEDERGABELISTEN = ("mpegurl", "x-scpls", "pls", "m3u", "xspf")

#: Format für ffmpeg nach Art der Antwort; fehlt die Art, erkennt ffmpeg selbst
FORMATE = {"audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/aac": "aac", "audio/aacp": "aac", "audio/x-aac": "aac",
           "audio/ogg": "ogg", "application/ogg": "ogg", "audio/opus": "ogg", "audio/flac": "flac"}


class StromFehler(Exception):
    """Der Sender ist nicht als Tonstrom lesbar (Fehlerstatus, zu viele Weiterleitungen, kein Ton)."""


class Wiedergabeliste(StromFehler):
    """Hinter der Adresse steht eine Liste von Adressen statt Ton; der Aufrufer nimmt den bisherigen Weg."""


def text_aus(roh: bytes) -> str:
    """Sendedaten als Text: gewöhnlich UTF-8, ältere Sender schicken westeuropäische Zeichen (Ti\xebsto, RAD-139)."""
    try:
        return roh.decode("utf-8")
    except UnicodeDecodeError:
        return roh.decode("cp1252", "replace")


@dataclass(frozen=True)
class Kopf:
    """Was der Sender beim Verbinden mitteilt."""

    adresse: str                  # nach den Weiterleitungen
    art: str                      # Content-Type ohne Zusatz
    metaint: int                  # Ton-Bytes zwischen zwei Angaben, 0 ohne Sendedaten
    bitrate: int                  # kbps laut icy-br, 0 wenn unbekannt
    name: str

    @property
    def format(self) -> Optional[str]:
        return FORMATE.get(self.art)


@dataclass(frozen=True)
class Angabe:
    """Eine Angabe der Sendedaten (roh, etwa "StreamTitle='...';") und ihre Stelle im Ton."""

    roh: str
    ton_bytes: int
    sekunde: float
    wand_ms: int                  # Zeit seit dem Start des Lesers (nur zur Auskunft)


Ziel = Callable[[bytes], Awaitable[None]]
BeiAngabe = Callable[[Angabe], Awaitable[None]]


class Stromleser:
    def __init__(self, adresse: str, ziel: Ziel, bei_angabe: Optional[BeiAngabe] = None, bitrate: int = 0):
        self.adresse = adresse
        self._ziel = ziel
        self._bei_angabe = bei_angabe
        self._bitrate_ersatz = bitrate
        self.kopf: Optional[Kopf] = None
        self.ton_bytes = 0
        self.neu_verbunden = 0
        self._laeuft = False
        self._leser: Optional[asyncio.StreamReader] = None
        self._schreiber: Optional[asyncio.StreamWriter] = None
        self._beginn = time.monotonic()

    @property
    def bytes_je_sekunde(self) -> float:
        kbps = (self.kopf.bitrate if self.kopf and self.kopf.bitrate else 0) or self._bitrate_ersatz or 128
        return kbps * 1000 / 8

    def sekunde(self, ton_bytes: int) -> float:
        return ton_bytes / self.bytes_je_sekunde

    async def verbinden(self) -> Kopf:
        """Verbindet (mit Weiterleitungen) und liest den Kopf; danach steht der Ton an."""
        self._schliessen()
        adresse = self.adresse
        for _ in range(HOECHSTENS_WEITERLEITUNGEN + 1):
            teile = urlsplit(adresse)
            if teile.scheme not in ("http", "https") or not teile.hostname:
                raise StromFehler(f"Keine Adresse für einen Tonstrom: {adresse}")
            sicher = teile.scheme == "https"
            port = teile.port or (443 if sicher else 80)
            pfad = (teile.path or "/") + (f"?{teile.query}" if teile.query else "")
            try:
                self._leser, self._schreiber = await asyncio.wait_for(
                    asyncio.open_connection(teile.hostname, port, ssl=TLS if sicher else None,
                                            server_hostname=teile.hostname if sicher else None), VERBINDEN_S)
            except (OSError, asyncio.TimeoutError, ssl.SSLError) as f:
                raise StromFehler(f"Sender nicht erreichbar: {f}") from f
            wirt = teile.hostname if teile.port is None else f"{teile.hostname}:{teile.port}"
            self._schreiber.write((f"GET {pfad} HTTP/1.0\r\nHost: {wirt}\r\nIcy-MetaData: 1\r\nUser-Agent: {KENNUNG}\r\n"
                                   "Accept: */*\r\nConnection: close\r\n\r\n").encode())
            await self._schreiber.drain()
            status, koepfe = await self._kopf_lesen()
            if status in (301, 302, 303, 307, 308) and koepfe.get("location"):
                adresse = urljoin(adresse, koepfe["location"])
                self._schliessen()
                continue
            if status != 200:
                self._schliessen()
                raise StromFehler(f"Sender antwortet mit Status {status}")
            art = koepfe.get("content-type", "").split(";")[0].strip().lower()
            if any(w in art for w in WIEDERGABELISTEN):
                self._schliessen()
                raise Wiedergabeliste(art)
            bitrate = koepfe.get("icy-br", "").split(",")[0].strip()
            self.kopf = Kopf(adresse=adresse, art=art, metaint=int(koepfe.get("icy-metaint") or 0),
                             bitrate=int(bitrate) if bitrate.isdigit() else 0, name=koepfe.get("icy-name", ""))
            return self.kopf
        self._schliessen()
        raise StromFehler("Zu viele Weiterleitungen")

    async def _kopf_lesen(self) -> tuple[int, dict[str, str]]:
        zeile = (await asyncio.wait_for(self._leser.readline(), LESEN_S)).decode("latin-1").strip()
        teile = zeile.split()
        if len(teile) < 2 or not teile[1].isdigit() or not (teile[0].startswith("HTTP/") or teile[0] == "ICY"):
            raise StromFehler(f"Unerwartete Antwort: {zeile[:80]}")
        koepfe: dict[str, str] = {}
        while True:
            z = (await asyncio.wait_for(self._leser.readline(), LESEN_S)).decode("latin-1").strip()
            if not z:
                break
            name, _, wert = z.partition(":")
            koepfe[name.strip().lower()] = wert.strip()
        return int(teile[1]), koepfe

    async def laufen(self) -> None:
        """Liest, bis stop() kommt oder der Sender nach allen Versuchen weg bleibt. Verbindet selbst, falls noch
        nicht geschehen."""
        self._laeuft = True
        versuche = 0
        try:
            while self._laeuft:
                vorher = self.ton_bytes
                try:
                    if self.kopf is None or self._leser is None:
                        await self.verbinden()
                    await self._lesen()
                except (StromFehler, OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as f:
                    if not self._laeuft:
                        break
                    logger.warning(f"Strom unterbrochen: {f}")
                    messung.merken("strom_weg", rechner=urlsplit(self.adresse).hostname, grund=f"{type(f).__name__}: {f}", ton_bytes=self.ton_bytes, versuch=versuche + 1)
                versuche = 1 if self.ton_bytes > vorher else versuche + 1    # kam Ton, zählt der Abbruch neu
                if not self._laeuft or versuche > NEU_VERBINDEN_VERSUCHE:
                    break
                self._schliessen()
                self.kopf = None
                self.neu_verbunden += 1
                await asyncio.sleep(NEU_VERBINDEN_PAUSE_S)
        finally:
            self._schliessen()

    async def _lesen(self) -> None:
        metaint = self.kopf.metaint if self.kopf else 0
        while self._laeuft:
            if not metaint:
                daten = await asyncio.wait_for(self._leser.read(BLOCK_OHNE_ANGABEN), LESEN_S)
                if not daten:
                    return
                await self._weiter(daten)
                continue
            try:
                daten = await asyncio.wait_for(self._leser.readexactly(metaint), LESEN_S)
            except asyncio.IncompleteReadError as f:
                if f.partial:                       # der Rest vor dem Abbruch ist Ton und gehört dazu
                    await self._weiter(f.partial)
                raise
            await self._weiter(daten)
            laenge = (await asyncio.wait_for(self._leser.readexactly(1), LESEN_S))[0] * 16
            if laenge and self._bei_angabe:
                roh = (await asyncio.wait_for(self._leser.readexactly(laenge), LESEN_S)).rstrip(b"\0")
                await self._bei_angabe(Angabe(roh=text_aus(roh), ton_bytes=self.ton_bytes,
                                              sekunde=self.sekunde(self.ton_bytes),
                                              wand_ms=int((time.monotonic() - self._beginn) * 1000)))
            elif laenge:
                await asyncio.wait_for(self._leser.readexactly(laenge), LESEN_S)

    async def _weiter(self, daten: bytes) -> None:
        self.ton_bytes += len(daten)
        await self._ziel(daten)

    def stop(self) -> None:
        self._laeuft = False
        self._schliessen()

    def _schliessen(self) -> None:
        if self._schreiber:
            try:
                self._schreiber.close()
            except Exception:
                pass
        self._schreiber = None
        self._leser = None
