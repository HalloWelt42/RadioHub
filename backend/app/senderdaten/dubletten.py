"""Dubletten und Varianten: rund 12.000 Sender (20 %) stehen mehrfach im Verzeichnis, mal mit demselben Strom, mal als
derselbe Sender in anderer Qualität ("Deutschlandfunk | DLF | MP3 128k" und "... | AAC 256k"). Eine Gruppe verbindet
Sender mit derselben normalisierten Stream-Adresse und, sonst, mit demselben bereinigten Namen im selben Land. Die beste
Variante steht vorn: Qualitätsstufe, dann Bitrate, dann erreichbar, dann Stimmen."""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit

# Anhänge, die nur zählen oder werben, aber denselben Strom liefern
_ZAEHLANHAENGE = {"aggregator", "ref", "source", "src", "from", "utm_source", "utm_medium", "utm_campaign",
                  "listening-from-radio-garden", "_ic2", "icy", "type", "awparams", "partnertok", "dist", "aw_0_1st.playerid"}
_STANDARDPORTS = {"http": 80, "https": 443}

# Angaben zu Codec, Bitrate und Strom in Namen ("MP3 128k", "AAC+ 64 kbps", "(HQ)", "HLS")
_NAMENSZUSATZ = re.compile(
    r"\b(mp3|aac\+?|aacp|he-aac|ogg|vorbis|opus|flac|hls|icecast|shoutcast|stream|ssl|https?|hq|lq|hd|hifi|"
    r"\d{2,4}\s*(k|kb|kbps|kbit|kbit/s))\b")
# Namen, die nach dem Bereinigen nichts mehr unterscheiden, verbinden keine Sender
_ALLGEMEIN = {"radio", "web radio", "webradio", "fm", "music", "musik", "live", "online", "test", "stream"}
_NICHT_WORT = re.compile(r"[^\w]+")


def adresse_norm(adresse: str) -> str:
    """Stream-Adresse in Vergleichsform: ohne Schema, Host klein, ohne Standardport und Schrägstrich am Ende, ohne
    Zählanhänge; übrige Anhänge sortiert. Leer, wenn keine brauchbare Adresse da ist."""
    text = (adresse or "").strip()
    if not text:
        return ""
    try:
        teile = urlsplit(text)
        port = teile.port
    except ValueError:
        return text.lower()
    if not teile.hostname:
        return text.lower()
    host = teile.hostname.lower()
    if port and port != _STANDARDPORTS.get(teile.scheme.lower()):
        host = f"{host}:{port}"
    pfad = teile.path.rstrip("/")
    anhaenge = sorted((k, v) for k, v in parse_qsl(teile.query, keep_blank_values=True) if k.lower() not in _ZAEHLANHAENGE)
    return host + pfad + (f"?{urlencode(anhaenge)}" if anhaenge else "")


def name_norm(name: str) -> str:
    """Name ohne Angaben zu Codec, Bitrate und Strom, klein, nur Wörter."""
    text = _NAMENSZUSATZ.sub(" ", (name or "").lower())
    return " ".join(w for w in _NICHT_WORT.split(text) if w)


@dataclass(frozen=True)
class Gruppenglied:
    uuid: str
    adresse_norm: str
    name_norm: str
    land: str


def gruppen(glieder: Iterable[Gruppenglied]) -> dict[str, str]:
    """Gruppe je Sender (Kennung der Gruppe: die kleinste uuid ihrer Glieder). Verbunden ist, wer dieselbe Adresse
    hat oder denselben Namen im selben Land (ein leerer Name verbindet nichts)."""
    eltern: dict[str, str] = {}

    def wurzel(u: str) -> str:
        while eltern[u] != u:
            eltern[u] = eltern[eltern[u]]
            u = eltern[u]
        return u

    def verbinden(a: str, b: str) -> None:
        wa, wb = wurzel(a), wurzel(b)
        if wa != wb:
            eltern[max(wa, wb)] = min(wa, wb)

    erste: dict[tuple[str, str], str] = {}
    for g in glieder:
        eltern.setdefault(g.uuid, g.uuid)
        schluessel = [("a", g.adresse_norm)] if g.adresse_norm else []
        if len(g.name_norm) >= 3 and g.name_norm not in _ALLGEMEIN:
            schluessel.append(("n", f"{g.land}|{g.name_norm}"))
        for s in schluessel:
            if s in erste:
                verbinden(erste[s], g.uuid)
            else:
                erste[s] = g.uuid
    return {u: wurzel(u) for u in eltern}


def rang(qualitaet_rang: int, kbps: int | None, erreichbar: bool, stimmen: int) -> tuple[int, int, int, int]:
    """Sortierschlüssel der besten Variante (größer ist besser)."""
    return qualitaet_rang, kbps or 0, int(erreichbar), stimmen
