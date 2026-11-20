"""Statische Senderliste der Webversion erzeugen (RAD-4, Entscheidungen 25 und 26)

Holt das Senderverzeichnis seitenweise (oder liest die Tabelle stations einer Datenbank nur lesend), bereitet jeden
Datensatz mit dem Senderdaten-Baustein auf und schreibt nur abspielbare Sender: Stream-Adresse (aufgelöst, sonst url)
über https, bei der letzten Prüfung des Verzeichnisses erreichbar, ohne Fehler im Zertifikat. Logos nur über https
(sonst leer), denn die Webversion läuft über https und lädt keine gemischten Inhalte.

    python -m app.werkzeuge.statische_liste --aus ../web/daten
    python -m app.werkzeuge.statische_liste --aus ../web/daten --aus-datenbank data/radiohub.db

Format von sender.json (Spaltenformat, Fassung FORMAT): {"kopf": {...}, "zeilen": [[...], ...]}. Der Kopf nennt die
Fassung des Formats und der Aufbereitung, den Zeitpunkt, die Herkunft, die Anzahl, die Spalten und die Wörterbücher;
Spalten mit wiederkehrenden Werten (Land, Sprache, Genre, Tag, Codec, ...) tragen Nummern in ihr Wörterbuch, die
Gruppe der Dubletten die Zeilennummer des Senders, dessen uuid die Gruppe kennzeichnet.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from collections import Counter
from collections.abc import AsyncIterator, Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ValidationError

from .. import senderdaten
from ..senderdaten import Sender, Verzeichnisdatensatz, dubletten
from ..senderdaten import sprachen as sprachtabelle
from ..services.senderquelle import abgleich, bestand

FORMAT = 1
DATEI = "sender.json"
SICHER = "https://"
# Gedankenstriche und typografische Anführungszeichen in Namen des Verzeichnisses schreibt die Datei als
# JSON-Escape: die Daten bleiben gleich, die Datei selbst enthält nur gerade Zeichen (Prüfung im Git-Haken)
_ALS_ESCAPE = {ord(z): f"\\u{ord(z):04x}" for z in "\u2013\u2014\u2018\u2019\u201c\u201d\u201e"}

# Spalten einer Zeile in dieser Reihenfolge; die mit Wörterbuch stehen in WOERTERBUCH_SPALTEN
SPALTEN: tuple[str, ...] = (
    "uuid", "name", "adresse", "adresse_aufgeloest", "logo", "homepage", "land", "land_name", "region", "bundesland",
    "sprachen", "spracheintraege", "genres", "tags", "codec", "kbps", "qualitaet", "stimmen", "hls", "gruppe",
)
# Spalte -> Wörterbuch (einzelner Wert oder Liste von Werten)
WOERTERBUCH_SPALTEN: dict[str, str] = {
    "land": "land", "land_name": "land_name", "region": "region", "bundesland": "bundesland", "sprachen": "sprache",
    "spracheintraege": "spracheintrag", "genres": "genre", "tags": "tag", "codec": "codec", "qualitaet": "qualitaet",
}

# Eine Zeile: Texte, Nummern in die Wörterbücher, Zahlen; kbps 0 heißt ohne Angabe, adresse_aufgeloest "" heißt
# wie adresse, hls 0 oder 1
Zeile = tuple[str, str, str, str, str, str, int, int, int, int, list[int], list[int], list[int], list[int], int, int,
              int, int, int, int]


class Kopf(BaseModel):
    format: int = FORMAT
    aufbereitung: int                       # senderdaten.FASSUNG
    erzeugt: str                            # ISO 8601, UTC
    quelle: Literal["verzeichnis", "datenbank"]
    anzahl: int
    spalten: list[str]
    woerter: dict[str, list[str]]           # Wörterbuch -> Werte, häufigste zuerst
    sprachnamen: dict[str, str]             # Code der Sprachtabelle -> deutscher Name (nur Codes der Liste)
    eintragscodes: dict[str, str]           # genauer Spracheintrag der Liste -> Code, wenn die Tabelle ihn kennt


class StatischeListe(BaseModel):
    kopf: Kopf
    zeilen: list[Zeile]


class Bericht(BaseModel):
    gelesen: int
    geschrieben: int
    datei: str
    bytes: int


# ----- Auswahl -----------------------------------------------------------------------------------------------------------

def abspielbar(d: Verzeichnisdatensatz) -> bool:
    """Spielt direkt im Browser über https: Adresse sicher, zuletzt erreichbar, Zertifikat in Ordnung."""
    adresse = (d.url_resolved or d.url).strip()
    return adresse.lower().startswith(SICHER) and bool(d.lastcheckok) and not d.ssl_error


def sicheres_logo(logo: str) -> str:
    return logo if logo.lower().startswith(SICHER) else ""


# ----- Quellen ------------------------------------------------------------------------------------------------------------

def _datensaetze(roh: Iterable[dict]) -> Iterator[Verzeichnisdatensatz]:
    for eintrag in roh:
        try:
            yield Verzeichnisdatensatz.model_validate(eintrag)
        except ValidationError:
            continue


async def aus_verzeichnis(transport: httpx.AsyncBaseTransport | None = None,
                          server: list[str] | None = None) -> AsyncIterator[Verzeichnisdatensatz]:
    """Das ganze Verzeichnis seitenweise über die Server der Einstellung (wie der Abgleich, mit Ausweichserver)."""
    liste = server if server is not None else abgleich.server_liste()
    if not liste:
        raise SystemExit("Kein Server des Senderverzeichnisses eingestellt (service_radio_browser_servers)")
    nummer, versatz = 0, 0
    async with abgleich.client_fabrik(transport)() as client:
        while True:
            roh, nummer = await abgleich.seite_laden(client, liste, nummer, versatz)
            for d in _datensaetze(roh):
                yield d
            if len(roh) < abgleich.SEITE:
                return
            versatz += abgleich.SEITE


def aus_datenbank(pfad: Path) -> Iterator[Verzeichnisdatensatz]:
    """Die Tabelle stations einer Datenbank nur lesend, ohne verschwundene Sender."""
    if not pfad.is_file():
        raise SystemExit(f"Datenbank nicht gefunden: {pfad}")
    verbindung = sqlite3.connect(f"{pfad.resolve().as_uri()}?mode=ro", uri=True)
    verbindung.row_factory = sqlite3.Row
    try:
        for zeile in verbindung.execute("SELECT * FROM stations WHERE verschwunden_am IS NULL ORDER BY uuid"):
            try:
                yield bestand.datensatz(zeile)
            except ValidationError:
                continue
    finally:
        verbindung.close()


# ----- Liste bauen --------------------------------------------------------------------------------------------------------

class _Woerterbuecher:
    """Zählt die Werte je Wörterbuch und vergibt danach Nummern, häufigste zuerst (kleine Nummern, kleine Datei)."""

    def __init__(self) -> None:
        self.zaehler: dict[str, Counter[str]] = {w: Counter() for w in dict.fromkeys(WOERTERBUCH_SPALTEN.values())}
        self.nummern: dict[str, dict[str, int]] = {}

    def zaehlen(self, woerterbuch: str, werte: Iterable[str]) -> None:
        self.zaehler[woerterbuch].update(werte)

    def festlegen(self) -> dict[str, list[str]]:
        werte = {w: [x for x, _ in sorted(z.items(), key=lambda p: (-p[1], p[0]))] for w, z in self.zaehler.items()}
        self.nummern = {w: {x: n for n, x in enumerate(liste)} for w, liste in werte.items()}
        return werte

    def nummer(self, woerterbuch: str, wert: str) -> int:
        return self.nummern[woerterbuch][wert]

    def liste(self, woerterbuch: str, werte: Iterable[str]) -> list[int]:
        return [self.nummern[woerterbuch][x] for x in werte]


def _werte(s: Sender) -> dict[str, list[str]]:
    """Die Werte eines Senders je Wörterbuch."""
    return {"land": [s.land], "land_name": [s.land_name], "region": [s.region], "bundesland": [s.bundesland],
            "sprache": [x.schluessel for x in s.sprachen], "spracheintrag": s.spracheintraege, "genre": s.genres,
            "tag": s.tags, "codec": [s.codec], "qualitaet": [s.qualitaet]}


def _zeile(s: Sender, w: _Woerterbuecher, gruppe: int) -> Zeile:
    return (s.uuid, s.name, s.adresse, "" if s.adresse_aufgeloest == s.adresse else s.adresse_aufgeloest,
            sicheres_logo(s.logo), s.homepage, w.nummer("land", s.land), w.nummer("land_name", s.land_name),
            w.nummer("region", s.region), w.nummer("bundesland", s.bundesland),
            w.liste("sprache", [x.schluessel for x in s.sprachen]), w.liste("spracheintrag", s.spracheintraege),
            w.liste("genre", s.genres), w.liste("tag", s.tags), w.nummer("codec", s.codec), s.kbps or 0,
            w.nummer("qualitaet", s.qualitaet), s.stimmen, int(s.hls), gruppe)


def _sprachnamen(sender: list[Sender]) -> dict[str, str]:
    namen = sprachtabelle.tabelle().namen
    codes = sorted({x.schluessel for s in sender for x in s.sprachen if x.code and x.schluessel in namen})
    return {c: namen[c] for c in codes}


def _eintragscodes(sender: list[Sender]) -> dict[str, str]:
    eintraege = sorted({e for s in sender for e in s.spracheintraege})
    return {e: c for e in eintraege if (c := sprachtabelle.code_von(e))}


def liste_bauen(saetze: Iterable[Verzeichnisdatensatz], quelle: Literal["verzeichnis", "datenbank"],
                zeit: datetime | None = None) -> tuple[StatischeListe, int]:
    """Die statische Liste aus den Datensätzen (je uuid der erste) und die Zahl der gelesenen Datensätze."""
    gelesen = 0
    nach_uuid: dict[str, Sender] = {}
    for d in saetze:
        gelesen += 1
        if d.stationuuid and d.stationuuid not in nach_uuid and abspielbar(d):
            nach_uuid[d.stationuuid] = senderdaten.aufbereiten(d)
    sender = [nach_uuid[u] for u in sorted(nach_uuid)]
    # Varianten innerhalb der Liste: die Webversion kennt nur diese Sender
    gruppen = dubletten.gruppen(dubletten.Gruppenglied(s.uuid, s.adresse_norm, s.name_norm, s.land) for s in sender)
    zeilennummer = {s.uuid: n for n, s in enumerate(sender)}
    w = _Woerterbuecher()
    for s in sender:
        for woerterbuch, werte in _werte(s).items():
            w.zaehlen(woerterbuch, werte)
    woerter = w.festlegen()
    zeilen = [_zeile(s, w, zeilennummer[gruppen[s.uuid]]) for s in sender]
    kopf = Kopf(aufbereitung=senderdaten.FASSUNG, quelle=quelle, anzahl=len(zeilen), spalten=list(SPALTEN),
                erzeugt=(zeit or datetime.now(timezone.utc)).isoformat(timespec="seconds"), woerter=woerter,
                sprachnamen=_sprachnamen(sender), eintragscodes=_eintragscodes(sender))
    return StatischeListe.model_construct(kopf=kopf, zeilen=zeilen), gelesen


def schreiben(liste: StatischeListe, ordner: Path) -> Path:
    """Schreibt sender.json kompakt (ohne Leerraum) über eine Zwischendatei."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / DATEI
    zwischen = ziel.with_suffix(".json.neu")
    daten = {"kopf": liste.kopf.model_dump(), "zeilen": liste.zeilen}
    text = json.dumps(daten, ensure_ascii=False, separators=(",", ":")).translate(_ALS_ESCAPE)
    zwischen.write_text(text, encoding="utf-8")
    zwischen.replace(ziel)
    return ziel


