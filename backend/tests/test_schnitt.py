"""Schnitt für Aufnahmen und Dateien der Kellerwolke (RAD-17): Stücke behalten oder verwerfen mit Namen, Schritte mit
Rückgängig (Aufnahme: vorige Fassung im Unterordner Schritte; Datei: Ergebnis daneben, das Original bleibt)."""

import json

from app.services.aufnahmen import aufnahmen
from conftest import ton
from test_aufnahmen import _mit_stuecken


def _ereignisse(antwort) -> list[dict]:
    assert antwort.status_code == 200, antwort.text
    return [json.loads(z[6:]) for z in antwort.text.splitlines() if z.startswith("data: ")]


async def test_aufnahme_schneiden_mit_verworfenem_stueck_und_rueckgaengig(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 2, 4.0)
    vorher = [(s["title"], s["file_path"]) for s in aufnahmen.segmente(sitzung["id"])]
    info = client.get("/api/schnitt/info", params={"art": "sitzung", "kennung": sitzung["id"]}).json()
    assert [s["name"] for s in info["stuecke"]] == ["Titel 1", "Titel 2"] and info["schritte"] == []
    stuecke = [{"von": 0, "bis": 2, "name": "Anfang", "behalten": False}, {"von": 2, "bis": 5, "name": "Mitte"},
               {"von": 5, "bis": 8, "name": "Schluss"}]
    ende = _ereignisse(client.post("/api/schnitt/schneiden", json={"art": "sitzung", "kennung": sitzung["id"], "stuecke": stuecke}))[-1]
    assert ende == {"type": "done", "count": 2}, ende
    neu = aufnahmen.segmente(sitzung["id"])
    assert [s["title"] for s in neu] == ["Mitte", "Schluss"] and all(s["file_path"] in speicher.dateien for s in neu)
    assert neu[0]["start_ms"] == 0 and neu[1]["start_ms"] == neu[0]["end_ms"]          # ohne den Anfang zusammengerückt
    assert abs(aufnahmen.sitzung(sitzung["id"])["duration"] - neu[1]["end_ms"] / 1000) < 0.01
    assert not any(p in speicher.dateien for _, p in vorher)                     # die alten liegen jetzt unter Schritte
    assert any("/Schritte/001/" in p for p in speicher.dateien)
    schritte = client.get("/api/schnitt/info", params={"art": "sitzung", "kennung": sitzung["id"]}).json()["schritte"]
    assert [s["was"] for s in schritte] == ["Geschnitten in 2 Stücke, 1 verworfen"]

    zurueck = client.post("/api/schnitt/rueckgaengig", json={"art": "sitzung", "kennung": sitzung["id"]})
    assert zurueck.status_code == 200 and zurueck.json()["zurueckgenommen"].startswith("Geschnitten")
    assert [(s["title"], s["file_path"]) for s in aufnahmen.segmente(sitzung["id"])] == vorher
    assert all(p in speicher.dateien for _, p in vorher)
    assert not any("/Schritte/" in p for p in speicher.dateien)
    assert client.post("/api/schnitt/rueckgaengig", json={"art": "sitzung", "kennung": sitzung["id"]}).status_code == 409


async def test_datei_der_kellerwolke_ergebnis_daneben_original_bleibt(client, speicher, wolke_speicher, tmp_path):
    original = ton(tmp_path / "Interview.mp3", 6.0)
    await wolke_speicher.ablegen("Interviews/Interview.mp3", original)
    inhalt = wolke_speicher.dateien["Interviews/Interview.mp3"]
    art = {"art": "datei", "kennung": "Interviews/Interview.mp3"}
    info = client.get("/api/schnitt/info", params=art).json()
    assert info["neben"] is True and info["stuecke"][0]["name"] == "Interview" and info["dauer"] > 5
    assert len(client.get("/api/schnitt/wellenform", params={**art, "start": 0, "dauer": 2}).content) > 0
    stuecke = [{"von": 0, "bis": 3, "name": "", "behalten": False}, {"von": 3, "bis": 6, "name": "Interview"}]  # vorgeschlagener Name
    assert _ereignisse(client.post("/api/schnitt/schneiden", json={**art, "stuecke": stuecke}))[-1]["type"] == "done"
    assert wolke_speicher.dateien["Interviews/Interview.mp3"] == inhalt                  # das Original bleibt
    assert "Interviews/Interview (geschnitten).mp3" in wolke_speicher.dateien
    assert client.post("/api/schnitt/rueckgaengig", json=art).status_code == 200
    assert "Interviews/Interview (geschnitten).mp3" in wolke_speicher.papierkorb
    assert client.get("/api/schnitt/info", params={"art": "datei", "kennung": "Interviews/Notiz.txt"}).status_code == 415


async def test_normalisieren_legt_einen_schritt_an(client, speicher, tmp_path):
    sitzung = await _mit_stuecken(tmp_path, 1, 3.0)
    ereignisse = _ereignisse(client.post("/api/schnitt/normalisieren", json={"art": "sitzung", "kennung": sitzung["id"]}))
    assert ereignisse[0]["type"] == "start" and ereignisse[-1] == {"type": "done", "count": 1}, ereignisse
    info = client.get("/api/schnitt/info", params={"art": "sitzung", "kennung": sitzung["id"]}).json()
    assert [s["was"] for s in info["schritte"]] == ["Normalisiert auf -16 LUFS"]
    assert client.post("/api/schnitt/rueckgaengig", json={"art": "sitzung", "kennung": sitzung["id"]}).status_code == 200
    assert len(aufnahmen.segmente(sitzung["id"])) == 1


async def test_liste_der_aufnahmen_seitenweise_mit_suche_und_ordner(client, speicher, tmp_path):
    from test_aufnahmen import _sitzung
    a = _sitzung("Suchfunk Nord")
    _sitzung("Suchfunk Süd")
    seite = client.get("/api/recording/sessions", params={"suche": "Suchfunk", "limit": 1}).json()
    assert seite["gesamt"] == 2 and seite["count"] == 1
    zweite = client.get("/api/recording/sessions", params={"suche": "Suchfunk", "limit": 1, "ab": 1}).json()
    assert {seite["sessions"][0]["id"], zweite["sessions"][0]["id"]} >= {a["id"]}
    nach_name = client.get("/api/recording/sessions", params={"suche": "Suchfunk", "sort": "sender", "absteigend": False}).json()
    assert [s["station_name"] for s in nach_name["sessions"]] == ["Suchfunk Nord", "Suchfunk Süd"]
    assert client.get("/api/recording/sessions", params={"ordner": "x"}).status_code == 422


async def test_schnitt_geht_auch_ohne_titelliste_in_der_ablage(client, speicher, tmp_path):
    from app.database import db_session
    sitzung = await _mit_stuecken(tmp_path, 1)
    with db_session() as conn:
        conn.execute("UPDATE sessions SET meta_file_path = ? WHERE id = ?", ("Aufnahmen/weg/Titelliste.json", sitzung["id"]))
    info = client.get("/api/schnitt/info", params={"art": "sitzung", "kennung": sitzung["id"]})
    assert info.status_code == 200, info.text
    assert info.json()["titelwechsel"] == [] and len(info.json()["stuecke"]) == 1
