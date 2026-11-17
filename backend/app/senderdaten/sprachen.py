"""Sprachen exakt: aus dem freien Text des Verzeichnisses (language) und den Codes (languagecodes) werden Sprachen mit
Code und deutschem Namen. Ein Eintrag, den die Tabelle `sprachen.toml` nicht kennt, bleibt als eigene Sprache aus
freiem Text stehen; verglichen wird immer der ganze Eintrag, nie ein Wortteil (RAD-2: "ger" traf "german")."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .modelle import Sprache

TABELLE = Path(__file__).with_name("sprachen.toml")
FREI = "frei:"

_ADRESSE = re.compile(r"https?://\S*")
_TEILER = re.compile(r"\s*(?:/|\||;|\+|&| and | y | und )\s*")
_WORTTEILER = re.compile(r"[\s\-()]+")
_VORSATZ = ("язык: ", "язык:", "language: ", "sprache: ")


@dataclass(frozen=True)
class Sprachtabelle:
    namen: dict[str, str]           # Code -> deutscher Name
    schreibweisen: dict[str, str]   # Schreibweise -> Code


@lru_cache(maxsize=1)
def tabelle() -> Sprachtabelle:
    daten = tomllib.loads(TABELLE.read_text(encoding="utf-8"))
    namen = {code: eintrag["name"] for code, eintrag in daten.items()}
    schreibweisen: dict[str, str] = {}
    for code, eintrag in daten.items():
        schreibweisen[code] = code
        for s in eintrag["schreibweisen"]:
            schreibweisen[saeubern(s)] = code
    return Sprachtabelle(namen, schreibweisen)


def saeubern(eintrag: str) -> str:
    """Ein Eintrag in Vergleichsform: klein, ohne angeklebte Adressen, ohne "#" vorn, ohne Satzzeichen am Ende, ohne
    Vorsätze wie "язык: ", Leerraum zusammengezogen."""
    text = _ADRESSE.sub("", eintrag.lower()).strip()
    for vorsatz in _VORSATZ:
        if text.startswith(vorsatz):
            text = text[len(vorsatz):]
    text = text.lstrip("#").strip().rstrip(".,/:\\-").strip()
    return " ".join(text.split())


def code_von(text: str) -> str | None:
    """Code einer Schreibweise oder eines Codes (auch dreibuchstabig, etwa "deu"); None, wenn unbekannt."""
    return tabelle().schreibweisen.get(saeubern(text))


def name_von(code: str) -> str:
    return tabelle().namen.get(code, code)


def _codes_im_teil(teil: str) -> list[str] | None:
    """Codes eines Teils: die ganze Schreibweise; sonst alle Wörter, wenn jedes eine Sprache ist ("english hindi");
    sonst das erste Wort mit Zusatz zur Gegend ("español chile", "português (brasil)"). None: unbekannt."""
    schreibweisen = tabelle().schreibweisen
    if teil in schreibweisen:
        return [schreibweisen[teil]]
    woerter = [w for w in _WORTTEILER.split(teil) if w]
    if len(woerter) > 1:
        codes = [schreibweisen.get(w) for w in woerter]
        if all(codes):
            return list(dict.fromkeys(c for c in codes if c))
        if codes[0] and len(woerter[0]) > 3:
            return [codes[0]]
    return None


def eintraege(language: str) -> list[str]:
    """Die Einträge des Verzeichnisses so, wie sie dort stehen (klein, ohne Rand), je einmal."""
    return list(dict.fromkeys(e for e in (roh.strip().lower() for roh in language.split(",")) if e))


def sprachen(language: str, languagecodes: str = "") -> list[Sprache]:
    """Die Sprachen eines Senders, je Sprache einmal, in der Reihenfolge des Verzeichnisses. `eintrag` ist der Eintrag
    so, wie er im Verzeichnis steht (nur klein und ohne Rand): an ihm hängen Regeln auf genaue Einträge."""
    ergebnis: dict[str, Sprache] = {}
    for roh in language.split(","):
        eintrag = roh.strip().lower()           # wie im Verzeichnis: Grundlage der Regeln auf genaue Einträge
        sauber = saeubern(eintrag)
        if not sauber:
            continue
        teile = [t for t in _TEILER.split(sauber) if t] or [sauber]
        gefunden = [(teil, _codes_im_teil(teil)) for teil in teile]
        if all(codes is None for _, codes in gefunden):
            schluessel = FREI + sauber
            ergebnis.setdefault(schluessel, Sprache(schluessel=schluessel, code=None, name=sauber, eintrag=eintrag))
            continue
        for teil, codes in gefunden:
            if codes is None:
                schluessel = FREI + teil
                ergebnis.setdefault(schluessel, Sprache(schluessel=schluessel, code=None, name=teil, eintrag=eintrag))
                continue
            for code in codes:
                ergebnis.setdefault(code, Sprache(schluessel=code, code=code, name=name_von(code), eintrag=eintrag))
    for roh in languagecodes.split(","):
        text = roh.strip().lower()
        if not re.fullmatch(r"[a-z]{2,3}", text):
            continue
        code = tabelle().schreibweisen.get(text, text)
        ergebnis.setdefault(code, Sprache(schluessel=code, code=code, name=name_von(code), eintrag=None))
    return list(ergebnis.values())
