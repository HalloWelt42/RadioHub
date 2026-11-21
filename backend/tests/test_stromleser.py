"""Stromleser und Titelbuch (RAD-33): eine Verbindung für Ton und Sendedaten. Der Ton kommt ohne Sendedaten an, jede
Angabe mit ihrer Stelle im Ton; Weiterleitungen und Server mit "ICY 200 OK" gehen, eine Wiedergabeliste wird erkannt;
bricht der Strom ab, verbindet der Leser neu und zählt weiter. Zeitversatz und Aufnahme verbinden sich je Sender nur
noch einmal (früher zweimal, die Aufnahme bei jedem Titelwechsel neu)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.services import recorder as recorder_modul
from app.services import stromleser as sl
from app.services.titelbuch import Titelbuch, titel_aus
from conftest import ton

METAINT = 4000
WERBUNG = "StreamTitle='';StreamUrl='';adw_ad='true';durationMilliseconds='15046';adId='198927';insertionType='preroll';"


def _angabe(text: str) -> bytes:
    roh = text.encode()
    roh += b"\0" * (-len(roh) % 16)
    return bytes([len(roh) // 16]) + roh


class Sender:
    """Nachgestellter Sender: /strom liefert Ton mit Sendedaten (ICY), /weiter leitet dorthin, /liste ist eine
    Wiedergabeliste. `angaben`: Block -> Text; `abbruch`: nach so vielen Blöcken bricht die erste Verbindung ab.
    Zählt die Verbindungen, die Sendedaten verlangen."""

    def __init__(self, ton: bytes, angaben: dict[int, str], abbruch: int | None = None, takt_s: float = 0.0):
        self.ton, self.angaben, self.abbruch, self.takt_s = ton, angaben, abbruch, takt_s
        self.verbindungen = 0
        self.mit_sendedaten = 0
        self.server: asyncio.AbstractServer | None = None

    async def __aenter__(self) -> "Sender":
        self.server = await asyncio.start_server(self._bedienen, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *_) -> None:
        self.server.close()
        await self.server.wait_closed()

    def adresse(self, pfad: str = "/strom") -> str:
        return f"http://127.0.0.1:{self.server.sockets[0].getsockname()[1]}{pfad}"

    async def _bedienen(self, leser: asyncio.StreamReader, schreiber: asyncio.StreamWriter) -> None:
        anfrage = (await leser.readuntil(b"\r\n\r\n")).decode()
        pfad = anfrage.split()[1]
        try:
            if pfad == "/weiter":
                schreiber.write(b"HTTP/1.0 302 Found\r\nLocation: /strom\r\n\r\n")
            elif pfad == "/liste":
                schreiber.write(b"HTTP/1.0 200 OK\r\nContent-Type: audio/x-mpegurl\r\n\r\nhttp://irgendwo/strom\n")
            elif "icy-metadata: 1" not in anfrage.lower():
                schreiber.write(b"HTTP/1.0 200 OK\r\nContent-Type: audio/mpeg\r\n\r\n" + self.ton)   # etwa ffprobe
            else:
                self.verbindungen += 1
                self.mit_sendedaten += 1
                erste = self.verbindungen == 1
                schreiber.write(f"ICY 200 OK\r\nicy-metaint: {METAINT}\r\nicy-br: 64\r\ncontent-type: audio/mpeg\r\n\r\n".encode())
                for i, ab in enumerate(range(0, len(self.ton), METAINT)):
                    if erste and self.abbruch is not None and i == self.abbruch:
                        break
                    schreiber.write(self.ton[ab:ab + METAINT])
                    if ab + METAINT <= len(self.ton):
                        schreiber.write(_angabe(self.angaben[i]) if i in self.angaben else b"\0")
                    await schreiber.drain()
                    if self.takt_s:
                        await asyncio.sleep(self.takt_s)
            await schreiber.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            schreiber.close()


@pytest.fixture
def mp3(tmp_path) -> bytes:
    return ton(tmp_path / "sender.mp3", 8.0).read_bytes()


@pytest.fixture(autouse=True)
def schnell(monkeypatch):
    monkeypatch.setattr(sl, "NEU_VERBINDEN_PAUSE_S", 0.0)


async def _lesen(adresse: str, versuche: int, monkeypatch, bis: int | None = None
                 ) -> tuple[sl.Stromleser, bytes, list[sl.Angabe]]:
    """Liest bis zum Ende (nach `versuche` Neuverbindungen ohne Ton) oder bis `bis` Bytes Ton da sind: solange Ton
    kommt, verbindet der Leser immer wieder neu, wie bei einem Sender, der nie endet."""
    monkeypatch.setattr(sl, "NEU_VERBINDEN_VERSUCHE", versuche)
    gelesen, angaben = bytearray(), []

    async def ziel(daten: bytes) -> None:
        gelesen.extend(daten)
        if bis is not None and len(gelesen) >= bis:
            leser.stop()

    async def bei_angabe(a: sl.Angabe) -> None:
        angaben.append(a)
    leser = sl.Stromleser(adresse, ziel, bei_angabe)
    await asyncio.wait_for(leser.laufen(), 20)
    return leser, bytes(gelesen), angaben


async def test_ton_ohne_sendedaten_und_angaben_an_ihrer_stelle(mp3, monkeypatch):
    async with Sender(mp3, {0: WERBUNG, 3: "StreamTitle='The Communards - Don't Leave Me This Way';"}) as sender:
        leser, gelesen, angaben = await _lesen(sender.adresse(), 0, monkeypatch)
    assert gelesen == mp3                                   # der Ton kommt vollständig und ohne Sendedaten an
    assert [(a.ton_bytes, a.roh) for a in angaben] == [(METAINT, WERBUNG),
                                                       (4 * METAINT, "StreamTitle='The Communards - Don't Leave Me This Way';")]
    assert angaben[1].sekunde == 4 * METAINT / 8000         # 64 kbit/s laut icy-br: 8000 Bytes je Sekunde
    assert leser.kopf.format == "mp3" and leser.kopf.metaint == METAINT
    assert titel_aus(angaben[1].roh) == "The Communards - Don't Leave Me This Way"


async def test_weiterleitung_und_antwort_icy(mp3, monkeypatch):
    async with Sender(mp3, {}) as sender:
        leser, gelesen, _ = await _lesen(sender.adresse("/weiter"), 0, monkeypatch)
    assert leser.kopf is None or leser.kopf.adresse.endswith("/strom")
    assert gelesen == mp3


async def test_wiedergabeliste_wird_erkannt(mp3):
    async with Sender(mp3, {}) as sender:
        with pytest.raises(sl.Wiedergabeliste):
            await sl.Stromleser(sender.adresse("/liste"), lambda d: asyncio.sleep(0)).verbinden()


async def test_abbruch_verbindet_neu_und_zaehlt_weiter(mp3, monkeypatch):
    async with Sender(mp3, {1: "StreamTitle='Eins';"}, abbruch=2) as sender:
        leser, gelesen, angaben = await _lesen(sender.adresse(), 1, monkeypatch, bis=2 * METAINT + len(mp3))
        assert sender.mit_sendedaten == 2
    assert leser.neu_verbunden == 1
    assert gelesen == mp3[:2 * METAINT] + mp3
    assert [a.ton_bytes for a in angaben] == [2 * METAINT, 2 * METAINT + 2 * METAINT]


async def test_titelbuch_stellen_sperrliste_und_wechsel(tmp_path):
    wechsel = []

    async def bei_wechsel(titel, ton_ms, ton_bytes):
        wechsel.append((titel, ton_ms, ton_bytes))
    buch = Titelbuch([{"pattern": "Werbung", "match_type": "contains"}], bei_wechsel, tmp_path / "titel.json")
    for b, text in ((8000, "StreamTitle='A - Eins';"), (16000, "StreamTitle='A - Eins';"),
                    (24000, "StreamTitle='Kurze Werbung';"), (40000, "StreamTitle='B - Zwei';")):
        await buch.angabe(sl.Angabe(roh=text, ton_bytes=b, sekunde=b / 8000, wand_ms=0))
    assert [(e["t"], e["title"], e["ignored"]) for e in buch.entries] == [
        (1000, "A - Eins", False), (3000, "A - Eins", True), (5000, "B - Zwei", False)]   # gesperrt: Anzeige bleibt
    assert wechsel == [("A - Eins", 1000, 8000), ("B - Zwei", 5000, 40000)]
    buch.abschliessen(48000)
    assert '"total_audio_bytes": 48000' in (tmp_path / "titel.json").read_text()


async def test_zeitversatz_verbindet_sich_einmal(mp3, tmp_path):
    from app.services.hls_buffer import HLSBufferService
    puffer = HLSBufferService(str(tmp_path / "hls"))
    # ein Sender, der während des Tests nicht endet (dreimal der Ton), schneller als Echtzeit
    async with Sender(mp3 * 3, {0: "StreamTitle='A - Eins';", 6: "StreamTitle='B - Zwei';"}, takt_s=0.1) as sender:
        assert (await puffer.start("s1", "Probesender", sender.adresse(), bitrate=64))["status"] == "started"
        for _ in range(100):
            if len(puffer.get_icy_entries()) >= 2 and len(list((tmp_path / "hls").glob("segment_*.ts"))) >= 3:
                break
            await asyncio.sleep(0.1)
        eintraege = puffer.get_icy_entries()
        await puffer.stop()
        assert sender.mit_sendedaten == 1                   # Ton und Titel aus derselben Verbindung
    assert [(e["title"], e["t"]) for e in eintraege] == [("A - Eins", 500), ("B - Zwei", 3500)]   # Stelle im Ton


async def test_aufnahme_teilt_ohne_neue_verbindung(client, mp3, monkeypatch):
    monkeypatch.setattr(recorder_modul, "MIN_SEGMENT_SECONDS", 0)
    rec = recorder_modul.rec_manager
    async with Sender(mp3 * 3, {0: "StreamTitle='A - Eins';", 8: "StreamTitle='B - Zwei';"}, takt_s=0.1) as sender:
        ergebnis = await rec.start("s1", "Probesender", sender.adresse(), 64)
        assert ergebnis["success"], ergebnis
        for _ in range(100):
            if rec.active_session and rec.active_session.segment_index >= 2:
                break
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)
        status = rec.get_status()
        await rec.stop()
        assert sender.mit_sendedaten == 1                   # früher: eine neue Verbindung je Titelwechsel
    assert [e["title"] for e in status["icy_entries"]] == ["A - Eins", "B - Zwei"]
