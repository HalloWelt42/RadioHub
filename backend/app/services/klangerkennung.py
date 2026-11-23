"""Werbung am Klang erkennen (HELF-256): der laufende Ton eines Empfangs geht in Stücken an den Propaganda-Filter; was er als
bekannte, hier wirkende Werbung nennt, wird eine Werbestelle auf der Zeitachse des Empfangs. Umgekehrt bekommt der Filter die
Spots, die der Sender selbst ankündigt, als Ausschnitt, damit er sie auch ohne Ankündigung wiedererkennt.

Der Empfang wartet nie darauf: ist der Filter fort oder zu langsam, ruht die Erkennung und beginnt später neu. Gefundene
Stellen bleiben.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from typing import Literal

import httpx

from ..sendewerbung.sitzung import Sitzungswerbung, Werbestelle
from . import propagandafilter as pf

logger = logging.getLogger("radiohub.klangerkennung")

STUECK_S = 1.0                     # so viel Ton geht auf einmal hinaus
RUECKSTAND_S = 120.0               # mehr wartet nicht; der älteste Ton fällt weg und der Strom beginnt neu
NEUER_VERSUCH_S = 30.0
RAND_S = 2.0                       # so viel Ton um einen angekündigten Spot geht mit
SPOT_VON_S, SPOT_BIS_S = 5.0, 90.0     # nur so lange Spots werden Signatur

Zustand = Literal["aus", "laeuft", "ruht"]


class Klangerkennung:
    def __init__(self, uuid: str, name: str, art: str | None, bytes_je_s: float, werbung: Sitzungswerbung,
                 lesen: Callable[[float, float], bytes], transport: httpx.AsyncBaseTransport | None = None) -> None:
        """`lesen`: Rohdaten des Empfangs zwischen zwei Sekunden (Mitschnitt)."""
        self.uuid, self.name, self.art, self._bps, self._werbung, self._lesen = uuid, name, art, bytes_je_s, werbung, lesen
        self._transport = transport
        self._e = pf.FilterEinstellungen.jetzt()
        self.zustand: Zustand = "aus"
        self.grund = ""
        self._warten: deque[tuple[int, bytes]] = deque()       # (Stelle im Ton, Daten)
        self._wartend = 0
        self._neu = asyncio.Event()
        self._lauf: asyncio.Task | None = None
        self._nebenher: set[asyncio.Task] = set()
        self._gemeldet: set[str] = set()

    def starten(self) -> None:
        if self._e.eingerichtet and self.uuid and self.art in ("mp3", "aac"):
            self._lauf = asyncio.create_task(self._laufen())

    def ton(self, daten: bytes, ab: int) -> None:
        """Der nächste Ton; nie warten, nie mehr als `RUECKSTAND_S` halten."""
        if self._lauf is None:
            return
        self._warten.append((ab, daten))
        self._wartend += len(daten)
        while self._wartend > RUECKSTAND_S * self._bps:
            self._wartend -= len(self._warten.popleft()[1])
        if self._wartend >= STUECK_S * self._bps:
            self._neu.set()

    async def _laufen(self) -> None:
        while True:
            try:
                async with pf.verbindung(self._e, self._transport) as c:
                    await self._strom(c)
            except (httpx.HTTPError, pf.FilterFehler) as f:
                if self.zustand != "ruht":
                    logger.info("%s: Erkennung ruht (%s)", self.name, f or type(f).__name__)
                self.zustand, self.grund = "ruht", str(f) or type(f).__name__
            await asyncio.sleep(NEUER_VERSUCH_S)

    async def _strom(self, c: httpx.AsyncClient) -> None:
        """Ein Strom beim Filter, solange der Ton lückenlos bleibt."""
        kennung = (await self._gut(await c.post("/api/v1/stroeme", json={"quelle": self.uuid, "name": self.name, "art": self.art}))).json()["id"]
        self.zustand, self.grund = "laeuft", ""
        stelle: int | None = None
        try:
            while True:
                await self._neu.wait()
                self._neu.clear()
                while self._warten:
                    teile, ab = [], self._warten[0][0]
                    if stelle is not None and ab != stelle:      # Ton ging verloren: die Zeitachse stimmt nicht mehr
                        raise pf.FilterFehler("zu langsam, beginnt neu")
                    while self._warten and sum(map(len, teile)) < 4 * STUECK_S * self._bps:
                        _, d = self._warten.popleft()
                        teile.append(d)
                        self._wartend -= len(d)
                    stueck = b"".join(teile)
                    stelle = ab + len(stueck)
                    antwort = await self._gut(await c.post(f"/api/v1/stroeme/{kennung}/ton", params={"ab": round(ab / self._bps, 3)}, content=stueck))
                    for s in antwort.json()["stellen"]:
                        if s["wirkt"]:
                            self._werbung.erkannt(s["signatur"], s["von"], s["bis"], s["werbender"])
        finally:
            self._nebenbei(self._beenden(kennung))

    @staticmethod
    async def _gut(antwort: httpx.Response) -> httpx.Response:
        if antwort.status_code >= 400:
            raise pf.FilterFehler(f"der Filter antwortet mit {antwort.status_code}")
        return antwort

    async def _beenden(self, kennung: str) -> None:
        try:
            await pf.fragen("DELETE", f"stroeme/{kennung}", transport=self._transport)
        except pf.FilterFehler:
            pass                                    # der Filter vergisst einen stillen Strom von selbst

    def _nebenbei(self, arbeit) -> None:
        t = asyncio.create_task(arbeit)
        self._nebenher.add(t)
        t.add_done_callback(self._nebenher.discard)

    def angekuendigt(self, s: Werbestelle) -> None:
        """Ein Spot, den der Sender angekündigt hat, ist zu Ende: als Signatur an den Filter (je Werbendem einmal)."""
        if self._lauf is None or not s.werbender or s.bis is None or not SPOT_VON_S <= s.bis - s.von <= SPOT_BIS_S:
            return
        if (schluessel := f"{s.kennung}:{s.werbender}") in self._gemeldet:
            return
        self._gemeldet.add(schluessel)
        ab = max(0.0, s.von - RAND_S)
        daten = self._lesen(ab, s.bis + RAND_S)
        if daten:
            self._nebenbei(self._melden(daten, s.von - ab, s.bis - ab, s.werbender))

    async def _melden(self, daten: bytes, von: float, bis: float, werbender: str) -> None:
        try:
            await pf.fragen("POST", "signaturen", transport=self._transport, content=daten, headers={"Content-Type": "application/octet-stream"},
                            params={"quelle": self.uuid, "name": self.name, "von": round(von, 3), "bis": round(bis, 3), "herkunft": "angabe",
                                    "werbender": werbender[:200]})
        except pf.FilterFehler as f:
            logger.info("%s: Spot nicht gemeldet (%s)", self.name, f)

    async def schliessen(self) -> None:
        if self._lauf:
            self._lauf.cancel()
            await asyncio.gather(self._lauf, return_exceptions=True)
            self._lauf = None
        if self._nebenher:
            await asyncio.wait(self._nebenher, timeout=2.0)
