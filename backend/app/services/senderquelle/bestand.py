"""Senderbestand: die Tabelle stations (Verzeichnis, wie geliefert) und was der Senderdaten-Baustein daraus macht
(sender_index mit den Feldern der Abfrage, sender_genre, sender_sprache, sender_spracheintrag, sender_tag und die
Volltextsuche sender_suche). Die Aufbereitung rechnet außerhalb der Schreibsperre und schreibt dann in einem Zug;
`nr` bleibt je Sender gleich, die Treffer der Regeln hängen daran."""
from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone

from ... import senderdaten
from ...senderdaten import Messung, Sender, Verzeichnisdatensatz, dubletten
from ...senderdaten.anpassung import Anpassung

log = logging.getLogger("radiohub.senderquelle")

FASSUNG_SCHLUESSEL = "aufbereitung_fassung"      # in cache_meta: Fassung des Bausteins, mit der aufbereitet wurde
ABGLEICH_SCHLUESSEL = "abgleich_zuletzt"         # in cache_meta: Ende des letzten vollständigen Abgleichs

# Spalten von stations -> Felder des Verzeichnisses
_FELDER = {"uuid": "stationuuid", "lastcheckoktime": "lastcheckoktime_iso8601",
           "lastchangetime": "lastchangetime_iso8601"}


def jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def datensatz(zeile: sqlite3.Row | dict) -> Verzeichnisdatensatz:
    """Ein Datensatz des Verzeichnisses aus einer Zeile von stations."""
    werte = {_FELDER.get(k, k): zeile[k] for k in zeile.keys()}
    return Verzeichnisdatensatz.model_validate(werte)


def messungen(v: sqlite3.Connection) -> dict[str, Messung]:
    return {z[0]: Messung(kbps=z[1] or None, codec=z[2] or "")
            for z in v.execute("SELECT uuid, bitrate, codec FROM detected_bitrates")}


def alle_aufbereiten(v: sqlite3.Connection) -> tuple[list[Sender], set[str]]:
    """Alle Sender aufbereitet (lesend) und die uuids der verschwundenen."""
    gemessen = messungen(v)
    sender, verschwunden = [], set()
    for zeile in v.execute("SELECT * FROM stations"):
        s = senderdaten.aufbereiten(datensatz(zeile), gemessen.get(zeile["uuid"]))
        sender.append(s)
        if zeile["verschwunden_am"]:
            verschwunden.add(s.uuid)
    return sender, verschwunden


def _suchtext(s: Sender) -> str:
    teile = [s.name, *s.genres, *s.tags, s.bundesland, s.land_name, *(x.name for x in s.sprachen)]
    return " ".join(t for t in teile if t)


def index_schreiben(v: sqlite3.Connection, sender: list[Sender], verschwunden: set[str]) -> int:
    """Schreibt die Aufbereitung (in der Transaktion des Aufrufers). Sichtbarkeit und Treffer rechnet danach
    `sichtbarkeit.neu_berechnen`. Liefert die Zahl der Sender."""
    gruppe = dubletten.gruppen(dubletten.Gruppenglied(s.uuid, s.adresse_norm, s.name_norm, s.land) for s in sender)
    v.executemany(
        """INSERT INTO sender_index (uuid, name_klein, land, codec, kbps, kbps_gemessen, qualitaet, qualitaet_rang,
                                     stimmen, erreichbar, gruppe, sprachen, genres, verschwunden)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(uuid) DO UPDATE SET name_klein = excluded.name_klein, land = excluded.land,
               codec = excluded.codec, kbps = excluded.kbps, kbps_gemessen = excluded.kbps_gemessen,
               qualitaet = excluded.qualitaet, qualitaet_rang = excluded.qualitaet_rang, stimmen = excluded.stimmen,
               erreichbar = excluded.erreichbar, gruppe = excluded.gruppe, sprachen = excluded.sprachen,
               genres = excluded.genres, verschwunden = excluded.verschwunden""",
        [(s.uuid, s.name.casefold().strip(), s.land, s.codec, s.kbps or 0, s.kbps_gemessen, s.qualitaet, s.qualitaet_rang,
          s.stimmen, int(s.erreichbar), gruppe[s.uuid],
          json.dumps([[x.schluessel, x.name] for x in s.sprachen], ensure_ascii=False),
          json.dumps(s.genres, ensure_ascii=False), int(s.uuid in verschwunden)) for s in sender])
    # Was es in stations nicht mehr gibt (dort wird nie gelöscht, nur in Tests und von Hand), fällt auch hier weg
    weg = [z[0] for z in v.execute("SELECT nr FROM sender_index WHERE uuid NOT IN (SELECT uuid FROM stations)")]
    if weg:
        v.execute("DELETE FROM sender_ausblendung WHERE nr IN (SELECT value FROM json_each(?))", (json.dumps(weg),))
        v.execute("DELETE FROM sender_index WHERE nr IN (SELECT value FROM json_each(?))", (json.dumps(weg),))
    nr = {u: n for u, n in v.execute("SELECT uuid, nr FROM sender_index")}
    for tabelle in ("sender_genre", "sender_sprache", "sender_spracheintrag", "sender_tag"):
        v.execute(f"DELETE FROM {tabelle}")
    v.executemany("INSERT OR IGNORE INTO sender_genre (genre, nr) VALUES (?, ?)",
                  [(g, nr[s.uuid]) for s in sender for g in s.genres])
    v.executemany("INSERT OR IGNORE INTO sender_sprache (schluessel, nr) VALUES (?, ?)",
                  [(x.schluessel, nr[s.uuid]) for s in sender for x in s.sprachen])
    v.executemany("INSERT OR IGNORE INTO sender_spracheintrag (eintrag, nr) VALUES (?, ?)",
                  [(e, nr[s.uuid]) for s in sender for e in s.spracheintraege])
    v.executemany("INSERT OR IGNORE INTO sender_tag (tag, nr) VALUES (?, ?)",
                  [(t, nr[s.uuid]) for s in sender for t in s.tags])
    v.execute("INSERT INTO sender_suche (sender_suche) VALUES ('delete-all')")
    v.executemany("INSERT INTO sender_suche (rowid, text) VALUES (?, ?)", [(nr[s.uuid], _suchtext(s)) for s in sender])
    v.execute("INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)", (FASSUNG_SCHLUESSEL, str(senderdaten.FASSUNG)))
    for tabelle in ("sender_index", "sender_genre", "sender_sprache", "sender_spracheintrag", "sender_tag"):
        v.execute(f"ANALYZE {tabelle}")
    return len(sender)


