"""RAD-7: Senderquelle über /api/radio: Aufbereitung, Abfrage mit Seitenzeiger und Facetten, Varianten, lebende Regeln
mit Vorschau, Folgen und Rückgängig, Favoriten als Ausnahme, Einzelsperren und Freigaben, ausgeblendete Sender mit
Grund, Werbung gewichtet, Abgleich als Auftrag mit nachgestelltem Senderverzeichnis (Ausweichserver, Verschwundene)."""

from __future__ import annotations

import json
import time
import uuid as uuid_modul

import httpx
import pytest

import conftest
from app.database import db_session
from app.services.senderquelle import abgleich, dienst, werbung

PRAEFIX = "rad7-"
NAME = "Rad7Probe"


def _sender(name: str, *, sprache: str = "german", tags: str = "", land: str = "DE", stimmen: int = 10,
            codec: str = "MP3", bitrate: int = 128, url: str | None = None) -> str:
    kennung = PRAEFIX + uuid_modul.uuid4().hex
    with db_session() as conn:
        conn.execute(
            "INSERT INTO stations (uuid, name, url, url_resolved, language, tags, votes, countrycode, country, codec, "
            "bitrate, lastcheckok) VALUES (?, ?, ?, '', ?, ?, ?, ?, 'Probeland', ?, ?, 1)",
            (kennung, f"{NAME} {name}", url or f"https://example.invalid/{kennung}", sprache, tags, stimmen, land, codec,
             bitrate))
    return kennung


def _favorit(kennung: str) -> None:
    with db_session() as conn:
        conn.execute("INSERT INTO favorites (uuid, name, url) VALUES (?, 'f', 'https://example.invalid')", (kennung,))


@pytest.fixture
def radio(client):
    yield client
    with db_session() as conn:
        for tabelle, spalte in (("stations", "uuid"), ("favorites", "uuid"), ("sender_sperre", "uuid"),
                                ("sender_freigabe", "uuid"), ("station_tags", "station_uuid"),
                                ("station_ad_status", "station_uuid"), ("blocklist", "uuid")):
            conn.execute(f"DELETE FROM {tabelle} WHERE {spalte} LIKE ?", (PRAEFIX + "%",))
        conn.execute("DELETE FROM regel WHERE herkunft = 'nutzer'")
    client.portal.call(dienst.aufbereiten)


def _aufbereiten(c) -> None:
    c.portal.call(dienst.aufbereiten)


def _abfrage(c, **filter) -> dict:
    antwort = c.post("/api/radio/abfrage", json={"suche": NAME, **filter})
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def _namen(ergebnis: dict) -> list[str]:
    return [e["name"].removeprefix(NAME + " ") for e in ergebnis["eintraege"]]


def test_minus_in_der_suche_schliesst_aus(radio):
    """Ein Wort mit Minus lässt jeden Sender weg, der es in Name, Genre oder Tag hat (Nutzer 20.11.2026)."""
    _sender("Jazz Werbefrei", tags="jazz")
    _sender("Jazz Shop", tags="jazz,shopping")
    _sender("Pop Werbung", tags="pop")
    _sender("Hit", tags="pop")
    _aufbereiten(radio)
    assert sorted(_namen(_abfrage(radio))) == ["Hit", "Jazz Shop", "Jazz Werbefrei", "Pop Werbung"]
    assert sorted(_namen(_abfrage(radio, suche=f"{NAME} -shopping"))) == ["Hit", "Jazz Werbefrei", "Pop Werbung"]   # Tag
    assert sorted(_namen(_abfrage(radio, suche=f"{NAME} -werbung -shop"))) == ["Hit", "Jazz Werbefrei"]           # Name
    assert sorted(_namen(_abfrage(radio, suche=f"{NAME} -hi"))) == ["Jazz Shop", "Jazz Werbefrei", "Pop Werbung"]  # kurz: Name
    assert sorted(_namen(_abfrage(radio, suche=f"{NAME} -"))) == ["Hit", "Jazz Shop", "Jazz Werbefrei", "Pop Werbung"]


