"""Senderdaten-Baustein (RAD-7, Entscheidungen 19 und 28): macht aus einem Datensatz des Senderverzeichnisses einen
aufbereiteten Sender. Ohne FastAPI und ohne Datenbank, nur mit Pydantic und den Tabellen dieses Ordners, damit der
Abgleich im Backend und das Skript der statischen Webversion (Etappe 3b) dieselbe Aufbereitung nutzen.

    from app.senderdaten import Verzeichnisdatensatz, aufbereiten
    sender = aufbereiten(Verzeichnisdatensatz.model_validate(roh), messung)

Teile: `sprachen` (Code und deutscher Name, freier Text als eigener Eintrag), `genres` (gepflegte Abbildung, Rauschen
und Frequenzen verworfen), `qualitaet` (Codec, Bitrate in kbit/s, Stufe), `dubletten` (Gruppen und beste Variante).
`FASSUNG` steigt mit jeder Änderung an Regeln oder Tabellen; ein Bestand mit älterer Fassung wird neu aufbereitet.
"""
from __future__ import annotations

from . import dubletten, genres, qualitaet, sprachen
from .modelle import QUALITAET_RANG, Messung, Qualitaet, Sender, Sprache, Verzeichnisdatensatz

FASSUNG = 1

__all__ = ["FASSUNG", "QUALITAET_RANG", "Messung", "Qualitaet", "Sender", "Sprache", "Verzeichnisdatensatz",
           "aufbereiten", "dubletten", "genres", "qualitaet", "sprachen"]

_KEIN_LOGO = {"", "null", "none", "undefined"}


def _logo(favicon: str) -> str:
    text = favicon.strip()
    return "" if text.lower() in _KEIN_LOGO or not text.lower().startswith(("http://", "https://")) else text


def aufbereiten(roh: Verzeichnisdatensatz, messung: Messung | None = None) -> Sender:
    """Ein aufbereiteter Sender. `messung` (eigene Messung am Strom) gilt vor Bitrate und Codec des Verzeichnisses."""
    codec_verzeichnis = qualitaet.codec(roh.codec)
    kbps_verzeichnis = qualitaet.kbps_aus_verzeichnis(roh.bitrate, codec_verzeichnis)
    kbps_gemessen = messung.kbps if messung and messung.kbps and messung.kbps > 0 else None
    codec_gemessen = qualitaet.codec(messung.codec) if messung and messung.codec else qualitaet.UNBEKANNT
    codec = codec_gemessen if codec_gemessen != qualitaet.UNBEKANNT else codec_verzeichnis
    kbps = kbps_gemessen or kbps_verzeichnis
    genre_liste, tag_liste = genres.zerlegen(roh.tags)
    adresse = roh.url_resolved or roh.url
    return Sender(
        uuid=roh.stationuuid,
        name=roh.name,
        adresse=roh.url,
        adresse_aufgeloest=roh.url_resolved,
        homepage=roh.homepage,
        logo=_logo(roh.favicon),
        land=roh.countrycode.upper(),
        land_name=roh.country,
        region=roh.iso_3166_2.upper(),
        bundesland=roh.state,
        geo_breite=roh.geo_lat,
        geo_laenge=roh.geo_long,
        sprachen=sprachen.sprachen(roh.language, roh.languagecodes),
        spracheintraege=sprachen.eintraege(roh.language),
        genres=genre_liste,
        tags=tag_liste,
        codec=codec,
        kbps_verzeichnis=kbps_verzeichnis,
        kbps_gemessen=kbps_gemessen,
        kbps=kbps,
        qualitaet=qualitaet.stufe(codec, kbps),
        hls=bool(roh.hls),
        ssl_fehler=bool(roh.ssl_error),
        stimmen=max(0, roh.votes),
        klicks=max(0, roh.clickcount),
        klicktrend=roh.clicktrend,
        erreichbar=bool(roh.lastcheckok),
        erreichbar_am=roh.lastcheckoktime_iso8601,
        geaendert_am=roh.lastchangetime_iso8601,
        erweiterte_info=roh.has_extended_info,
        adresse_norm=dubletten.adresse_norm(adresse),
        name_norm=dubletten.name_norm(roh.name),
    )