def aufbereitung_noetig(v: sqlite3.Connection) -> str | None:
    """Grund, den Bestand neu aufzubereiten ("leer", "fassung", "bestand"); None, wenn er passt."""
    stationen = v.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    index = v.execute("SELECT COUNT(*) FROM sender_index").fetchone()[0]
    if stationen and not index:
        return "leer"
    zeile = v.execute("SELECT value FROM cache_meta WHERE key = ?", (FASSUNG_SCHLUESSEL,)).fetchone()
    if stationen and (not zeile or zeile[0] != str(senderdaten.FASSUNG)):
        return "fassung"
    if stationen != index:
        return "bestand"
    return None


def angepasst(v: sqlite3.Connection, anpassung: Anpassung) -> list[str]:
    """uuids im Bestand, die nach der Anpassung nicht zum Katalog gehören."""
    return [z[0] for z in v.execute("SELECT uuid FROM stations") if anpassung.trifft(z[0])]


def anpassen(v: sqlite3.Connection, anpassung: Anpassung) -> int:
    """Nimmt Sender, die nach der Anpassung nicht zum Katalog gehören, aus stations (in der Transaktion des Aufrufers);
    `index_schreiben` lässt sie danach auch in der Aufbereitung weg. Eigene Daten (Favoriten, Sperren) bleiben."""
    weg = angepasst(v, anpassung)
    if weg:
        v.execute("DELETE FROM stations WHERE uuid IN (SELECT value FROM json_each(?))", (json.dumps(weg),))
    return len(weg)


# ----- Abgleich mit dem Verzeichnis -------------------------------------------------------------------------------------

_SPALTEN = ("uuid", "name", "url", "url_resolved", "favicon", "country", "countrycode", "language", "tags", "codec",
            "bitrate", "votes", "clickcount", "homepage", "lastcheck", "cached_at", "last_seen", "languagecodes",
            "iso_3166_2", "state", "geo_lat", "geo_long", "hls", "ssl_error", "clicktrend", "lastcheckok",
            "lastcheckoktime", "lastchangetime", "has_extended_info", "verschwunden_am")


def stationen_speichern(v: sqlite3.Connection, datensaetze: Iterable[Verzeichnisdatensatz], zeit: str,
                        anpassung: Anpassung | None = None) -> int:
    """Übernimmt Datensätze des Verzeichnisses in stations (neu oder aktualisiert, nie ersetzt); wer geliefert wird,
    ist nicht verschwunden. Was die Anpassung trifft, kommt nicht hinein."""
    if anpassung is not None:
        datensaetze = [d for d in datensaetze if not anpassung.trifft(d.stationuuid)]
    zeilen = [(d.stationuuid, d.name, d.url, d.url_resolved, d.favicon, d.country, d.countrycode, d.language, d.tags,
               d.codec, d.bitrate, d.votes, d.clickcount, d.homepage, str(d.lastcheckok), zeit, zeit, d.languagecodes,
               d.iso_3166_2, d.state, d.geo_lat, d.geo_long, d.hls, d.ssl_error, d.clicktrend, d.lastcheckok,
               d.lastcheckoktime_iso8601, d.lastchangetime_iso8601, int(d.has_extended_info), None)
              for d in datensaetze if d.stationuuid]
    platz = ", ".join("?" * len(_SPALTEN))
    aendern = ", ".join(f"{s} = excluded.{s}" for s in _SPALTEN if s not in ("uuid", "cached_at"))
    v.executemany(f"INSERT INTO stations ({', '.join(_SPALTEN)}) VALUES ({platz}) "
                  f"ON CONFLICT(uuid) DO UPDATE SET {aendern}", zeilen)
    return len(zeilen)


def verschwundene_markieren(v: sqlite3.Connection, seit: str, zeit: str) -> int:
    """Wer seit `seit` nicht mehr geliefert wurde, gilt als verschwunden (bleibt im Bestand, wird nicht gelöscht)."""
    return v.execute("UPDATE stations SET verschwunden_am = ? WHERE verschwunden_am IS NULL "
                     "AND (last_seen IS NULL OR last_seen < ?)", (zeit, seit)).rowcount
