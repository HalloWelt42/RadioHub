"""Einstellungen des RadioHub: eine Quelle für alles, was der Server braucht (RAD-6, Entscheidung 8).

Kellerwolke, Leitstelle, Zertifikatsstelle, Anmeldung und Sicherung bringt das Gerüst des Appkerns mit
(`Grundeinstellungen`); hier kommen die eigenen Felder dazu. Ein Wert kommt aus der Datenbank des Gerüsts (in der
Oberfläche gesetzt), sonst aus der Umgebung (`RADIOHUB_<FELD>`, etwa RADIOHUB_VERTONUNG_ADRESSE), sonst aus der
Vorgabe; fest ist er mit `RADIOHUB_FEST_<FELD>` (vom Ausrollen gesetzt, etwa der App-Schlüssel der Kellerwolke).

Die Namen der Felder sind die früheren Namen: die Umgebungswerte `RADIOHUB_*` gelten unverändert, und die Felder, die
früher in der Tabelle `config` standen (`CONFIG_FELDER`), heißen wie ihre Schlüssel dort. Deren Werte übernimmt der
erste Start einmal (`uebergang.config_uebernehmen`); Schlüssel der Tabelle, die nur die Oberfläche betreffen (Sprache,
zuletzt gehörter Sender, Länder der Seitenleiste, Filter bis Etappe 3), bleiben dort.

Die laufende App bindet ihre Einstellungen mit `binden`; Dienste lesen den gültigen Stand mit `stand()`. Ohne
laufende App (Werkzeuge wie `python -m app.umzug`) liest `stand()` denselben Stand nur lesend aus der Datenbank des
Gerüsts und der Umgebung.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any, Literal

from pydantic import Field, field_validator

from appkern.app import Grundeinstellungen
from appkern.einstellungen import Einstellungen, nur_lesen

from . import ort, uebergang

KENNUNG = "radiohub"
PRAEFIX = f"{KENNUNG.upper()}_"

# Gruppe = Bereich der Einstellungsseite (RAD-11): jedes Feld hat genau einen Ort
ALLGEMEIN = {"gruppe": "Allgemein"}
RADIO = {"gruppe": "Radio"}
WIEDERGABE = {"gruppe": "Wiedergabe"}
AUFNAHMEN = {"gruppe": "Aufnahmen"}
PODCASTS = {"gruppe": "Podcasts"}
WECKER = {"gruppe": "Wecker und Zeitansage"}
ABLAGE = {"gruppe": "Ablage"}
DIENSTE = {"gruppe": "Dienste"}

SPRACHEN = {"de": "Deutsch", "en": "English", "fr": "Français", "es": "Español", "it": "Italiano", "pt": "Português",
            "nl": "Nederlands", "pl": "Polski", "cs": "Čeština", "sk": "Slovenčina", "da": "Dansk", "sv": "Svenska",
            "no": "Norsk", "fi": "Suomi", "hu": "Magyar", "ro": "Română", "tr": "Türkçe", "ru": "Русский", "ja": "日本語",
            "zh": "中文"}
Sprache = Literal["de", "en", "fr", "es", "it", "pt", "nl", "pl", "cs", "sk", "da", "sv", "no", "fi", "hu", "ro", "tr", "ru",
                  "ja", "zh"]
Pruefart = Literal["url_check", "header_check"]
Abtastrate = Literal[22050, 32000, 44100, 48000]

RADIO_BROWSER = ["https://de1.api.radio-browser.info", "https://at1.api.radio-browser.info",
                 "https://nl1.api.radio-browser.info"]


class AppEinstellungen(Grundeinstellungen):
    # --- Ablage in der Kellerwolke (früher RADIOHUB_KELLERWOLKE_WURZEL und _GEDULD_S) ---
    kellerwolke_wurzel: str = Field("Apps/RadioHub", min_length=1, max_length=200, title="Ordner in der Kellerwolke",
                                    json_schema_extra=ABLAGE,
                                    description="Wurzelordner der Aufnahmen, Podcast-Folgen und Bausteine der Zeitansage "
                                                "in der Kellerwolke.")
    kellerwolke_geduld_s: float = Field(900.0, ge=0, le=3600, title="Wartezeit beim Speichern",
                                        json_schema_extra={**ABLAGE, "einheit": "s", "schritt": 60},
                                        description="So lange wartet das Ablegen einer Aufnahme oder Folge, wenn die "
                                                    "Kellerwolke gerade nicht erreichbar ist, damit ein Neustart dort "
                                                    "nichts kostet.")
    # --- Wecker und Zeitansage (früher RADIOHUB_ORTSSUCHE_ADRESSE, _VERTONUNG_ADRESSE, _ZEITSTIMME, _ZEITSTIMME_TEMPO) ---
    ortssuche_adresse: str = Field("", max_length=200, title="Ortssuche", json_schema_extra=WECKER,
                                   description="Kartensuche (OSM lokal) für den Ort der Sonnenzeiten. Leer: keine Suche, "
                                               "der Standort des Telefons geht trotzdem.")
    vertonung_adresse: str = Field("", max_length=200, title="Vertonung", json_schema_extra=WECKER,
                                   description="Vertonung, die die Bausteine der Zeitansage spricht. Sie nimmt den "
                                               "App-Schlüssel der Kellerwolke als Zugang.")
    zeitstimme: str = Field("katalog:sohee", max_length=200, title="Stimme der Zeitansage", json_schema_extra=WECKER,
                            description="Stimme der Zeitansage aus der Vertonung: aus dem Katalog oder eine private, die "
                                        "die Vertonung für RadioHub freigibt. Jede Stimme spricht ihre eigenen Bausteine; "
                                        "nach einem Wechsel fehlen sie, bis sie erzeugt sind.")
    zeitstimme_tempo: float = Field(1.0, ge=0.5, le=2.0, title="Sprechtempo der Zeitansage",
                                    json_schema_extra={**WECKER, "schritt": 0.05},
                                    description="1,0 ist das Tempo der Stimme; kleiner spricht langsamer.")
    # --- Propaganda-Filter (HELF-256) ---
    propaganda_filter_adresse: str = Field("", max_length=200, title="Propaganda-Filter", json_schema_extra=DIENSTE,
                                           description="Eigener Dienst, der Werbung in Ton findet (etwa beim Vergleich "
                                                       "zweier Fassungen einer gespeicherten Folge). Er nimmt den "
                                                       "App-Schlüssel der Kellerwolke als Zugang. Leer: RadioHub "
                                                       "bietet den Vergleich nicht an.")
    # --- Zugriff (früher ALLOWED_ORIGINS) ---
    erlaubte_urspruenge: list[str] = Field(default_factory=list, title="Erlaubte Ursprünge (CORS)",
                                           json_schema_extra=DIENSTE,
                                           description="Nur nötig, wenn eine fremde Seite die Schnittstelle im Browser "
                                                       "nutzen soll (etwa https://rechner:5180); nie *. Leer: die "
                                                       "Oberfläche spricht über denselben Ursprung. Gilt nach einem "
                                                       "Neustart.")
    # --- früher in der Tabelle config ---
    recording_bitrate: int = Field(192, ge=8, le=512, title="Bitrate der Aufnahme",
                                   json_schema_extra={**AUFNAHMEN, "einheit": "kbit/s", "schritt": 8},
                                   description="Bitrate, mit der eine Aufnahme gespeichert wird, wenn der Sender sie "
                                               "nicht selbst vorgibt.")
    recording_debug_log: bool = Field(False, title="Aufnahme protokollieren", json_schema_extra=AUFNAHMEN,
                                      description="Schreibt zu jeder Aufnahme ein Protokoll der Ereignisse (Start, "
                                                  "Stocken, Größe, Ende) neben die Aufnahme, für die Fehlersuche.")
    hls_min_bitrate: int = Field(32, ge=8, le=512, title="Kleinste Bitrate",
                                 json_schema_extra={**WIEDERGABE, "einheit": "kbit/s", "schritt": 8},
                                 description="Untergrenze der Bitrate im Zeitversatz.")
    hls_max_bitrate: int = Field(320, ge=8, le=512, title="Größte Bitrate",
                                 json_schema_extra={**WIEDERGABE, "einheit": "kbit/s", "schritt": 8},
                                 description="Obergrenze der Bitrate im Zeitversatz; schwächere Sender werden nicht "
                                             "aufgebläht.")
    hls_sample_rate: Abtastrate = Field(44100, title="Abtastrate", json_schema_extra={**WIEDERGABE, "beschriftungen": {
        "22050": "22.050 Hz", "32000": "32.000 Hz", "44100": "44.100 Hz", "48000": "48.000 Hz"}},
                                        description="Abtastrate des Puffers.")
    hls_puffer_minuten: int = Field(120, ge=15, le=480, title="Länge des Puffers",
                                    json_schema_extra={**WIEDERGABE, "einheit": "min", "schritt": 15},
                                    description="So weit lässt sich ein laufender Sender zurückspulen, in Schritten von "
                                                "15 Minuten bis 8 Stunden (RAD-92).")
    hls_puffer_ordner: str = Field("/tmp/radiohub-hls", min_length=1, max_length=300, title="Ordner der Puffer-Stücke",
                                   json_schema_extra=WIEDERGABE,
                                   description="Wo der Zeitversatz seine Stücke ablegt (jede Sekunde eins); am Pi ein "
                                               "Bereich im Arbeitsspeicher (RADIOHUB_HLS_PUFFER_ORDNER, RAD-92).")
    podcast_auto_refresh: bool = Field(True, title="Abos von selbst abrufen", json_schema_extra=PODCASTS,
                                       description="Ruft die Feeds aller Abos regelmäßig ab.")
    podcast_refresh_interval: int = Field(21600, ge=60, le=7 * 86400, title="Abstand des Abrufs",
                                          json_schema_extra={**PODCASTS, "einheit": "s", "schritt": 3600},
                                          description="So viele Sekunden liegen zwischen zwei Abrufen der Feeds.")
    service_radio_browser_servers: list[str] = Field(default_factory=lambda: list(RADIO_BROWSER),
                                                     title="Senderverzeichnis", json_schema_extra=DIENSTE,
                                                     description="Server des Senderverzeichnisses, in dieser Reihenfolge "
                                                                 "gefragt.")
    abgleich_uhrzeit: str = Field("04:30", pattern=r"^(([01]\d|2[0-3]):[0-5]\d)?$", title="Uhrzeit des Abgleichs",
                                  json_schema_extra={**RADIO, "einheit": "Uhrzeit"},
                                  description="Jede Nacht um diese Uhrzeit (Ortszeit, etwa 04:30) gleicht das Radio seinen "
                                              "Bestand mit dem Senderverzeichnis ab: neue Sender, geänderte Angaben, "
                                              "verschwundene markiert. Leer: nur auf Anstoß.")
    service_itunes_search_url: str = Field("https://itunes.apple.com/search", title="Podcast-Verzeichnis, weltweit",
                                           json_schema_extra=DIENSTE, description="Suche nach Podcasts beim Abonnieren.")
    service_fyyd_search_url: str = Field("https://api.fyyd.de/0.2/search/podcast", title="Podcast-Verzeichnis, deutsch",
                                         json_schema_extra=DIENSTE,
                                         description="Zweite Suche, vor allem deutschsprachige Podcasts.")
    # --- RAD-11: bisher in der Tabelle config (Stand der Oberfläche), jetzt hier mit Grenzen und Prüfung ---
    language: Sprache = Field("de", title="Sprache", json_schema_extra={**ALLGEMEIN, "beschriftungen": SPRACHEN},
                              description="Sprache der Oberfläche, für alle Geräte.")
    ad_detection_enabled: bool = Field(True, title="Werbeerkennung", json_schema_extra=RADIO,
                                       description="Prüft Sender auf reine Werbe- und Verkaufskanäle.")
    ad_detection_methods: list[Pruefart] = Field(default_factory=lambda: ["url_check", "header_check"], title="Verfahren",
                                                 json_schema_extra={**RADIO, "beschriftungen": {
                                                     "url_check": "Adresse prüfen", "header_check": "HTTP-Header prüfen"}},
                                                 description="Woran ein Sender erkannt wird; beide zugleich sind möglich.")
    ad_detection_threshold: int = Field(80, ge=40, le=100, title="Schwelle",
                                        json_schema_extra={**RADIO, "einheit": "%", "schritt": 5},
                                        description="Ab dieser Sicherheit gilt ein Sender als verdächtig.")
    werbung_ueberspringen: bool = Field(True, title="Angekündigte Werbung überspringen", json_schema_extra=RADIO,
                                        description="Gilt für alle Sender, je Sender abschaltbar: der Spot beim Verbinden "
                                                    "wird nicht gespielt, im Zeitversatz wird Werbung übersprungen, live "
                                                    "stumm geschaltet, bis sie vorbei ist (RAD-33).")
    ort_name: str = Field("", max_length=120, title="Ort", json_schema_extra=WECKER,
                          description="Name des Orts der Sonnenzeiten (Nachtmodus der Weckeransicht).")
    ort_breite: float | None = Field(None, ge=-90, le=90, title="Breite", json_schema_extra=WECKER,
                                     description="Geografische Breite des Orts.")
    ort_laenge: float | None = Field(None, ge=-180, le=180, title="Länge", json_schema_extra=WECKER,
                                     description="Geografische Länge des Orts.")

    @field_validator("ad_detection_methods", mode="before")
    @classmethod
    def _verfahren_aus_text(cls, wert: Any) -> Any:
        """Früher als JSON-Text im JSON gespeichert (doppelt verpackt); so kommt es aus der Tabelle config."""
        return json.loads(wert) if isinstance(wert, str) else wert

    @field_validator("ad_detection_threshold", mode="before")
    @classmethod
    def _schwelle_in_prozent(cls, wert: Any) -> Any:
        """Früher ein Anteil (0,8); jetzt Prozent wie in der Oberfläche."""
        if isinstance(wert, str):
            wert = float(wert)
        return round(wert * 100) if isinstance(wert, (int, float)) and 0 < wert <= 1 else wert


# Felder, die früher in der Tabelle config standen; über /api/config bleiben sie unter diesen Schlüsseln lesbar und
# änderbar (die heutige Oberfläche nutzt das bis Teil 2c)
CONFIG_FELDER: frozenset[str] = frozenset({
    "recording_bitrate", "recording_debug_log", "hls_min_bitrate", "hls_max_bitrate", "hls_sample_rate",
    "podcast_auto_refresh", "podcast_refresh_interval", "service_radio_browser_servers", "service_itunes_search_url",
    "service_fyyd_search_url",
})
# RAD-11: aus dem Stand der Oberfläche in die Einstellungen; eigener Übertrag (der erste ist auf bestehenden Rechnern
# schon gelaufen), danach ebenfalls unter /api/config erreichbar
CONFIG_FELDER_RAD11: frozenset[str] = frozenset({
    "language", "ad_detection_enabled", "ad_detection_methods",
    "ad_detection_threshold", "ort_name", "ort_breite", "ort_laenge",
})
UEBERTRAEGE: tuple[tuple[str, frozenset[str]], ...] = (
    ("radiohub_config_uebertrag", CONFIG_FELDER),
    ("radiohub_config_uebertrag_rad11", CONFIG_FELDER_RAD11),
)
CONFIG_FELDER = CONFIG_FELDER | CONFIG_FELDER_RAD11 | {"hls_puffer_minuten", "werbung_ueberspringen"}
# Felder, die nur zusammen gesetzt werden dürfen (Regel in regeln_pruefen); der Übertrag setzt sie gemeinsam (RAD-90)
ZUSAMMEN: tuple[frozenset[str], ...] = (frozenset({"ort_breite", "ort_laenge"}),)


def regeln_pruefen(alt: AppEinstellungen, neu: AppEinstellungen) -> str | None:
    """Regeln über mehrere Felder (vor jedem Speichern, appkern Einstellungen.regel)."""
    if neu.hls_min_bitrate > neu.hls_max_bitrate:
        return "Die kleinste Bitrate darf nicht größer sein als die größte."
    if (neu.ort_breite is None) != (neu.ort_laenge is None):
        return "Breite und Länge des Orts gehören zusammen: beide angeben oder beide leer lassen."
    return None

_gebunden: Einstellungen[AppEinstellungen] | None = None
_gelesen: AppEinstellungen | None = None


def binden(einstellungen: Einstellungen[AppEinstellungen] | None) -> None:
    """Die Einstellungen der laufenden App (vom Gerüst); None löst die Bindung (Ende der App, Prüfungen)."""
    global _gebunden, _gelesen
    _gebunden, _gelesen = einstellungen, None


def stand() -> AppEinstellungen:
    """Der gültige Stand: in der laufenden App der des Gerüsts, sonst einmal nur lesend aus Datenbank und Umgebung."""
    global _gelesen
    if _gebunden is not None:
        return _gebunden.stand
    if _gelesen is None:
        uebergang.alte_umgebung_uebernehmen()
        _gelesen = nur_lesen(ort.geruest_ordner() / f"{KENNUNG}.sqlite", AppEinstellungen, umgebung_praefix=PRAEFIX)
    return _gelesen


def herkunft(name: str) -> str:
    """Woher ein Wert kommt (fest, gespeichert, umgebung, vorgabe); ohne laufende App unbekannt."""
    return _gebunden.herkunft(name) if _gebunden is not None else "vorgabe"


async def aendern(werte: Mapping[str, Any]) -> set[str]:
    """Ändert Einstellungen der laufenden App (alles oder nichts); `None` setzt einen Wert auf die Vorgabe zurück."""
    if _gebunden is None:
        raise RuntimeError("Einstellungen lassen sich nur in der laufenden App ändern")
    return await _gebunden.aendern(werte)
