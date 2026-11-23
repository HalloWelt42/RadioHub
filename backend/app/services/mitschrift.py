"""Was beim Mitlesen entsteht, in die Kellerwolke (RAD-131): der Originalton, die gesprochene Übersetzung und das Transkript.

Während des Mitlesens wächst eine Mitschrift im Arbeitsordner (`arbeit/mitlesen/<Kennung>`): der gehörte Ton, die gesprochenen
Absätze hintereinander und das Blatt mit dem Text. Am Ende kommt der Ton in die Ablage und die beiden anderen als seine
Begleitdateien daneben, wie überall im Haus (`X.mp3`, `X.sprache.mp3`, `X.transkript.json`); das Transkript hat das Format
`transkript/1`, die Transkription öffnet es also wie ein eigenes. Zeiten sind Sekunden ab Beginn der jeweiligen Datei.

Nichts geht verloren, wenn der Dienst endet oder die Ablage fehlt: der Arbeitsordner bleibt, bis alles liegt, und der nächste
Start (oder das nächste Ende) holt es nach. Den Zielpfad merkt sich das Blatt, ein zweiter Versuch schreibt also dieselben Dateien.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from ..ablage import ablage, orte
from .segment_splitter import splitter

logger = logging.getLogger("radiohub.mitschrift")

BLATT, STIMME = "blatt.json", "stimme.mp3"
ROLLE_STIMME, ROLLE_TRANSKRIPT = "sprache", "transkript"


class Zeile(BaseModel):
    """Ein Absatz: wo er im Originalton liegt und, wenn gesprochen, wo in der Stimme."""

    nr: int
    start: float
    ende: float
    #: Uhrzeit, zu der es gesendet wurde
    zeit: str
    text: str
    uebersetzung: str = ""
    stimme_ab: float | None = None
    stimme_s: float = 0.0


class Blatt(BaseModel):
    sender: str
    uuid: str
    beginn: str
    endung: str
    sprache: str = ""
    ziel: str = ""
    dauer_s: float = 0.0
    stimme_s: float = 0.0
    #: Zielpfad in der Ablage, sobald das Ablegen begonnen hat
    pfad: str = ""
    zeilen: list[Zeile] = []

    def transkript(self) -> dict:
        """Als `transkript/1` der Transkription; die Übersetzung steht je Segment dabei."""
        segmente = []
        for z in self.zeilen:
            s: dict = {"start": z.start, "ende": max(z.start, z.ende), "text": z.text, "zeit": z.zeit}
            if z.uebersetzung:
                s["uebersetzung"] = z.uebersetzung
            if z.stimme_ab is not None:
                s["stimme"] = {"start": z.stimme_ab, "ende": round(z.stimme_ab + z.stimme_s, 2)}
            segmente.append(s)
        return {"format": "transkript/1", "name": f"{self.sender} {orte.zeitpunkt(self.beginn)}"[:200], "sprache": self.sprache or "und",
                "dauer_s": round(self.dauer_s, 2), "segmente": segmente,
                **({"uebersetzt_in": self.ziel} if any(z.uebersetzung for z in self.zeilen) else {}),
                "erzeugt_mit": {"dienst": "hoeren", "app": "RadioHub", "sprecher_aus": "ohne"}}


@dataclass
class Mitschrift:
    """Eine laufende Mitschrift im Arbeitsordner."""

    ordner: Path
    blatt: Blatt
    #: (Sekunde des Empfangs, Sekunde der Datei, Länge) je Stück Ton
    _stuecke: list[tuple[float, float, float]] = field(default_factory=list)
    _zeilen: dict[int, Zeile] = field(default_factory=dict)

    @property
    def ton_datei(self) -> Path:
        return self.ordner / f"ton{self.blatt.endung}"

    def ton(self, daten: bytes, von: float, bis: float) -> None:
        with self.ton_datei.open("ab") as f:
            f.write(daten)
        self._stuecke.append((von, self.blatt.dauer_s, bis - von))
        self.blatt.dauer_s += bis - von

    def _in_datei(self, sekunde: float) -> float:
        for von, ab, laenge in reversed(self._stuecke):
            if von <= sekunde <= von + laenge:
                return round(ab + sekunde - von, 2)
        return round(self.blatt.dauer_s, 2)

    def absatz(self, nr: int, von: float, bis: float, zeit: str, text: str) -> None:
        z = self._zeilen[nr] = Zeile(nr=nr, start=self._in_datei(von), ende=self._in_datei(bis), zeit=zeit, text=text)
        self.blatt.zeilen.append(z)
        self.merken()

    def uebersetzt(self, nr: int, uebersetzung: str) -> None:
        if (z := self._zeilen.get(nr)) is not None:
            z.uebersetzung = uebersetzung
            self.merken()

    def gesprochen(self, nr: int, ton: bytes, dauer_s: float) -> None:
        if (z := self._zeilen.get(nr)) is not None:
            with (self.ordner / STIMME).open("ab") as f:
                f.write(ton)
            z.stimme_ab, z.stimme_s = round(self.blatt.stimme_s, 2), round(dauer_s, 2)
            self.blatt.stimme_s += dauer_s
            self.merken()

    def merken(self) -> None:
        _schreiben(self.ordner, self.blatt)


def _schreiben(ordner: Path, blatt: Blatt) -> None:
    neu = ordner / f"{BLATT}.neu"
    neu.write_text(blatt.model_dump_json(), encoding="utf-8")
    neu.replace(ordner / BLATT)


async def _ablegen(ordner: Path, blatt: Blatt) -> str:
    """Ton, Stimme und Transkript an ihren Platz; liefert den Pfad des Tons."""
    a = ablage()
    if not blatt.pfad:
        blatt.pfad = await a.freier_pfad(orte.mitlesung(blatt.sender, blatt.beginn, blatt.endung))
        _schreiben(ordner, blatt)
    ton = ordner / f"ton{blatt.endung}"
    await a.ablegen(blatt.pfad, await _mit_kopf(ton))
    stimme = ordner / STIMME
    if stimme.exists():
        await a.begleiten(blatt.pfad, ROLLE_STIMME, ".sprache.mp3", await _mit_kopf(stimme), "audio/mpeg")
    await a.begleiten(blatt.pfad, ROLLE_TRANSKRIPT, ".transkript.json", _json(blatt.transkript()), "application/json")
    return blatt.pfad


def _json(daten: dict) -> bytes:
    return json.dumps(daten, ensure_ascii=False, indent=1).encode("utf-8")


async def _mit_kopf(datei: Path) -> Path:
    """Aneinandergehängter Ton bekommt einen Kopf mit der richtigen Länge; gelingt das nicht, bleibt er, wie er ist."""
    return await splitter.zusammenfuegen([datei], datei.with_name(f"fertig-{datei.name}")) or datei


async def _still(_ereignis: str, _stufe: str) -> None:
    return None


@dataclass
class Mitschriften:
    """Beginnt Mitschriften, legt sie am Ende ab und holt liegengebliebene nach."""

    wurzel: Callable[[], Path]
    #: meldet, was abgelegt wurde oder woran es scheitert (Text, Stufe)
    melden: Callable[[str, str], Awaitable[None]] = _still
    _laufend: set[Path] = field(default_factory=set)
    _aufgaben: set[asyncio.Task[None]] = field(default_factory=set)
    _sperre: asyncio.Lock = field(default_factory=asyncio.Lock)

    def beginnen(self, sender: str, uuid: str, endung: str, ziel: str, beginn: datetime) -> Mitschrift:
        ordner = self.wurzel() / uuid4().hex
        ordner.mkdir(parents=True)
        self._laufend.add(ordner)
        return Mitschrift(ordner, Blatt(sender=sender, uuid=uuid, beginn=beginn.isoformat(timespec="seconds"), endung=endung, ziel=ziel))

    def fertig(self, m: Mitschrift) -> None:
        """Das Mitlesen ist zu Ende: im Hintergrund ablegen, das Radio wartet nicht darauf."""
        m.merken()
        self._laufend.discard(m.ordner)
        aufgabe = asyncio.create_task(self.nachholen(), name="mitschrift-ablegen")
        self._aufgaben.add(aufgabe)
        aufgabe.add_done_callback(self._aufgaben.discard)

    async def nachholen(self) -> None:
        """Alles ablegen, was nicht mehr wächst."""
        async with self._sperre:
            for ordner in sorted(p for p in self.wurzel().iterdir() if p.is_dir() and p not in self._laufend):
                await self._einen(ordner)

    async def _einen(self, ordner: Path) -> None:
        try:
            blatt = Blatt.model_validate_json((ordner / BLATT).read_bytes())
        except (OSError, ValidationError):
            blatt = None
        if blatt is None or not blatt.zeilen or not (ordner / f"ton{blatt.endung}").exists():
            shutil.rmtree(ordner, ignore_errors=True)        # nichts gehört: es gibt nichts abzulegen
            return
        try:
            pfad = await _ablegen(ordner, blatt)
        except Exception as f:  # noqa: BLE001 - bleibt liegen, der nächste Versuch holt es nach
            logger.warning("Mitschrift %s nicht abgelegt: %s", blatt.sender, f)
            await self.melden(f"{blatt.sender} {orte.zeitpunkt(blatt.beginn)} nicht abgelegt, wird nachgeholt: {f}", "warnung")
            return
        shutil.rmtree(ordner, ignore_errors=True)
        await self.melden(f"abgelegt: {pfad}", "info")
