"""Einstellungen aus einer Quelle (RAD-6): die früheren Umgebungswerte RADIOHUB_* gelten unverändert, ebenso die alten
Formen (Schlüssel als Datei, Zertifikatsstelle, ALLOWED_ORIGINS); Werte der Tabelle config, die jetzt Einstellungen sind,
gehen einmal in die Einstellungen; /api/config bleibt für die heutige Oberfläche dieselbe Schnittstelle."""

import json
import sqlite3

from appkern.datenbank import Datenbank
from appkern.einstellungen import Einstellungen
from appkern.einstellungen.dienst import aus_umgebung

from app import einstellungen, uebergang
from app.einstellungen import PRAEFIX, UEBERTRAEGE, AppEinstellungen

ERSTER_UEBERTRAG = UEBERTRAEGE[0][1]       # die Felder bis RAD-11; die Sprache blieb damals in der Tabelle

# was compose.pi.yml und die .env auf dem Pi bis Fassung 0.15 setzten (Handbuch: Einstellungen des Hauses)
ALTE_ENV = {
    "RADIOHUB_KELLERWOLKE_ADRESSE": "https://192.0.2.10:39280",
    "RADIOHUB_KELLERWOLKE_WURZEL": "Apps/RadioHub",
    "RADIOHUB_KELLERWOLKE_CA": "/zertifikate/rootCA.pem",
    "RADIOHUB_KELLERWOLKE_GEDULD_S": "600",
    "RADIOHUB_ORTSSUCHE_ADRESSE": "http://osmlocal:8120",
    "RADIOHUB_VERTONUNG_ADRESSE": "https://192.0.2.20:8641",
    "RADIOHUB_ZEITSTIMME": "stimme-7",
    "RADIOHUB_ZEITSTIMME_TEMPO": "0.9",
}


def _stand(umgebung: dict, daten) -> AppEinstellungen:
    uebergang.alte_umgebung_uebernehmen(umgebung, daten)
    return AppEinstellungen.model_validate(aus_umgebung(AppEinstellungen, PRAEFIX, umgebung))


def test_alte_env_gilt_unveraendert(tmp_path):
    schluessel = tmp_path / "kellerwolke.schluessel"
    schluessel.write_text("kw_app_aus_datei\n")
    stand = _stand({**ALTE_ENV, "RADIOHUB_KELLERWOLKE_SCHLUESSEL": str(schluessel)}, tmp_path)
    assert stand.kellerwolke_adresse == "https://192.0.2.10:39280"
    assert stand.kellerwolke_schluessel.get_secret_value() == "kw_app_aus_datei"
    assert stand.kellerwolke_wurzel == "Apps/RadioHub" and stand.kellerwolke_geduld_s == 600
    assert stand.ca_datei == "/zertifikate/rootCA.pem"
    assert stand.ortssuche_adresse == "http://osmlocal:8120" and stand.vertonung_adresse == "https://192.0.2.20:8641"
    assert stand.zeitstimme == "stimme-7" and stand.zeitstimme_tempo == 0.9


def test_schluessel_ohne_angabe_aus_der_frueheren_datei(tmp_path):
    (tmp_path / "kellerwolke.schluessel").write_text("kw_app_vorgabe")
    assert _stand(dict(ALTE_ENV), tmp_path).kellerwolke_schluessel.get_secret_value() == "kw_app_vorgabe"
    # ein fester Schlüssel vom Ausrollen geht vor: die alte Datei bleibt dann unbeachtet
    umgebung = {**ALTE_ENV, "RADIOHUB_FEST_KELLERWOLKE_SCHLUESSEL": "kw_app_fest"}
    assert uebergang.alte_umgebung_uebernehmen(umgebung, tmp_path) == ["RADIOHUB_KELLERWOLKE_CA gilt als RADIOHUB_CA_DATEI"]
    assert "RADIOHUB_KELLERWOLKE_SCHLUESSEL" not in umgebung


def test_schluessel_als_wert_und_unlesbare_datei(tmp_path):
    assert _stand({"RADIOHUB_KELLERWOLKE_SCHLUESSEL": "kw_app_wert"}, tmp_path).kellerwolke_schluessel.get_secret_value() \
        == "kw_app_wert"
    umgebung = {"RADIOHUB_KELLERWOLKE_SCHLUESSEL": str(tmp_path / "fehlt")}
    getan = uebergang.alte_umgebung_uebernehmen(umgebung, tmp_path)
    assert "RADIOHUB_KELLERWOLKE_SCHLUESSEL" not in umgebung and "nicht lesen" in getan[0]
    assert all("kw_app" not in zeile for zeile in getan)