async def _alle(quelle: AsyncIterator[Verzeichnisdatensatz]) -> list[Verzeichnisdatensatz]:
    return [d async for d in quelle]


def erzeugen(ordner: Path, datenbank: Path | None = None) -> Bericht:
    if datenbank is not None:
        liste, gelesen = liste_bauen(aus_datenbank(datenbank), "datenbank")
    else:
        try:
            saetze = asyncio.run(_alle(aus_verzeichnis()))
        except abgleich.AuftragFehler as f:
            raise SystemExit(str(f)) from f
        liste, gelesen = liste_bauen(saetze, "verzeichnis")
    ziel = schreiben(liste, ordner)
    return Bericht(gelesen=gelesen, geschrieben=liste.kopf.anzahl, datei=str(ziel), bytes=ziel.stat().st_size)


def main() -> None:
    teiler = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    teiler.add_argument("--aus", required=True, type=Path, help="Ordner für sender.json")
    teiler.add_argument("--aus-datenbank", type=Path, default=None,
                        help="statt des Verzeichnisses die Tabelle stations dieser Datenbank (nur lesend)")
    argumente = teiler.parse_args()
    bericht = erzeugen(argumente.aus, argumente.aus_datenbank)
    print(f"{bericht.geschrieben} abspielbare von {bericht.gelesen} Sendern nach {bericht.datei} "
          f"({bericht.bytes / 1_000_000:.1f} MB)")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
