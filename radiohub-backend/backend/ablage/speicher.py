"""Ablage im Arbeitsspeicher, für Tests: verhält sich wie die Kellerwolke (Ordner entstehen beim Ablegen, Löschen
legt in einen Papierkorb, Ablegen auf eine vorhandene Datei schreibt eine neue Version)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from .port import Ablage, Belegt, Eintrag, NichtGefunden, eltern, sauberer_pfad


class SpeicherAblage(Ablage):
    def __init__(self) -> None:
        self.dateien: dict[str, bytes] = {}
        self.ordner: set[str] = set()
        self.versionen: dict[str, int] = {}
        self.papierkorb: list[str] = []
        self._zeit: dict[str, datetime] = {}

    def _ordner_anlegen(self, pfad: str) -> None:
        while pfad:
            self.ordner.add(pfad)
            pfad = eltern(pfad)

    def _eintrag(self, pfad: str) -> Eintrag | None:
        if pfad in self.dateien:
            return Eintrag(pfad, False, len(self.dateien[pfad]), self._zeit[pfad])
        if pfad in self.ordner:
            return Eintrag(pfad, True, 0, self._zeit.get(pfad, datetime.now()))
        return None

    async def eintrag(self, pfad: str) -> Eintrag | None:
        return self._eintrag(sauberer_pfad(pfad))

    async def liste(self, ordner: str) -> list[Eintrag]:
        ordner = sauberer_pfad(ordner)
        kinder = {p for p in self.ordner | set(self.dateien) if eltern(p) == ordner and p}
        eintraege = [self._eintrag(p) for p in kinder]
        return sorted((e for e in eintraege if e), key=lambda e: (not e.ist_ordner, e.name.lower()))

    async def schreiben(self, pfad: str, daten: bytes) -> Eintrag:
        pfad = sauberer_pfad(pfad)
        if pfad in self.ordner:
            raise Belegt(f"{pfad} ist ein Ordner")
        self._ordner_anlegen(eltern(pfad))
        self.dateien[pfad] = bytes(daten)
        self.versionen[pfad] = self.versionen.get(pfad, 0) + 1
        self._zeit[pfad] = datetime.now()
        return self._eintrag(pfad)

    async def ablegen(self, pfad: str, quelle: Path) -> Eintrag:
        return await self.schreiben(pfad, quelle.read_bytes())

    async def lesen(self, pfad: str, start: int | None = None, ende: int | None = None) -> AsyncIterator[bytes]:
        pfad = sauberer_pfad(pfad)
        if pfad not in self.dateien:
            raise NichtGefunden(f"{pfad} nicht gefunden")
        daten = self.dateien[pfad]
        anfang = start or 0
        schluss = len(daten) if ende is None else ende + 1
        yield daten[anfang:schluss]

    async def verschieben(self, pfad: str, neuer_pfad: str) -> Eintrag:
        pfad, neuer_pfad = sauberer_pfad(pfad), sauberer_pfad(neuer_pfad)
        if self._eintrag(pfad) is None:
            raise NichtGefunden(f"{pfad} nicht gefunden")
        if self._eintrag(neuer_pfad) is not None:
            raise Belegt(f"{neuer_pfad} gibt es schon")
        self._ordner_anlegen(eltern(neuer_pfad))
        for alt in [p for p in list(self.dateien) if p == pfad or p.startswith(pfad + "/")]:
            neu = neuer_pfad + alt[len(pfad):]
            self.dateien[neu] = self.dateien.pop(alt)
            self.versionen[neu] = self.versionen.pop(alt, 1)
            self._zeit[neu] = self._zeit.pop(alt)
        for alt in [p for p in list(self.ordner) if p == pfad or p.startswith(pfad + "/")]:
            self.ordner.discard(alt)
            self.ordner.add(neuer_pfad + alt[len(pfad):])
        return self._eintrag(neuer_pfad)

    async def loeschen(self, pfad: str) -> bool:
        pfad = sauberer_pfad(pfad)
        if self._eintrag(pfad) is None:
            return False
        for p in [p for p in list(self.dateien) if p == pfad or p.startswith(pfad + "/")]:
            del self.dateien[p]
            self.papierkorb.append(p)
        for p in [p for p in list(self.ordner) if p == pfad or p.startswith(pfad + "/")]:
            self.ordner.discard(p)
        return True

    async def zustand(self) -> dict:
        return {"art": "speicher", "ziel": "Arbeitsspeicher", "wurzel": "", "verbunden": True, "meldung": "Testablage"}
