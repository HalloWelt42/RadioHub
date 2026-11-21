"""Werbeangaben lesen (RAD-33): aus einer Angabe der Sendedaten wird, wenn sie Werbung ankündigt, eine `Werbeangabe`.
Woran das zu erkennen ist, steht in `angaben.toml` (je Format Ausdrücke); hier ist nur das Lesen, ohne Ein- und
Ausgabe, damit es mit echten Angaben prüfbar ist (tests/test_sendewerbung.py)."""

from __future__ import annotations

import re
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

TABELLE = Path(__file__).with_name("angaben.toml")

Ende = Literal["dauer", "wechsel"]


class Format(BaseModel):
    name: str
    erkennen: re.Pattern[str]
    kennung: re.Pattern[str]
    werbender: Optional[re.Pattern[str]] = None
    titel: Optional[re.Pattern[str]] = None
    dauer_ms: Optional[re.Pattern[str]] = None
    einfuegung: Optional[re.Pattern[str]] = None
    verbinden: tuple[str, ...] = ()
    ende: Ende = "wechsel"


class Grenze(BaseModel):
    fenster_s: float
    stille_db: float
    stille_mindestens_s: float


class Regeln(BaseModel):
    grenze: Grenze
    formate: tuple[Format, ...]


class Werbeangabe(BaseModel):
    """Was eine Angabe über einen Spot sagt."""

    format: str
    kennung: str
    werbender: str = ""
    titel: str = ""
    dauer_ms: Optional[int] = None
    beim_verbinden: bool = False
    ende: Ende


@lru_cache(maxsize=1)
def regeln() -> Regeln:
    daten = tomllib.loads(TABELLE.read_text(encoding="utf-8"))
    ausdruck = lambda f, k: re.compile(f[k]) if f.get(k) else None
    formate = tuple(Format(name=f["name"], erkennen=re.compile(f["erkennen"]), kennung=re.compile(f["kennung"]),
                           werbender=ausdruck(f, "werbender"), titel=ausdruck(f, "titel"),
                           dauer_ms=ausdruck(f, "dauer_ms"), einfuegung=ausdruck(f, "einfuegung"),
                           verbinden=tuple(f.get("verbinden", ())), ende=f.get("ende", "wechsel"))
                    for f in daten["format"])
    return Regeln(grenze=Grenze(**daten["grenze"]), formate=formate)


def lesen(roh: str) -> Optional[Werbeangabe]:
    """Die Werbeangabe in einer Angabe der Sendedaten, oder None, wenn sie keine Werbung ankündigt."""
    for f in regeln().formate:
        if not f.erkennen.search(roh):
            continue
        kennung = _gruppe(f.kennung, roh)
        if not kennung:
            continue
        dauer = _gruppe(f.dauer_ms, roh)
        einfuegung = _gruppe(f.einfuegung, roh)
        return Werbeangabe(format=f.name, kennung=kennung, werbender=_gruppe(f.werbender, roh),
                           titel=_gruppe(f.titel, roh), dauer_ms=int(dauer) if dauer.isdigit() else None,
                           beim_verbinden=bool(einfuegung) and einfuegung in f.verbinden,
                           ende=f.ende if dauer.isdigit() else "wechsel")
    return None


def _gruppe(ausdruck: Optional[re.Pattern[str]], roh: str) -> str:
    treffer = ausdruck.search(roh) if ausdruck else None
    return treffer.group(1).strip() if treffer else ""
