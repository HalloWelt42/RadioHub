"""Schnittstelle der Ablage: wo das RadioHub seine Dateien hält.

Jede Datei des RadioHub (Aufnahmen, Podcast-Folgen, Titellisten, Wellenformen) liegt in der Ablage. Pfade sind immer
relativ zum Wurzelordner der Ablage (etwa `Aufnahmen/SWR3/2026-10-28 14-00-05/001 Titel.mp3`) und mit `/` getrennt.
Lokal hält das RadioHub nur Zwischenstände (laufende Aufnahme, Download, Arbeitskopie beim Schneiden).

Adapter: `KellerwolkeAblage` für den Betrieb, `SpeicherAblage` für Tests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath


class AblageFehler(Exception):
    """Grundfehler der Ablage; die Meldung ist für Menschen lesbar."""


class NichtEingerichtet(AblageFehler):
    """Adresse oder Schlüssel fehlen: das RadioHub kann keine Dateien ablegen."""


class NichtErreichbar(AblageFehler):
    """Die Ablage antwortet nicht."""


class NichtGefunden(AblageFehler):
    """Unter dem Pfad liegt nichts."""


class Belegt(AblageFehler):
    """Unter dem Zielpfad liegt schon etwas."""


@dataclass(frozen=True)
class Eintrag:
    """Eine Datei oder ein Ordner in der Ablage."""

    pfad: str
    ist_ordner: bool
    groesse: int
    geaendert: datetime

    @property
    def name(self) -> str:
        return PurePosixPath(self.pfad).name

    @property
    def endung(self) -> str:
        return PurePosixPath(self.pfad).suffix.lower()


def eltern(pfad: str) -> str:
    """Elternordner eines Pfads ("" für die Wurzel)."""
    teil = str(PurePosixPath(pfad).parent)
    return "" if teil == "." else teil


def sauberer_pfad(pfad: str) -> str:
    """Pfad ohne leere Teile; "." und ".." sind nicht erlaubt (kein Ausbruch aus der Wurzel)."""
    teile = [t.strip() for t in str(pfad).replace("\\", "/").split("/") if t.strip()]
    if any(t in (".", "..") for t in teile):
        raise ValueError(f"Unerlaubter Pfad: {pfad!r}")
    return "/".join(teile)


class Ablage(ABC):
    """Dateien des RadioHub, unabhängig davon, wo sie liegen."""

    @abstractmethod
    async def eintrag(self, pfad: str) -> Eintrag | None:
        """Datei oder Ordner unter dem Pfad, None wenn es ihn nicht gibt."""

    @abstractmethod
    async def liste(self, ordner: str) -> list[Eintrag]:
        """Direkte Kinder eines Ordners (Ordner vor Dateien, nach Namen); leer, wenn es den Ordner nicht gibt."""

    @abstractmethod
    async def ablegen(self, pfad: str, quelle: Path) -> Eintrag:
        """Lokale Datei ablegen: neu anlegen oder als neue Version einer vorhandenen Datei. Fehlende Ordner entstehen."""

    @abstractmethod
    async def schreiben(self, pfad: str, daten: bytes) -> Eintrag:
        """Kleinen Inhalt ablegen (Titelliste, Wellenform), sonst wie `ablegen`."""

    @abstractmethod
    def lesen(self, pfad: str, start: int | None = None, ende: int | None = None) -> AsyncIterator[bytes]:
        """Inhalt stückweise; mit `start` (und `ende`, einschließlich) nur ein Bereich."""

    @abstractmethod
    async def verschieben(self, pfad: str, neuer_pfad: str) -> Eintrag:
        """Datei oder Ordner verschieben und umbenennen; `Belegt`, wenn das Ziel schon existiert."""

    @abstractmethod
    async def loeschen(self, pfad: str) -> bool:
        """In den Papierkorb (wiederherstellbar); False, wenn es nichts zu löschen gab."""

    @abstractmethod
    async def zustand(self) -> dict:
        """Kurzer Stand für die Oberfläche: Art, Ziel, Wurzel, verbunden, Meldung."""

    async def schliessen(self) -> None:
        """Verbindungen freigeben."""

    # --- Abgeleitet: für alle Adapter gleich ---------------------------------------------------------------------

    async def lesen_ganz(self, pfad: str, start: int | None = None, ende: int | None = None) -> bytes:
        """Nur für kleine Inhalte oder Bereiche."""
        return b"".join([teil async for teil in self.lesen(pfad, start, ende)])

    async def herunterladen(self, pfad: str, ziel: Path) -> Path:
        """In eine lokale Datei: erst vollständig unter vorläufigem Namen, dann an ihren Platz."""
        ziel.parent.mkdir(parents=True, exist_ok=True)
        vorlaeufig = ziel.with_name(f".{ziel.name}.teil")
        try:
            with open(vorlaeufig, "wb") as datei:
                async for teil in self.lesen(pfad):
                    datei.write(teil)
            vorlaeufig.replace(ziel)
        finally:
            vorlaeufig.unlink(missing_ok=True)
        return ziel

    async def alle_dateien(self, ordner: str) -> list[Eintrag]:
        """Alle Dateien unter einem Ordner, auch in Unterordnern."""
        dateien: list[Eintrag] = []
        offen = [ordner]
        while offen:
            for eintrag in await self.liste(offen.pop()):
                if eintrag.ist_ordner:
                    offen.append(eintrag.pfad)
                else:
                    dateien.append(eintrag)
        return dateien

    async def freier_pfad(self, pfad: str) -> str:
        """Der Pfad selbst, wenn er frei ist, sonst mit Zähler vor der Endung (`Name (2).mp3`)."""
        if await self.eintrag(pfad) is None:
            return pfad
        teil = PurePosixPath(pfad)
        for zaehler in range(2, 1000):
            kandidat = str(teil.with_name(f"{teil.stem} ({zaehler}){teil.suffix}"))
            if await self.eintrag(kandidat) is None:
                return kandidat
        raise Belegt(f"Kein freier Name für {pfad}")
