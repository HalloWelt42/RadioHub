"""Abfrage der Senderliste (Entscheidung 4, Vorgaben 1 bis 3): Schnellfilter über die sichtbaren Sender, Seiten per
Zeiger (Sortierwert und uuid als Nebenschlüssel), Gesamtzahl, Einträge mit allen Zusatzdaten und Facetten mit Zahlen
unter den aktiven Regeln. Alles über die Indizes von sender_index; keine Seite liest den ganzen Bestand.

Varianten: gebündelt zeigt die Liste je Gruppe nur den Vertreter (den besten sichtbaren Sender). Sobald nach Codec,
Qualität oder Bitrate gefiltert wird, zeigt sie jede passende Variante einzeln, denn genau darin unterscheiden sie sich.
"""
from __future__ import annotations

import base64
import json
import sqlite3
from dataclasses import dataclass, field

from ...senderdaten import QUALITAET_RANG
from . import sichtbarkeit
from .modelle import (BEWERTUNGEN, WERBE_STUFEN, Abfrageergebnis, Facette, Facetten, SenderEintrag, SpracheKurz,
                      StationQuery, Werbestatus)

_WERBE_NAMEN = {n: k for k, n in WERBE_STUFEN.items()}
_BEWERTUNG = "(CASE WHEN t.tag_key = 'sterne' THEN 'sterne:' || t.tag_value ELSE t.tag_key END)"

# Sortierung: Spalten mit Richtung (die letzte ist immer uuid aufsteigend)
_SORTEN: dict[str, list[tuple[str, str]]] = {
    "stimmen": [("i.stimmen", "DESC")],
    "name": [("i.name_klein", "ASC")],
    "qualitaet": [("i.qualitaet_rang", "DESC"), ("i.kbps", "DESC")],
    "bitrate": [("i.kbps", "DESC")],
}


class FalscherZeiger(ValueError):
    """Der Seitenzeiger passt nicht zur Sortierung oder ist beschädigt."""


@dataclass
class Bedingungen:
    teile: list[str] = field(default_factory=list)
    werte: list[object] = field(default_factory=list)

    def dazu(self, teil: str, *werte: object) -> None:
        self.teile.append(teil)
        self.werte.extend(werte)

    @property
    def sql(self) -> str:
        return " AND ".join(self.teile) or "1 = 1"


def _liste(werte: list[object]) -> str:
    return json.dumps(list(werte), ensure_ascii=False)


def _in(spalte: str, werte: list[object]) -> str:
    """`spalte IN (?, ?, ...)`: mit bekannter Zahl der Werte schätzt SQLite die Treffer und wählt den passenden Index
    (bei json_each nimmt es eine feste Größe an und liest im Zweifel den ganzen Bestand)."""
    return f"{spalte} IN ({', '.join('?' * len(werte))})"


def buendeln(q: StationQuery) -> bool:
    return q.varianten_buendeln and not (q.codecs or q.qualitaet or q.bitrate_min or q.bitrate_max)


def _fts(text: str) -> str:
    return '"' + text.replace('"', '""') + '"'


def _wie(text: str) -> str:
    """Teilstück für LIKE, mit maskierten Platzhaltern."""
    return "%" + text.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def suche_zerlegen(suche: str) -> tuple[str, list[str]]:
    """Suchtext und Ausschlüsse: ein Wort mit vorangestelltem Minus schließt jeden Sender aus, der es in Name, Genre,
    Tag, Ort oder Sprache hat (Nutzer 20.11.2026: "mit minus den sender wegfiltern"); ein Minus allein zählt nicht."""
    woerter = [w for w in suche.split() if w != "-"]
    aus = [w for w in woerter if w.startswith("-")]
    return " ".join(w for w in woerter if w not in aus), [w[1:] for w in aus]


# Eine Wahl in diesen Gruppen hebt die Bündelung auf (jede passende Variante erscheint); ihre Zahlen zählen darum
# ungebündelt, sonst änderte sich die Zahl am Wert beim Klick (RAD-73)
_OHNE_BUENDELUNG = frozenset({"codecs", "qualitaet"})