def test_abfrage_mit_filtern_seiten_und_facetten(radio):
    klassik = _sender("Klassik", tags="classical", codec="FLAC", bitrate=0, stimmen=500)
    _sender("Pop", tags="pop,hip hop", stimmen=300)
    _sender("Russisch", sprache="russian", tags="news", land="RU", stimmen=200)
    _sender("Leise", tags="pop", stimmen=5, bitrate=32)
    _favorit(klassik)
    _aufbereiten(radio)

    alle = _abfrage(radio)
    assert alle["gesamt"] == 4 and _namen(alle) == ["Klassik", "Pop", "Russisch", "Leise"]
    erster = alle["eintraege"][0]
    assert (erster["qualitaet"], erster["codec"], erster["favorit"], erster["genres"]) == ("verlustfrei", "FLAC", True,
                                                                                            ["Klassik"])
    assert erster["sprachen"] == [{"schluessel": "de", "name": "Deutsch"}]
    # der Eintrag trägt seine Stream-Adresse: die Oberfläche spielt ihn ohne weitere Abfrage
    assert (erster["adresse"], erster["adresse_aufgeloest"]) == (f"https://example.invalid/{klassik}", "")
    assert _namen(_abfrage(radio, laender=["DE"], genres=["Hip-Hop"])) == ["Pop"]
    assert _namen(_abfrage(radio, nur_favoriten=True, laender=["DE"])) == ["Klassik"]   # Favoriten wirken mit
    assert _namen(_abfrage(radio, qualitaet=["niedrig"])) == ["Leise"]
    assert _namen(_abfrage(radio, sortierung="name")) == ["Klassik", "Leise", "Pop", "Russisch"]

    # Seiten über den Zeiger: lückenlos, ohne Doppel, Gesamtzahl nur auf der ersten Seite
    gesehen, zeiger = [], None
    while True:
        seite = _abfrage(radio, anzahl=1, nach=zeiger)
        gesehen += _namen(seite)
        assert (seite["gesamt"] is None) == (zeiger is not None)
        assert (seite["facetten"] is None) == (zeiger is not None)
        zeiger = seite["weiter"]
        if not zeiger:
            break
    assert gesehen == ["Klassik", "Pop", "Russisch", "Leise"]
    assert radio.post("/api/radio/abfrage", json={"nach": "kaputt"}).status_code == 400

    facetten = alle["facetten"]
    assert {"wert": "Hip-Hop", "name": "Hip-Hop", "anzahl": 1} in facetten["genres"]
    assert {f["wert"]: f["anzahl"] for f in facetten["qualitaet"]}["verlustfrei"] == 1
    assert {f["wert"]: f["anzahl"] for f in facetten["laender"]} == {"DE": 3, "RU": 1}
    # die Gruppe "Länder" zählt ohne ihren eigenen Filter
    assert {f["wert"]: f["anzahl"] for f in _abfrage(radio, laender=["RU"])["facetten"]["laender"]} == {"DE": 3, "RU": 1}


def test_varianten_gebuendelt_mit_bester_vorn(radio):
    gut = _sender("Welle | AAC 256k", codec="AAC", bitrate=256, stimmen=10)
    schwach = _sender("Welle | MP3 64k", codec="MP3", bitrate=64, stimmen=900)
    _aufbereiten(radio)
    liste = _abfrage(radio)
    assert [e["uuid"] for e in liste["eintraege"]] == [gut] and liste["eintraege"][0]["varianten"] == 2
    assert [e["uuid"] for e in radio.get(f"/api/radio/sender/{schwach}/varianten").json()] == [gut, schwach]
    # nach Codec gefiltert zeigt die Liste jede passende Variante
    assert [e["uuid"] for e in _abfrage(radio, codecs=["MP3"])["eintraege"]] == [schwach]
    # ein Favorit ist Vertreter seiner Gruppe
    _favorit(schwach)
    _aufbereiten(radio)
    assert [e["uuid"] for e in _abfrage(radio)["eintraege"]] == [schwach]


