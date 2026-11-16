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
from typing import Any

from pydantic import Field

from appkern.app import Grundeinstellungen
from appkern.einstellungen import Einstellungen, nur_lesen

from . import ort, uebergang

KENNUNG = "radiohub"
PRAEFIX = f"{KENNUNG.upper()}_"

ABLAGE = {"gruppe": "Ablage"}
AUFNAHME = {"gruppe": "Aufnahme"}
ZEITVERSATZ = {"gruppe": "Zeitversatz"}
PODCASTS = {"gruppe": "Podcasts"}
WECKER = {"gruppe": "Wecker"}
DIENSTE = {"gruppe": "Dienste"}

RADIO_BROWSER = ["https://de1.api.radio-browser.info", "https://at1.api.radio-browser.info",
                 "https://nl1.api.radio-browser.info"]


class AppEinstellungen(Grundeinstellungen):
    # --- Ablage in der Kellerwolke (früher RADIOHUB_KELLERWOLKE_WURZEL und _GEDULD_S) ---
    kellerwolke_wurzel: str = Field("Apps/RadioHub", min_length=1, max_length=200, title="Ordner in der Kellerwolke",
                                    json_schema_extra=ABLAGE,
                                    description="Wurzelordner der Aufnahmen, Podcast-Folgen und Bausteine der Zeitansage "
                                                "in der Kellerwolke.")
    kellerwolke_geduld_s: float = Field(900.0, ge=0, le=86400, title="Geduld beim Ablegen",
                                        json_schema_extra={**ABLAGE, "einheit": "Sekunden"},
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
    zeitstimme: str = Field("", max_length=200, title="Zeit-Stimme", json_schema_extra=WECKER,
                            description="Kennung der Stimme für die Zeitansage; in der Vertonung für RadioHub freigeben.")
    zeitstimme_tempo: float = Field(1.0, ge=0.5, le=2.0, title="Tempo der Zeit-Stimme",
                                    json_schema_extra={**WECKER, "schritt": 0.05},
                                    description="1,0 ist das Tempo der Stimme; kleiner spricht langsamer.")
    # --- Zugriff (früher ALLOWED_ORIGINS) ---
    erlaubte_urspruenge: list[str] = Field(default_factory=list, title="Fremde Ursprünge",
                                           json_schema_extra={"gruppe": "Zugang"},
                                           description="Nur nötig, wenn eine fremde Seite die Schnittstelle im Browser "
                                                       "nutzen soll (etwa https://rechner:5180); nie *. Leer: die "
                                                       "Oberfläche spricht über denselben Ursprung. Gilt nach einem "
                                                       "Neustart.")
    # --- früher in der Tabelle config ---
    recording_bitrate: int = Field(192, ge=8, le=512, title="Bitrate der Aufnahme",
                                   json_schema_extra={**AUFNAHME, "einheit": "kbit/s"},
                                   description="Bitrate, mit der eine Aufnahme gespeichert wird, wenn der Sender sie "
                                               "nicht selbst vorgibt.")
    recording_debug_log: bool = Field(False, title="Aufnahme protokollieren", json_schema_extra=AUFNAHME,
                                      description="Schreibt zu jeder Aufnahme ein Protokoll der Ereignisse (Start, "
                                                  "Stocken, Größe, Ende) neben die Aufnahme, für die Fehlersuche.")
    hls_min_bitrate: int = Field(32, ge=8, le=512, title="Kleinste Bitrate",
                                 json_schema_extra={**ZEITVERSATZ, "einheit": "kbit/s"},
                                 description="Untergrenze der Bitrate im Zeitversatz.")
    hls_max_bitrate: int = Field(320, ge=8, le=512, title="Größte Bitrate",
                                 json_schema_extra={**ZEITVERSATZ, "einheit": "kbit/s"},
                                 description="Obergrenze der Bitrate im Zeitversatz; schwächere Sender werden nicht "
                                             "aufgebläht.")
    hls_sample_rate: int = Field(44100, ge=8000, le=192000, title="Abtastrate",
                                 json_schema_extra={**ZEITVERSATZ, "einheit": "Hz"},
                                 description="Abtastrate des Zeitversatzes.")
    podcast_auto_refresh: bool = Field(True, title="Abos von selbst abrufen", json_schema_extra=PODCASTS,
                                       description="Ruft die Feeds aller Abos regelmäßig ab.")
    podcast_refresh_interval: int = Field(21600, ge=60, le=7 * 86400, title="Abstand des Abrufs",
                                          json_schema_extra={**PODCASTS, "einheit": "Sekunden", "schritt": 3600},
                                          description="So viele Sekunden liegen zwischen zwei Abrufen der Feeds.")
    service_radio_browser_servers: list[str] = Field(default_factory=lambda: list(RADIO_BROWSER),
                                                     title="Senderverzeichnis", json_schema_extra=DIENSTE,
                                                     description="Server des Senderverzeichnisses, in dieser Reihenfolge "
                                                                 "gefragt.")
    service_itunes_search_url: str = Field("https://itunes.apple.com/search", title="Podcast-Suche (Apple)",
                                           json_schema_extra=DIENSTE, description="Suche im Podcast-Verzeichnis von Apple.")
    service_fyyd_search_url: str = Field("https://api.fyyd.de/0.2/search/podcast", title="Podcast-Suche (fyyd)",
                                         json_schema_extra=DIENSTE, description="Suche im deutschen Podcast-Verzeichnis fyyd.")


# Felder, die früher in der Tabelle config standen; über /api/config bleiben sie unter diesen Schlüsseln lesbar und
# änderbar (die heutige Oberfläche nutzt das bis Teil 2c)
CONFIG_FELDER: frozenset[str] = frozenset({
    "recording_bitrate", "recording_debug_log", "hls_min_bitrate", "hls_max_bitrate", "hls_sample_rate",
    "podcast_auto_refresh", "podcast_refresh_interval", "service_radio_browser_servers", "service_itunes_search_url",
    "service_fyyd_search_url",
})

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