def bedingungen(q: StationQuery, ohne: str | None = None) -> Bedingungen:
    """WHERE-Teile der Abfrage; `ohne` lässt den Filter einer Facettengruppe weg (für deren Zahlen)."""
    b = Bedingungen()
    b.dazu("i.sichtbar = 1")
    if buendeln(q) and ohne not in _OHNE_BUENDELUNG:
        b.dazu("i.vertreter = 1")
    if q.nur_erreichbar:
        b.dazu("(i.erreichbar = 1 OR i.favorit = 1)")       # Favoriten bleiben sichtbar
    suche, ausschluesse = suche_zerlegen(q.suche)
    if len(suche) >= 3:
        b.dazu("i.nr IN (SELECT rowid FROM sender_suche WHERE sender_suche MATCH ?)", _fts(suche))
    elif suche:
        b.dazu("i.name_klein LIKE ? ESCAPE '\\'", _wie(suche))
    for wort in ausschluesse:
        if len(wort) >= 3:
            b.dazu("i.nr NOT IN (SELECT rowid FROM sender_suche WHERE sender_suche MATCH ?)", _fts(wort))
        else:
            b.dazu("i.name_klein NOT LIKE ? ESCAPE '\\'", _wie(wort))
    if q.laender and ohne != "laender":
        b.dazu(_in("i.land", q.laender), *q.laender)
    if q.genres and ohne != "genres":
        b.dazu(f"i.nr IN (SELECT nr FROM sender_genre WHERE {_in('genre', q.genres)})", *q.genres)
    if q.qualitaet and ohne != "qualitaet":
        b.dazu(_in("i.qualitaet", q.qualitaet), *q.qualitaet)
    if q.codecs and ohne != "codecs":
        b.dazu(_in("i.codec", q.codecs), *q.codecs)
    if q.bitrate_min:
        b.dazu("i.kbps >= ?", q.bitrate_min)
    if q.bitrate_max:
        b.dazu("i.kbps <= ?", q.bitrate_max)
    if q.stimmen_min:
        b.dazu("i.stimmen >= ?", q.stimmen_min)
    if q.stimmen_max is not None:
        b.dazu("i.stimmen <= ?", q.stimmen_max)
    if q.bewertungen and ohne != "bewertungen":
        b.dazu(f"i.uuid IN (SELECT t.station_uuid FROM station_tags t WHERE t.source = 'user' "
               f"AND {_BEWERTUNG} IN (SELECT value FROM json_each(?)))", _liste(q.bewertungen))
    if q.kategorien and ohne != "kategorien":
        b.dazu("i.uuid IN (SELECT station_uuid FROM category_stations WHERE category_id IN (SELECT value FROM json_each(?)))",
               _liste(q.kategorien))
    if q.nur_favoriten:
        b.dazu("i.favorit = 1")
    return b


# ----- Seitenzeiger ------------------------------------------------------------------------------------------------------

def _spalten(q: StationQuery) -> list[tuple[str, str]]:
    """Spalten und Richtungen der Ordnung; umgekehrt läuft alles von hinten, auch die uuid (derselbe Index rückwärts)."""
    spalten = [*_SORTEN[q.sortierung], ("i.uuid", "ASC")]
    return [(s, "ASC" if r == "DESC" else "DESC") for s, r in spalten] if q.umgekehrt else spalten


def _kennung(q: StationQuery) -> str:
    return f"-{q.sortierung}" if q.umgekehrt else q.sortierung


