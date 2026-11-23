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
    assert not any("x-leitstelle-wichtig" in r.headers for r in d.anfragen), "nur Lesen ist nicht wichtig"
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
    await asyncio.sleep(0.05)
    assert x.laeuft, "vielleicht verbindet der Sender nur neu"
    jetzt[0] += m.NACHFOLGER_S + 1
    await bis_(lambda: not x.laeuft)


async def test_verbindet_der_sender_neu_geht_es_dort_weiter(bau):
    d, alt, neu, gesprochen = Dienst(), Empfang(), Empfang(), []
    x = bau(d)
    x.stimme, x.stimme_da = await _sprecher(gesprochen), lambda: True
    await x.starten(alt, m.Wahl(sprache="en", ziel="de", uebersetzen=True, sprechen=True))
    await bis_(lambda: any(a.ton_s for a in x.stand(0).absaetze))
    vorher = x.stand(0)
    x.nachfolger = lambda uuid: neu if uuid == "u1" else None
    alt.beendet = True
    await bis_(lambda: neu.gelesen)
    assert neu.gelesen[0][0] == 0.0
    await bis_(lambda: len(x.stand(0).absaetze) > len(vorher.absaetze))
    st = x.stand(0)
    assert st.laeuft and st.sprechen and [a.nr for a in st.absaetze] == sorted({a.nr for a in st.absaetze}), "derselbe Text läuft weiter"
    await bis_(lambda: x.stand(0).absaetze[-1].ton_s > 0)
    await x.beenden()


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


# ----- Übersetzerstimme (RAD-130)

async def _sprecher(zeichen: list[str], dauer: float = 0.0):
    async def sprechen(text: str, sprache: str) -> m.Gesprochen:
        zeichen.append(f"{sprache}:{text}")
        await asyncio.sleep(dauer)
        return m.Gesprochen(b"mp3", 12.34)
    return sprechen


async def test_spricht_fertig_uebersetzte_absaetze(bau):
    d, e, gesprochen = Dienst(), Empfang(), []
    x = bau(d)
    x.stimme, x.stimme_da = await _sprecher(gesprochen), lambda: True
    await x.starten(e, m.Wahl(sprache="en", ziel="de"))
    await bis_(lambda: x.stand(0).absaetze)
    assert not gesprochen and x.stand(0).kann_sprechen and not x.stand(0).sprechen
    x.stellen(sprechen=True)                                  # schließt Übersetzen ein und holt den Vorlauf
    await bis_(lambda: any(a.ton_s for a in x.stand(0).absaetze))
    a = next(a for a in x.stand(0).absaetze if a.ton_s)
    assert a.ton_s == 12.3 and x.ton(a.nr) == b"mp3" and gesprochen[0] == "de:Das ist die Übersetzung."
    chats = [r for r in d.anfragen if r.url.path.endswith("/chat/completions")]
    assert chats and all(r.headers.get("x-leitstelle-wichtig") == "ja" for r in chats), "beim Dolmetschen wichtig"
    assert not any("x-leitstelle-wichtig" in r.headers for r in d.anfragen if r.url.path.endswith("/stt"))
    assert x.stand(0).uebersetzen and x.stand(0).sprechen
    x.stellen(uebersetzen=False)
    assert not x.stand(0).sprechen, "ohne Übersetzung gibt es nichts zu sprechen"
    await x.beenden()
    assert x.ton(a.nr) == b"mp3" and x.ton(999) is None


async def test_kommt_es_nicht_nach_bleibt_der_aelteste_stumm(bau, monkeypatch):
    monkeypatch.setattr(m, "SPRECHEN_WARTET", 2)
    d, e, gesprochen = Dienst(), Empfang(), []
    x = bau(d)
    x.stimme, x.stimme_da = await _sprecher(gesprochen, 0.3), lambda: True
    await x.starten(e, m.Wahl(sprache="en", ziel="de", uebersetzen=True, sprechen=True))
    e.weiter(180)
    await bis_(lambda: sum(bool(a.uebersetzung) for a in x.stand(0).absaetze) >= 6)
    await bis_(lambda: x._zu_sprechen.empty() and sum(bool(a.ton_s) for a in x.stand(0).absaetze) == len(gesprochen))
    stumm = [a.nr for a in x.stand(0).absaetze if a.uebersetzung and not a.ton_s]
    assert stumm and max(a.nr for a in x.stand(0).absaetze if a.ton_s) > min(stumm)
    await x.beenden()