def test_neue_namen_gehen_vor_und_allowed_origins(tmp_path):
    umgebung = {"RADIOHUB_KELLERWOLKE_CA": "/alt.pem", "RADIOHUB_CA_DATEI": "/neu.pem",
                "ALLOWED_ORIGINS": "https://a.example, *, https://b.example"}
    stand = _stand(umgebung, tmp_path)
    assert stand.ca_datei == "/neu.pem"
    assert stand.erlaubte_urspruenge == ["https://a.example", "*", "https://b.example"]   # "*" verwirft config.erlaubte_urspruenge


async def test_config_werte_gehen_einmal_in_die_einstellungen(tmp_path):
    db_pfad = tmp_path / "radiohub.db"
    v = sqlite3.connect(db_pfad)
    v.execute("CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT)")
    v.executemany("INSERT INTO config VALUES (?, ?)", [
        ("podcast_refresh_interval", "7200"), ("service_itunes_search_url", json.dumps("https://suche.example")),
        ("hls_max_bitrate", "\"viel\""), ("language", "\"en\""), ("recording_bitrate", "128")])
    v.commit()
    v.close()
    async with Datenbank(":memory:") as db:
        e = Einstellungen(db, AppEinstellungen, umgebung_praefix=PRAEFIX, umgebung={"RADIOHUB_FEST_RECORDING_BITRATE": "256"})
        await e.starten()
        uebernommen, uebergangen = await uebergang.config_uebernehmen(e, db_pfad, ERSTER_UEBERTRAG)
        assert uebernommen == ["podcast_refresh_interval", "service_itunes_search_url"]
        assert len(uebergangen) == 1 and uebergangen[0].startswith("hls_max_bitrate")
        assert e.stand.podcast_refresh_interval == 7200 and e.herkunft("podcast_refresh_interval") == "gespeichert"
        assert e.stand.recording_bitrate == 256 and e.stand.hls_max_bitrate == 320     # fest bleibt, ungültig: Vorgabe
        await e.aendern({"podcast_refresh_interval": 3600})
        assert (await uebergang.config_uebernehmen(e, db_pfad, ERSTER_UEBERTRAG))[0] == []   # Gespeichertes bleibt
        assert e.stand.podcast_refresh_interval == 3600
    v = sqlite3.connect(db_pfad)
    assert v.execute("SELECT COUNT(*) FROM config").fetchone()[0] == 5               # die Tabelle bleibt, wie sie war
    v.close()


def test_api_config_trennt_einstellungen_und_stand_der_oberflaeche(client):
    vorher = client.get("/api/config").json()
    assert vorher["podcast_refresh_interval"] == 21600 and vorher["language"] == "de"
    antwort = client.put("/api/config", json={"updates": {"podcast_refresh_interval": 10800, "language": "en"}})
    assert antwort.status_code == 200 and antwort.json()["config"]["podcast_refresh_interval"] == 10800
    felder = {f["name"]: f for f in client.get("/api/v1/einstellungen").json()}
    assert felder["podcast_refresh_interval"]["wert"] == 10800 and felder["podcast_refresh_interval"]["herkunft"] == "gespeichert"
    assert "kellerwolke_schluessel" not in client.get("/api/config").json()                 # Geheimnisse nie unter /api/config
    assert client.put("/api/config", json={"updates": {"hls_sample_rate": "laut"}}).status_code == 422
    zurueck = client.put("/api/config", json={"updates": {"podcast_refresh_interval": None, "language": None}}).json()["config"]
    assert zurueck["podcast_refresh_interval"] == 21600 and zurueck["language"] == "de"     # None heißt Vorgabe
    assert einstellungen.herkunft("podcast_refresh_interval") == "vorgabe"
    assert client.post("/api/config/reset").status_code in (404, 405)                       # ohne Bedienung entfallen (RAD-11)