def test_regel_mit_vorschau_folgen_und_rueckgaengig(radio):
    russisch = _sender("Russisch", sprache="russian")
    kuerzel = _sender("Kürzel", sprache="ru")              # Code als Schreibweise
    _sender("Deutsch", sprache="german")
    _aufbereiten(radio)

    entwurf = {"art": "sprache", "schluessel": ["ru"]}
    vorschau = radio.post("/api/radio/regeln/vorschau", json=entwurf).json()
    assert (vorschau["betroffen"], vorschau["neu_ausgeblendet"], vorschau["favoriten"]) == (2, 2, 0)
    assert vorschau["titel"] == "Sprache ist Russisch (ru)"
    assert {b["uuid"] for b in vorschau["beispiele"]} == {russisch, kuerzel}
    assert _abfrage(radio)["gesamt"] == 3, "Vorschau ändert nichts"

    angelegt = radio.post("/api/radio/regeln", json=entwurf)
    assert angelegt.status_code == 201
    aenderung = angelegt.json()
    regel = aenderung["regel"]
    assert (aenderung["ausgeblendet"], regel["betroffen"], regel["nur_diese"]) == (2, 2, 2)
    assert _namen(_abfrage(radio)) == ["Deutsch"]
    assert radio.post("/api/radio/regeln", json=entwurf).status_code == 409        # keine doppelte Regel

    grund = radio.get(f"/api/radio/sender/{russisch}/sichtbarkeit").json()
    assert not grund["sichtbar"] and [g["titel"] for g in grund["gruende"]] == ["Sprache ist Russisch (ru)"]
    seite = radio.post("/api/radio/ausgeblendet", json={"suche": NAME, "regel": regel["id"]}).json()
    assert seite["gesamt"] == 2 and all(e["gruende"][0]["regel"] == regel["id"] for e in seite["eintraege"])
    assert any(g["regel"] == regel["id"] and g["anzahl"] >= 2 for g in seite["gruende"])

    aus = radio.patch(f"/api/radio/regeln/{regel['id']}", json={"an": False}).json()
    assert aus["wieder_sichtbar"] == 2 and _abfrage(radio)["gesamt"] == 3
    radio.patch(f"/api/radio/regeln/{regel['id']}", json={"an": True})
    folgen = radio.get(f"/api/radio/regeln/{regel['id']}/folgen").json()
    assert folgen["wieder_sichtbar"] == 2
    assert radio.delete(f"/api/radio/regeln/{regel['id']}").status_code == 428      # erst die Folgen ansehen
    weg = radio.delete(f"/api/radio/regeln/{regel['id']}?bestaetigt=true").json()
    assert weg["wieder_sichtbar"] == 2 and _abfrage(radio)["gesamt"] == 3
    assert radio.delete("/api/radio/regeln/einzelsperren?bestaetigt=true").status_code == 400


def test_lebende_regel_gilt_fuer_neue_sender_und_genaue_eintraege(radio):
    _sender("Alt", tags="tv")
    _aufbereiten(radio)
    regel = radio.post("/api/radio/regeln", json={"art": "tag", "tags": ["TV"]}).json()["regel"]
    _sender("Neu", tags="tv,news")                        # kommt nach der Regel dazu
    _sender("Fernsehturm", tags="tvturm")                 # kein Wortteil
    eintrag = _sender("Eintrag", sprache="ger")
    _sender("Ganz", sprache="german")
    _aufbereiten(radio)
    assert _namen(_abfrage(radio, sortierung="name")) == ["Eintrag", "Fernsehturm", "Ganz"]
    assert radio.get("/api/radio/regeln").json()["regeln"][0]["id"] == regel["id"]
    radio.post("/api/radio/regeln", json={"art": "sprache", "eintraege": ["ger"]})   # genau der Eintrag, nicht "german"
    assert _namen(_abfrage(radio, sortierung="name")) == ["Fernsehturm", "Ganz"]
    assert not radio.get(f"/api/radio/sender/{eintrag}/sichtbarkeit").json()["sichtbar"]


def test_favoriten_bleiben_als_ausnahme_sichtbar(radio):
    favorit = _sender("Favorit", sprache="rad7-sprache", stimmen=1)
    _favorit(favorit)
    _aufbereiten(radio)
    entwurf = {"art": "sprache", "eintraege": ["rad7-sprache"]}
    vorschau = radio.post("/api/radio/regeln/vorschau", json=entwurf).json()
    assert (vorschau["betroffen"], vorschau["favoriten"], vorschau["neu_ausgeblendet"]) == (1, 1, 0)
    radio.post("/api/radio/regeln", json=entwurf)
    eintrag = _abfrage(radio)["eintraege"][0]
    assert eintrag["uuid"] == favorit and [g["titel"] for g in eintrag["ausnahme"]] == ['Sprache ist "rad7-sprache"']
    bestand = radio.get("/api/radio/regeln").json()["bestand"]
    assert bestand["ausnahmen"] >= 1


def test_einzelsperre_und_freigabe_mit_rueckgaengig(radio):
    auge = _sender("Auge", stimmen=50)
    regel_getroffen = _sender("Getroffen", sprache="russian")
    _aufbereiten(radio)
    assert not radio.post("/api/radio/sperren", json={"uuid": auge}).json()["sichtbar"]
    assert _namen(_abfrage(radio)) == ["Getroffen"]
    assert radio.post("/api/radio/regeln/vorschau", json={"art": "sprache", "schluessel": ["ru"]}).json()["betroffen"] == 1
    assert radio.delete(f"/api/radio/sperren/{auge}").json()["sichtbar"]
    radio.post("/api/radio/regeln", json={"art": "sprache", "schluessel": ["ru"]})
    frei = radio.post("/api/radio/freigaben", json={"uuid": regel_getroffen}).json()
    assert frei["sichtbar"] and frei["freigegeben"]
    eintrag = next(e for e in _abfrage(radio)["eintraege"] if e["uuid"] == regel_getroffen)
    assert eintrag["ausnahme"][0]["art"] == "sprache"
    assert not radio.delete(f"/api/radio/freigaben/{regel_getroffen}").json()["sichtbar"]
    assert radio.post("/api/radio/sperren", json={"uuid": "rad7-gibt-es-nicht"}).status_code == 404


