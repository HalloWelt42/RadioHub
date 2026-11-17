"""RAD-7: Senderdaten-Baustein mit echten Beispielen aus dem Befund (Sicherung vom 16.11.2026) und einem echten
Datensatz des Senderverzeichnisses (Deutschlandfunk, abgerufen am 17.11.2026)."""

from __future__ import annotations

import pytest

from app.senderdaten import Messung, Verzeichnisdatensatz, aufbereiten, dubletten, genres, qualitaet, sprachen

DLF = {
    "changeuuid": "8d0391fd-c0fe-4029-bc36-357d02fd3afc", "stationuuid": "1c3e8be2-5b14-4933-bad3-87cbc227cba4",
    "serveruuid": None, "name": "Deutschlandfunk | DLF | MP3 128k",
    "url": "https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3?aggregator=web",
    "url_resolved": "https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3?aggregator=web",
    "homepage": "https://www.deutschlandfunk.de/",
    "favicon": "https://www.deutschlandfunk.de/static/img/deutschlandfunk/icons/apple-touch-icon-128x128.png",
    "tags": "culture,news,public service,information", "country": "Germany", "countrycode": "DE",
    "iso_3166_2": "DE-BE", "state": "Berlin", "language": "german", "languagecodes": "DE", "votes": 12249,
    "lastchangetime_iso8601": "2026-11-12T05:35:43Z", "codec": "MP3", "bitrate": 128, "hls": 0, "lastcheckok": 1,
    "lastcheckoktime_iso8601": "2026-11-12T05:35:43Z", "clickcount": 695, "clicktrend": 695, "ssl_error": 0,
    "geo_lat": 52.4802578, "geo_long": 13.3347639, "geo_distance": None, "has_extended_info": False,
}


def _sender(**felder):
    return aufbereiten(Verzeichnisdatensatz.model_validate({**DLF, **felder}))


def test_echter_datensatz_mit_allen_nuetzlichen_feldern():
    s = _sender()
    assert (s.land, s.region, s.bundesland) == ("DE", "DE-BE", "Berlin")
    assert (s.geo_breite, s.geo_laenge) == (52.4802578, 13.3347639)
    assert s.erreichbar and s.erreichbar_am == "2026-11-12T05:35:43Z" and s.klicktrend == 695
    assert not s.hls and not s.ssl_fehler and not s.erweiterte_info
    assert [(x.code, x.name) for x in s.sprachen] == [("de", "Deutsch")]
    assert s.genres == ["Kultur", "Nachrichten", "Öffentlich-rechtlich"]
    assert (s.codec, s.kbps, s.qualitaet) == ("MP3", 128, "mittel")
    assert s.adresse_norm == "st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3"     # Zählanhang weg
    assert s.name_norm == "deutschlandfunk dlf"


def test_fehlende_felder_und_null_werte():
    s = aufbereiten(Verzeichnisdatensatz.model_validate({"stationuuid": "x", "name": None, "favicon": "null",
                                                         "bitrate": None, "geo_lat": "", "votes": "7"}))
    assert (s.name, s.logo, s.kbps, s.geo_breite, s.stimmen, s.qualitaet) == ("", "", None, None, 7, "unbekannt")


@pytest.mark.parametrize("language, erwartet", [
    ("german", [("de", "Deutsch")]),
    ("ger", [("de", "Deutsch")]),                       # Kürzel, nicht Wortteil
    ("swiss german", [("gsw", "Schweizerdeutsch")]),    # nicht Deutsch
    ("язык: русский", [("ru", "Russisch")]),
    ("español argentina", [("es", "Spanisch")]),        # Gegend als Zusatz
    ("português  brasil", [("pt", "Portugiesisch")]),
    ("english/russian", [("en", "Englisch"), ("ru", "Russisch")]),
    ("english hindi", [("en", "Englisch"), ("hi", "Hindi")]),
    ("germanhttps://stream.laut.fm/deutrockosterreich", [("de", "Deutsch")]),
    ("#spanish", [("es", "Spanisch")]),
    ("asunción", [(None, "asunción")]),                 # freier Text bleibt eigener Eintrag
])
def test_sprachen_exakt(language, erwartet):
    assert [(x.code, x.name) for x in sprachen.sprachen(language)] == erwartet


def test_sprachcodes_ergaenzen_und_freie_eintraege_bleiben_genau():
    liste = sprachen.sprachen("deutsch fränkisch,rock", "de,EN,xyz,1")
    assert [(x.schluessel, x.eintrag) for x in liste] == [
        ("de", "deutsch fränkisch"), ("frei:rock", "rock"), ("en", None), ("xyz", None)]
    assert sprachen.eintraege(" German, swiss german ,,ENGLISH,german") == ["german", "swiss german", "english"]


