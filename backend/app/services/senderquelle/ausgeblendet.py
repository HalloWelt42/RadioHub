"""Ausgeblendete Sender seitenweise und durchsuchbar, je Sender mit Grund; Einzelsperren (Auge) und Freigaben je
Sender; Kandidaten für neue Regeln mit Zahlen."""
from __future__ import annotations

import json
import sqlite3

from ...senderdaten import sprachen as sprachtabelle
from . import regeln, sichtbarkeit
from .modelle import (BEWERTUNGEN, AusgeblendetAnfrage, AusgeblendeterSender, AusgeblendetSeite, GrundZahl, Kandidat)

_AUSGEBLENDET = "i.sichtbar = 0 AND i.verschwunden = 0"


def seite(v: sqlite3.Connection, a: AusgeblendetAnfrage) -> AusgeblendetSeite:
    bedingung, werte = _AUSGEBLENDET, []
    if a.regel:
        bedingung += " AND EXISTS (SELECT 1 FROM sender_ausblendung x WHERE x.nr = i.nr AND x.regel = ?)"
        werte.append(a.regel)
    suche = " ".join(a.suche.split())
    if len(suche) >= 3:
        bedingung += " AND i.nr IN (SELECT rowid FROM sender_suche WHERE sender_suche MATCH ?)"
        werte.append('"' + suche.replace('"', '""') + '"')
    elif suche:
        bedingung += " AND i.name_klein LIKE ?"
        werte.append(f"%{suche.casefold()}%")
    gesamt = v.execute(f"SELECT COUNT(*) FROM sender_index i WHERE {bedingung}", werte).fetchone()[0]
    seiten = max(1, -(-gesamt // a.anzahl))
    nummer = min(a.seite, seiten - 1)
    zeilen = v.execute(f"""SELECT i.nr, i.uuid, i.land, i.stimmen, s.name, s.favicon FROM sender_index i
                           JOIN stations s ON s.uuid = i.uuid WHERE {bedingung}
                           ORDER BY i.stimmen DESC, i.uuid LIMIT ? OFFSET ?""",
                       [*werte, a.anzahl, nummer * a.anzahl]).fetchall()
    gruende = sichtbarkeit.gruende(v, [z["nr"] for z in zeilen])
    zahlen = [GrundZahl(regel=z["id"], titel=regeln.titel(z["art"], regeln.entwurf_lesen(z["art"], z["wert"])), anzahl=z["n"])
              for z in v.execute(f"""SELECT r.id, r.art, r.wert, COUNT(*) AS n FROM sender_ausblendung x
                                     JOIN regel r ON r.id = x.regel AND r.an = 1 JOIN sender_index i ON i.nr = x.nr
                                     WHERE {_AUSGEBLENDET} GROUP BY r.id ORDER BY n DESC""")]
    return AusgeblendetSeite(
        gesamt=gesamt, seite=nummer, seiten=seiten, gruende=zahlen,
        eintraege=[AusgeblendeterSender(uuid=z["uuid"], name=z["name"] or "", land=z["land"], stimmen=z["stimmen"],
                                        logo=z["favicon"] if (z["favicon"] or "").startswith(("http://", "https://")) else "",
                                        gruende=gruende.get(z["nr"], [])) for z in zeilen])


# ----- Einzelsperren und Freigaben --------------------------------------------------------------------------------------

def sperren(v: sqlite3.Connection, uuid: str, zeit: str, herkunft: str = "auge") -> bool:
    """Einzelsperre (Auge); hebt eine Freigabe desselben Senders auf. False, wenn es den Sender nicht gibt."""
    zeile = v.execute("SELECT name FROM stations WHERE uuid = ?", (uuid,)).fetchone()
    if zeile is None:
        return False
    v.execute("INSERT OR IGNORE INTO sender_sperre (uuid, name, herkunft, angelegt_am) VALUES (?, ?, ?, ?)",
              (uuid, zeile[0] or "", herkunft, zeit))
    v.execute("DELETE FROM sender_freigabe WHERE uuid = ?", (uuid,))
    return True


def entsperren(v: sqlite3.Connection, uuid: str) -> bool:
    return v.execute("DELETE FROM sender_sperre WHERE uuid = ?", (uuid,)).rowcount > 0


def freigeben(v: sqlite3.Connection, uuid: str, zeit: str) -> bool:
    """Sender wieder sichtbar: eine Einzelsperre wird aufgehoben; trifft ihn danach noch eine eingeschaltete Regel,
    bleibt er als Ausnahme (Freigabe) sichtbar."""
    zeile = v.execute("SELECT nr FROM sender_index WHERE uuid = ?", (uuid,)).fetchone()
    if zeile is None:
        return False
    entsperren(v, uuid)
    weitere = v.execute("""SELECT 1 FROM sender_ausblendung a JOIN regel r ON r.id = a.regel AND r.an = 1
                           WHERE a.nr = ? AND a.regel <> ?""", (zeile[0], regeln.EINZELSPERREN)).fetchone()
    if weitere:
        v.execute("INSERT OR IGNORE INTO sender_freigabe (uuid, angelegt_am) VALUES (?, ?)", (uuid, zeit))
    return True


def freigabe_zuruecknehmen(v: sqlite3.Connection, uuid: str) -> bool:
    return v.execute("DELETE FROM sender_freigabe WHERE uuid = ?", (uuid,)).rowcount > 0


# ----- Kandidaten für neue Regeln --------------------------------------------------------------------------------------

def _gezaehlt(v: sqlite3.Connection, sql: str, werte: list[object], grenze: int) -> list[sqlite3.Row]:
    return v.execute(f"""SELECT x.wert, COUNT(*) AS anzahl, SUM(i.favorit) AS favoriten FROM ({sql}) x
                         JOIN sender_index i ON i.nr = x.nr AND i.verschwunden = 0
                         GROUP BY x.wert ORDER BY anzahl DESC, x.wert LIMIT ?""", [*werte, grenze]).fetchall()


def kandidaten(v: sqlite3.Connection, art: str, suche: str, grenze: int) -> list[Kandidat]:
    text = suche.strip().casefold()
    muster = f"%{text}%"
    if art == "sprache":
        codes = [c for c, n in sprachtabelle.tabelle().namen.items() if text and (text in n.casefold() or text == c)]
        zeilen = _gezaehlt(v, "SELECT schluessel AS wert, nr FROM sender_sprache WHERE (? = '' OR schluessel LIKE ? "
                              "OR schluessel IN (SELECT value FROM json_each(?)))",
                           [text, f"frei:%{text}%" if text else "%", json.dumps(codes)], grenze)
        return [Kandidat(schluessel=z["wert"], code=None if z["wert"].startswith(sprachtabelle.FREI) else z["wert"],
                         name=z["wert"].removeprefix(sprachtabelle.FREI) if z["wert"].startswith(sprachtabelle.FREI)
                         else sprachtabelle.name_von(z["wert"]), anzahl=z["anzahl"], favoriten=z["favoriten"] or 0)
                for z in zeilen]
    if art in ("genre", "tag"):
        tabelle, spalte = ("sender_genre", "genre") if art == "genre" else ("sender_tag", "tag")
        zeilen = _gezaehlt(v, f"SELECT {spalte} AS wert, nr FROM {tabelle} WHERE lower({spalte}) LIKE ?", [muster], grenze)
        return [Kandidat(schluessel=z["wert"], name=z["wert"], anzahl=z["anzahl"], favoriten=z["favoriten"] or 0) for z in zeilen]
    if art == "bewertung":
        zeilen = _gezaehlt(v, "SELECT (CASE WHEN t.tag_key = 'sterne' THEN 'sterne:' || t.tag_value ELSE t.tag_key END) "
                              "AS wert, i.nr FROM station_tags t JOIN sender_index i ON i.uuid = t.station_uuid "
                              "WHERE t.source = 'user'", [], 50)
        return [Kandidat(schluessel=z["wert"], name=BEWERTUNGEN[z["wert"]], anzahl=z["anzahl"], favoriten=z["favoriten"] or 0)
                for z in zeilen if z["wert"] in BEWERTUNGEN]
    if art == "einzeln":
        if len(text) < 2:
            return []
        zeilen = v.execute("""SELECT i.uuid, s.name, i.land, i.favorit FROM sender_index i JOIN stations s ON s.uuid = i.uuid
                              WHERE i.name_klein LIKE ? AND i.verschwunden = 0 ORDER BY i.stimmen DESC LIMIT ?""",
                           (muster, grenze)).fetchall()
        return [Kandidat(schluessel=z["uuid"], name=z["name"] or "", code=z["land"], anzahl=1, favoriten=z["favorit"])
                for z in zeilen]
    raise ValueError(f"Für die Art {art} gibt es keine Kandidaten")
