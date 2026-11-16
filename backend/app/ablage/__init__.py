"""Ablage des RadioHub: Schnittstelle, Adapter und die eine Instanz der laufenden App.

Beim Start richtet `main` die Ablage aus den Einstellungen ein (`starten`), außer ein Test hat vorher eine
`SpeicherAblage` vorgegeben (`vorgeben`). Alle Dienste holen sie über `ablage()`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from .einstellungen import AblageEinstellungen
from .port import Ablage, AblageFehler, Belegt, Eintrag, NichtEingerichtet, NichtErreichbar, NichtGefunden, eltern
from .speicher import SpeicherAblage


class KeineAblage(Ablage):
    """Platzhalter, solange Adresse oder Schlüssel fehlen: jede Dateiarbeit meldet, was zu tun ist."""

    def __init__(self, grund: str) -> None:
        self.grund = grund

    def _fehlt(self) -> NichtEingerichtet:
        return NichtEingerichtet(self.grund)

    async def eintrag(self, pfad: str) -> Eintrag | None:
        raise self._fehlt()

    async def liste(self, ordner: str) -> list[Eintrag]:
        raise self._fehlt()

    async def ablegen(self, pfad: str, quelle: Path) -> Eintrag:
        raise self._fehlt()

    async def schreiben(self, pfad: str, daten: bytes) -> Eintrag:
        raise self._fehlt()

    async def lesen(self, pfad: str, start: int | None = None, ende: int | None = None) -> AsyncIterator[bytes]:
        raise self._fehlt()
        yield b""  # pragma: no cover

    async def verschieben(self, pfad: str, neuer_pfad: str) -> Eintrag:
        raise self._fehlt()

    async def loeschen(self, pfad: str) -> bool:
        raise self._fehlt()

    async def zustand(self) -> dict:
        return {"art": "keine", "ziel": "", "wurzel": "", "verbunden": False, "meldung": self.grund}


_aktuell: Ablage = KeineAblage("Ablage noch nicht gestartet")
_vorgegeben = False


def ablage() -> Ablage:
    return _aktuell


def setzen(neu: Ablage) -> Ablage:
    global _aktuell
    _aktuell = neu
    return neu


def vorgeben(neu: Ablage) -> Ablage:
    """Für Tests: diese Ablage gilt, auch über den Start der App hinweg."""
    global _vorgegeben
    _vorgegeben = True
    return setzen(neu)


def starten() -> Ablage:
    """Beim Start der App: die vorgegebene Ablage oder die aus den Einstellungen."""
    return _aktuell if _vorgegeben else einrichten()


def einrichten(einstellungen: AblageEinstellungen | None = None) -> Ablage:
    """Ablage nach den Einstellungen: Kellerwolke, wenn Adresse und Schlüssel da sind, sonst der Platzhalter."""
    e = einstellungen or AblageEinstellungen.aus_umgebung()
    if not e.eingerichtet:
        return setzen(KeineAblage("Kellerwolke nicht eingerichtet: RADIOHUB_KELLERWOLKE_ADRESSE und "
                                  "RADIOHUB_KELLERWOLKE_SCHLUESSEL setzen (siehe README)"))
    from .kellerwolke import KellerwolkeAblage
    try:
        return setzen(KellerwolkeAblage.aus_einstellungen(e))
    except OSError as f:
        return setzen(KeineAblage(f"Schlüssel oder Zertifikat nicht lesbar: {f}"))


__all__ = [
    "Ablage", "AblageEinstellungen", "AblageFehler", "Belegt", "Eintrag", "KeineAblage", "NichtEingerichtet",
    "NichtErreichbar", "NichtGefunden", "SpeicherAblage", "ablage", "einrichten", "eltern", "setzen", "starten",
    "vorgeben",
]
