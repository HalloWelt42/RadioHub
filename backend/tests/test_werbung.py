"""Werbestellen in Podcast-Folgen (RAD-32): Kapitel nach Werbung, von Hand setzen, verwerfen und zurück, eine neue Suche
ersetzt nur ihre Quelle und bringt Verworfenes nicht zurück, Übersicht in den Listen, Fassung ohne Werbung daneben."""

from __future__ import annotations

import json

from app.database import db_session
from app.services import werbestellen as ws
from app.services.aufnahmen import probe_duration
from conftest import ton
from test_podcasts import _folge


def _ereignisse(antwort) -> list[dict]:
    assert antwort.status_code == 200, antwort.text
    return [json.loads(z[6:]) for z in antwort.text.splitlines() if z.startswith("data: ")]


def test_kapitel_mit_werbung_werden_stellen():
    kapitel = [{"startTime": 0, "title": "Intro"}, {"startTime": 60, "title": "Werbung"}, {"startTime": 120, "title": "Thema"},
               {"startTime": 900, "title": "Sponsored by Werkzeugladen", "endTime": 960}, {"startTime": 1500, "title": "Ad break"}]
    stellen = ws.kapitel_werbung(kapitel, 1600)
    assert [(s.von, s.bis) for s in stellen] == [(60, 120), (900, 960), (1500, 1600)]
    assert ws.kapitel_werbung([{"startTime": 10, "title": "Adresse und Anfahrt"}], 100) == []   # kein Wort "ad"


def test_setzen_verwerfen_und_zurueck(client, speicher):
    folge = _folge("Werkstattfunk", "Hobel einstellen")
    neu = client.post(f"/api/podcasts/episodes/{folge}/werbung", json={"von": 10, "bis": 40, "text": "Spot"})
    assert neu.status_code == 200, neu.text
    stelle = neu.json()
    assert stelle["herkunft"] == "hand" and stelle["verworfen"] is False
    assert client.post(f"/api/podcasts/episodes/{folge}/werbung", json={"von": 10, "bis": 11}).status_code == 400
    assert [s["id"] for s in client.get(f"/api/podcasts/episodes/{folge}/werbung").json()["stellen"]] == [stelle["id"]]
    assert client.patch(f"/api/podcasts/werbung/{stelle['id']}", json={"verworfen": True}).json()["verworfen"] is True
    assert client.get(f"/api/podcasts/episodes/{folge}/werbung").json()["stellen"] == []
    assert client.patch(f"/api/podcasts/werbung/{stelle['id']}", json={"verworfen": False}).status_code == 200
    assert len(client.get(f"/api/podcasts/episodes/{folge}/werbung").json()["stellen"]) == 1


def test_neue_suche_ersetzt_ihre_quelle_und_achtet_verworfene(speicher):
    folge = _folge("Morgenlage", "Der Tag")
    ws.anlegen(folge, ws.Neu(von=500, bis=530), "hand")
    assert ws.ersetzen(folge, "kapitel", [ws.Neu(von=0, bis=30), ws.Neu(von=100, bis=160)]) == 2
    verworfen = next(s for s in ws.stellen(folge) if s.von == 100)
    ws.verwerfen(verworfen.id, True)
    assert ws.ersetzen(folge, "kapitel", [ws.Neu(von=0, bis=30), ws.Neu(von=102, bis=158)]) == 1      # überdeckt die verworfene
    assert sorted((s.von, s.herkunft) for s in ws.stellen(folge)) == [(0, "kapitel"), (500, "hand")]


def test_listen_zeigen_zahl_und_dauer(client, speicher):
    folge = _folge("Sternstunde Physik", "Warum der Himmel nachts dunkel ist")
    ws.anlegen(folge, ws.Neu(von=0, bis=38))
    ws.anlegen(folge, ws.Neu(von=1312, bis=1384))
    with db_session() as conn:
        abo = conn.execute("SELECT podcast_id FROM podcast_episodes WHERE id = ?", (folge,)).fetchone()[0]
    eintrag = next(e for e in client.get(f"/api/podcasts/{abo}/episodes").json()["episodes"] if e["id"] == folge)
    assert eintrag["werbung_anzahl"] == 2 and eintrag["werbung_dauer"] == 110


