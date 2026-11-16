"""
Merkmale der Sender als Listen (RAD-2)

Sprachen und Tags kommen aus dem Senderverzeichnis als Text mit Kommas, etwa "german,english" oder
"pop, rock, 80s". Verglichen wird hier immer ein ganzer Eintrag gegen einen ganzen Eintrag, nie ein Wortteil:
Der frühere Vergleich per LIKE '%ger%' traf "german" und blendete so fast alle deutschen Sender aus.

Die SQL-Funktion `merkmal_trifft(spalte, ?)` meldet jede Datenbankverbindung an (database.get_db); der Parameter
ist die gesuchte Liste als JSON-Text, gebaut mit `liste_als_parameter`.
"""
from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from typing import Iterable

SQL_FUNKTION = "merkmal_trifft"


def eintraege(feld: str | None) -> frozenset[str]:
    """Die Einträge eines Feldes: an Kommas geteilt, ohne Rand, klein geschrieben, ohne leere."""
    if not feld:
        return frozenset()
    return frozenset(teil for teil in (roh.strip().lower() for roh in feld.split(",")) if teil)


def normiert(werte: Iterable[str]) -> frozenset[str]:
    """Eine gesuchte Liste in derselben Form wie `eintraege`."""
    return frozenset(w for w in (str(roh).strip().lower() for roh in werte) if w)


def liste_als_parameter(werte: Iterable[str]) -> str:
    """Parameter für `merkmal_trifft`: die normierte Liste als JSON-Text (sortiert, damit der Zwischenspeicher trifft)."""
    return json.dumps(sorted(normiert(werte)), ensure_ascii=False)


@lru_cache(maxsize=64)
def _gesucht(liste_json: str) -> frozenset[str]:
    return normiert(json.loads(liste_json))


def trifft(feld: str | None, liste_json: str) -> int:
    """1, wenn mindestens ein Eintrag des Feldes in der gesuchten Liste steht, sonst 0."""
    return 1 if eintraege(feld) & _gesucht(liste_json) else 0


def anmelden(conn: sqlite3.Connection) -> None:
    """Macht `merkmal_trifft` in dieser Verbindung verfügbar."""
    conn.create_function(SQL_FUNKTION, 2, trifft, deterministic=True)
