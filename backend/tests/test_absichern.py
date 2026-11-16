"""Absichern (RAD-5): keine CORS-Freigabe für fremde Ursprünge, Durchleiter nur für bekannte Sender und Folgen mit
TLS-Prüfung und Weiterleitungen nur auf http und https, Wiedergabe aus der Ablage nur in Aufnahmen und Podcasts,
/health ohne volle Prüfung der Datenbank."""

import ssl
import uuid

import httpx
import pytest

from app import database
from app.config import erlaubte_urspruenge
from app.database import db_session
from app.services import durchleiter


# ----- CORS --------------------------------------------------------------------------------------------------------------

def test_urspruenge_vorgabe_leer_und_nie_stern():
    assert erlaubte_urspruenge("") == []
    assert erlaubte_urspruenge("*") == []
    assert erlaubte_urspruenge(" https://a.example , *, https://b.example") == ["https://a.example", "https://b.example"]


def test_keine_freigabe_fuer_fremde_urspruenge(client):
    antwort = client.get("/health", headers={"Origin": "https://fremd.example"})
    assert "access-control-allow-origin" not in antwort.headers
    vorab = client.options("/api/config", headers={"Origin": "https://fremd.example", "Access-Control-Request-Method": "PUT"})
    assert "access-control-allow-origin" not in vorab.headers


# ----- Durchleiter: Adresse nur aus der Datenbank ------------------------------------------------------------------------

def _sender(url: str | None = "http://sender.test/url", aufgeloest: str | None = None, eigene: str | None = None,
            tabelle: str = "stations") -> str:
    kennung = str(uuid.uuid4())
    with db_session() as c:
        c.execute(f"INSERT INTO {tabelle} (uuid, name, url, url_resolved) VALUES (?, 'Probe', ?, ?)", (kennung, url, aufgeloest))
        if eigene:
            c.execute("INSERT INTO station_custom_urls (station_uuid, custom_url, original_url) VALUES (?, ?, ?)",
                      (kennung, eigene, url or ""))
    return kennung


def test_eigene_adresse_vor_aufgeloester_vor_eingetragener():
    assert durchleiter.sender_adresse(_sender()) == "http://sender.test/url"
    assert durchleiter.sender_adresse(_sender(aufgeloest="https://sender.test/aufgeloest")) == "https://sender.test/aufgeloest"
    assert durchleiter.sender_adresse(_sender(aufgeloest="https://sender.test/a", eigene="https://eigen.test/strom")) \
        == "https://eigen.test/strom"


def test_favorit_ohne_eintrag_im_senderbestand():
    assert durchleiter.sender_adresse(_sender(url="https://favorit.test/strom", tabelle="favorites")) == "https://favorit.test/strom"


def test_unbekannter_sender_404(client):
    assert client.get(f"/api/stream/sender/{uuid.uuid4()}").status_code == 404


def test_alter_durchleiter_mit_adresse_gibt_es_nicht_mehr(client):
    assert client.get("/api/stream/proxy", params={"url": "http://192.168.178.1/"}).status_code == 404


@pytest.mark.parametrize("adresse", ["file:///etc/passwd", "ftp://sender.test/strom", "gopher://x", "http:///ohne-rechner", "strom"])
def test_nur_http_und_https(adresse):
    with pytest.raises(durchleiter.UnerlaubteAdresse):
        durchleiter.pruefen(adresse)


def test_tls_wird_geprueft():
    client = durchleiter._client()
    kontext = client._transport._pool._ssl_context
    assert kontext.verify_mode == ssl.CERT_REQUIRED and kontext.check_hostname


# ----- Durchleiter: Weiterleitungen, Köpfe, Range ------------------------------------------------------------------------

@pytest.fixture
def gegenstelle(monkeypatch):
    """Gegenstelle zum Schein: Antworten je Adresse, gesehene Anfragen."""
    antworten: dict[str, httpx.Response] = {}
    gesehen: list[httpx.Request] = []

    def handler(anfrage: httpx.Request) -> httpx.Response:
        gesehen.append(anfrage)
        return antworten.get(str(anfrage.url), httpx.Response(404))

    def client() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)

    monkeypatch.setattr(durchleiter, "_client", client)
    return antworten, gesehen


