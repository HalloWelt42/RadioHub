"""Messmodus (RAD-143): schreibt nur, wenn er an ist, hört an der Grenze auf, und der Bericht nennt das Auffällige."""

import json

import pytest

from app.services import messung as modul
from app.services.messung import Messung, berichten, messung


@pytest.fixture
def an(client, monkeypatch, tmp_path):
    monkeypatch.setattr(modul, "_an", lambda: True)
    monkeypatch.setattr(modul, "_ordner", lambda: tmp_path)
    messung._voll, messung._gesammelt = False, []
    yield tmp_path
    messung._voll, messung._gesammelt = False, []


def test_aus_schreibt_nichts(client, monkeypatch, tmp_path):
    monkeypatch.setattr(modul, "_ordner", lambda: tmp_path)
    monkeypatch.setattr(modul, "_an", lambda: False)
    m = Messung()
    m.merken("ton", anzahl=3)
    m.schreiben()
    assert list(tmp_path.iterdir()) == []
    assert client.get("/api/messung/aktiv").json() == {"aktiv": False}


def test_wege(an, client):
    antwort = client.post("/api/messung", json={"geraet": "Mac", "ereignisse": [
        {"art": "ton", "werte": {"anzahl": 40, "ereignisse": {"seeking": 20, "playing": 20}}}, {"art": "gestockt", "werte": {"dauer_s": 2.5}, "vor_ms": 0},
        {"art": "zustand", "werte": {"medium": "spielt"}}]})
    assert antwort.status_code == 202 and antwort.json() == {"aktiv": True}
    (d,) = client.get("/api/messung").json()["dateien"]
    assert d["ereignisse"] == 3
    b = client.get(f"/api/messung/{d['name']}/bericht").json()
    assert [x["was"] for x in b["auffaellig"]] == ["Ton springt schnell hin und her", "Ton stockt"] and b["arten"]["zustand"] == 1
    zeile = json.loads(client.get(f"/api/messung/{d['name']}").text.splitlines()[0])
    assert zeile["geraet"] == "Mac" and zeile["t"]
    assert client.get("/api/messung/..%2Fradiohub.db").status_code == 404
    assert client.post("/api/messung", json={"geraet": "x", "ereignisse": [{"art": "../x"}]}).status_code == 422
    assert client.delete("/api/messung").json() == {"geloescht": 1}


def test_grenze_der_groesse(an, monkeypatch):
    monkeypatch.setattr(modul, "HOECHSTENS", 50)
    m = Messung()
    for _ in range(3):
        m.merken("angabe", roh="x" * 100)
        m.schreiben()
    assert not m.aktiv and len(list(an.iterdir())) == 1


def test_bericht_zaehlt_grenzen_nach_grund():
    b = berichten([{"t": "1", "art": "grenze", "grund": g} for g in ("pause", "pause", "angabe")] +
                  [{"t": "2", "art": "abgelegt", "dauer_s": 0.4}, {"t": "3", "art": "abgelegt", "fehler": "weg"}, {"t": "4", "art": "strom_weg"}])
    assert b.grenzen == {"pause": 2, "angabe": 1}
    assert [x.was for x in b.auffaellig] == ["Ablegen gescheitert", "Verbindung zum Sender gerissen"]


async def test_feinschnitt_misst_jede_grenze(an, client, monkeypatch, tmp_path):
    from app.services.feinschnitt import Stueck
    from app.services.feinschnitt_lauf import Analyse
    from app.services.laufschnitt import Laufschnitt
    lauf = Laufschnitt("x", lambda *_: None, list, None)
    a = Analyse(dauer=100, wechsel=[(0, "A", False), (31.0, "B", False), (62.0, "C", False)], stillen=[(29.5, 30.0)], pegel=[])
    lauf._messen(a, [Stueck(0, 29.85, "A"), Stueck(29.85, 62.0, "B")], 1000.0)
    messung.schreiben()
    (d,) = an.glob("*.jsonl")
    g = [json.loads(z) for z in d.read_text().splitlines()]
    assert [(x["grund"], x["bei_s"], x["abstand_s"]) for x in g] == [("pause", 1029.85, -1.15), ("angabe", 1062.0, 0.0)]
