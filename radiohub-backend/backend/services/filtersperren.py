"""
Filtersperren: Sender, die die Ausschlüsse der Einstellungen treffen (RAD-2)

Ein Sender wird gesperrt, wenn eine seiner Sprachen oder einer seiner Tags genau einem ausgeschlossenen Eintrag
entspricht oder er weniger Stimmen hat als verlangt. Als Grund steht an der Sperre nur, was ihn wirklich trifft
(etwa "language:russian"), nicht mehr die ganze Liste.

Die Sperren stehen in der Tabelle blocklist mit category 'filter'. Sperren von Hand (manual) und aus der
Werbeerkennung (ad) fasst dieser Dienst nie an.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel

from .. import sender_merkmale
from .config_service import config_service

KATEGORIE = "filter"


class FilterKriterien(BaseModel):
    sprachen: list[str] = []
    tags: list[str] = []
    mindeststimmen: int = 0

    @property
    def leer(self) -> bool:
        return not self.sprachen and not self.tags and self.mindeststimmen <= 0

    def vereinigt(self, andere: "FilterKriterien") -> "FilterKriterien":
        """Beide zusammen: alle Sprachen und Tags, die strengere Mindestzahl an Stimmen."""
        return FilterKriterien(
            sprachen=sorted(sender_merkmale.normiert(self.sprachen + andere.sprachen)),
            tags=sorted(sender_merkmale.normiert(self.tags + andere.tags)),
            mindeststimmen=max(self.mindeststimmen, andere.mindeststimmen),
        )


@dataclass(frozen=True)
class Sperre:
    uuid: str
    name: str
    grund: str


@dataclass
class Abgleich:
    """Unterschied zwischen den heutigen Filtersperren und dem, was die Kriterien ergeben."""
    neu: list[Sperre] = field(default_factory=list)            # wird gesperrt
    frei: list[Sperre] = field(default_factory=list)           # wird freigegeben (Grund: der alte)
    bleiben: list[Sperre] = field(default_factory=list)        # bleibt gesperrt (Grund: der neue)
    favoriten_frei: list[str] = field(default_factory=list)    # Namen der Favoriten, die wieder erscheinen
    favoriten_neu: list[str] = field(default_factory=list)     # Namen der Favoriten, die neu verschwinden


def kriterien_aus_einstellungen() -> FilterKriterien:
    """Die Ausschlüsse, wie sie in den Einstellungen (Radio, Filter) stehen."""
    return FilterKriterien(
        sprachen=config_service.get("filter_excluded_languages", []) or [],
        tags=config_service.get("filter_excluded_tags", []) or [],
        mindeststimmen=int(config_service.get("filter_min_votes", 0) or 0),
    )


def kriterien_aus_sperren(conn: sqlite3.Connection) -> FilterKriterien:
    """Alle Ausschlüsse, mit denen je ausgeblendet wurde, gelesen aus den Gründen der Filtersperren.

    Frühere Ausblendungen (etwa nach den Tags tv oder webcam) stehen nicht unbedingt noch in den Einstellungen;
    ihre Gründe ("language:x, tag:y, votes<n") halten sie fest. So geht beim Neuberechnen keine Entscheidung verloren.
    """
    sprachen, tags, stimmen = set(), set(), 0
    for (grund,) in conn.execute("SELECT DISTINCT reason FROM blocklist WHERE category = ?", (KATEGORIE,)):
        for teil in (grund or "").split(", "):
            art, _, wert = teil.partition(":")
            if art == "language" and wert:
                sprachen.add(wert)
            elif art == "tag" and wert:
                tags.add(wert)
            elif teil.startswith("votes<") and teil[6:].isdigit():
                stimmen = max(stimmen, int(teil[6:]))
    return FilterKriterien(sprachen=sorted(sprachen), tags=sorted(tags), mindeststimmen=stimmen)


def kriterien_fuer_neuberechnung(conn: sqlite3.Connection) -> FilterKriterien:
    """Was beim Neuberechnen gilt (Entscheidung des Nutzers zu RAD-2, Variante C): die Sprachen genau wie in den
    Einstellungen, dazu die Tags und die Mindeststimmen früherer Ausblendungen."""
    frueher = kriterien_aus_sperren(conn)
    return kriterien_aus_einstellungen().vereinigt(
        FilterKriterien(tags=frueher.tags, mindeststimmen=frueher.mindeststimmen))


def in_einstellungen_uebernehmen(kriterien: FilterKriterien) -> None:
    """Schreibt Tags und Mindeststimmen in die Einstellungen, damit dort steht, was die Sperren bewirkt."""
    config_service.set("filter_excluded_tags", list(kriterien.tags))
    config_service.set("filter_min_votes", kriterien.mindeststimmen)


def treffer(conn: sqlite3.Connection, kriterien: FilterKriterien) -> list[Sperre]:
    """Alle Sender, die die Kriterien treffen, je mit dem Grund, der sie trifft."""
    if kriterien.leer:
        return []
    sprachen = sender_merkmale.normiert(kriterien.sprachen)
    tags = sender_merkmale.normiert(kriterien.tags)
    ergebnis = []
    for zeile in conn.execute("SELECT uuid, name, language, tags, votes FROM stations"):
        gruende = [f"language:{s}" for s in sorted(sender_merkmale.eintraege(zeile["language"]) & sprachen)]
        gruende += [f"tag:{t}" for t in sorted(sender_merkmale.eintraege(zeile["tags"]) & tags)]
        if kriterien.mindeststimmen > 0 and (zeile["votes"] or 0) < kriterien.mindeststimmen:
            gruende.append(f"votes<{kriterien.mindeststimmen}")
        if gruende:
            ergebnis.append(Sperre(zeile["uuid"], zeile["name"] or "", ", ".join(gruende)))
    return ergebnis


def abgleichen(conn: sqlite3.Connection, kriterien: FilterKriterien) -> Abgleich:
    """Vergleicht die heutigen Filtersperren mit dem Ergebnis der Kriterien, ohne etwas zu ändern."""
    soll = {s.uuid: s for s in treffer(conn, kriterien)}
    ist = {z["uuid"]: Sperre(z["uuid"], z["name"] or "", z["reason"] or "")
           for z in conn.execute("SELECT uuid, name, reason FROM blocklist WHERE category = ?", (KATEGORIE,))}
    anders_gesperrt = {z["uuid"] for z in conn.execute(
        "SELECT uuid FROM blocklist WHERE category IS NULL OR category != ?", (KATEGORIE,))}
    favoriten = {z["uuid"]: z["name"] or "" for z in conn.execute("SELECT uuid, name FROM favorites")}

    abgleich = Abgleich(
        neu=[s for u, s in soll.items() if u not in ist and u not in anders_gesperrt],
        frei=[s for u, s in ist.items() if u not in soll],
        bleiben=[s for u, s in soll.items() if u in ist],
    )
    abgleich.favoriten_frei = sorted(favoriten[s.uuid] for s in abgleich.frei if s.uuid in favoriten)
    abgleich.favoriten_neu = sorted(favoriten[s.uuid] for s in abgleich.neu if s.uuid in favoriten)
    return abgleich


def anwenden(conn: sqlite3.Connection, kriterien: FilterKriterien) -> Abgleich:
    """Bringt die Filtersperren auf den Stand der Kriterien (in der Transaktion der Verbindung)."""
    abgleich = abgleichen(conn, kriterien)
    jetzt = datetime.now().isoformat()
    conn.executemany("DELETE FROM blocklist WHERE uuid = ? AND category = ?",
                     [(s.uuid, KATEGORIE) for s in abgleich.frei])
    conn.executemany("UPDATE blocklist SET reason = ? WHERE uuid = ? AND category = ?",
                     [(s.grund, s.uuid, KATEGORIE) for s in abgleich.bleiben])
    conn.executemany(
        "INSERT OR IGNORE INTO blocklist (uuid, name, reason, category, blocked_at) VALUES (?, ?, ?, ?, ?)",
        [(s.uuid, s.name, s.grund, KATEGORIE, jetzt) for s in abgleich.neu])
    return abgleich
