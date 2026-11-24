"""RAD-4: Werkzeug der statischen Senderliste: nur abspielbare Sender, Logos nur über https, Varianten als Gruppe,
Spaltenformat mit Wörterbüchern, Datenbank nur lesend, Verzeichnis seitenweise mit Ausweichserver (ohne Netz)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from app import senderdaten
from app.senderdaten import Verzeichnisdatensatz
from app.services.senderquelle import abgleich
from app.werkzeuge import statische_liste as sl

SPALTEN_DB = ("uuid name url url_resolved favicon country countrycode language tags codec bitrate votes clickcount "
              "homepage lastcheck cached_at last_seen languagecodes iso_3166_2 state geo_lat geo_long hls ssl_error "
              "clicktrend lastcheckok lastcheckoktime lastchangetime has_extended_info verschwunden_am").split()


def _station(uuid: str, name: str, **mehr) -> dict:
    return {"uuid": uuid, "name": name, "url": f"https://strom.test/{uuid}", "url_resolved": f"https://strom.test/{uuid}",
            "favicon": "https://logo.test/a.png", "country": "Germany", "countrycode": "DE", "language": "german,ger",
            "tags": "pop,news,92.4 fm", "codec": "MP3", "bitrate": 128, "votes": 10, "homepage": "https://welle.test",
            "languagecodes": "de", "iso_3166_2": "DE-BE", "state": "Berlin", "hls": 0, "ssl_error": 0, "lastcheckok": 1,
            "verschwunden_am": None, **mehr}


PROBE = [
    _station("a1", "Welle | MP3 128k", votes=50),
    _station("a2", "Welle | AAC 256k", codec="AAC", bitrate=256, votes=5, favicon="http://logo.test/unsicher.png"),
    _station("b1", "Unsicher", url="http://strom.test/b1", url_resolved="http://strom.test/b1"),
    _station("b2", "Aufgelöst sicher", url="http://strom.test/b2", url_resolved="https://strom.test/b2-sicher"),
    _station("c1", "Nicht erreichbar", lastcheckok=0),
    _station("c2", "Zertifikat kaputt", ssl_error=1),
    _station("c3", "Verschwunden", verschwunden_am="2026-11-01T00:00:00+00:00"),
    _station("d1", "Russisch", language="russian", languagecodes="ru", tags="news", countrycode="RU",
             country="Russia", votes=3, url_resolved=""),
]


@pytest.fixture
def probe_db(tmp_path: Path) -> Path:
    pfad = tmp_path / "radiohub.db"
    with sqlite3.connect(pfad) as v:
        v.execute(f"CREATE TABLE stations ({', '.join(SPALTEN_DB)})")
        for s in PROBE:
            werte = {k: s.get(k) for k in SPALTEN_DB}
            v.execute(f"INSERT INTO stations ({', '.join(werte)}) VALUES ({', '.join('?' * len(werte))})", list(werte.values()))
    return pfad


def _lesen(datei: Path) -> tuple[dict, list[dict]]:
    """sender.json mit aufgelösten Wörterbüchern: je Zeile ein Wörterbuch der Spalten."""
    daten = json.loads(datei.read_text(encoding="utf-8"))
    kopf = daten["kopf"]
    zeilen = []
    for roh in daten["zeilen"]:
        zeile = dict(zip(kopf["spalten"], roh, strict=True))
        for spalte, woerterbuch in sl.WOERTERBUCH_SPALTEN.items():
            werte = kopf["woerter"][woerterbuch]
            zeile[spalte] = [werte[n] for n in zeile[spalte]] if isinstance(zeile[spalte], list) else werte[zeile[spalte]]
        zeilen.append(zeile)
    return kopf, zeilen


def test_nur_abspielbare_sender_mit_sicheren_logos(probe_db, tmp_path):
    bericht = sl.erzeugen(tmp_path / "web", probe_db)
    kopf, zeilen = _lesen(Path(bericht.datei))
    nach_uuid = {z["uuid"]: z for z in zeilen}
    assert sorted(nach_uuid) == ["a1", "a2", "b2", "d1"]
    assert (bericht.gelesen, bericht.geschrieben) == (7, 4)            # verschwundene liest es gar nicht erst
    assert nach_uuid["a2"]["logo"] == "" and nach_uuid["a1"]["logo"] == "https://logo.test/a.png"
    # aufgelöste Adresse nur, wenn sie von der Adresse abweicht
    assert (nach_uuid["b2"]["adresse"], nach_uuid["b2"]["adresse_aufgeloest"]) == ("http://strom.test/b2",
                                                                                    "https://strom.test/b2-sicher")
    assert nach_uuid["a1"]["adresse_aufgeloest"] == ""
    assert (kopf["format"], kopf["aufbereitung"], kopf["quelle"], kopf["anzahl"]) == (sl.FORMAT, senderdaten.FASSUNG,
                                                                                      "datenbank", 4)
    assert kopf["spalten"] == list(sl.SPALTEN)


def test_felder_fuer_die_regeln_im_browser(probe_db, tmp_path):
    kopf, zeilen = _lesen(Path(sl.erzeugen(tmp_path, probe_db).datei))
    a1 = next(z for z in zeilen if z["uuid"] == "a1")
    assert a1["sprachen"] == ["de"] and a1["spracheintraege"] == ["german", "ger"]
    assert a1["genres"] == ["Pop", "Nachrichten"] and a1["tags"] == ["pop", "news"]   # Frequenz verworfen
    assert (a1["land"], a1["land_name"], a1["region"], a1["bundesland"]) == ("DE", "Germany", "DE-BE", "Berlin")
    assert (a1["codec"], a1["kbps"], a1["qualitaet"], a1["stimmen"], a1["hls"]) == ("MP3", 128, "mittel", 50, 0)
    assert kopf["sprachnamen"] == {"de": "Deutsch", "ru": "Russisch"}
    assert kopf["eintragscodes"] == {"ger": "de", "german": "de", "russian": "ru"}
    # häufigste Werte zuerst: kleine Nummern
    assert kopf["woerter"]["land"][0] == "DE"


def test_varianten_als_gruppe_ueber_die_zeilennummer(probe_db, tmp_path):
    sl.erzeugen(tmp_path, probe_db)
    daten = json.loads((tmp_path / sl.DATEI).read_text(encoding="utf-8"))
    uuid, gruppe = daten["kopf"]["spalten"].index("uuid"), daten["kopf"]["spalten"].index("gruppe")
    gruppen = {z[uuid]: daten["zeilen"][z[gruppe]][uuid] for z in daten["zeilen"]}
    assert gruppen == {"a1": "a1", "a2": "a1", "b2": "b2", "d1": "d1"}


def test_datenbank_bleibt_unveraendert(probe_db, tmp_path):
    vorher = hashlib.sha256(probe_db.read_bytes()).hexdigest()
    sl.erzeugen(tmp_path, probe_db)
    assert hashlib.sha256(probe_db.read_bytes()).hexdigest() == vorher
    assert not list(probe_db.parent.glob("*.db-*")), "keine Begleitdateien einer Schreibverbindung"
    with pytest.raises(SystemExit):
        sl.erzeugen(tmp_path, tmp_path / "fehlt.db")


def test_verzeichnis_seitenweise_mit_ausweichserver(monkeypatch):
    roh = [{**{k: v for k, v in s.items() if k not in ("uuid", "verschwunden_am")}, "stationuuid": s["uuid"],
            "votes": s["votes"]} for s in PROBE if s["uuid"] != "c3"]
    abrufe: list[tuple[str, int]] = []

    def antworten(request: httpx.Request) -> httpx.Response:
        versatz = int(request.url.params["offset"])
        abrufe.append((request.url.host, versatz))
        if request.url.host.startswith("kaputt"):
            return httpx.Response(503)
        return httpx.Response(200, json=roh[versatz:versatz + abgleich.SEITE] + ([{"name": "ohne uuid"}] if not versatz else []))

    monkeypatch.setattr(abgleich, "SEITE", 3)
    server = ["https://kaputt.verzeichnis.test", "https://gut.verzeichnis.test"]

    async def holen():
        return [d async for d in sl.aus_verzeichnis(httpx.MockTransport(antworten), server)]
    saetze = asyncio.run(holen())
    liste, gelesen = sl.liste_bauen(saetze, "verzeichnis")
    assert gelesen == 7 and liste.kopf.anzahl == 4 and liste.kopf.quelle == "verzeichnis"
    assert abrufe[:2] == [("kaputt.verzeichnis.test", 0), ("gut.verzeichnis.test", 0)]
    assert [v for h, v in abrufe[2:]] == [3, 6], "nach einem Ausfall bleibt es beim Server, der antwortet"


def test_typografische_zeichen_als_escape(tmp_path):
    name = "Welle \u2013 \u201eKlassik\u201c"
    satz = Verzeichnisdatensatz.model_validate({"stationuuid": "t1", "name": name, "url": "https://strom.test/t1",
                                                "lastcheckok": 1})
    datei = sl.schreiben(sl.liste_bauen([satz], "verzeichnis")[0], tmp_path)
    roh = datei.read_text(encoding="utf-8")
    assert "\u2013" not in roh and "\\u2013" in roh
    assert json.loads(roh)["zeilen"][0][1] == name


def test_nachfolger_mit_derselben_adresse_laufen_mit(tmp_path):
    def satz(uuid: str, adresse: str, stimmen: int = 1) -> Verzeichnisdatensatz:
        return Verzeichnisdatensatz.model_validate({"stationuuid": uuid, "name": uuid, "url": adresse, "lastcheckok": 1,
                                                    "votes": stimmen})

    def bauen(*saetze: Verzeichnisdatensatz) -> dict[str, str]:
        vorgaenger = sl.vorgaenger_lesen(tmp_path / sl.DATEI)
        sl.schreiben(sl.liste_bauen(saetze, "verzeichnis", vorgaenger=vorgaenger)[0], tmp_path)
        kopf, zeilen = _lesen(tmp_path / sl.DATEI)
        return {alt: zeilen[zeile]["uuid"] for alt, zeile in kopf["nachfolger"].items()}

    assert bauen(satz("alt", "https://strom.test/eins"), satz("bleibt", "https://strom.test/zwei"),
                 satz("weg", "https://strom.test/drei")) == {}
    assert bauen(satz("neu-klein", "https://strom.test/eins"), satz("neu-gross", "https://strom.test/eins", 9),
                 satz("bleibt", "https://strom.test/zwei")) == {"alt": "neu-gross"}
    # beim nächsten Wechsel zeigt auch die erste Kennung auf den jetzigen Sender
    assert bauen(satz("noch-neuer", "https://strom.test/eins"), satz("bleibt", "https://strom.test/zwei")) == {
        "alt": "noch-neuer", "neu-gross": "noch-neuer", "neu-klein": "noch-neuer"}
