"""Anmeldung mit dem Konto der Kellerwolke (RAD-6): alle Wege unter /api brauchen sie, frei sind nur die
Gesundheitsprobe und was das Gerüst freigibt (App, Anmeldung). Ton und Bilder, die der Browser ohne eigenen Kopf holt,
kommen mit dem Lesezugang (Keks unter /api)."""

import pytest

from conftest import SITZUNG

GESCHUETZT = ["/api/config", "/api/wecker", "/api/favorites", "/api/hls/status", "/api/recordings/stats",
              "/api/storage/ablage", "/api/datenbank/pruefung", "/api/v1/verbindungen", "/api/v1/einstellungen",
              "/api/v1/protokoll"]


@pytest.mark.parametrize("weg", GESCHUETZT)
def test_ohne_sitzung_401(anonym, weg):
    antwort = anonym.get(weg)
    assert antwort.status_code == 401
    assert antwort.headers["www-authenticate"] == "Kellerwolke-Sitzung"   # nur daran meldet die Oberfläche ab


@pytest.mark.parametrize("weg", GESCHUETZT)
def test_mit_sitzung_ok(client, weg):
    assert client.get(weg).status_code == 200


def test_fremde_sitzung_401(anonym):
    assert anonym.get("/api/config", headers={"X-Kellerwolke-Sitzung": "fremd"}).status_code == 401


def test_frei_ohne_anmeldung(anonym):
    assert anonym.get("/health").json()["status"] == "healthy"
    app = anonym.get("/api/v1/app").json()
    assert app["kennung"] == "radiohub" and not app["einrichtung_noetig"] and app["anmeldung"] == "kellerwolke"
    assert anonym.get("/api/v1/anmeldung").json() == {"angemeldet": False, "konto": None}


def test_anmelden_mit_passwort_gibt_die_sitzung(anonym):
    assert anonym.post("/api/v1/anmeldung", json={"kennung": "probe", "passwort": "falsch"}).status_code == 401
    angemeldet = anonym.post("/api/v1/anmeldung", json={"kennung": "probe", "passwort": "geheim"}).json()
    assert angemeldet["konto"]["name"] == "probe"
    assert anonym.get("/api/config", headers={"X-Kellerwolke-Sitzung": angemeldet["token"]}).status_code == 200


def test_lesezugang_gilt_unter_api_fuer_ton_und_bilder(anonym):
    antwort = anonym.post("/api/v1/anmeldung/zugang", headers={"X-Kellerwolke-Sitzung": SITZUNG})
    assert antwort.status_code == 204
    kekse = antwort.headers.get_list("set-cookie")
    unter_api = [k for k in kekse if "Path=/api;" in k or k.endswith("Path=/api")]
    assert unter_api and all("HttpOnly" in k and "SameSite=strict" in k for k in kekse)
    # ohne Kopf, nur mit dem Keks (wie <audio>, <img>, EventSource)
    assert anonym.get("/api/recordings/stats").status_code == 200
    anonym.cookies.clear()
    assert anonym.get("/api/recordings/stats").status_code == 401


def test_seiten_der_oberflaeche_und_unbekannte_wege(anonym):
    for seite in ("/", "/radio", "/radio/sender/abc", "/einstellungen/allgemein", "/telefon/wecker"):
        assert anonym.get(seite).status_code == 200, seite
    assert anonym.get("/api/gibt-es-nicht").status_code in (401, 404)
    assert anonym.get("/fehlt.js").status_code == 404