def zeiger_bauen(q: StationQuery, zeile: sqlite3.Row) -> str:
    werte = [zeile[s.split(".")[1]] for s, _ in _spalten(q)]
    roh = json.dumps([_kennung(q), *werte], ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(roh).decode().rstrip("=")


def zeiger_lesen(q: StationQuery, zeiger: str) -> list[object]:
    try:
        daten = json.loads(base64.urlsafe_b64decode(zeiger + "=" * (-len(zeiger) % 4)))
    except (ValueError, TypeError) as f:
        raise FalscherZeiger("Seitenzeiger unlesbar") from f
    if not isinstance(daten, list) or not daten or daten[0] != _kennung(q) or len(daten) != len(_spalten(q)) + 1:
        raise FalscherZeiger("Seitenzeiger passt nicht zur Sortierung")
    return daten[1:]


def _nach(b: Bedingungen, q: StationQuery, werte: list[object]) -> None:
    """Bedingung "nach dem Zeiger": (a, b, uuid) in der Richtung der Sortierung; die erste Spalte zusätzlich als
    Bereich, damit SQLite im Index springt statt zu zählen."""
    spalten = _spalten(q)
    oder: list[str] = []
    oder_werte: list[object] = []
    for n, (spalte, richtung) in enumerate(spalten):
        gleich = [f"{s} = ?" for s, _ in spalten[:n]]
        oder.append("(" + " AND ".join([*gleich, f"{spalte} {'<' if richtung == 'DESC' else '>'} ?"]) + ")")
        oder_werte += [*werte[:n], werte[n]]
    erste, richtung = spalten[0]
    b.dazu(f"{erste} {'<=' if richtung == 'DESC' else '>='} ?", werte[0])
    b.dazu("(" + " OR ".join(oder) + ")", *oder_werte)


# ----- Abfrage -----------------------------------------------------------------------------------------------------------

def _eintraege(v: sqlite3.Connection, zeilen: list[sqlite3.Row]) -> list[SenderEintrag]:
    if not zeilen:
        return []
    uuids, nrs = [z["uuid"] for z in zeilen], [z["nr"] for z in zeilen]
    u = _liste(uuids)
    kategorien: dict[str, list[int]] = {}
    for z in v.execute("""SELECT c.station_uuid, c.category_id FROM category_stations c JOIN categories k ON k.id = c.category_id
                          AND k.scope = 'radio' WHERE c.station_uuid IN (SELECT value FROM json_each(?))
                          ORDER BY k.sort_order, k.id""", (u,)):
        kategorien.setdefault(z[0], []).append(z[1])
    bewertungen: dict[str, list[str]] = {}
    for z in v.execute(f"SELECT t.station_uuid, {_BEWERTUNG} FROM station_tags t WHERE t.source = 'user' "
                       "AND t.station_uuid IN (SELECT value FROM json_each(?))", (u,)):
        if z[1] in BEWERTUNGEN:
            bewertungen.setdefault(z[0], []).append(z[1])
    entscheidung = {z[0]: z[1] for z in v.execute(
        "SELECT station_uuid, user_action FROM station_ad_status WHERE station_uuid IN (SELECT value FROM json_each(?)) "
        "AND user_action IN ('blocked', 'allowed')", (u,))}
    adressen = {z[0]: z[1] for z in v.execute(
        "SELECT station_uuid, custom_url FROM station_custom_urls WHERE station_uuid IN (SELECT value FROM json_each(?))", (u,))}
    gruende = sichtbarkeit.gruende(v, [z["nr"] for z in zeilen if z["getroffen"] or z["verschwunden"]]) if nrs else {}
    ergebnis = []
    for z in zeilen:
        e = entscheidung.get(z["uuid"])
        ergebnis.append(SenderEintrag(
            uuid=z["uuid"], name=z["name"] or "", logo=_logo(z["favicon"]), homepage=z["homepage"] or "",
            land=z["land"], land_name=z["country"] or "", region=(z["iso_3166_2"] or "").upper(), bundesland=z["state"] or "",
            sprachen=[SpracheKurz(schluessel=s, name=n) for s, n in json.loads(z["sprachen"])],
            genres=json.loads(z["genres"]), codec=z["codec"], kbps=z["kbps"] or None, kbps_gemessen=bool(z["kbps_gemessen"]),
            qualitaet=z["qualitaet"], stimmen=z["stimmen"], erreichbar=bool(z["erreichbar"]), hls=bool(z["hls"]),
            gruppe=z["gruppe"], varianten=z["varianten"], favorit=bool(z["favorit"]),
            ausnahme=gruende.get(z["nr"], []) if z["sichtbar"] else [], verschwunden=bool(z["verschwunden"]),
            kategorien=kategorien.get(z["uuid"], []), bewertungen=bewertungen.get(z["uuid"], []),
            werbung=Werbestatus(stufe=_WERBE_NAMEN[z["werbe_stufe"]],
                                entscheidung={"blocked": "gesperrt", "allowed": "erlaubt"}.get(e or "")),
            eigene_adresse=adressen.get(z["uuid"]), adresse=z["url"] or "", adresse_aufgeloest=z["url_resolved"] or ""))
    return ergebnis


def _logo(favicon: str | None) -> str:
    text = (favicon or "").strip()
    return text if text.lower().startswith(("http://", "https://")) else ""


_SPALTEN = ("i.nr, i.uuid, i.name_klein, i.land, i.codec, i.kbps, i.kbps_gemessen, i.qualitaet, i.qualitaet_rang, "
            "i.stimmen, i.erreichbar, i.gruppe, i.sprachen, i.genres, i.verschwunden, i.favorit, i.werbe_stufe, "
            "i.getroffen, i.sichtbar, i.varianten, s.name, s.favicon, s.homepage, s.country, s.iso_3166_2, s.state, s.hls, "
            "s.url, s.url_resolved")


def seite(v: sqlite3.Connection, q: StationQuery) -> tuple[list[SenderEintrag], str | None, int | None]:
    """(Einträge, Zeiger der nächsten Seite, Gesamtzahl nur ohne Zeiger)."""
    b = bedingungen(q)
    gesamt = None if q.nach else v.execute(f"SELECT COUNT(*) FROM sender_index i WHERE {b.sql}", b.werte).fetchone()[0]
    if q.nach:
        _nach(b, q, zeiger_lesen(q, q.nach))
    ordnung = ", ".join(f"{s} {r}" for s, r in _spalten(q))
    zeilen = v.execute(f"SELECT {_SPALTEN} FROM sender_index i JOIN stations s ON s.uuid = i.uuid WHERE {b.sql} "
                       f"ORDER BY {ordnung} LIMIT ?", [*b.werte, q.anzahl + 1]).fetchall()
    weiter = zeiger_bauen(q, zeilen[q.anzahl - 1]) if len(zeilen) > q.anzahl else None
    return _eintraege(v, zeilen[:q.anzahl]), weiter, gesamt


def varianten(v: sqlite3.Connection, uuid: str) -> list[SenderEintrag]:
    """Alle sichtbaren Varianten der Gruppe eines Senders, die beste vorn."""
    zeilen = v.execute(f"""SELECT {_SPALTEN} FROM sender_index i JOIN stations s ON s.uuid = i.uuid
                           WHERE i.gruppe = (SELECT gruppe FROM sender_index WHERE uuid = ?) AND i.sichtbar = 1
                           ORDER BY i.vertreter DESC, i.qualitaet_rang DESC, i.kbps DESC, i.erreichbar DESC,
                                    i.stimmen DESC, i.uuid""", (uuid,)).fetchall()
    return _eintraege(v, zeilen)


# ----- Facetten ----------------------------------------------------------------------------------------------------------

def _zaehlen(v: sqlite3.Connection, sql: str, werte: list[object]) -> dict[str, int]:
    return {str(z[0]): z[1] for z in v.execute(sql, werte) if z[0] is not None}


_LANDNAMEN: dict[str, str] = {}


def landnamen(v: sqlite3.Connection, codes: list[str]) -> dict[str, str]:
    """Namen der Länder, wie das Verzeichnis sie führt (englisch; deutsche Namen bildet die Oberfläche aus dem Code).
    Im Speicher gemerkt, bis der Bestand neu aufbereitet ist (`landnamen_vergessen`)."""
    fehlen = [c for c in set(codes) if c not in _LANDNAMEN]
    if fehlen:
        _LANDNAMEN.update({c: c for c in fehlen})
        _LANDNAMEN.update({z[0]: z[1] or z[0] for z in v.execute(
            "SELECT countrycode, MAX(country) FROM stations WHERE countrycode IN (SELECT value FROM json_each(?)) "
            "GROUP BY countrycode", (_liste(fehlen),))})
    return {c: _LANDNAMEN[c] for c in codes}


def landnamen_vergessen() -> None:
    _LANDNAMEN.clear()


def facetten(v: sqlite3.Connection, q: StationQuery, laender_leiste: list[str]) -> Facetten:
    """Zahlen je Wert unter den aktiven Regeln und den übrigen Filtern. Länder: die der Seitenleiste und die gewählten;
    ohne Einstellung alle."""
    b = bedingungen(q, "laender")
    leiste = sorted(set(laender_leiste) | set(q.laender)) if laender_leiste else []
    land_sql = f"SELECT i.land, COUNT(*) FROM sender_index i WHERE {b.sql} AND i.land <> ''"
    land_werte = list(b.werte)
    if leiste:
        land_sql += " AND " + _in("i.land", leiste)
        land_werte += leiste
    laender = _zaehlen(v, land_sql + " GROUP BY i.land", land_werte)
    land_namen = landnamen(v, [*laender, *leiste])

    b = bedingungen(q, "genres")
    genres = _zaehlen(v, f"SELECT g.genre, COUNT(*) FROM sender_genre g JOIN sender_index i ON i.nr = g.nr "
                         f"WHERE {b.sql} GROUP BY g.genre", b.werte)
    b = bedingungen(q, "qualitaet")
    stufen = _zaehlen(v, f"SELECT i.qualitaet, COUNT(*) FROM sender_index i WHERE {b.sql} GROUP BY i.qualitaet", b.werte)
    b = bedingungen(q, "codecs")
    codecs = _zaehlen(v, f"SELECT i.codec, COUNT(*) FROM sender_index i WHERE {b.sql} GROUP BY i.codec", b.werte)
    b = bedingungen(q, "bewertungen")
    bewertungen = _zaehlen(v, f"SELECT {_BEWERTUNG}, COUNT(DISTINCT i.nr) FROM station_tags t JOIN sender_index i "
                              f"ON i.uuid = t.station_uuid WHERE t.source = 'user' AND {b.sql} GROUP BY 1", b.werte)
    b = bedingungen(q, "kategorien")
    kategorien = _zaehlen(v, f"SELECT c.category_id, COUNT(*) FROM category_stations c JOIN sender_index i "
                             f"ON i.uuid = c.station_uuid WHERE {b.sql} GROUP BY c.category_id", b.werte)
    kategorie_namen = [(str(z[0]), z[1]) for z in v.execute(
        "SELECT id, name FROM categories WHERE scope = 'radio' ORDER BY sort_order, id")]

    def sortiert(zahlen: dict[str, int], namen: dict[str, str] | None = None, gewaehlt: list[str] = ()) -> list[Facette]:
        werte = set(zahlen) | set(gewaehlt)
        return sorted((Facette(wert=w, name=(namen or {}).get(w, w), anzahl=zahlen.get(w, 0)) for w in werte),
                      key=lambda f: (-f.anzahl, f.name))

    return Facetten(
        laender=sortiert(laender, land_namen, [*leiste]),
        genres=sortiert(genres, gewaehlt=q.genres),
        qualitaet=[Facette(wert=s, name=s, anzahl=stufen.get(s, 0)) for s in sorted(QUALITAET_RANG, key=QUALITAET_RANG.get, reverse=True)],
        codecs=sortiert(codecs, gewaehlt=q.codecs),
        bewertungen=[Facette(wert=k, name=n, anzahl=bewertungen.get(k, 0)) for k, n in BEWERTUNGEN.items()
                     if bewertungen.get(k) or k in q.bewertungen],
        kategorien=[Facette(wert=k, name=n, anzahl=kategorien.get(k, 0)) for k, n in kategorie_namen],
    )


def abfragen(v: sqlite3.Connection, q: StationQuery, laender_leiste: list[str]) -> Abfrageergebnis:
    eintraege, weiter, gesamt = seite(v, q)
    mit = q.mit_facetten if q.mit_facetten is not None else q.nach is None
    return Abfrageergebnis(gesamt=gesamt, eintraege=eintraege, weiter=weiter,
                           facetten=facetten(v, q, laender_leiste) if mit else None)
