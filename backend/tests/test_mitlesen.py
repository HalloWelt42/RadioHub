"""Live mitlesen (RAD-129): Schnitt an leisen Stellen, Absätze aus ganzen Sätzen, Ablauf am Empfang mit nachgestellter
Leitstelle, Übersetzung nur bei fremder Sprache, und Aus heißt aus."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.services import mitlesen as m
from app.sendewerbung.sitzung import Sitzungswerbung, Werbestelle
from appkern.leitstelle import GehoertesSegment, Leitstelle


def seg(von: float, bis: float, text: str) -> GehoertesSegment:
    return GehoertesSegment(start=von, ende=bis, text=text)


def test_schnitt_an_der_leisesten_stelle():
    pegel = [(i / 10, -20.0) for i in range(0, 600)]
    pegel[224:228] = [(22.4 + i / 10, -55.0) for i in range(4)]
    assert m.schnitt(pegel, 0.0, 29.0) is None, "erst wenn der ganze Bereich gesendet ist"
    assert 22.4 <= m.schnitt(pegel, 0.0, 31.0) <= 22.8
    pegel[50:54] = [(5.0 + i / 10, -70.0) for i in range(4)]
    assert m.schnitt(pegel, 0.0, 31.0) > 15, "nie zu kurz"
    assert m.schnitt([], 10.0, 41.0) == 40.0, "ohne Pegel an der Grenze"


def test_absaetze_enden_mit_einem_satz():
    s = m.Absatzsammler()
    lang = "Das ist ein recht langer Satz, der schon für sich allein fast einen ganzen Absatz füllt und weiter und weiter geht"
    assert s.nehmen([seg(0, 8, lang), seg(8, 15, "und erst hier")]) == []
    (a,) = s.nehmen([seg(15, 22, "sein Ende findet. Danach folgt noch einer."), seg(22, 30, "Der nächste beginnt")])
    assert a[:2] == (0, 22) and a[2].endswith("folgt noch einer.") and "Der nächste" not in a[2]
    assert s.rest() == [(22, 30, "Der nächste beginnt")] and s.rest() == []
    ohne = m.Absatzsammler()
    assert len(ohne.nehmen([seg(i * 10, i * 10 + 10, "ohne jedes Satzzeichen") for i in range(8)])) == 1, "wartet nicht ewig"


class Empfang:
    """Was das Mitlesen vom Empfang braucht."""

    def __init__(self) -> None:
        self.uuid, self.name, self.beendet, self.anfang_s = "u1", "Probe", False, 0.0
        self.jetzt_s = 100.0
        self.pegel = [(i / 10, -20.0) for i in range(0, 1000)]
        self.werbung = Sitzungswerbung()
        self.kopf = SimpleNamespace(format="mp3")
        self.gelesen: list[tuple[float, float]] = []

    def ton_zwischen(self, von: float, bis: float) -> bytes:
        self.gelesen.append((von, bis))
        return b"ton"

    def weiter(self, sekunden: float) -> None:
        self.pegel += [(self.jetzt_s + i / 10, -20.0) for i in range(int(sekunden * 10))]
        self.jetzt_s += sekunden


class Dienst:
    def __init__(self, sprache: str = "en") -> None:
        self.anfragen: list[httpx.Request] = []
        self.sprache, self.stoerung = sprache, False

    def leitstelle(self) -> Leitstelle:
        def antwort(r: httpx.Request) -> httpx.Response:
            self.anfragen.append(r)
            if self.stoerung:
                return httpx.Response(503, json={"error": {"code": "halt", "message": "Halt"}})
            if r.url.path.endswith("/stt"):
                return httpx.Response(200, json={"language": self.sprache, "segments": [
                    {"start": 0, "end": 9, "text": "This is a rather long first sentence which keeps going for quite a while so that it fills a paragraph"},
                    {"start": 9, "end": 15, "text": "and here it ends. A second one follows right away, and it is complete."}]})
            return httpx.Response(200, json={"choices": [{"message": {"content": "Das ist die Übersetzung."}}]})
        return Leitstelle("https://ls.test", "ls_x", "RadioHub", client=httpx.AsyncClient(transport=httpx.MockTransport(antwort)))

    def zahl(self, ende: str) -> int:
        return sum(r.url.path.endswith(ende) for r in self.anfragen)


@pytest.fixture
def bau(monkeypatch):
    monkeypatch.setattr(m, "TAKT_S", 0.01)
    monkeypatch.setattr(m, "NACH_FEHLER_S", 0.01)

    def los(dienst: Dienst) -> m.Mitleser:
        ls = dienst.leitstelle()
        return m.Mitleser(leitstelle=lambda: ls, modell=lambda: "gross", ziel_name=lambda k: "Deutsch")
    return los


async def bis_(bedingung, sekunden: float = 3.0) -> None:
    for _ in range(int(sekunden * 100)):
        if bedingung():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("kam nicht")


async def test_steigt_im_puffer_ein_und_uebersetzt(bau):
    d, e = Dienst(), Empfang()
    x = bau(d)
    await x.starten(e, m.Wahl(sprache="en", ziel="de", uebersetzen=True))
    await bis_(lambda: x.stand(0).absaetze and x.stand(0).absaetze[0].uebersetzung)
    assert e.gelesen[0][0] == 10.0, "90 Sekunden zurück"
    st = x.stand(0)
    assert st.absaetze[0].text.startswith("This is") and st.absaetze[0].uebersetzung == "Das ist die Übersetzung."
    assert st.laeuft and st.sprache == "en" and x.fremd
    hoer = next(r for r in d.anfragen if r.url.path.endswith("/stt"))
    assert b'name="language"\r\n\r\nen' in hoer.content and hoer.headers["x-leitstelle-halten"] == str(m.HALTEN_S)
    neu = x.stand(st.fassung)
    e.weiter(40)
    await bis_(lambda: len(x.stand(0).absaetze) > len(st.absaetze))
    assert all(a.nr > st.absaetze[-1].nr for a in x.stand(st.fassung).absaetze) or neu.absaetze == []
    await x.beenden()


async def test_eigene_sprache_wird_nicht_uebersetzt(bau):
    d, e = Dienst("de"), Empfang()
    x = bau(d)
    await x.starten(e, m.Wahl(sprache="de", ziel="de", uebersetzen=True))
    await bis_(lambda: len(x.stand(0).absaetze) >= 2)
    await asyncio.sleep(0.05)
    assert d.zahl("/completions") == 0 and not x.fremd
    await x.beenden()


async def test_ohne_label_wird_die_sprache_erkannt_und_spaeter_uebersetzt(bau):
    d, e = Dienst("fr"), Empfang()
    x = bau(d)
    await x.starten(e, m.Wahl(sprache="", ziel="de", uebersetzen=False))
    await bis_(lambda: x.stand(0).absaetze)
    assert x.stand(0).sprache == "fr" and x.fremd and d.zahl("/completions") == 0
    x.stellen(True)
    await bis_(lambda: any(a.uebersetzung for a in x.stand(0).absaetze))
    await x.beenden()


async def test_aus_heisst_aus(bau):
    d, e = Dienst(), Empfang()
    x = bau(d)
    await x.starten(e, m.Wahl(sprache="en"))
    await bis_(lambda: x.stand(0).absaetze)
    await x.beenden()
    n = len(d.anfragen)
    e.weiter(200)
    await asyncio.sleep(0.1)
    assert len(d.anfragen) == n and not x.laeuft and x.stand(0).zustand == "aus"
    assert x.stand(0).absaetze, "der Text bleibt stehen"


async def test_hoert_auf_wenn_niemand_liest_oder_das_radio_endet(bau):
    d, e = Dienst(), Empfang()
    x = bau(d)
    jetzt = [0.0]
    x.uhr = lambda: jetzt[0]
    await x.starten(e, m.Wahl(sprache="en"))
    jetzt[0] = m.LESER_WEG_S + 1
    await bis_(lambda: not x.laeuft)
    assert x._grund == "niemand liest"
    await x.starten(e, m.Wahl(sprache="en"))
    e.beendet = True
    await bis_(lambda: not x.laeuft)


async def test_stoerung_wird_gezeigt_und_geht_weiter(bau):
    d, e = Dienst(), Empfang()
    d.stoerung = True
    x = bau(d)
    await x.starten(e, m.Wahl(sprache="en"))
    await bis_(lambda: x.stand(0).zustand == "gestoert")
    assert x.stand(0).grund == "Halt"
    d.stoerung = False
    await bis_(lambda: x.stand(0).absaetze)
    await x.beenden()


async def test_werbung_wird_nicht_mitgeschrieben(bau):
    d, e = Dienst(), Empfang()
    e.werbung.stellen.append(Werbestelle(von=9.5, von_aus="angabe", bis=40.0, bis_aus="dauer", format="adw", kennung="1"))
    x = bau(d)
    await x.starten(e, m.Wahl(sprache="en"))
    await bis_(lambda: e.gelesen)
    assert e.gelesen[0][0] == 40.0
    await x.beenden()


def test_wege(client, anonym):
    assert anonym.get("/api/mitlesen").status_code == 401
    assert client.get("/api/mitlesen/kann").json() == {"eingerichtet": False}
    assert client.post("/api/mitlesen", json={"uuid": "x"}).status_code == 503
    assert client.post("/api/mitlesen", json={"uuid": "x", "sprache": "Deutsch"}).status_code == 422
    assert client.get("/api/mitlesen").json()["laeuft"] is False
    assert client.delete("/api/mitlesen").json()["zustand"] == "aus"
