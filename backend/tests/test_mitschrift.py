"""Ablage beim Mitlesen (RAD-131): Ton, Stimme und Transkript nebeneinander, Zeiten auf die Datei, nichts geht verloren."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytest

from app import ablage as ablage_paket
from app.ablage import KeineAblage, SpeicherAblage
from app.services import mitlesen as m
from app.services import mitschrift as ms
from app.services.uebersetzerstimme import Gesprochen
from tests.test_mitlesen import Dienst, Empfang, bau, bis_  # noqa: F401

BEGINN = datetime(2026, 11, 23, 20, 25, 0)
STAMM = "Mitlesen/Probe/2026-11-23 20-25-00"


@pytest.fixture
def speicher(monkeypatch):
    s = SpeicherAblage()
    monkeypatch.setattr(ablage_paket, "_aktuell", s)

    async def ohne_kopf(datei: Path) -> Path:
        return datei
    monkeypatch.setattr(ms, "_mit_kopf", ohne_kopf)
    return s


def schriften(tmp_path: Path) -> tuple[ms.Mitschriften, list[tuple[str, str]]]:
    gemeldet: list[tuple[str, str]] = []

    async def melden(text: str, stufe: str) -> None:
        gemeldet.append((text, stufe))
    return ms.Mitschriften(lambda: tmp_path, melden), gemeldet


async def fertig(s: ms.Mitschriften, x: ms.Mitschrift) -> None:
    s.fertig(x)
    await asyncio.gather(*s._aufgaben)


def gefuellt(s: ms.Mitschriften) -> ms.Mitschrift:
    x = s.beginnen("Probe", "u1", ".mp3", "de", BEGINN)
    x.ton(b"aaa", 1000.0, 1020.0)
    x.ton(b"bbb", 1050.0, 1070.0)                      # dazwischen lag übersprungene Werbung
    x.absatz(1, 1002.0, 1015.0, "2026-11-23T20:25:02+01:00", "Uno.")
    x.absatz(2, 1055.0, 1069.0, "2026-11-23T20:25:55+01:00", "Due.")
    x.uebersetzt(1, "Eins.")
    x.gesprochen(1, b"s1", 4.0)
    x.uebersetzt(2, "Zwei.")
    x.gesprochen(2, b"s2", 5.0)
    return x


async def test_ton_mit_stimme_und_transkript_daneben(speicher, tmp_path):
    s, gemeldet = schriften(tmp_path)
    await fertig(s, gefuellt(s))
    assert sorted(speicher.dateien) == [f"{STAMM}.mp3", f"{STAMM}.sprache.mp3", f"{STAMM}.transkript.json"]
    assert speicher.dateien[f"{STAMM}.mp3"] == b"aaabbb" and speicher.dateien[f"{STAMM}.sprache.mp3"] == b"s1s2"
    t = json.loads(speicher.dateien[f"{STAMM}.transkript.json"])
    assert (t["format"], t["dauer_s"], t["uebersetzt_in"]) == ("transkript/1", 40.0, "de")
    eins, zwei = t["segmente"]
    assert (eins["start"], eins["ende"], eins["text"], eins["uebersetzung"], eins["stimme"]) == (2.0, 15.0, "Uno.", "Eins.", {"start": 0.0, "ende": 4.0})
    assert (zwei["start"], zwei["ende"], zwei["stimme"]) == (25.0, 39.0, {"start": 4.0, "ende": 9.0})
    assert list(tmp_path.iterdir()) == [] and gemeldet == [(f"abgelegt: {STAMM}.mp3", "info")]


async def test_ohne_stimme_und_ohne_text(speicher, tmp_path):
    s, _ = schriften(tmp_path)
    x = s.beginnen("Probe", "u1", ".aac", "de", BEGINN)
    x.ton(b"aaa", 0.0, 20.0)
    await fertig(s, x)
    assert speicher.dateien == {} and list(tmp_path.iterdir()) == [], "nichts gehört, nichts abgelegt"
    x = s.beginnen("Probe", "u1", ".aac", "de", BEGINN)
    x.ton(b"aaa", 0.0, 20.0)
    x.absatz(1, 1.0, 9.0, "z", "Nur Text.")
    await fertig(s, x)
    assert sorted(speicher.dateien) == [f"{STAMM}.aac", f"{STAMM}.transkript.json"]


async def test_fehlende_ablage_wird_nachgeholt_und_laufendes_bleibt(speicher, tmp_path, monkeypatch):
    s, gemeldet = schriften(tmp_path)
    laufend = gefuellt(s)
    laufend.merken()
    monkeypatch.setattr(ablage_paket, "_aktuell", KeineAblage("fehlt"))
    await fertig(s, gefuellt(s))
    assert len(list(tmp_path.iterdir())) == 2 and gemeldet[-1][1] == "warnung"
    monkeypatch.setattr(ablage_paket, "_aktuell", speicher)
    await s.nachholen()
    assert f"{STAMM}.mp3" in speicher.dateien and list(tmp_path.iterdir()) == [laufend.ordner]
    neu, _ = schriften(tmp_path)                       # nach einem Neustart läuft nichts mehr: auch das wird abgelegt
    await neu.nachholen()
    assert f"{STAMM} (2).mp3" in speicher.dateien and list(tmp_path.iterdir()) == []


async def test_zweiter_versuch_schreibt_dieselben_dateien(speicher, tmp_path, monkeypatch):
    s, _ = schriften(tmp_path)
    echt, mal = SpeicherAblage.begleiten, []

    async def bricht(self, *a):
        mal.append(1)
        if len(mal) == 1:
            raise OSError("weg")
        return await echt(self, *a)
    monkeypatch.setattr(SpeicherAblage, "begleiten", bricht)
    await fertig(s, gefuellt(s))
    await s.nachholen()
    assert sorted(speicher.dateien) == [f"{STAMM}.mp3", f"{STAMM}.sprache.mp3", f"{STAMM}.transkript.json"]


async def test_mitlesen_legt_am_ende_ab(bau, speicher, tmp_path):  # noqa: F811
    s, _ = schriften(tmp_path)
    x, e = bau(Dienst()), Empfang()
    x.mitschriften = lambda: s

    async def stimme(_text: str, _sprache: str) -> Gesprochen:
        return Gesprochen(b"stimme", 3.0)
    x.stimme, x.stimme_da = stimme, lambda: True
    await x.starten(e, m.Wahl(sprache="en", ziel="de"))
    x.stellen(sprechen=True)
    await bis_(lambda: any(a.ton_s for a in x.stand(0).absaetze))
    assert x.stand(0).ablegen
    await x.beenden()
    await bis_(lambda: len(speicher.dateien) == 3)
    assert not x.stand(0).ablegen and all(p.startswith("Mitlesen/Probe/") for p in speicher.dateien)
    t = json.loads(next(v for p, v in speicher.dateien.items() if p.endswith(".json")))
    g = next(z for z in t["segmente"] if "stimme" in z)
    assert t["sprache"] == "en" and g["uebersetzung"] == "Das ist die Übersetzung." and g["stimme"] == {"start": 0.0, "ende": 3.0}
    assert any(v.startswith(b"ton") for p, v in speicher.dateien.items() if p.endswith(".mp3") and ".sprache" not in p)
