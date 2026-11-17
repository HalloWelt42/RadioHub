"""RAD-7: Die Typen der Oberfläche (frontend/src/lib/radio/typen.ts) führen je Schnittstelle genau die Felder ihres
Pydantic-Modells (eine Wahrheit: das Modell; die Typen folgen ihm)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.services.senderquelle import modelle

TYPEN = Path(__file__).resolve().parents[2] / "frontend/src/lib/radio/typen.ts"
_SCHNITTSTELLE = re.compile(r"export interface (\w+) \{(.*?)\n\}", re.S)
_FELD = re.compile(r"^\s*(\w+)\??:", re.M)


def _schnittstellen() -> dict[str, set[str]]:
    text = TYPEN.read_text(encoding="utf-8")
    return {name: set(_FELD.findall(rumpf)) for name, rumpf in _SCHNITTSTELLE.findall(text)}


MODELLE = {name: klasse for name, klasse in vars(modelle).items()
           if isinstance(klasse, type) and issubclass(klasse, BaseModel) and klasse.__module__ == modelle.__name__}


@pytest.mark.parametrize("name", sorted(MODELLE))
def test_jedes_modell_hat_seine_schnittstelle(name):
    schnittstellen = _schnittstellen()
    assert name in schnittstellen, f"typen.ts: export interface {name} fehlt"
    assert schnittstellen[name] == set(MODELLE[name].model_fields), name


def test_keine_schnittstelle_ohne_modell():
    assert set(_schnittstellen()) <= set(MODELLE)
