"""Ablage in der Kellerwolke über den Zugang des Appkerns (App-Schlüssel, Pfade unter dem Wurzelordner).

Lesen, Listen, Verschieben und Löschen kommen aus der Oberfläche und warten nicht auf eine fehlende Kellerwolke;
Ablegen läuft im Hintergrund (nach Aufnahme, Download, Schnitt) und wartet so lange, wie die Einstellung
`geduld_s` erlaubt, damit ein Neustart der Kellerwolke keine Aufnahme kostet.
"""

from __future__ import annotations

import logging
import ssl
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from appkern.kellerwolke import (
    Kellerwolke, KellerwolkeFehler, Knoten, Konflikt, StandVeraltet,
    NichtErreichbar as KwNichtErreichbar, NichtGefunden as KwNichtGefunden,
)

from .einstellungen import AblageEinstellungen
from .port import Ablage, AblageFehler, Belegt, Eintrag, NichtErreichbar, NichtGefunden, eltern, sauberer_pfad

log = logging.getLogger("radiohub.ablage")


def _uebersetzt(fehler: KellerwolkeFehler) -> AblageFehler:
    if isinstance(fehler, KwNichtErreichbar):
        return NichtErreichbar(str(fehler))
    if isinstance(fehler, KwNichtGefunden):
        return NichtGefunden(str(fehler))
    if isinstance(fehler, (Konflikt, StandVeraltet)):
        return Belegt(str(fehler))
    return AblageFehler(f"Kellerwolke: {fehler}")


def tls_pruefung(ca_datei: str) -> ssl.SSLContext | bool:
    """Übliche Zertifikatsstellen und dazu die eingestellte (Hausstelle im Heimnetz)."""
    if not ca_datei:
        return True
    kontext = ssl.create_default_context()
    kontext.load_verify_locations(ca_datei)
    return kontext


class KellerwolkeAblage(Ablage):
    def __init__(self, zugang: Kellerwolke, wurzel: str, geduld_s: float,
                 client: httpx.AsyncClient | None = None) -> None:
        self._wurzel = sauberer_pfad(wurzel)
        self._schreiben = zugang.mit_geduld(geduld_s)
        self._sofort = zugang.mit_geduld(0)
        self._zugang = zugang
        self._client = client

    @classmethod
    def aus_einstellungen(cls, e: AblageEinstellungen, *, transport: httpx.AsyncBaseTransport | None = None,
                          ) -> KellerwolkeAblage:
        schluessel = Path(e.schluessel_datei).expanduser().read_text(encoding="utf-8").strip()
        client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=300.0), verify=tls_pruefung(e.ca_datei),
                                   transport=transport)
        return cls(Kellerwolke(e.adresse, schluessel, client=client), e.wurzel, e.geduld_s, client)

    def __repr__(self) -> str:
        return f"KellerwolkeAblage({self._zugang.adresse!r}, {self._wurzel!r})"

    # --- Pfade ------------------------------------------------------------------------------------------------------

    def _voll(self, pfad: str) -> str:
        rel = sauberer_pfad(pfad)
        return f"{self._wurzel}/{rel}" if rel else self._wurzel

    def _eintrag(self, knoten: Knoten) -> Eintrag:
        voll = knoten.pfad.strip("/")
        rel = voll[len(self._wurzel):].lstrip("/") if voll.startswith(self._wurzel) else voll
        return Eintrag(rel, knoten.ist_ordner, knoten.groesse or 0, knoten.geaendert_am)

    async def _knoten(self, pfad: str) -> Knoten:
        try:
            return await self._sofort.pfad(self._voll(pfad))
        except KellerwolkeFehler as f:
            raise _uebersetzt(f) from f

    # --- Lesen ------------------------------------------------------------------------------------------------------

    async def eintrag(self, pfad: str) -> Eintrag | None:
        try:
            knoten = await self._sofort.finden(self._voll(pfad))
        except KellerwolkeFehler as f:
            raise _uebersetzt(f) from f
        return self._eintrag(knoten) if knoten else None

    async def liste(self, ordner: str) -> list[Eintrag]:
        try:
            knoten = await self._sofort.finden(self._voll(ordner))
            if knoten is None or not knoten.ist_ordner:
                return []
            return [self._eintrag(k) async for k in self._sofort.alle_kinder(knoten.id)]
        except KellerwolkeFehler as f:
            raise _uebersetzt(f) from f

    async def lesen(self, pfad: str, start: int | None = None, ende: int | None = None) -> AsyncIterator[bytes]:
        knoten = await self._knoten(pfad)
        try:
            async for teil in self._sofort.lesen(knoten.id, start=start, ende=ende):
                yield teil
        except KellerwolkeFehler as f:
            raise _uebersetzt(f) from f

    # --- Schreiben --------------------------------------------------------------------------------------------------

    async def _ablegen(self, pfad: str, inhalt: bytes | Path) -> Eintrag:
        voll = self._voll(pfad)
        try:
            vorhanden = await self._schreiben.finden(voll)
            if vorhanden is not None:
                if vorhanden.ist_ordner:
                    raise Belegt(f"{pfad} ist ein Ordner")
                knoten = await self._schreiben.neue_version(vorhanden.id, inhalt, stand=vorhanden.etag or "")
            else:
                await self._schreiben.ordner(eltern(voll))
                knoten = await self._schreiben.schreiben(voll, inhalt, nur_neu=True)
        except KellerwolkeFehler as f:
            raise _uebersetzt(f) from f
        return self._eintrag(knoten)

    async def ablegen(self, pfad: str, quelle: Path) -> Eintrag:
        return await self._ablegen(pfad, quelle)

    async def schreiben(self, pfad: str, daten: bytes) -> Eintrag:
        return await self._ablegen(pfad, bytes(daten))

    async def verschieben(self, pfad: str, neuer_pfad: str) -> Eintrag:
        knoten = await self._knoten(pfad)
        ziel = self._voll(neuer_pfad)
        try:
            if await self._sofort.finden(ziel) is not None:
                raise Belegt(f"{neuer_pfad} gibt es schon")
            ordner = await self._sofort.ordner(eltern(ziel))
            name = ziel.rsplit("/", 1)[-1]
            return self._eintrag(await self._sofort.umziehen(knoten.id, ordner.id, name))
        except KellerwolkeFehler as f:
            raise _uebersetzt(f) from f

    async def loeschen(self, pfad: str) -> bool:
        try:
            knoten = await self._sofort.finden(self._voll(pfad))
            if knoten is None:
                return False
            await self._sofort.loeschen(knoten.id)
            return True
        except KellerwolkeFehler as f:
            raise _uebersetzt(f) from f

    # --- Stand ------------------------------------------------------------------------------------------------------

    async def zustand(self) -> dict:
        stand = {"art": "kellerwolke", "ziel": self._zugang.adresse, "wurzel": self._wurzel, "verbunden": False}
        try:
            ich = await self._sofort.ich()
        except KellerwolkeFehler as f:
            return {**stand, "meldung": str(_uebersetzt(f))}
        return {**stand, "verbunden": True, "app": ich.app, "konto": ich.konto,
                "meldung": f"Verbunden als App {ich.app} im Konto {ich.konto}"}

    async def schliessen(self) -> None:
        await self._zugang.schliessen()
        if self._client is not None:
            await self._client.aclose()
