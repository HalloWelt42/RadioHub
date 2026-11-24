"""Messmodus (RAD-143): schreibt mit, was beim Hören und Aufnehmen geschieht, damit sich hinterher jede auffällige Stelle erklären
lässt, etwa nach einer Nacht Aufnahme.

Eine Datei je Tag (`messung_JJJJ-MM-TT.jsonl`, eine Zeile je Ereignis: `t` Uhrzeit, `art`, Werte) im Datenordner; nichts davon geht
aus dem Haus. Der Schalter ist die Einstellung `messmodus`; aus, kostet ein Aufruf von `merken` nichts. Gesammelt wird im Speicher
und alle paar Sekunden angehängt. Ist die Grenze erreicht, hört er auf und sagt es; gelöscht wird nur auf Wunsch.

Wer misst, steht bei der Sache selbst: der Stromleser seine Verbindungen, der Rekorder Teilen und Ablegen, der Feinschnitt jede
Grenze mit ihrem Grund, die Oberfläche das Tonelement. Hier stehen nur Sammeln, Auslastung und der Bericht.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..config import DB_PATH

logger = logging.getLogger("radiohub.messung")

SCHREIBEN_ALLE_S = 3.0
AUSLASTUNG_ALLE_S = 30.0
#: alle Dateien zusammen höchstens
HOECHSTENS = 200 << 20
#: im Speicher höchstens so viele Ereignisse (die Platte ist weg oder hängt)
GESAMMELT_HOECHSTENS = 20000

#: ab hier gilt etwas als auffällig
VIELE_TONEREIGNISSE, HAENGT_S, ABLAGE_LANGSAM_S, SCHNITT_LANGSAM_S, LAST_HOCH = 12, 1.0, 10.0, 30.0, 6.0


class Datei(BaseModel):
    name: str
    groesse: int
    ereignisse: int
    von: str
    bis: str


class Auffaellig(BaseModel):
    t: str
    was: str
    werte: dict[str, Any]


class Bericht(BaseModel):
    ereignisse: int
    arten: dict[str, int]
    #: Grenzen des Feinschnitts nach ihrem Grund (pause, tal, angabe, werbung)
    grenzen: dict[str, int]
    auffaellig: list[Auffaellig]


def _ordner() -> Path:
    ordner = DB_PATH.parent / "messung"
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner


def _an() -> bool:
    from ..einstellungen import stand
    return stand().messmodus


class Messung:
    def __init__(self) -> None:
        self._gesammelt: list[str] = []
        self._voll = False
        #: was zur Auslastung gehört und nur andere wissen (laufende Aufnahme, Empfänge)
        self.lage: Callable[[], dict[str, Any]] = dict

    @property
    def aktiv(self) -> bool:
        return not self._voll and _an()

    def merken(self, art: str, vor_ms: float = 0, **werte: Any) -> None:
        if not self.aktiv or len(self._gesammelt) >= GESAMMELT_HOECHSTENS:
            return
        self._gesammelt.append(json.dumps({"t": (datetime.now() - timedelta(milliseconds=vor_ms)).isoformat(timespec="milliseconds"), "art": art, **werte},
                                          ensure_ascii=False, default=str))

    def schreiben(self) -> None:
        zeilen, self._gesammelt = self._gesammelt, []
        if not zeilen:
            return
        ordner = _ordner()
        if sum(d.stat().st_size for d in ordner.glob("messung_*.jsonl")) > HOECHSTENS:
            self._voll = True
            logger.warning(f"Messmodus: {HOECHSTENS >> 20} MB erreicht, es wird nichts mehr mitgeschrieben")
            return
        with open(ordner / f"messung_{datetime.now():%Y-%m-%d}.jsonl", "a", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")

    async def laufen(self) -> None:
        """Schreibt und misst die Auslastung, solange die App läuft."""
        zuletzt = 0.0
        while True:
            await asyncio.sleep(SCHREIBEN_ALLE_S)
            try:
                if self.aktiv and time.monotonic() - zuletzt >= AUSLASTUNG_ALLE_S:
                    zuletzt = time.monotonic()
                    self.merken("auslastung", **auslastung(), **self.lage())
                await asyncio.to_thread(self.schreiben)
            except Exception as f:  # noqa: BLE001 - die Messung stört nie den Betrieb
                logger.warning(f"Messung: {f}")

    # --- Auswerten ------------------------------------------------------------------------------------------------

    def dateien(self) -> list[Datei]:
        aus = []
        for d in sorted(_ordner().glob("messung_*.jsonl"), reverse=True):
            zeilen = d.read_text(encoding="utf-8").splitlines()
            if zeilen:
                aus.append(Datei(name=d.name, groesse=d.stat().st_size, ereignisse=len(zeilen), von=json.loads(zeilen[0])["t"], bis=json.loads(zeilen[-1])["t"]))
        return aus

    def pfad(self, name: str) -> Path | None:
        return next((d for d in _ordner().glob("messung_*.jsonl") if d.name == name), None)

    def bericht(self, name: str) -> Bericht | None:
        pfad = self.pfad(name)
        if pfad is None:
            return None
        with open(pfad, encoding="utf-8") as f:
            return berichten(json.loads(z) for z in f if z.strip())

    def loeschen(self) -> int:
        """Alle Messdateien (nur auf ausdrücklichen Wunsch); liefert ihre Zahl."""
        self._gesammelt, self._voll = [], False
        alle = list(_ordner().glob("messung_*.jsonl"))
        for d in alle:
            d.unlink()
        return len(alle)


def auslastung() -> dict[str, Any]:
    werte: dict[str, Any] = {"last": round(os.getloadavg()[0], 2), "frei_gb": round(shutil.disk_usage(DB_PATH.parent).free / 2 ** 30, 1)}
    try:
        meminfo = dict(z.split(":", 1) for z in Path("/proc/meminfo").read_text().splitlines())
        mb = lambda k: int(meminfo[k].split()[0]) // 1024                            # noqa: E731
        werte |= {"speicher_frei_mb": mb("MemAvailable"), "auslagerung_frei_mb": mb("SwapFree")}
        werte["app_mb"] = int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE") >> 20
    except (OSError, KeyError, ValueError):
        pass                                                                         # nicht auf diesem System
    return werte


def berichten(ereignisse: Iterable[dict[str, Any]]) -> Bericht:
    arten: Counter[str] = Counter()
    grenzen: Counter[str] = Counter()
    auffaellig: list[Auffaellig] = []
    for e in ereignisse:
        art = e["art"]
        arten[art] += 1
        if art == "grenze":
            grenzen[e.get("grund", "?")] += 1
        if was := _auffaellig(art, e):
            auffaellig.append(Auffaellig(t=e["t"], was=was, werte={k: v for k, v in e.items() if k not in ("t", "art")}))
    return Bericht(ereignisse=sum(arten.values()), arten=dict(arten.most_common()), grenzen=dict(grenzen), auffaellig=sorted(auffaellig, key=lambda a: a.t))


def _auffaellig(art: str, e: dict[str, Any]) -> str:
    if art == "ton" and e.get("anzahl", 0) >= VIELE_TONEREIGNISSE:
        return "Ton springt schnell hin und her"
    if art == "gestockt" and e.get("dauer_s", 0) >= HAENGT_S:
        return "Ton stockt"
    if art in ("strom_weg", "ton_fehler", "seite_fehler", "hls_fehler", "netz_weg", "stueckschleife", "luecke", "steht"):
        return {"strom_weg": "Verbindung zum Sender gerissen", "ton_fehler": "Fehler am Ton", "seite_fehler": "Fehler in der Oberfläche",
                "hls_fehler": "Fehler im Zeitversatz", "netz_weg": "Gerät ohne Netz", "stueckschleife": "Dasselbe Tonstück in einer Schleife",
                "luecke": "Aussetzer beim Aufnehmen", "steht": "Aufnahme steht"}[art]
    if art == "abgelegt" and (e.get("fehler") or e.get("dauer_s", 0) >= ABLAGE_LANGSAM_S):
        return "Ablegen gescheitert" if e.get("fehler") else "Ablegen langsam"
    if art == "feinschnitt" and (e.get("fehler") or e.get("dauer_s", 0) >= SCHNITT_LANGSAM_S):
        return "Feinschnitt gescheitert" if e.get("fehler") else "Feinschnitt langsam"
    if art == "auslastung" and e.get("last", 0) >= LAST_HOCH:
        return "Server stark ausgelastet"
    if art == "seite_haengt":
        return "Oberfläche hängt"
    return ""


messung = Messung()
