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


Bestaetigen = Literal["stille"]

SENDERNAME = "{sendername}"


class Format(BaseModel):
    name: str
    #: regulärer Ausdruck; mit {sendername} erst beim Lesen gebildet (der Name des Senders, maskiert)
    erkennen: str
    kennung: re.Pattern[str]
    werbender: Optional[re.Pattern[str]] = None
    titel: Optional[re.Pattern[str]] = None
    dauer_ms: Optional[re.Pattern[str]] = None
    einfuegung: Optional[re.Pattern[str]] = None
    verbinden: tuple[str, ...] = ()
    ende: Ende = "wechsel"
    nur_beim_verbinden: bool = False
    bestaetigen: Optional[Bestaetigen] = None
    mindestens_s: Optional[float] = None
    hoechstens_s: Optional[float] = None

    def trifft(self, roh: str, sendername: str) -> bool:
        if SENDERNAME not in self.erkennen:
            return _ausdruck(self.erkennen).search(roh) is not None
        return bool(sendername) and re.search(self.erkennen.replace(SENDERNAME, re.escape(sendername)), roh) is not None


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
    bestaetigen: Optional[Bestaetigen] = None
    #: mit bestaetigen "stille": Ende an der ersten Stille in diesem Abstand vom Anfang, ohne sie verworfen
    mindestens_s: Optional[float] = None
    hoechstens_s: Optional[float] = None


@lru_cache(maxsize=1)
def regeln() -> Regeln:
    daten = tomllib.loads(TABELLE.read_text(encoding="utf-8"))
    ausdruck = lambda f, k: re.compile(f[k]) if f.get(k) else None
    formate = tuple(Format(name=f["name"], erkennen=f["erkennen"], kennung=re.compile(f["kennung"]),
                           werbender=ausdruck(f, "werbender"), titel=ausdruck(f, "titel"),
                           dauer_ms=ausdruck(f, "dauer_ms"), einfuegung=ausdruck(f, "einfuegung"),
                           verbinden=tuple(f.get("verbinden", ())), ende=f.get("ende", "wechsel"),
                           nur_beim_verbinden=f.get("nur_beim_verbinden", False), bestaetigen=f.get("bestaetigen"),
                           mindestens_s=f.get("mindestens_s"), hoechstens_s=f.get("hoechstens_s"))
                    for f in daten["format"])
    return Regeln(grenze=Grenze(**daten["grenze"]), formate=formate)


def lesen(roh: str, sendername: str = "", erste: bool = False) -> Optional[Werbeangabe]:
    """Die Werbeangabe in einer Angabe der Sendedaten, oder None, wenn sie keine Werbung ankündigt. `sendername`: der
    Name aus dem Kopf des Stroms (icy-name); `erste`: die erste Angabe der Verbindung."""
    for f in regeln().formate:
        if (f.nur_beim_verbinden and not erste) or not f.trifft(roh, sendername):
            continue
        kennung = _gruppe(f.kennung, roh)
        if not kennung:
            continue
        dauer = _gruppe(f.dauer_ms, roh)
        einfuegung = _gruppe(f.einfuegung, roh)
        return Werbeangabe(format=f.name, kennung=kennung, werbender=_gruppe(f.werbender, roh),
                           titel=_gruppe(f.titel, roh), dauer_ms=int(dauer) if dauer.isdigit() else None,
                           beim_verbinden=(bool(einfuegung) and einfuegung in f.verbinden) or f.nur_beim_verbinden,
                           ende=f.ende if dauer.isdigit() else "wechsel", bestaetigen=f.bestaetigen,
                           mindestens_s=f.mindestens_s, hoechstens_s=f.hoechstens_s)
    return None


@lru_cache(maxsize=64)
def _ausdruck(muster: str) -> re.Pattern[str]:
    return re.compile(muster)


def _gruppe(ausdruck: Optional[re.Pattern[str]], roh: str) -> str:
    treffer = ausdruck.search(roh) if ausdruck else None
    return treffer.group(1).strip() if treffer else ""