async def test_ohne_stimme_wird_gesagt_warum(bau):
    d, e = Dienst(), Empfang()
    x = bau(d)

    async def nein(text: str, sprache: str) -> m.Gesprochen:
        raise m.StimmeFehler("Vertonung antwortet 403", True)
    x.stimme, x.stimme_da = nein, lambda: True
    await x.starten(e, m.Wahl(sprache="en", ziel="de", uebersetzen=True, sprechen=True))
    await bis_(lambda: not x.stand(0).sprechen)
    assert "403" in x.stand(0).grund and x.laeuft, "gelesen wird weiter"
    await x.beenden()


async def test_stimme_der_vertonung(monkeypatch):
    from app.services import uebersetzerstimme as u
    from appkern.verbund import VerbundFehler
    gesehen: list[tuple[str, str, dict]] = []

    async def unveraendert(wav: bytes) -> bytes:
        return wav
    monkeypatch.setattr(u, "kuerzen", unveraendert)
    einst = SimpleNamespace(vertonung_adresse="https://vertonung.test/", uebersetzerstimme="", zeitstimme="katalog:sohee", zeitstimme_tempo=1.1,
                            kellerwolke_schluessel=SimpleNamespace(get_secret_value=lambda: "kw_x"))
    monkeypatch.setattr(u, "einstellungen_stand", lambda: einst)

    class Verbund:
        status = 200

        async def anfrage(self, methode, adresse, pfad, *, timeout, json):
            gesehen.append((adresse, pfad, json))
            if self.status != 200:
                raise VerbundFehler("nein", self.status or None)
            return httpx.Response(200, content=b"wav", headers={"X-Dauer": "7.5"})
    v = Verbund()
    assert u.eingerichtet()
    g = await u.sprechen(v, "Guten Abend.", "de")
    assert (g.ton, g.dauer_s) == (b"wav", 7.5) and gesehen[0][:2] == ("https://vertonung.test", "/api/v1/sprechen")
    assert gesehen[0][2]["stimme"] == {"art": "katalog", "name": "sohee"} and gesehen[0][2]["tempo"] == 1.1
    einst.uebersetzerstimme = "katalog:vivian"
    await u.sprechen(v, "x", "de")
    assert gesehen[-1][2]["stimme"]["name"] == "vivian", "die eigene Stimme geht der Zeitstimme vor"
    for v.status, dauerhaft in ((403, True), (422, True), (429, False), (503, False), (0, False)):
        with pytest.raises(u.StimmeFehler) as f:
            await u.sprechen(v, "x", "de")
        assert f.value.dauerhaft is dauerhaft
    einst.vertonung_adresse = ""
    assert not u.eingerichtet()
    with pytest.raises(u.StimmeFehler, match="fehlt"):
        await u.sprechen(v, "x", "de")


async def test_beim_sprechen_wird_knapp_gedolmetscht(bau):
    d, e = Dienst(), Empfang()
    x = bau(d)
    x.stimme, x.stimme_da = await _sprecher([]), lambda: True
    await x.starten(e, m.Wahl(sprache="en", ziel="de", uebersetzen=True))
    await bis_(lambda: d.zahl("/completions") >= 1)
    anweisung = lambda: json.loads(next(r for r in reversed(d.anfragen) if r.url.path.endswith("/completions")).content)["messages"][0]["content"]
    assert "vorgelesen" not in anweisung()
    x.stellen(sprechen=True)
    e.weiter(40)
    n = d.zahl("/completions")
    await bis_(lambda: d.zahl("/completions") > n)
    assert "vorgelesen" in anweisung() and "Zeichen" in anweisung()
    await x.beenden()


def test_weg_des_tons(client):
    assert client.get("/api/mitlesen/ton/7").status_code == 404
    assert client.put("/api/mitlesen", json={"sprechen": True}).json()["kann_sprechen"] is False
