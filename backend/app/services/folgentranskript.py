"""Transkripte der Podcast-Folgen (RAD-22): mitlesen beim Hören.

Zwei Herkünfte: das Transkript des Feeds (VTT, SRT oder JSON, mit Zeiten) und das gehörte. Gehört wird auf Knopfdruck von der
Transkription, der gemeinsamen App dafür: die gespeicherte Folge geht als Anfrage über die Kellerwolke dorthin, das Ergebnis legt
sie als Begleitdatei neben die Folge (`.transkript.json`, Format `transkript/1`). RadioHub führt dazu einen Auftrag, der den
Fortschritt zeigt und nach einem Neustart weiterwartet. Ein gehörtes Transkript geht dem des Feeds vor.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Literal

import httpx
from appkern.auftraege import Art, AuftragFehler, Kontext, Phase
from pydantic import BaseModel

from ..ablage import AblageFehler, ablage
from ..database import db_session
from ..einstellungen import stand as einstellungen_stand

ART = "folge_transkribieren"
ROLLE = "transkript"
TAKT_S = 3.0
ABSATZ_ZEICHEN, PAUSE_S = 220, 2.5            # ein Absatz ist so lang und endet mit einem Satz; eine Pause oder ein Sprecher trennt
GEMERKT = 12                                  # so viele gelesene Transkripte bleiben im Arbeitsspeicher
SATZENDE = re.compile(r"[.!?。！？…][\"')\]»]*$")
ZEITZEILE = re.compile(r"((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})")
SPRECHER = re.compile(r"<v(?:\.[^ >]+)?\s+([^>]+)>")

Herkunft = Literal["feed", "gehoert", "vertont"]


class Segment(BaseModel):
    start: float
    ende: float
    text: str
    sprecher: str = ""


class Absatz(BaseModel):
    nr: int
    von: float
    bis: float
    text: str
    sprecher: str = ""


class Transkript(BaseModel):
    herkunft: Herkunft
    sprache: str = ""
    absaetze: list[Absatz]


def _sekunden(text: str) -> float:
    s = 0.0
    for teil in text.replace(",", ".").split(":"):
        s = s * 60 + float(teil)
    return s


def aus_untertiteln(inhalt: str) -> list[Segment]:
    """VTT oder SRT"""
    segmente: list[Segment] = []
    offen: Segment | None = None
    for zeile in [*inhalt.splitlines(), ""]:
        z = zeile.strip()
        if m := ZEITZEILE.search(z):
            offen = Segment(start=_sekunden(m[1]), ende=_sekunden(m[2]), text="")
        elif not z:
            if offen and offen.text:
                segmente.append(offen)
            offen = None
        elif offen:
            if s := SPRECHER.search(z):
                offen.sprecher = s[1].strip()
            offen.text = f"{offen.text} {re.sub(r'<[^>]+>', '', z)}".strip()
    return segmente


def aus_json(daten: dict) -> list[Segment]:
    """`transkript/1` der Transkription oder das JSON der Feeds (startTime, endTime, body, speaker)"""
    namen = {s.get("kennung"): s.get("name") or "" for s in daten.get("sprecher") or [] if isinstance(s, dict)}
    aus = []
    for s in daten.get("segmente") or daten.get("segments") or []:
        text = str(s.get("text") or s.get("body") or "").strip()
        if text:
            start = float(s.get("start", s.get("startTime", 0)) or 0)
            ende = float(s.get("ende", s.get("endTime", start)) or start)
            aus.append(Segment(start=start, ende=ende, text=text, sprecher=namen.get(s.get("sprecher"), "") or str(s.get("speaker") or "")))
    return aus


def absaetze(segmente: list[Segment]) -> list[Absatz]:
    """Segmente zu lesbaren Absätzen: ganze Sätze, getrennt an Pausen und Sprecherwechseln."""
    aus: list[Absatz] = []
    for s in segmente:
        a = aus[-1] if aus else None
        voll = a is not None and len(a.text) >= ABSATZ_ZEICHEN and SATZENDE.search(a.text)
        pause = a is not None and s.start - a.bis > PAUSE_S and SATZENDE.search(a.text)
        if a is None or voll or pause or (s.sprecher and s.sprecher != a.sprecher):
            aus.append(Absatz(nr=len(aus), von=round(s.start, 2), bis=round(s.ende, 2), text=s.text, sprecher=s.sprecher))
        else:
            a.text, a.bis = f"{a.text} {s.text}", round(max(a.bis, s.ende), 2)
    return aus


class Eingabe(BaseModel):
    folge_id: int


class Ergebnis(BaseModel):
    absaetze: int


class Gehoert(BaseModel):
    sprache: str = ""
    segmente: list[Segment]


class Gespeichert(BaseModel):
    pfad: str
    titel: str


async def _kein_abruf(_adresse: str) -> tuple[str, str]:
    raise httpx.HTTPError("kein Abruf eingerichtet")


class Folgentranskripte:
    """`folge`: die Folge aus der Datenbank; `speichern`: legt sie in der Ablage ab; `abruf`: Inhalt und Typ einer Adresse des Feeds."""

    def __init__(self) -> None:
        self.folge: Callable[[int], Awaitable[dict | None]] | None = None
        self.speichern: Callable[[int], Awaitable[dict]] | None = None
        self.abruf: Callable[[str], Awaitable[tuple[str, str]]] = _kein_abruf
        self._gemerkt: OrderedDict[tuple[int, str], Transkript] = OrderedDict()

    # ----- Lesen

    async def lesen(self, folge: dict, fassung: str = "") -> Transkript | None:
        """`fassung`: der Text einer vertonten Fassung (Sprache), sonst der des Originals."""
        if fassung:
            return await self._begleiter(folge, f"{ROLLE}_{fassung}", "vertont")
        return await self._begleiter(folge, ROLLE, "gehoert") or await self._feed(folge)

    def vergessen(self, folge_id: int) -> None:
        for schluessel in [s for s in self._gemerkt if s[0] == folge_id]:
            del self._gemerkt[schluessel]

    async def _begleiter(self, folge: dict, rolle: str, herkunft: Herkunft) -> Transkript | None:
        pfad = folge.get("local_path") if folge.get("is_downloaded") else None
        if not pfad:
            return None
        schluessel = (folge["id"], rolle)
        if (t := self._gemerkt.get(schluessel)) is not None:
            return t
        try:
            roh = await ablage().begleiter_lesen(pfad, rolle)
        except AblageFehler:
            return None
        if roh is None:
            return None
        daten = json.loads(roh)
        return self._merken(schluessel, Transkript(herkunft=herkunft, sprache=str(daten.get("sprache") or ""), absaetze=absaetze(aus_json(daten))))

    async def _feed(self, folge: dict) -> Transkript | None:
        adresse = str(folge.get("transcript_url") or "")
        if not adresse:
            return None
        schluessel = (folge["id"], "feed")
        if (t := self._gemerkt.get(schluessel)) is not None:
            return t
        try:
            inhalt, typ = await self.abruf(adresse)
        except httpx.HTTPError:
            return None
        try:
            segmente = aus_json(json.loads(inhalt)) if "json" in typ or adresse.lower().endswith(".json") else aus_untertiteln(inhalt)
        except (ValueError, AttributeError, TypeError):
            return None
        if not segmente:
            return None
        self._text_merken(folge["id"], segmente)
        return self._merken(schluessel, Transkript(herkunft="feed", absaetze=absaetze(segmente)))

    def _merken(self, schluessel: tuple[int, str], t: Transkript) -> Transkript:
        self._gemerkt[schluessel] = t
        while len(self._gemerkt) > GEMERKT:
            self._gemerkt.popitem(last=False)
        return t

    @staticmethod
    def _text_merken(folge_id: int, segmente: list[Segment]) -> None:
        """Der reine Text in die Datenbank: die Suche der Folgen findet ihn."""
        with db_session() as conn:
            conn.execute("UPDATE podcast_episodes SET transcript = ? WHERE id = ?", ("\n".join(s.text for s in segmente), folge_id))

    # ----- Hören lassen

    def kann(self) -> bool:
        return bool(einstellungen_stand().transkription_app.strip())

    async def gespeichert(self, k: Kontext, folge_id: int) -> Gespeichert:
        """Die Folge in der Ablage (speichert sie, wenn sie noch nicht da ist)."""
        assert self.folge is not None and self.speichern is not None
        folge = await self.folge(folge_id)
        if folge is None:
            raise AuftragFehler("Die Folge gibt es nicht mehr")
        await k.fortschritt(None, "Folge in der Kellerwolke speichern", phase="speichern")
        ablage_stand = await self.speichern(folge_id)
        if not ablage_stand.get("success"):
            raise AuftragFehler(f"Folge nicht gespeichert: {ablage_stand.get('error') or 'unbekannt'}")
        await k.pruefen()
        return Gespeichert(pfad=ablage_stand["path"], titel=str(folge.get("title") or folge_id))

    async def gehoert_sichern(self, k: Kontext, folge_id: int, pfad: str, neu: bool = False) -> Gehoert:
        """Das gehörte Transkript neben der Folge; fehlt es (oder soll es neu), transkribiert die Transkription."""
        roh = None if neu else await self._roh(pfad)
        if roh is None:
            await self._hoeren_lassen(k, pfad)
            roh = await self._roh(pfad)
            if roh is None:
                raise AuftragFehler("Die Transkription ist fertig, aber ihr Transkript liegt nicht neben der Folge")
        daten = json.loads(roh)
        gehoert = Gehoert(sprache=str(daten.get("sprache") or ""), segmente=aus_json(daten))
        self._text_merken(folge_id, gehoert.segmente)
        self._gemerkt.pop((folge_id, ROLLE), None)
        return gehoert

    @staticmethod
    async def _roh(pfad: str) -> bytes | None:
        try:
            return await ablage().begleiter_lesen(pfad, ROLLE)
        except AblageFehler as f:
            raise AuftragFehler(f"Transkript nicht lesbar: {f}") from f

    async def _hoeren_lassen(self, k: Kontext, pfad: str) -> None:
        if "anfrage" not in k.zwischenstand:
            try:
                anfrage = await ablage().weitergeben(pfad, einstellungen_stand().transkription_app.strip(), "transkribieren", {"sprache": "auto"})
            except AblageFehler as f:
                raise AuftragFehler(f"Transkription: {f}") from f
            await k.merken(anfrage=anfrage)
        await self._abwarten(k, k.zwischenstand["anfrage"])

    async def _transkribieren(self, k: Kontext) -> Ergebnis:
        e: Eingabe = k.eingabe
        folge = await self.gespeichert(k, e.folge_id)
        gehoert = await self.gehoert_sichern(k, e.folge_id, folge.pfad, neu=True)
        return Ergebnis(absaetze=len(absaetze(gehoert.segmente)))

    async def _abwarten(self, k: Kontext, anfrage: str) -> None:
        await k.fortschritt(None, "Transkription", phase="hoeren")
        while True:
            await k.pruefen()
            try:
                s = await ablage().anfragestand(anfrage)
            except AblageFehler as f:            # die Kellerwolke ist kurz weg: weiter warten, der Abbruch bleibt möglich
                await k.fortschritt(None, str(f))
            else:
                if s.zustand == "fertig":
                    return
                if s.zustand in ("fehler", "abgebrochen", "abgelaufen"):
                    await k.merken(anfrage=None)
                    k.zwischenstand.pop("anfrage", None)
                    raise AuftragFehler(f"Transkription: {s.meldung or s.zustand}")
                await k.fortschritt(s.fortschritt, s.meldung or "wartet")
            await asyncio.sleep(TAKT_S)

    def art(self) -> Art:
        return Art(name=ART, titel="Folge transkribieren", arbeit=self._transkribieren, eingabe=Eingabe, fortsetzbar=True,
                   nach_neustart="fortsetzen", hoechstens=2, gegenstand=lambda e: f"folge:{e.get('folge_id')}",
                   phasen=[Phase(schluessel="speichern", titel="Folge speichern", symbol="cloud-arrow-up"),
                           Phase(schluessel="hoeren", titel="Transkribieren", symbol="closed-captioning")])


folgentranskripte = Folgentranskripte()
