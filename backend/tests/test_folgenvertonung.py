"""Vertonte Fassungen der Folgen (RAD-26): ein Lauf durch alle Schritte, Neustart, Abbruch, Fehler, Originalstimmen; die Wege zum
Wählen, Abspielen und Löschen."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from appkern.auftraege import AuftragAbgebrochen, AuftragFehler
from appkern.verbund import VerbundFehler

from app import ablage as ablage_paket
from app.ablage import Anfragestand, SpeicherAblage
from app.database import db_session
from app.services import folgentranskript as ft
from app.services import folgenvertonung as fv
from app.services.vertonungsdienst import Auftragsstand, Spurtext, Texte, Textspur

PFAD = "Podcasts/Abo/2026-11-24 Episode.mp3"
ENGLISCH = {"sprache": "en", "segmente": [{"start": 0, "ende": 2, "text": "Hello."}, {"start": 2, "ende": 4, "text": "Bye."}]}


class Dienst:
    """Die Vertonung, nachgestellt"""

    def __init__(self):
        self.abgaben, self.abgebrochen, self.weg = [], [], []
        self.zustand = Auftragsstand(zustand="laeuft", fortschritt=0.3, schritt="Sprechen")
        self.uebersetzt = Textspur(sprache="de", segmente=[Spurtext(start=0, ende=2, text="Hallo.", sprecher="Sprecher"),
                                                            Spurtext(start=2, ende=4, text="Tschüss.", sprecher="Sprecher")])
        self.gehoert: Textspur | None = None

    async def abgeben(self, ton, name, ausgang, sprache, stimme, *, original, segmente):
        self.abgaben.append(SimpleNamespace(inhalt=ton.read_bytes(), name=name, ausgang=ausgang, sprache=sprache, stimme=stimme,
                                            original=original, segmente=segmente))
        return f"v{len(self.abgaben)}"

    async def stand(self, _auftrag):
        if isinstance(self.zustand, Exception):
            raise self.zustand
        return self.zustand

    async def texte(self, _auftrag):
        return Texte(transkript=self.gehoert, uebersetzung=self.uebersetzt)

    async def ton(self, plan_id, ziel):
        ziel.write_bytes(f"ton {plan_id}".encode())

    async def abbrechen(self, auftrag): self.abgebrochen.append(auftrag)
    async def abgeholt(self, auftrag): self.weg.append(auftrag)


class Kontext:
    def __init__(self, stimme="", zwischenstand=None):
        self.eingabe = fv.Eingabe(folge_id=1, sprache="de", stimme=stimme)
        self.zwischenstand, self.schritte, self.halt = dict(zwischenstand or {}), [], False

    async def pruefen(self):
        if self.halt:
            raise AuftragAbgebrochen()

    async def fortschritt(self, anteil, schritt="", phase=None): self.schritte.append((anteil, schritt, phase))
    async def merken(self, **w): self.zwischenstand.update(w)


@pytest.fixture
def umgebung(monkeypatch, tmp_path):
    s = SpeicherAblage()
    einst = SimpleNamespace(transkription_app="Transkription", podcast_stimme="", uebersetzerstimme="katalog:sohee", zeitstimme="")
    monkeypatch.setattr(ablage_paket, "_aktuell", s)
    monkeypatch.setattr(ft, "TAKT_S", 0.01)
    monkeypatch.setattr(fv, "TAKT_S", 0.01)
    monkeypatch.setattr(ft, "einstellungen_stand", lambda: einst)
    monkeypatch.setattr(fv, "einstellungen_stand", lambda: einst)
    monkeypatch.setattr(fv, "get_arbeit_dir", lambda *_: tmp_path)
    monkeypatch.setattr(ft.Folgentranskripte, "_text_merken", staticmethod(lambda *_: None))
    gemerkt: list[tuple[int, fv.Fassung]] = []
    monkeypatch.setattr(fv, "merken", lambda i, f: gemerkt.append((i, f)))
    t = ft.Folgentranskripte()

    async def folge(i):
        return {"id": i, "title": "Episode"}

    async def speichern(_i):
        await s.schreiben(PFAD, b"englisch")
        return {"success": True, "path": PFAD}
    t.folge, t.speichern = folge, speichern
    dienst, v = Dienst(), fv.Folgenvertonung(t)
    v.dienst = lambda: dienst
    return SimpleNamespace(s=s, v=v, t=t, dienst=dienst, gemerkt=gemerkt, einst=einst)


async def _transkript(s, inhalt=ENGLISCH):
    await s.schreiben(PFAD, b"englisch")
    await s.begleiten(PFAD, "transkript", ".transkript.json", json.dumps(inhalt).encode(), "")


async def test_ganzer_weg(umgebung, tmp_path):
    u, k = umgebung, Kontext()
    assert u.v.kann()
    lauf = asyncio.create_task(u.v._vertonen(k))
    await asyncio.sleep(0.03)
    assert u.s.anfragen["a1"][:3] == (PFAD, "Transkription", "transkribieren"), "ohne Transkript wird erst gehört"
    await _transkript(u.s)
    u.s.anfragestaende["a1"] = Anfragestand("fertig", 1.0)
    await asyncio.sleep(0.05)
    (abgabe,) = u.dienst.abgaben
    assert (abgabe.inhalt, abgabe.name, abgabe.ausgang, abgabe.sprache, abgabe.original) == (b"englisch", "Episode", "en", "de", False)
    assert abgabe.stimme == {"art": "katalog", "name": "sohee"} and [x.text for x in abgabe.segmente] == ["Hello.", "Bye."]
    assert (0.3, "Sprechen", None) in k.schritte
    u.dienst.zustand = Auftragsstand(zustand="fertig", ergebnis={"plan_id": "p1"})
    ergebnis = await lauf
    assert ergebnis.pfad == "Podcasts/Abo/2026-11-24 Episode.de.sprache.m4a" and ergebnis.absaetze == 2
    assert u.s.dateien[ergebnis.pfad] == b"ton p1" and u.s.dateien[PFAD] == b"englisch", "das Original bleibt"
    text = json.loads(await u.s.begleiter_lesen(PFAD, "transkript_de"))
    assert (text["format"], text["sprache"], [x["text"] for x in text["segmente"]]) == ("transkript/1", "de", ["Hallo.", "Tschüss."])
    assert [e.name for e in await u.s.begleiter(PFAD)] == [
        "2026-11-24 Episode.de.sprache.m4a", "2026-11-24 Episode.de.transkript.json", "2026-11-24 Episode.transkript.json"]
    assert u.gemerkt == [(1, fv.Fassung(sprache="de", pfad=ergebnis.pfad, stimme="katalog:sohee"))] and u.dienst.weg == ["v1"]
    assert not list(tmp_path.iterdir()), "kein Zwischenstand bleibt liegen"
    folge = {"id": 1, "is_downloaded": 1, "local_path": PFAD}
    assert (await u.t.lesen(folge, "de")).herkunft == "vertont" and (await u.t.lesen(folge)).absaetze[0].text == "Hello. Bye."
    await u.s.loeschen(PFAD)
    assert not u.s.dateien and len(u.s.papierkorb) == 4, "Original, Fassung und beide Transkripte zusammen"


async def test_neustart_verfolgt_denselben_auftrag(umgebung):
    await _transkript(umgebung.s)
    umgebung.dienst.zustand = Auftragsstand(zustand="fertig", ergebnis={"plan_id": "p1"})
    await umgebung.v._vertonen(Kontext(zwischenstand={"vertonung": "v7"}))
    assert not umgebung.dienst.abgaben and umgebung.dienst.weg == ["v7"]


async def test_vertonung_kurz_weg_wartet_weiter(umgebung):
    await _transkript(umgebung.s)
    umgebung.dienst.zustand = VerbundFehler("nicht erreichbar")
    k = Kontext()
    lauf = asyncio.create_task(umgebung.v._vertonen(k))
    await asyncio.sleep(0.05)
    assert not lauf.done() and k.zwischenstand["vertonung"] == "v1"
    umgebung.dienst.zustand = Auftragsstand(zustand="fertig", ergebnis={"plan_id": "p1"})
    assert (await lauf).absaetze == 2


async def test_abbruch_und_fehler(umgebung):
    u = umgebung
    await _transkript(u.s)
    k = Kontext()
    lauf = asyncio.create_task(u.v._vertonen(k))
    await asyncio.sleep(0.03)
    k.halt = True
    with pytest.raises(AuftragAbgebrochen):
        await lauf
    assert u.dienst.abgebrochen == ["v1"] and "vertonung" not in k.zwischenstand

    u.dienst.zustand = Auftragsstand(zustand="fehler", fehler="Keine Stimme\nSpur")
    k = Kontext()
    with pytest.raises(AuftragFehler, match="^Vertonung: Keine Stimme$"):
        await u.v._vertonen(k)
    assert "vertonung" not in k.zwischenstand, "wiederholen fragt neu an"
    u.dienst.zustand = VerbundFehler("Auftrag fehlt", 404)
    with pytest.raises(AuftragFehler, match="Auftrag fehlt"):
        await u.v._vertonen(Kontext())

    await _transkript(u.s, {**ENGLISCH, "sprache": "de"})
    with pytest.raises(AuftragFehler, match="schon in dieser Sprache"):
        await u.v._vertonen(Kontext())
    u.einst.uebersetzerstimme = ""
    assert not u.v.kann()
    with pytest.raises(AuftragFehler, match="Stimme fehlt"):
        await u.v._vertonen(Kontext())


async def test_originalstimmen_hoert_die_vertonung(umgebung):
    u = umgebung
    u.dienst.zustand = Auftragsstand(zustand="fertig", ergebnis={"plan_id": "p1"})
    u.dienst.gehoert = Textspur(sprache="en", segmente=[Spurtext(start=0, ende=2, text="Hello.", sprecher="Anna")])
    await u.v._vertonen(Kontext(stimme=fv.ORIGINAL))
    (abgabe,) = u.dienst.abgaben
    assert abgabe.original and abgabe.segmente is None and not u.s.anfragen and abgabe.stimme == {"art": "katalog", "name": "sohee"}
    original = json.loads(await u.s.begleiter_lesen(PFAD, "transkript"))
    assert original["sprache"] == "en" and original["sprecher"] == [{"kennung": "s1", "name": "Anna"}], "auch das Original behält seinen Text"


async def test_dienst_meldet_falsche_adresse():
    import httpx
    from app.services.vertonungsdienst import Vertonungsdienst

    class Verbund:
        async def anfrage(self, *_a, **_k):
            return httpx.Response(301, headers={"location": "https://anders.test/"}, text="")
    with pytest.raises(VerbundFehler, match="Adresse der Vertonung"):
        await Vertonungsdienst(Verbund(), "https://vertonung.test/").stand("v1")


def test_wege(client):
    with db_session() as conn:
        abo = conn.execute("INSERT INTO podcast_subscriptions (feed_url, title) VALUES ('https://feed.test/rad26', 'Abo')").lastrowid
        folge = conn.execute("INSERT INTO podcast_episodes (podcast_id, guid, title, is_downloaded, local_path) VALUES (?, 'rad26', 'Episode', 1, ?)",
                             (abo, PFAD)).lastrowid
    s = ablage_paket.ablage()
    asyncio.run(_transkript(s))
    asyncio.run(s.begleiten(PFAD, "sprache_de", ".de.sprache.m4a", b"deutsch", "audio/mp4"))
    weg = f"/api/podcasts/episodes/{folge}"
    try:
        stand = client.get(f"{weg}/vertonung").json()
        assert (stand["fassungen"], stand["gewaehlt"], stand["ziel"], stand["zielname"]) == ([], "", "de", "Deutsch")
        assert client.put(f"{weg}/fassung", json={"sprache": "de"}).status_code == 404
        fv.merken(folge, fv.Fassung(sprache="de", pfad="Podcasts/Abo/2026-11-24 Episode.de.sprache.m4a", stimme="katalog:sohee"))
        stand = client.get(f"{weg}/vertonung").json()
        assert (stand["gewaehlt"], stand["fassungen"][0]["name"]) == ("de", "Deutsch")
        roh = client.get(weg).json()
        assert (roh["fassung"], roh["fassungen"]) == ("de", "de")
        assert client.get(f"{weg}/play?fassung=de").content == b"deutsch" and client.get(f"{weg}/play").content == b"englisch"
        assert client.get(f"{weg}/play?fassung=fr").status_code == 404 and client.get(f"{weg}/datei?fassung=fr").status_code == 404
        assert client.put(f"{weg}/fassung", json={"sprache": ""}).json()["gewaehlt"] == ""
        dateien = client.get(f"{weg}/dateien").json()["dateien"]
        assert [(d["art"], d["pfad"].rsplit("/", 1)[1]) for d in dateien] == [
            ("folge", "2026-11-24 Episode.mp3"), ("begleiter", "2026-11-24 Episode.de.sprache.m4a"),
            ("begleiter", "2026-11-24 Episode.transkript.json")]
        assert client.delete(f"{weg}/download").status_code == 200
        assert client.get(f"{weg}/vertonung").json()["fassungen"] == [] and client.get(f"{weg}/dateien").json()["dateien"] == []
        assert client.get("/api/podcasts/episodes/999999/vertonung").status_code == 404
    finally:
        with db_session() as conn:
            conn.execute("DELETE FROM podcast_episodes WHERE id = ?", (folge,))
            conn.execute("DELETE FROM podcast_subscriptions WHERE id = ?", (abo,))