def test_genres_aus_dem_tag_chaos():
    # Hip-Hop in vier Schreibweisen, 80er dreifach (Befund Abschnitt 8)
    for tags in ("hiphop", "hip-hop", "hip hop", "#HipHop"):
        assert genres.zerlegen(tags)[0] == ["Hip-Hop"]
    for tags in ("80s", "80's", "80er", "1980s"):
        assert genres.zerlegen(tags)[0] == ["80er"]
    g, t = genres.zerlegen("pop,music,radio,fm,101.5,88.4 fm,99.9mhz,am 1220,moi merino,eigener tag")
    assert g == ["Pop"]
    assert t == ["pop", "eigener tag"]           # Rauschen und Frequenzen verworfen


@pytest.mark.parametrize("bitrate, codec, kbps", [
    (128000, "MP3", 128),          # bit/s statt kbit/s
    (64000, "AAC+", 64),
    (128, "MP3", 128),
    (1672, "AAC", None),           # unmöglich für AAC
    (0, "MP3", None),
    (1411, "FLAC", 1411),
])
def test_bitrate_in_kbit(bitrate, codec, kbps):
    assert qualitaet.kbps_aus_verzeichnis(bitrate, qualitaet.codec(codec)) == kbps


@pytest.mark.parametrize("codec, kbps, stufe", [
    ("FLAC", None, "verlustfrei"), ("OGG", 1411, "verlustfrei"), ("AAC", 128, "hoch"), ("MP3", 256, "hoch"),
    ("MP3", 192, "mittel"), ("MP3", 128, "mittel"), ("AAC", 64, "mittel"), ("MP3", 64, "niedrig"),
    ("AAC", 48, "niedrig"), ("MP3", None, "unbekannt"), ("unbekannt", 2560, "unbekannt"),
])
def test_qualitaetsstufen(codec, kbps, stufe):
    assert qualitaet.stufe(codec, kbps) == stufe


def test_codecs_einheitlich():
    assert [qualitaet.codec(c) for c in ("AAC+", "AAC,H.264", "UNKNOWN", "", "mp3", "vorbis", "MP4")] == [
        "AAC", "AAC", "unbekannt", "unbekannt", "MP3", "OGG", "AAC"]


def test_gemessene_bitrate_gilt_vor_dem_verzeichnis():
    s = aufbereiten(Verzeichnisdatensatz.model_validate(DLF), Messung(kbps=256, codec="aac"))
    assert (s.kbps_verzeichnis, s.kbps_gemessen, s.kbps, s.codec, s.qualitaet) == (128, 256, 256, "AAC", "hoch")
    leer = aufbereiten(Verzeichnisdatensatz.model_validate(DLF), Messung(kbps=0, codec="unknown"))
    assert (leer.kbps, leer.codec) == (128, "MP3")


def test_dubletten_als_gruppe_mit_bester_variante():
    mp3 = _sender()
    aac = _sender(stationuuid="2", name="Deutschlandfunk | DLF | AAC 256k", codec="AAC", bitrate=256,
                  url="https://st01.sslstream.dlf.de/dlf/01/high/aac/stream.aac", url_resolved="")
    doppelt = _sender(stationuuid="3", name="DLF Nachrichten", url="http://ST01.sslstream.dlf.de:80/dlf/01/128/mp3/stream.mp3/",
                      url_resolved="")
    fremd = _sender(stationuuid="4", name="Deutschlandfunk | DLF", countrycode="AT",
                    url="https://example.invalid/x", url_resolved="")
    glieder = [dubletten.Gruppenglied(s.uuid, s.adresse_norm, s.name_norm, s.land) for s in (mp3, aac, doppelt, fremd)]
    gruppe = dubletten.gruppen(glieder)
    assert gruppe[mp3.uuid] == gruppe[aac.uuid] == gruppe[doppelt.uuid] != gruppe[fremd.uuid]
    beste = max((mp3, aac), key=lambda s: dubletten.rang(s.qualitaet_rang, s.kbps, s.erreichbar, s.stimmen))
    assert beste.uuid == "2"


def test_allgemeine_namen_verbinden_nichts():
    a = _sender(stationuuid="a", name="Radio", url="https://a.invalid/1", url_resolved="")
    b = _sender(stationuuid="b", name="Radio (HQ)", url="https://b.invalid/2", url_resolved="")
    gruppe = dubletten.gruppen(dubletten.Gruppenglied(s.uuid, s.adresse_norm, s.name_norm, s.land) for s in (a, b))
    assert gruppe["a"] != gruppe["b"]