async def test_rad11_uebertrag_nimmt_stand_der_oberflaeche_mit(tmp_path):
    """Der zweite Übertrag (RAD-11) holt Sprache, Werbeerkennung und Ort aus der Tabelle, auch die doppelt verpackten
    Verfahren und die Schwelle als Anteil. Der Rückblick der Puffer-Aufnahme ist seit RAD-46 keine Einstellung mehr (die
    Aufnahme beginnt am laufenden Titel), die Klicktöne seit RAD-68 nicht (es gibt keine Klänge mehr); beide bleiben in
    der alten Tabelle."""
    db_pfad = tmp_path / "radiohub.db"
    v = sqlite3.connect(db_pfad)
    v.execute("CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT)")
    v.executemany("INSERT INTO config VALUES (?, ?)", [
        ("language", "\"en\""), ("ui_click_sounds", "false"), ("hls_rec_lookback_minutes", "12"),
        ("ad_detection_methods", json.dumps(json.dumps(["header_check"]))), ("ad_detection_threshold", "0.9"),
        ("ort_name", "\"Hannover\""), ("ort_breite", "52.37"), ("ort_laenge", "9.74"), ("last_station_uuid", "\"x\"")])
    v.commit()
    v.close()
    async with Datenbank(":memory:") as db:
        e = Einstellungen(db, AppEinstellungen, umgebung_praefix=PRAEFIX, umgebung={})
        await e.starten()
        uebernommen, uebergangen = await uebergang.config_uebernehmen(e, db_pfad, UEBERTRAEGE[1][1])
        assert uebergangen == [] and "last_station_uuid" not in uebernommen
        assert "hls_rec_lookback_minutes" not in uebernommen and "ui_click_sounds" not in uebernommen
        st = e.stand
        assert st.language == "en"
        assert st.ad_detection_methods == ["header_check"] and st.ad_detection_threshold == 90
        assert (st.ort_name, st.ort_breite, st.ort_laenge) == ("Hannover", 52.37, 9.74)


def test_rad11_regeln_und_felder_ueber_die_schnittstelle(client):
    felder = {f["name"]: f for f in client.get("/api/v1/einstellungen").json()}
    assert felder["language"]["art"] == "auswahl" and felder["language"]["beschriftungen"]["de"] == "Deutsch"
    assert felder["hls_puffer_minuten"]["kleinste"] == 10 and felder["hls_puffer_minuten"]["einheit"] == "min"
    assert felder["hls_sample_rate"]["art"] == "auswahl" and felder["service_fyyd_search_url"]["titel"] == "Podcast-Verzeichnis, deutsch"
    assert {f["gruppe"] for f in felder.values() if f["name"] in einstellungen.CONFIG_FELDER} <= {
        "Allgemein", "Radio", "Wiedergabe", "Aufnahmen", "Podcasts", "Wecker und Zeitansage", "Ablage", "Dienste"}
    falsch = client.patch("/api/v1/einstellungen", json={"werte": {"hls_min_bitrate": 256, "hls_max_bitrate": 128}})
    assert falsch.status_code in (400, 409, 422) and "kleinste Bitrate" in falsch.text
    weg = client.patch("/api/v1/einstellungen", json={"werte": {"hls_rec_lookback_minutes": 5}})   # seit RAD-46 entfallen
    assert weg.status_code == 422 and "hls_rec_lookback_minutes" in weg.text and "hls_rec_lookback_minutes" not in felder
    assert client.put("/api/wecker/ort", json={"name": "Hannover", "breite": 52.37, "laenge": 9.74}).status_code == 200
    assert client.get("/api/wecker/ort").json() == {"name": "Hannover", "breite": 52.37, "laenge": 9.74}
    assert einstellungen.stand().ort_name == "Hannover"
    halb = client.put("/api/wecker/ort", json={"name": "Nirgends", "breite": 10, "laenge": None})
    assert halb.status_code == 422 and "Breite und Länge" in halb.text
    client.patch("/api/v1/einstellungen", json={"werte": {"ort_name": None, "ort_breite": None, "ort_laenge": None}})


def test_eingebaute_titelmuster_bleiben(client):
    """RAD-11: eingebaute Muster der Titel lassen sich nicht löschen, eigene schon."""
    eintraege = client.get("/api/recording/icy-ignore").json()["items"]
    eingebaut = next(e for e in eintraege if e["source"] != "user")
    assert client.delete(f"/api/recording/icy-ignore/{eingebaut['id']}").status_code == 409
    assert client.post("/api/recording/icy-ignore/remove-by-pattern", json={"pattern": eingebaut["pattern"]}).status_code == 409
    neu = client.post("/api/recording/icy-ignore", json={"pattern": "Probe RAD-11", "match_type": "contains"}).json()["id"]
    assert client.delete(f"/api/recording/icy-ignore/{neu}").status_code == 200
