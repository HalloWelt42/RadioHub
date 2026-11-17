"""Genres aus dem Tag-Chaos: die gepflegte Abbildung in `genres.toml` macht aus Schreibweisen ein Genre, verwirft
Rauschen und Frequenzen und lässt alle übrigen Tags als Tags stehen."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

TABELLE = Path(__file__).with_name("genres.toml")


@dataclass(frozen=True)
class Genretabelle:
    schreibweisen: dict[str, str]                   # Schreibweise -> Genre
    muster: tuple[tuple[re.Pattern[str], str], ...]  # Ausdruck -> Genre
    rauschen: frozenset[str]
    frequenzen: tuple[re.Pattern[str], ...]
    alle: tuple[str, ...]                           # alle Genres in der Reihenfolge der Tabelle


@lru_cache(maxsize=1)
def tabelle() -> Genretabelle:
    daten = tomllib.loads(TABELLE.read_text(encoding="utf-8"))
    schreibweisen = {saeubern(s): genre for genre, liste in daten["genres"].items() for s in liste}
    muster = tuple((re.compile(m["ausdruck"]), m["genre"]) for m in daten["muster"])
    alle = tuple(dict.fromkeys([*daten["genres"], *(g for _, g in muster)]))
    return Genretabelle(schreibweisen=schreibweisen, muster=muster,
                        rauschen=frozenset(saeubern(w) for w in daten["verwerfen"]["woerter"]),
                        frequenzen=tuple(re.compile(m) for m in daten["verwerfen"]["muster"]), alle=alle)


def saeubern(tag: str) -> str:
    """Ein Tag in Vergleichsform: klein, ohne Rand, ohne "#" vorn, Leerraum zusammengezogen."""
    return " ".join(tag.strip().lower().lstrip("#").split())


def ist_rauschen(tag: str) -> bool:
    t = tabelle()
    return tag in t.rauschen or any(m.match(tag) for m in t.frequenzen)


def genre_von(tag: str) -> str | None:
    t = tabelle()
    if tag in t.schreibweisen:
        return t.schreibweisen[tag]
    return next((genre for ausdruck, genre in t.muster if ausdruck.match(tag)), None)


def zerlegen(tags: str) -> tuple[list[str], list[str]]:
    """(Genres, Tags) eines Senders: Genres aus der Tabelle, je einmal; Tags gesäubert ohne Rauschen und Frequenzen."""
    genres: dict[str, None] = {}
    sauber: dict[str, None] = {}
    for roh in tags.split(","):
        tag = saeubern(roh)
        if not tag or ist_rauschen(tag):
            continue
        sauber[tag] = None
        genre = genre_von(tag)
        if genre:
            genres[genre] = None
    return list(genres), list(sauber)
