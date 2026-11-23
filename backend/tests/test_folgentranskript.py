"""Transkripte der Folgen (RAD-22): Feed mit Zeiten, gehört über die Transkription, Absätze aus ganzen Sätzen, Auftrag wartet weiter."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from appkern.auftraege import AuftragFehler

from app import ablage as ablage_paket
from app.ablage import Anfragestand, SpeicherAblage
from app.services import folgentranskript as ft

PFAD = "Podcasts/Abo/2026-11-23 Folge.mp3"


@pytest.fixture
def speicher(monkeypatch):
    s = SpeicherAblage()
    monkeypatch.setattr(ablage_paket, "_aktuell", s)
    monkeypatch.setattr(ft, "TAKT_S", 0.01)
    monkeypatch.setattr(ft.Folgentranskripte, "_text_merken", staticmethod(lambda *_: None))
    return s


def test_untertitel_vtt_und_srt():
    vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.500\n<v Anna>Guten Tag.\n\n01:00:00.000 --> 01:00:02.000\nZweite\nZeile.\n"
    a, b = ft.aus_untertiteln(vtt)
    assert (a.start, a.ende, a.text, a.sprecher) == (1.0, 3.5, "Guten Tag.", "Anna") and (b.start, b.text) == (3600.0, "Zweite Zeile.")
    assert ft.aus_untertiteln("1\n00:00:01,200 --> 00:00:02,000\nHallo\n")[0].start == 1.2
    assert ft.aus_untertiteln("<html>kein Transkript</html>") == []


def test_json_der_transkription_und_der_feeds():
    t = {"sprecher": [{"kennung": "s1", "name": "Anna"}], "segmente": [{"start": 0, "ende": 2, "text": " Hallo. ", "sprecher": "s1"}, {"start": 2, "ende": 3, "text": ""}]}
    (s,) = ft.aus_json(t)
    assert (s.text, s.sprecher, s.ende) == ("Hallo.", "Anna", 2.0)
    assert ft.aus_json({"segments": [{"startTime": 1.5, "endTime": 2, "body": "Hi", "speaker": "Bob"}]})[0].sprecher == "Bob"


def test_absaetze():
    seg = lambda v, b, t, s="": ft.Segment(start=v, ende=b, text=t, sprecher=s)  # noqa: E731
    lang = "x" * ft.ABSATZ_ZEICHEN + "."
    assert [a.text for a in ft.absaetze([seg(0, 1, "Ein Satz"), seg(1, 2, "geht weiter."), seg(2, 3, "Noch einer.")])] == ["Ein Satz geht weiter. Noch einer."]
    assert len(ft.absaetze([seg(0, 1, lang), seg(1, 2, "Neu.")])) == 2, "voll"
    assert len(ft.absaetze([seg(0, 1, "Ende."), seg(9, 10, "Nach der Pause.")])) == 2
    assert len(ft.absaetze([seg(0, 1, "mitten im"), seg(9, 10, "Satz.")])) == 1, "nie mitten im Satz"
    a = ft.absaetze([seg(0, 1, "A", "Anna"), seg(1, 2, "B", "Bob")])
    assert [(x.nr, x.sprecher, x.von, x.bis) for x in a] == [(0, "Anna", 0, 1), (1, "Bob", 1, 2)]


async def test_feed_und_gehoert(speicher):
    x = ft.Folgentranskripte()
    folge = {"id": 1, "is_downloaded": 0, "local_path": None, "transcript_url": "https://feed.test/1.vtt"}
    assert await x.lesen({**folge, "transcript_url": ""}) is None
    assert await x.lesen(folge) is None, "der Feed antwortet nicht"
    gerufen = []

    async def abruf(adresse):
        gerufen.append(adresse)
        return "WEBVTT\n\n00:01.000 --> 00:02.000\nHallo.\n", "text/vtt"
    x.abruf = abruf
    t = await x.lesen(folge)
    assert t and t.herkunft == "feed" and t.absaetze[0].text == "Hallo." and await x.lesen(folge) and len(gerufen) == 1
    await speicher.schreiben(PFAD, b"ton")
    await speicher.begleiten(PFAD, "transkript", ".transkript.json", json.dumps({"sprache": "de", "segmente": [{"start": 0, "ende": 1, "text": "Gehört."}]}).encode(), "")
    t = await x.lesen({**folge, "is_downloaded": 1, "local_path": PFAD})
    assert t and t.herkunft == "gehoert" and t.sprache == "de", "gehört geht vor"


class Kontext:
    def __init__(self, folge_id=1, zwischenstand=None):
        self.eingabe, self.zwischenstand, self.schritte = ft.Eingabe(folge_id=folge_id), dict(zwischenstand or {}), []

    async def pruefen(self): ...
    async def fortschritt(self, anteil, schritt="", phase=None): self.schritte.append((anteil, schritt, phase))
    async def merken(self, **w): self.zwischenstand.update(w)


def bau(speicher):
    x = ft.Folgentranskripte()

    async def folge(i):
        return {"id": i} if i == 1 else None

    async def speichern(_i):
        await speicher.schreiben(PFAD, b"ton")
        return {"success": True, "path": PFAD}
    x.folge, x.speichern = folge, speichern
    return x


async def test_auftrag_speichert_gibt_weiter_und_wartet(speicher, monkeypatch):
    monkeypatch.setattr(ft, "einstellungen_stand", lambda: type("E", (), {"transkription_app": "Transkription"})())
    x, k = bau(speicher), Kontext()
    lauf = asyncio.create_task(x._transkribieren(k))
    await asyncio.sleep(0.03)
    assert speicher.anfragen["a1"] == (PFAD, "Transkription", "transkribieren", {"sprache": "auto"})
    speicher.anfragestaende["a1"] = Anfragestand("laeuft", 0.4, "Abschnitt 2 von 5")
    await asyncio.sleep(0.03)
    assert (0.4, "Abschnitt 2 von 5", None) in k.schritte
    await speicher.begleiten(PFAD, "transkript", ".transkript.json", json.dumps({"segmente": [{"start": 0, "ende": 1, "text": "Gehört."}]}).encode(), "")
    speicher.anfragestaende["a1"] = Anfragestand("fertig", 1.0)
    assert (await lauf).absaetze == 1
    wieder = Kontext(zwischenstand={"anfrage": "a1"})             # nach einem Neustart: dieselbe Anfrage, keine zweite
    assert (await x._transkribieren(wieder)).absaetze == 1 and len(speicher.anfragen) == 1


async def test_auftrag_nennt_den_grund(speicher, monkeypatch):
    monkeypatch.setattr(ft, "einstellungen_stand", lambda: type("E", (), {"transkription_app": "Transkription"})())
    x = bau(speicher)
    with pytest.raises(AuftragFehler, match="gibt es nicht mehr"):
        await x._transkribieren(Kontext(folge_id=2))
    k = Kontext()
    lauf = asyncio.create_task(x._transkribieren(k))
    await asyncio.sleep(0.03)
    speicher.anfragestaende["a1"] = Anfragestand("fehler", None, "Hördienst fehlt")
    with pytest.raises(AuftragFehler, match="Hördienst fehlt"):
        await lauf
    assert "anfrage" not in k.zwischenstand, "wiederholen fragt neu an"

    async def nicht(_i):
        return {"success": False, "error": "HTTP 404"}
    x.speichern = nicht
    with pytest.raises(AuftragFehler, match="HTTP 404"):
        await x._transkribieren(Kontext())


async def test_wege(client):
    r = client.get("/api/podcasts/episodes/999999/transkript")
    assert r.status_code == 404