def test_suche_ueber_kapitel_als_strom(client, speicher, monkeypatch):
    folge = _folge("Küchenkunde", "Brot ohne Kneten")
    with db_session() as conn:
        conn.execute("UPDATE podcast_episodes SET chapters_url = 'https://feed.test/kapitel.json', duration = 600 WHERE id = ?", (folge,))

    async def kapitel(adresse, dauer, client=None):
        assert adresse.endswith("kapitel.json") and dauer == 600
        return [ws.Neu(von=300, bis=345, text='Kapitel "Werbung"')]
    monkeypatch.setattr(ws, "kapitel_lesen", kapitel)
    assert client.get(f"/api/podcasts/episodes/{folge}/werbung").json()["quellen"] == ["kapitel"]
    ende = _ereignisse(client.post(f"/api/podcasts/episodes/{folge}/werbung/suchen"))[-1]
    assert ende == {"type": "done", "gefunden": {"kapitel": 1}}, ende


async def test_fassung_ohne_werbung_liegt_daneben(client, speicher, tmp_path):
    folge = _folge("Hörspielzeit", "Das Haus am Kanal")
    datei = ton(tmp_path / "folge.mp3", 10.0)
    pfad = "Podcasts/Hörspielzeit/2026-10-01 Das Haus am Kanal.mp3"
    await speicher.ablegen(pfad, datei)
    with db_session() as conn:
        conn.execute("UPDATE podcast_episodes SET is_downloaded = 1, local_path = ? WHERE id = ?", (pfad, folge))
    ws.anlegen(folge, ws.Neu(von=2, bis=6))
    ende = _ereignisse(client.post(f"/api/podcasts/episodes/{folge}/ohne-werbung"))[-1]
    assert ende["type"] == "done", ende
    neu = ende["pfad"]
    assert neu == "Podcasts/Hörspielzeit/2026-10-01 Das Haus am Kanal (ohne Werbung).mp3"
    assert pfad in speicher.dateien and neu in speicher.dateien                         # das Original bleibt
    (tmp_path / "ohne.mp3").write_bytes(speicher.dateien[neu])
    assert abs(await probe_duration(tmp_path / "ohne.mp3") - 6.0) < 0.5


def test_abo_schalter(client, speicher):
    folge = _folge("Zahlenzauber", "Das Geburtstagsrätsel")
    with db_session() as conn:
        abo = conn.execute("SELECT podcast_id FROM podcast_episodes WHERE id = ?", (folge,)).fetchone()[0]
    assert client.put(f"/api/podcasts/{abo}/werbung", json={"ueberspringen": False, "pruefen": True}).status_code == 200
    with db_session() as conn:
        r = conn.execute("SELECT werbung_ueberspringen, werbung_pruefen FROM podcast_subscriptions WHERE id = ?", (abo,)).fetchone()
    assert tuple(r) == (0, 1)
    assert client.put(f"/api/podcasts/{abo}/werbung", json={}).status_code == 400


async def test_neue_folgen_pruefen_sucht_ueber_die_kapitel(speicher, monkeypatch):
    from app.services.podcast import podcast_service
    folge = _folge("Morgenlage", "Der Tag: Haushalt")
    with db_session() as conn:
        conn.execute("UPDATE podcast_episodes SET chapters_url = 'https://feed.test/k.json', duration = 1200 WHERE id = ?", (folge,))
        abo = conn.execute("SELECT podcast_id FROM podcast_episodes WHERE id = ?", (folge,)).fetchone()[0]

    async def kapitel(adresse, dauer, client=None):
        return [ws.Neu(von=0, bis=30, text='Kapitel "Sponsor"')]
    monkeypatch.setattr(ws, "kapitel_lesen", kapitel)
    await podcast_service._werbung_pruefen(abo, 1)
    assert [(s.von, s.herkunft) for s in ws.stellen(folge)] == [(0, "kapitel")]