def test_kandidaten_mit_zahlen(radio):
    favorit = _sender("Chinesisch", sprache="chinese,mandarin")
    _sender("Kanton", sprache="cantonese")
    _favorit(favorit)
    _aufbereiten(radio)
    kandidaten = radio.get("/api/radio/regeln/kandidaten", params={"art": "sprache", "suche": "chin"}).json()
    nach_code = {k["schluessel"]: k for k in kandidaten}
    assert nach_code["zh"]["name"] == "Chinesisch (Mandarin)" and nach_code["zh"]["favoriten"] >= 1
    assert nach_code["yue"]["anzahl"] >= 1
    genres = radio.get("/api/radio/regeln/kandidaten", params={"art": "genre", "suche": "nach"}).json()
    assert all("nach" in g["name"].lower() for g in genres)


@pytest.mark.parametrize("zeichen, stufe", [
    (["HEADER_SUSPICIOUSLY_SHORT_TTL"], 0),                              # Cache-Kopf allein reicht nicht
    (["HEADER_SUSPICIOUSLY_SHORT_TTL", "HEADER_NO_ICY_NAME"], 1),
    (["URL_AGGREGATOR_RELAY"], 2),
    (["URL_SSAI_DOMAIN", "HEADER_SUSPICIOUSLY_SHORT_TTL"], 3),
])
def test_werbung_gewichtet(zeichen, stufe):
    assert werbung.stufe(entscheidung=None, status="suspect", von_hand=False, gruende=zeichen, markiert=False,
                         widersprochen=False) == stufe


def test_werbeentscheidung_und_eigene_markierung(radio):
    entschieden = _sender("Entschieden")
    markiert = _sender("Markiert")
    verdacht = _sender("Verdacht")
    with db_session() as conn:
        conn.execute("INSERT INTO station_ad_status (station_uuid, block_status, user_action, reasons_json) "
                     "VALUES (?, 'confirmed_ad', 'blocked', '[]')", (entschieden,))
        conn.execute("INSERT INTO station_ad_status (station_uuid, block_status, reasons_json) VALUES (?, 'suspect', ?)",
                     (verdacht, json.dumps([{"reason": "HEADER_SUSPICIOUSLY_SHORT_TTL", "confidence": 0.5}])))
        conn.execute("INSERT INTO station_tags (station_uuid, tag_key, source) VALUES (?, 'werbung', 'user')", (markiert,))
    _aufbereiten(radio)
    radio.post("/api/radio/regeln", json={"art": "werbung", "stufe": "eigene"})
    assert _namen(_abfrage(radio, sortierung="name")) == ["Markiert", "Verdacht"]
    radio.post("/api/radio/regeln", json={"art": "werbung", "stufe": "verdacht"})
    assert _namen(_abfrage(radio)) == ["Verdacht"]
    werbe = {e["uuid"]: e["werbung"] for e in radio.post("/api/radio/abfrage", json={"suche": NAME}).json()["eintraege"]}
    assert werbe[verdacht] == {"stufe": "keine", "entscheidung": None}


# ----- Abgleich mit nachgestelltem Senderverzeichnis -------------------------------------------------------------------

def _datensatz(kennung: str, name: str, **mehr) -> dict:
    return {"stationuuid": kennung, "name": f"{NAME} {name}", "url": f"https://example.invalid/{kennung}",
            "url_resolved": "", "countrycode": "DE", "country": "Germany", "language": "german",
            "languagecodes": "de", "codec": "MP3", "bitrate": 128000, "votes": 7, "lastcheckok": 1,
            "iso_3166_2": "DE-NW", "state": "Nordrhein-Westfalen", "geo_lat": 51.2, "geo_long": 6.8, **mehr}


