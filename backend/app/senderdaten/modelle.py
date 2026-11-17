"""Modelle des Senderdaten-Bausteins: der rohe Datensatz des Senderverzeichnisses und der aufbereitete Sender."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

Qualitaet = Literal["verlustfrei", "hoch", "mittel", "niedrig", "unbekannt"]

# Rang einer Qualitätsstufe (höher ist besser); Grundlage der Sortierung und der besten Variante
QUALITAET_RANG: dict[str, int] = {"verlustfrei": 4, "hoch": 3, "mittel": 2, "niedrig": 1, "unbekannt": 0}

_TEXTE = ("stationuuid", "name", "url", "url_resolved", "homepage", "favicon", "tags", "country", "countrycode",
          "iso_3166_2", "state", "language", "languagecodes", "codec", "lastchangetime_iso8601",
          "lastcheckoktime_iso8601")
_ZAHLEN = ("votes", "bitrate", "hls", "lastcheckok", "clickcount", "clicktrend", "ssl_error")


class Verzeichnisdatensatz(BaseModel):
    """Ein Sender, wie ihn das Senderverzeichnis liefert (/json/stations). Fehlende oder leere Werte werden zu "" bzw.
    0; unbekannte Felder werden übergangen."""

    model_config = ConfigDict(extra="ignore")

    stationuuid: str
    name: str = ""
    url: str = ""
    url_resolved: str = ""
    homepage: str = ""
    favicon: str = ""
    tags: str = ""
    country: str = ""
    countrycode: str = ""
    iso_3166_2: str = ""
    state: str = ""
    language: str = ""
    languagecodes: str = ""
    votes: int = 0
    codec: str = ""
    bitrate: int = 0
    hls: int = 0
    lastcheckok: int = 0
    lastcheckoktime_iso8601: str = ""
    lastchangetime_iso8601: str = ""
    clickcount: int = 0
    clicktrend: int = 0
    ssl_error: int = 0
    geo_lat: float | None = None
    geo_long: float | None = None
    has_extended_info: bool = False

    @field_validator(*_TEXTE, mode="before")
    @classmethod
    def _text(cls, wert: Any) -> str:
        return "" if wert is None else str(wert).strip()

    @field_validator(*_ZAHLEN, mode="before")
    @classmethod
    def _zahl(cls, wert: Any) -> int:
        try:
            return int(wert or 0)
        except (TypeError, ValueError):
            return 0

    @field_validator("geo_lat", "geo_long", mode="before")
    @classmethod
    def _ort(cls, wert: Any) -> float | None:
        try:
            return None if wert in (None, "") else float(wert)
        except (TypeError, ValueError):
            return None

    @field_validator("has_extended_info", mode="before")
    @classmethod
    def _wahr(cls, wert: Any) -> bool:
        return str(wert).lower() in ("1", "true")


class Messung(BaseModel):
    """Was die eigene Messung am Strom ergab (Tabelle detected_bitrates); gilt vor der Angabe des Verzeichnisses."""

    kbps: int | None = None
    codec: str = ""


class Sprache(BaseModel):
    """Eine Sprache eines Senders. Mit Code (ISO 639) und sauberem deutschem Namen, wenn der Eintrag bekannt ist;
    sonst ein Eintrag aus freiem Text (code None, name ist der Eintrag). `eintrag` ist der Text im Verzeichnis, aus
    dem die Sprache stammt (None, wenn sie nur aus languagecodes kommt)."""

    schluessel: str             # Code oder "frei:<eintrag>"
    code: str | None
    name: str
    eintrag: str | None


class Sender(BaseModel):
    """Ein aufbereiteter Sender: alle nützlichen Felder des Verzeichnisses, dazu Sprachen, Genres, Bitrate in kbit/s,
    Qualitätsstufe und die Schlüssel für Dubletten."""

    uuid: str
    name: str
    adresse: str
    adresse_aufgeloest: str
    homepage: str
    logo: str
    land: str                   # ISO 3166-1, groß; "" ohne Angabe
    land_name: str
    region: str                 # ISO 3166-2, etwa DE-BE
    bundesland: str
    geo_breite: float | None
    geo_laenge: float | None
    sprachen: list[Sprache]
    spracheintraege: list[str]  # die Einträge des Verzeichnisses (klein, ohne Rand): für Regeln auf genaue Einträge
    genres: list[str]
    tags: list[str]             # Einträge ohne Rauschen und Frequenzen, klein
    codec: str                  # MP3, AAC, OGG, OPUS, FLAC, ... oder "unbekannt"
    kbps_verzeichnis: int | None
    kbps_gemessen: int | None
    kbps: int | None            # gemessen vor Verzeichnis
    qualitaet: Qualitaet
    hls: bool
    ssl_fehler: bool
    stimmen: int
    klicks: int
    klicktrend: int
    erreichbar: bool            # lastcheckok
    erreichbar_am: str          # lastcheckoktime (ISO 8601) oder ""
    geaendert_am: str
    erweiterte_info: bool
    adresse_norm: str           # für Dubletten: Strom ohne Schema, Standardport und Zählanhänge
    name_norm: str              # für Dubletten: Name ohne Angaben zu Codec und Bitrate

    @property
    def qualitaet_rang(self) -> int:
        return QUALITAET_RANG[self.qualitaet]