def test_weiterleitung_auf_https_und_koepfe(client, gegenstelle):
    antworten, gesehen = gegenstelle
    kennung = _sender(url="http://sender.test/strom")
    antworten["http://sender.test/strom"] = httpx.Response(302, headers={"Location": "https://cdn.test/strom.mp3"})
    antworten["https://cdn.test/strom.mp3"] = httpx.Response(
        206, content=b"ton", headers={"Content-Type": "audio/mpeg", "icy-name": "Probe FM", "icy-br": "128",
                                      "Content-Range": "bytes 0-2/3", "X-Fremd": "nein"})
    antwort = client.get(f"/api/stream/sender/{kennung}", headers={"Range": "bytes=0-2"})
    assert antwort.status_code == 206 and antwort.content == b"ton"
    assert antwort.headers["icy-name"] == "Probe FM" and antwort.headers["icy-br"] == "128"
    assert antwort.headers["content-range"] == "bytes 0-2/3" and "x-fremd" not in antwort.headers
    assert all(a.headers["range"] == "bytes=0-2" for a in gesehen)


def test_weiterleitung_auf_anderes_schema_400(client, gegenstelle):
    antworten, _ = gegenstelle
    kennung = _sender(url="http://sender.test/umweg")
    antworten["http://sender.test/umweg"] = httpx.Response(301, headers={"Location": "file:///etc/passwd"})
    assert client.get(f"/api/stream/sender/{kennung}").status_code == 400


def test_zu_viele_weiterleitungen_502(client, gegenstelle):
    antworten, _ = gegenstelle
    kennung = _sender(url="http://sender.test/kreis")
    antworten["http://sender.test/kreis"] = httpx.Response(302, headers={"Location": "/kreis"})
    assert client.get(f"/api/stream/sender/{kennung}").status_code == 502


def test_fehler_der_gegenstelle_wird_gemeldet(client, gegenstelle):
    kennung = _sender(url="http://sender.test/weg")
    assert client.get(f"/api/stream/sender/{kennung}").status_code == 404


# ----- Podcast-Durchleiter: nur bekannte Folgen ----------------------------------------------------------------------------

def _folge(audio_url: str) -> int:
    with db_session() as c:
        abo = c.execute("INSERT INTO podcast_subscriptions (feed_url, title) VALUES (?, 'Probe')",
                        (f"https://feed.test/{uuid.uuid4()}",)).lastrowid
        return c.execute("INSERT INTO podcast_episodes (podcast_id, guid, title, audio_url) VALUES (?, ?, 'Folge', ?)",
                         (abo, str(uuid.uuid4()), audio_url)).lastrowid


def test_unbekannte_folge_404(client):
    assert client.get("/api/podcasts/episodes/999999/stream").status_code == 404


def test_folge_mit_fremdem_schema_400(client):
    assert client.get(f"/api/podcasts/episodes/{_folge('file:///etc/passwd')}/stream").status_code == 400


def test_folge_wird_durchgeleitet(client, gegenstelle):
    antworten, _ = gegenstelle
    antworten["https://feed.test/folge.mp3"] = httpx.Response(200, content=b"folge", headers={"Content-Type": "audio/mpeg"})
    antwort = client.get(f"/api/podcasts/episodes/{_folge('https://feed.test/folge.mp3')}/stream")
    assert antwort.status_code == 200 and antwort.content == b"folge"


# ----- Wiedergabe aus der Ablage -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("pfad", ["../geheim.mp3", "Aufnahmen/../../geheim.mp3", "Aufnahmen/./x.mp3", "Zeitansage/es-ist.mp3",
                                  "/etc/passwd", ""])
def test_wiedergabe_ausserhalb_der_bereiche_400(client, pfad):
    assert client.get("/api/recordings/play", params={"path": pfad}).status_code == 400


async def test_wiedergabe_im_bereich(client, speicher):
    await speicher.schreiben("Aufnahmen/Welle/2026-01-02 03-04-05/001 Titel.mp3", b"ton")
    assert client.get("/api/recordings/play", params={"path": "Aufnahmen/Welle/2026-01-02 03-04-05/001 Titel.mp3"}).content == b"ton"
    assert client.get("/api/recordings/play", params={"path": "Podcasts/Abo/fehlt.mp3"}).status_code == 404


# ----- /health ohne volle Prüfung ------------------------------------------------------------------------------------------

def test_health_ohne_integritaetspruefung(client, monkeypatch):
    befehle: list[str] = []
    original = database.get_db

    def mit_spur():
        verbindung = original()
        verbindung.set_trace_callback(befehle.append)
        return verbindung

    monkeypatch.setattr(database, "get_db", mit_spur)
    antwort = client.get("/health").json()
    assert antwort["status"] == "healthy" and antwort["database"] == "healthy"
    assert any("SELECT 1" in b for b in befehle)
    assert not any("integrity_check" in b for b in befehle)


def test_volle_pruefung_als_eigener_aufruf(client):
    antwort = client.get("/api/datenbank/pruefung").json()
    assert antwort["integrity"] is True and antwort["status"] == "healthy"
