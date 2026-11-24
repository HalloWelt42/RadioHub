"""Ablage des RadioHub: Schnittstelle, Adapter und die eine Instanz der laufenden App.

Die laufende App richtet die Ablage nach jedem Aufbau der Zugänge des Gerüsts ein (`starten` mit dem Zugang zur
Kellerwolke), außer ein Test hat vorher eine `SpeicherAblage` vorgegeben (`vorgeben`). Alle Dienste holen sie über
`ablage()`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from appkern.kellerwolke import Kellerwolke

from .einstellungen import AblageEinstellungen
from .port import Ablage, AblageFehler, Anfragestand, Belegt, Eintrag, NichtEingerichtet, NichtErreichbar, NichtGefunden, Platz, eltern
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

    async def begleiten(self, pfad: str, rolle: str, zusatz: str, daten: bytes | Path, inhaltstyp: str) -> Eintrag:
        raise self._fehlt()

    async def begleiter_lesen(self, pfad: str, rolle: str) -> bytes | None:
        raise self._fehlt()

    async def begleiter(self, pfad: str) -> list[Eintrag]:
        raise self._fehlt()

    async def weitergeben(self, pfad: str, app: str, aktion: str, optionen: dict[str, str]) -> str:
        raise self._fehlt()

    async def anfragestand(self, anfrage: str) -> Anfragestand:
        raise self._fehlt()

    async def lesen(self, pfad: str, start: int | None = None, ende: int | None = None) -> AsyncIterator[bytes]:
        raise self._fehlt()
        yield b""  # pragma: no cover

    async def verschieben(self, pfad: str, neuer_pfad: str) -> Eintrag:
        raise self._fehlt()

    async def loeschen(self, pfad: str) -> bool:
        raise self._fehlt()

    async def platz(self) -> Platz:
        return Platz()

    async def zustand(self) -> dict:
        return {"art": "keine", "ziel": "", "wurzel": "", "verbunden": False, "meldung": self.grund}


_aktuell: Ablage = KeineAblage("Ablage noch nicht gestartet")
_vorgegeben = False
_wolke: Ablage = KeineAblage("Kellerwolke nicht eingerichtet")


def ablage() -> Ablage:
    return _aktuell


def wolke() -> Ablage:
    """Die ganze Kellerwolke (RAD-17), Pfade ab der obersten Ebene; Lesen braucht die Freigabe "Alles lesen"."""
    return _wolke


def wolke_setzen(neu: Ablage) -> Ablage:
    global _wolke
    _wolke = neu
    return neu


def setzen(neu: Ablage) -> Ablage:
    global _aktuell
    _aktuell = neu
    return neu


def vorgeben(neu: Ablage) -> Ablage:
    """Für Tests: diese Ablage gilt, auch über den Start der App hinweg."""
    global _vorgegeben
    _vorgegeben = True
    return setzen(neu)


NICHT_EINGERICHTET = ("Kellerwolke nicht eingerichtet: Adresse und App-Schlüssel in den Einstellungen unter "
                      "Verbindungen (RADIOHUB_KELLERWOLKE_ADRESSE und RADIOHUB_KELLERWOLKE_SCHLUESSEL)")


def starten(zugang: Kellerwolke | None, einstellungen: AblageEinstellungen | None = None) -> Ablage:
    """Nach jedem Aufbau der Zugänge: die vorgegebene Ablage oder die über diesen Zugang."""
    return _aktuell if _vorgegeben else einrichten(zugang, einstellungen)


def einrichten(zugang: Kellerwolke | None, einstellungen: AblageEinstellungen | None = None) -> Ablage:
    """Ablage über den Zugang zur Kellerwolke (der des Gerüsts, er gehört nicht der Ablage); ohne Zugang der
    Platzhalter, der bei jeder Dateiarbeit sagt, was fehlt."""
    if zugang is None:
        wolke_setzen(KeineAblage(NICHT_EINGERICHTET))
        return setzen(KeineAblage(NICHT_EINGERICHTET))
    from .kellerwolke import KellerwolkeAblage, KellerwolkeWolke
    e = einstellungen or AblageEinstellungen()
    wolke_setzen(KellerwolkeWolke(zugang, e.geduld_s))
    return setzen(KellerwolkeAblage(zugang, e.wurzel, e.geduld_s))


__all__ = [
    "Ablage", "AblageEinstellungen", "AblageFehler", "Anfragestand", "Belegt", "Eintrag", "KeineAblage", "Platz", "NichtEingerichtet",
    "NichtErreichbar", "NichtGefunden", "SpeicherAblage", "ablage", "einrichten", "eltern", "setzen", "starten",
    "vorgeben", "wolke", "wolke_setzen",
]
