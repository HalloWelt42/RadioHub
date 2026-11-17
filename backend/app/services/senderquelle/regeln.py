"""Lebende Ausschlussregeln (Entscheidung 5): je Art eine Abfrage, die die getroffenen Sender liefert (Spalte nr von
sender_index). Regeln gelten auch für neue Sender, weil die Treffer nach jedem Abgleich neu entstehen. Gespeichert in
der Tabelle regel (wert: der Entwurf als JSON ohne die Art); zwei Regeln gibt es immer bzw. bis zur Überführung:
"einzelsperren" (Einzelsender per Auge) und "altbestand" (die frühere Sperrliste)."""
from __future__ import annotations

import json
import sqlite3
import uuid as uuid_modul

from pydantic import TypeAdapter

from ...senderdaten import sprachen as sprachtabelle
from .modelle import (BEWERTUNGEN, WERBE_STUFEN, BewertungEntwurf, GenreEntwurf, Regel, RegelArt, RegelEntwurf,
                      SpracheEntwurf, StimmenEntwurf, TagEntwurf, WerbungEntwurf)

EINZELSPERREN = "einzelsperren"
ALTBESTAND = "altbestand"
_ENTWURF = TypeAdapter(RegelEntwurf)

ERKLAERUNG: dict[str, str] = {
    "sprache": "exakter Sprachcode oder Eintrag, Sender ohne Angabe bleiben sichtbar",
    "genre": "normalisiertes Genre, alle Schreibweisen",
    "tag": "genauer Tag des Senderverzeichnisses",
    "stimmen": "gilt auch für neue Sender",
    "werbung": "aus Messung und eigener Bewertung, der Cache-Kopf allein zählt nicht",
    "bewertung": "eigene Bewertungen",
    "einzeln": "per Auge ausgeblendet",
    "altsperren": "Sperrliste vor der Überführung in Regeln",
}
_WERBUNG_TITEL = {"eigene": "eigene Entscheidung", "hoch": "hoch", "mittel": "mittel", "verdacht": "jeder Verdacht"}


def entwurf_lesen(art: str, wert: str) -> RegelEntwurf | None:
    if art in ("einzeln", "altsperren"):
        return None
    return _ENTWURF.validate_python({**json.loads(wert or "{}"), "art": art})


def entwurf_speichern(entwurf: RegelEntwurf) -> str:
    return json.dumps(entwurf.model_dump(exclude={"art"}), ensure_ascii=False, sort_keys=True)


def _aufzaehlung(werte: list[str], grenze: int = 4) -> str:
    if len(werte) <= grenze:
        return ", ".join(werte)
    return f"{', '.join(werte[:grenze])} und {len(werte) - grenze} weitere"


def titel(art: str, entwurf: RegelEntwurf | None) -> str:
    """Die Regel in Worten, wie die Oberfläche sie zeigt."""
    if isinstance(entwurf, SpracheEntwurf):
        namen = [f"{sprachtabelle.name_von(s)} ({s})" if not s.startswith(sprachtabelle.FREI)
                 else s.removeprefix(sprachtabelle.FREI) for s in entwurf.schluessel]
        namen += [f'"{e}"' for e in entwurf.eintraege]
        return f"Sprache ist {_aufzaehlung(namen)}"
    if isinstance(entwurf, GenreEntwurf):
        return f"Genre ist {_aufzaehlung(entwurf.genres)}"
    if isinstance(entwurf, TagEntwurf):
        return f"Tag ist {_aufzaehlung(entwurf.tags)}"
    if isinstance(entwurf, StimmenEntwurf):
        return f"weniger als {entwurf.mindeststimmen} Stimmen"
    if isinstance(entwurf, WerbungEntwurf):
        return f"Werbeverdacht {_WERBUNG_TITEL[entwurf.stufe]}"
    if isinstance(entwurf, BewertungEntwurf):
        return f"eigene Bewertung {_aufzaehlung([BEWERTUNGEN[b] for b in entwurf.bewertungen])}"
    return {"einzeln": "Einzelsperren", "altsperren": "Sperren von früher (vor der Überführung)"}.get(art, art)


def treffer_sql(art: str, entwurf: RegelEntwurf | None) -> tuple[str, list[object]]:
    """Abfrage, die die Spalte nr der getroffenen Sender liefert (verschwundene eingeschlossen)."""
    if isinstance(entwurf, SpracheEntwurf):
        return ("SELECT nr FROM sender_sprache WHERE schluessel IN (SELECT value FROM json_each(?)) UNION "
                "SELECT nr FROM sender_spracheintrag WHERE eintrag IN (SELECT value FROM json_each(?))",
                [json.dumps(entwurf.schluessel), json.dumps(entwurf.eintraege)])
    if isinstance(entwurf, GenreEntwurf):
        return "SELECT DISTINCT nr FROM sender_genre WHERE genre IN (SELECT value FROM json_each(?))", [json.dumps(entwurf.genres)]
    if isinstance(entwurf, TagEntwurf):
        return "SELECT DISTINCT nr FROM sender_tag WHERE tag IN (SELECT value FROM json_each(?))", [json.dumps(entwurf.tags)]
    if isinstance(entwurf, StimmenEntwurf):
        return "SELECT nr FROM sender_index WHERE stimmen < ?", [entwurf.mindeststimmen]
    if isinstance(entwurf, WerbungEntwurf):
        return "SELECT nr FROM sender_index WHERE werbe_stufe >= ?", [WERBE_STUFEN[entwurf.stufe]]
    if isinstance(entwurf, BewertungEntwurf):
        return ("SELECT DISTINCT i.nr FROM station_tags t JOIN sender_index i ON i.uuid = t.station_uuid "
                "WHERE t.source = 'user' AND (CASE WHEN t.tag_key = 'sterne' THEN 'sterne:' || t.tag_value "
                "ELSE t.tag_key END) IN (SELECT value FROM json_each(?))", [json.dumps(entwurf.bewertungen)])
    if art == "einzeln":
        return "SELECT i.nr FROM sender_sperre s JOIN sender_index i ON i.uuid = s.uuid", []
    if art == "altsperren":
        return "SELECT DISTINCT i.nr FROM blocklist b JOIN sender_index i ON i.uuid = b.uuid", []
    raise ValueError(f"Unbekannte Art: {art}")


