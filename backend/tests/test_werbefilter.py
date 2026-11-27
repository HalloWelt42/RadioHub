"""Werbung am Klang (HELF-256): der Ton geht an den Filter, Treffer werden Werbestellen, angekündigte Spots werden Signaturen;
die Liste des Lernlaufs folgt dem, was man hört; die Wege der Oberfläche reichen durch."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
import pytest

from app.database import db_session
from app.services import hoerverlauf, klangerkennung, lernliste
from app.services import propagandafilter as pf
from app.sendewerbung.sitzung import KLANG_BEIM_VERBINDEN_S, Sitzungswerbung, Werbestelle

E = pf.FilterEinstellungen(adresse="https://filter.test", schluessel="kw_app_radiohub")
BPS = 16000.0


class Filter:
    def __init__(self) -> None:
        self.stuecke: list[tuple[float, int]] = []
        self.signaturen: list[dict] = []
        self.beendet: list[str] = []
        self.antworten: list[httpx.Response] = []
        self.stellen: list[dict] = []
        self.listen: list[list[dict]] = []

    def transport(self) -> httpx.MockTransport:
        def antwort(r: httpx.Request) -> httpx.Response:
            p = r.url.path
            if p.endswith("/ton"):
                if self.antworten:
                    return self.antworten.pop(0)
                self.stuecke.append((float(r.url.params["ab"]), len(r.read())))
                return httpx.Response(200, json={"id": "s", "quelle": "u", "geprueft_bis": 0, "stellen": self.stellen})
            if p == "/api/v1/stroeme":
                return httpx.Response(201, json={"id": f"s{len(self.beendet)}"})
            if r.method == "DELETE":
                self.beendet.append(p)
                return httpx.Response(204)
            if p == "/api/v1/signaturen" and r.method == "POST":
                self.signaturen.append({**r.url.params, "bytes": len(r.read())})
                return httpx.Response(201, json={})
            if p == "/api/v1/lernlauf/sender":
                self.listen.append(json.loads(r.content))
            return httpx.Response(200, json={})
        return httpx.MockTransport(antwort)


@pytest.fixture
def filter_(monkeypatch) -> Filter:
    f = Filter()
    monkeypatch.setattr(pf.FilterEinstellungen, "jetzt", classmethod(lambda cls: E))
    monkeypatch.setattr(klangerkennung, "NEUER_VERSUCH_S", 0.01)
    return f


def stelle(von=10.0, bis=25.0, wirkt=True, signatur="sig-1", werbender="firma.de") -> dict:
    return {"signatur": signatur, "von": von, "bis": bis, "sicher_ab": von + 5, "wirkt": wirkt, "werbender": werbender, "abgebrochen": False}


def erkennung(f: Filter, werbung: Sitzungswerbung, art: str | None = "mp3") -> klangerkennung.Klangerkennung:
    return klangerkennung.Klangerkennung("uuid-1", "Sender", art, BPS, werbung, lambda a, b: bytes(int((b - a) * BPS)), f.transport())


async def bis_(bedingung, sekunden=3.0) -> None:
    for _ in range(int(sekunden * 100)):
        if bedingung():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("kam nicht")


async def test_ton_geht_hinaus_und_treffer_werden_stellen(filter_):
    gemeldet: list[Werbestelle] = []
    w = Sitzungswerbung(bei_ende=gemeldet.append)
    k = erkennung(filter_, w)
    k.starten()
    filter_.stellen = [stelle(wirkt=False)]
    k.ton(bytes(32000), 0)
    await bis_(lambda: filter_.stuecke)
    assert filter_.stuecke == [(0.0, 32000)] and w.stellen == [], "ein Vorschlag wirkt nicht"
    filter_.stellen = [stelle()]
    k.ton(bytes(32000), 32000)
    await bis_(lambda: w.stellen)
    (s,) = w.stellen
    assert (s.von, s.bis, s.format, s.werbender, s.name, k.zustand) == (10.0, 25.0, "klang", "firma.de", "firma.de", "laeuft")
    filter_.stellen = [stelle(bis=21.0)]                       # abgebrochen: das Ende rückt, keine zweite Stelle
    k.ton(bytes(32000), 64000)
    await bis_(lambda: w.stellen[0].bis == 21.0)
    assert len(w.stellen) == 1
    w.ton_bis(40.0)
    assert len(gemeldet) == 1
    await k.schliessen()
    assert filter_.beendet == ["/api/v1/stroeme/s0"]


async def test_ausfall_beginnt_neu_und_stellen_bleiben(filter_):
    w = Sitzungswerbung()
    k = erkennung(filter_, w)
    filter_.stellen = [stelle()]
    k.starten()
    k.ton(bytes(32000), 0)
    await bis_(lambda: w.stellen)
    filter_.antworten = [httpx.Response(404, json={"detail": "weg"})]
    k.ton(bytes(32000), 32000)
    await bis_(lambda: k.zustand == "ruht" or filter_.beendet)
    k.ton(bytes(32000), 96000)
    await bis_(lambda: (6.0, 32000) in filter_.stuecke)
    assert len(w.stellen) == 1 and k.zustand == "laeuft"
    await k.schliessen()


async def test_rueckstand_bleibt_begrenzt(filter_):
    k = erkennung(filter_, Sitzungswerbung())
    k._lauf = asyncio.create_task(asyncio.sleep(60))           # der Filter kommt nicht nach
    for i in range(300):
        k.ton(bytes(16000), i * 16000)
    assert k._wartend <= klangerkennung.RUECKSTAND_S * BPS and k._warten[0][0] > 0
    await k.schliessen()


async def test_angekuendigter_spot_wird_einmal_signatur(filter_, monkeypatch):
    k = erkennung(filter_, Sitzungswerbung())
    k.starten()
    echt = pf.fragen
    monkeypatch.setattr(pf, "fragen", lambda *a, **kw: echt(*a, **{**kw, "transport": filter_.transport()}))
    s = Werbestelle(von=1.0, von_aus="verbinden", bis=21.0, bis_aus="dauer", format="adw", kennung="77", werbender="firma.de")
    k.angekuendigt(s)
    k.angekuendigt(s)
    k.angekuendigt(s.model_copy(update={"werbender": "", "kennung": "78"}))
    k.angekuendigt(s.model_copy(update={"bis": 300.0, "kennung": "79"}))
    await bis_(lambda: filter_.signaturen)
    (n,) = filter_.signaturen
    assert (n["von"], n["bis"], n["herkunft"], n["werbender"], n["quelle"]) == ("1.0", "21.0", "angabe", "firma.de", "uuid-1")
    assert n["bytes"] == 23 * BPS
    await k.schliessen()


async def test_ohne_lesbares_format_ruht_es(filter_):
    k = erkennung(filter_, Sitzungswerbung(), art="ogg")
    k.starten()
    k.ton(bytes(64000), 0)
    assert k.zustand == "aus" and not k._warten


def test_angekuendigtes_gilt_vor_dem_klang():
    w = Sitzungswerbung()
    w.stellen.append(Werbestelle(von=5, von_aus="angabe", bis=30, bis_aus="dauer", format="adw", kennung="1"))
    w.erkannt("sig", 6.0, 29.0, "firma.de")
    assert len(w.stellen) == 1
    w.erkannt("sig", 40.0, 60.0, "")
    assert [s.format for s in w.stellen] == ["adw", "klang"] and w.stellen[1].name == ""


def test_spot_beim_verbinden_wird_abgewartet():
    """RAD-154: ein am Klang erkannter Spot am Anfang des Tons ist ein Spot beim Verbinden und beginnt mit dem ersten Ton, wie
    eine Angabe beim Verbinden; so wartet der Start ihn ab."""
    w = Sitzungswerbung()
    s = w.erkannt("sig", 0.0, 25.0, "AIDA")
    assert s is not None and (s.von, s.von_aus, s.beim_verbinden) == (0.0, "verbinden", True)
    knapp = Sitzungswerbung().erkannt("sig", KLANG_BEIM_VERBINDEN_S, 20.0, "AIDA")
    assert knapp is not None and (knapp.von, knapp.beim_verbinden) == (0.0, True)
    assert w.erkannt("sig", 0.0, 22.0, "AIDA") is s and s.bis == 22.0 and len(w.stellen) == 1, "dieselbe Stelle rückt nur ihr Ende"
    spaeter = w.erkannt("sig", KLANG_BEIM_VERBINDEN_S + 0.5, 40.0, "AIDA")
    assert spaeter is not None and (spaeter.von, spaeter.von_aus, spaeter.beim_verbinden) == (KLANG_BEIM_VERBINDEN_S + 0.5, "klang", False)
    angekuendigt = Sitzungswerbung()
    angekuendigt.stellen.append(Werbestelle(von=0, von_aus="verbinden", bis=15, bis_aus="dauer", format="adw", kennung="1", beim_verbinden=True))
    assert angekuendigt.erkannt("sig", 1.0, 14.0, "") is None and len(angekuendigt.stellen) == 1


class _Mitschrift(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.zeilen: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.zeilen.append(record.getMessage())


@pytest.fixture
def protokoll():
    """Was die Klangerkennung ins Protokoll schreibt, direkt am Logger (radiohub reicht im Betrieb nicht an die Wurzel weiter)."""
    log, mitschrift = logging.getLogger("radiohub.klangerkennung"), _Mitschrift()
    vorher = log.level
    log.addHandler(mitschrift)
    log.setLevel(logging.INFO)
    yield lambda: mitschrift.zeilen
    log.setLevel(vorher)
    log.removeHandler(mitschrift)


async def test_funde_im_protokoll(filter_, protokoll):
    """RAD-154: Beginn und Ende des Stroms, je Fund eine Zeile, auch wenn der Filter ihn in jeder Antwort wieder nennt."""
    w = Sitzungswerbung()
    w.stellen.append(Werbestelle(von=40, von_aus="angabe", bis=60, bis_aus="dauer", format="adw", kennung="1"))
    k = erkennung(filter_, w)
    k.starten()
    filter_.stellen = [stelle(0.0, 25.0, signatur="sig-aida", werbender="AIDA"), stelle(30.0, 38.0, wirkt=False, werbender=""),
                       stelle(41.0, 59.0, signatur="sig-3")]
    for i in range(3):
        k.ton(bytes(32000), i * 32000)
        await bis_(lambda: len(filter_.stuecke) > i)
    await k.schliessen()
    zeilen = protokoll()
    assert zeilen == [
        "Sender: Strom zum Filter beginnt (s0)",
        "Sender: Fund AIDA 0.0 bis 25.0 s wirkt, beim Verbinden",
        "Sender: Fund Signatur sig-1 30.0 bis 38.0 s verworfen: wirkt hier nicht (Vorschlag)",
        "Sender: Fund firma.de 41.0 bis 59.0 s verworfen: angekündigter Spot gilt vor",
        "Sender: Strom zum Filter endet (s0, bis 6.0 s)",
    ], zeilen
    assert [s.format for s in w.stellen] == ["klang", "adw"] and w.stellen[0].beim_verbinden


def _sender(nr: int, genres: list[str], land="DE", stimmen=100, favorit=0, sichtbar=1, url="") -> str:
    uuid = f"lern-{nr}"
    with db_session() as c:
        c.execute("INSERT OR REPLACE INTO stations (uuid, name, url, url_resolved, hls) VALUES (?, ?, ?, '', 0)",
                  (uuid, f"Sender {nr}", url or f"http://s{nr}.test/live"))
        c.execute("INSERT OR REPLACE INTO sender_index (nr, uuid, land, stimmen, erreichbar, genres, sprachen, favorit, sichtbar) "
                  "VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)", (900000 + nr, uuid, land, stimmen, json.dumps(genres), json.dumps(["de"]), favorit, sichtbar))
        c.executemany("INSERT OR REPLACE INTO sender_genre (genre, nr) VALUES (?, ?)", [(g, 900000 + nr) for g in genres])
    return uuid


@pytest.fixture
def lernsender():
    yield
    with db_session() as c:
        c.execute("DELETE FROM sender_genre WHERE nr >= 900000")
        c.execute("DELETE FROM sender_index WHERE nr >= 900000")
        c.execute("DELETE FROM stations WHERE uuid LIKE 'lern-%'")
        c.execute("DELETE FROM hoerverlauf")


async def test_liste_folgt_dem_hoeren(filter_, lernsender, monkeypatch):
    fav, oft = _sender(1, ["probegenre"], favorit=1), _sender(2, ["probegenre"])
    _sender(3, ["probegenre"], stimmen=3000)                       # ähnlich
    _sender(4, ["probegenre"], land="FR", stimmen=3000)            # auch, aber weiter weg
    _sender(5, ["anderes"], stimmen=9000)                          # nur bekannt
    _sender(6, ["probegenre"], sichtbar=0, stimmen=9999)           # ausgeblendet
    _sender(7, ["probegenre"], url="http://s7.test/live.m3u8")
    for _ in range(40):
        hoerverlauf.merken(oft, 60)
    liste = {s.quelle: s for s in lernliste.zusammenstellen()}
    assert (liste[fav].grund, liste[oft].grund) == ("favorit", "gehoert") and liste[oft].gewicht > 1
    assert (liste["lern-3"].grund, liste["lern-4"].grund, liste["lern-5"].grund) == ("aehnlich", "aehnlich", "bekannt")
    assert liste["lern-3"].gewicht > liste["lern-4"].gewicht
    assert "lern-6" not in liste and "lern-7" not in liste
    echt = pf.fragen
    monkeypatch.setattr(pf, "fragen", lambda *a, **kw: echt(*a, **{**kw, "transport": filter_.transport()}))
    assert await lernliste.weitergeben() == len(liste) == len(filter_.listen[0])


def test_wege_der_oberflaeche(client, anonym):
    assert anonym.get("/api/werbefilter").status_code == 401
    assert client.get("/api/werbefilter").json()["eingerichtet"] is False
    assert client.get("/api/werbefilter/spots/pruefen").status_code == 503
    assert client.get("/api/werbefilter/spots/boese").status_code == 422
    assert client.put("/api/werbefilter/lernlauf", json={"von": "25:00"}).status_code == 422