@pytest.fixture
def verzeichnis(monkeypatch, speicher):
    """App mit nachgestelltem Senderverzeichnis: der erste Server fällt aus, der zweite liefert `liste`."""
    from fastapi.testclient import TestClient
    liste: list[dict] = []
    abrufe: list[str] = []

    def antworten(request: httpx.Request) -> httpx.Response:
        if request.url.host.endswith("verzeichnis.test"):
            abrufe.append(request.url.host)
            if request.url.host.startswith("kaputt"):
                return httpx.Response(503)
            return httpx.Response(200, json=liste)
        return conftest.kellerwolke(request)

    monkeypatch.setattr(abgleich, "server_liste", lambda: ["https://kaputt.verzeichnis.test", "https://gut.verzeichnis.test"])
    with db_session() as conn:      # Sender anderer Prüfungen in der gemeinsamen Datenbank: danach wie vorher
        fremde = [z[0] for z in conn.execute("SELECT uuid FROM stations WHERE verschwunden_am IS NULL AND uuid NOT LIKE ?",
                                             (PRAEFIX + "%",))]
    from app.main import app_bauen
    from app import ort
    app = app_bauen(ort.daten_ordner(), transport=httpx.MockTransport(antworten))
    with TestClient(app, headers={"X-Kellerwolke-Sitzung": conftest.SITZUNG}) as c:
        yield c, liste, abrufe
    with db_session() as conn:
        conn.execute("DELETE FROM stations WHERE uuid LIKE ?", (PRAEFIX + "%",))
        conn.execute("DELETE FROM cache_meta WHERE key = ?", (abgleich.BEGINN_SCHLUESSEL,))
        conn.execute("UPDATE stations SET verschwunden_am = NULL WHERE uuid IN (SELECT value FROM json_each(?))",
                     (json.dumps(fremde),))


def _abgleich(c) -> dict:
    auftrag = c.post("/api/radio/abgleich")
    assert auftrag.status_code == 202, auftrag.text
    for _ in range(200):
        stand = c.get(f"/api/v1/auftraege/{auftrag.json()['id']}").json()
        if stand["zustand"] not in ("wartet", "laeuft"):
            return stand
        time.sleep(0.05)
    raise AssertionError("Abgleich endet nicht")


def test_abgleich_als_auftrag_mit_ausweichserver_und_verschwundenen(verzeichnis, monkeypatch):
    c, liste, abrufe = verzeichnis
    monkeypatch.setattr(abgleich, "MINDESTANTEIL", 0)     # die gemeinsame Datenbank hält Sender anderer Prüfungen
    a, b = PRAEFIX + "a", PRAEFIX + "b"
    liste += [_datensatz(a, "Eins", hls=1, clicktrend=5), _datensatz(b, "Zwei", lastcheckok=0)]
    stand = _abgleich(c)
    assert stand["zustand"] == "fertig", stand
    assert stand["ergebnis"]["geladen"] == 2 and stand["ergebnis"]["server"] == "https://gut.verzeichnis.test"
    assert abrufe[:2] == ["kaputt.verzeichnis.test", "gut.verzeichnis.test"]
    with db_session() as conn:
        zeile = conn.execute("SELECT languagecodes, iso_3166_2, hls, clicktrend, lastcheckok, geo_lat FROM stations "
                             "WHERE uuid = ?", (a,)).fetchone()
    assert tuple(zeile) == ("de", "DE-NW", 1, 5, 1, 51.2)
    eintraege = _abfrage(c)["eintraege"]
    assert [e["uuid"] for e in eintraege] == [a]                         # nicht erreichbare nur auf Wunsch
    assert eintraege[0]["kbps"] == 128                                   # bit/s erkannt
    assert {e["uuid"] for e in _abfrage(c, nur_erreichbar=False)["eintraege"]} == {a, b}

    # verschwunden ist, wer in zwei Abgleichen fehlt; markiert, nie gelöscht
    liste[:] = [_datensatz(a, "Eins")]

    def verschwunden() -> int:
        with db_session() as conn:
            return conn.execute("SELECT verschwunden_am IS NOT NULL FROM stations WHERE uuid = ?", (b,)).fetchone()[0]
    assert _abgleich(c)["zustand"] == "fertig" and verschwunden() == 0
    stand = _abgleich(c)
    assert stand["ergebnis"]["verschwunden"] >= 1 and verschwunden() == 1
    assert {e["uuid"] for e in _abfrage(c, nur_erreichbar=False)["eintraege"]} == {a}
    assert c.get("/api/radio/regeln").json()["bestand"]["verschwunden"] >= 1
    assert c.get("/api/radio/abgleich").json()["zuletzt"]


def test_abgleich_bricht_ab_wenn_das_verzeichnis_fast_leer_ist(verzeichnis):
    c, liste, _ = verzeichnis
    for i in range(4):
        _sender(f"Bestand {i}")
    liste[:] = [_datensatz(PRAEFIX + "einzig", "Einzig")]
    stand = _abgleich(c)
    assert stand["zustand"] == "fehler" and "nichts als verschwunden" in stand["fehler"]