# ----- Lesen und schreiben ----------------------------------------------------------------------------------------------

def _regel(z: sqlite3.Row | dict, zahlen: dict[str, tuple[int, int, int]]) -> Regel:
    entwurf = entwurf_lesen(z["art"], z["wert"])
    betroffen, favoriten, nur_diese = zahlen.get(z["id"], (0, 0, 0))
    return Regel(id=z["id"], art=z["art"], an=bool(z["an"]), herkunft=z["herkunft"], titel=titel(z["art"], entwurf),
                 erklaerung=ERKLAERUNG.get(z["art"], ""), entwurf=entwurf, betroffen=betroffen, favoriten=favoriten,
                 nur_diese=nur_diese, angelegt_am=z["angelegt_am"], geaendert_am=z["geaendert_am"])


def zahlen(v: sqlite3.Connection, regel_id: str | None = None) -> dict[str, tuple[int, int, int]]:
    """Je Regel: (betroffen, davon Favoriten, nur durch sie ausgeblendet) ohne verschwundene Sender."""
    bereich = "AND a.regel = ?" if regel_id else ""
    werte = [regel_id] if regel_id else []
    return {z[0]: (z[1], z[2] or 0, z[3] or 0) for z in v.execute(
        f"""SELECT a.regel, COUNT(*), SUM(i.favorit),
                   SUM(CASE WHEN i.favorit = 0 AND i.freigegeben = 0 AND NOT EXISTS (
                         SELECT 1 FROM sender_ausblendung b JOIN regel r ON r.id = b.regel AND r.an = 1
                         WHERE b.nr = a.nr AND b.regel <> a.regel) THEN 1 ELSE 0 END)
            FROM sender_ausblendung a JOIN sender_index i ON i.nr = a.nr AND i.verschwunden = 0
            WHERE 1 = 1 {bereich} GROUP BY a.regel""", werte)}


def alle(v: sqlite3.Connection) -> list[Regel]:
    """Alle Regeln, neueste zuerst; Einzelsperren und Altbestand am Ende."""
    z = zahlen(v)
    return [_regel(r, z) for r in v.execute(
        "SELECT * FROM regel ORDER BY art IN ('einzeln', 'altsperren'), angelegt_am DESC, id")]


def holen(v: sqlite3.Connection, regel_id: str) -> Regel | None:
    zeile = v.execute("SELECT * FROM regel WHERE id = ?", (regel_id,)).fetchone()
    return _regel(zeile, zahlen(v, regel_id)) if zeile else None


def gleiche(v: sqlite3.Connection, entwurf: RegelEntwurf) -> str | None:
    """Kennung einer bestehenden Regel mit demselben Inhalt."""
    zeile = v.execute("SELECT id FROM regel WHERE art = ? AND wert = ?", (entwurf.art, entwurf_speichern(entwurf))).fetchone()
    return zeile[0] if zeile else None


def anlegen(v: sqlite3.Connection, entwurf: RegelEntwurf, zeit: str, herkunft: str = "nutzer") -> str:
    regel_id = uuid_modul.uuid4().hex[:12]
    v.execute("INSERT INTO regel (id, art, wert, an, herkunft, angelegt_am, geaendert_am) VALUES (?, ?, ?, 1, ?, ?, ?)",
              (regel_id, entwurf.art, entwurf_speichern(entwurf), herkunft, zeit, zeit))
    return regel_id


def schalten(v: sqlite3.Connection, regel_id: str, an: bool, zeit: str) -> bool:
    return v.execute("UPDATE regel SET an = ?, geaendert_am = ? WHERE id = ?", (int(an), zeit, regel_id)).rowcount > 0


def entfernen(v: sqlite3.Connection, regel_id: str) -> bool:
    """Entfernt eine Regel samt Treffern; die Einzelsperren bleiben als Regel immer da."""
    if regel_id == EINZELSPERREN:
        raise ValueError("Die Einzelsperren sind keine entfernbare Regel; einzelne Sender gibt das Auge frei")
    return v.execute("DELETE FROM regel WHERE id = ?", (regel_id,)).rowcount > 0


def art_von(v: sqlite3.Connection, regel_id: str) -> RegelArt | None:
    zeile = v.execute("SELECT art FROM regel WHERE id = ?", (regel_id,)).fetchone()
    return zeile[0] if zeile else None
