"""Übergabe zwischen Geräten im Radio (RAD-18): Modelle von Zustand und Paket"""
import pytest
from pydantic import ValidationError

from app.geraete import RadioPaket, RadioZustand


def test_paket_braucht_die_quelle_seiner_art():
    p = RadioPaket.model_validate({"art": "folge", "folge": {"id": 7, "title": "Folge"}, "podcast": {"id": 3}, "stelle": 61.5})
    assert p.folge.id == 7 and p.folge.model_dump()["title"] == "Folge" and p.stelle == 61.5
    with pytest.raises(ValidationError):
        RadioPaket.model_validate({"art": "sender", "folge": {"id": 7}})
    with pytest.raises(ValidationError):
        RadioPaket.model_validate({"art": "aufnahme", "aufnahme": {"playUrl": ""}})


def test_zustand_kurz():
    assert RadioZustand(art="sender", titel="MANGORADIO", laeuft=True).laeuft
    with pytest.raises(ValidationError):
        RadioZustand(art="sender", titel="x" * 301)
