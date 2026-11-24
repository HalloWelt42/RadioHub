"""Der Dienst der Vertonung (RAD-26): eine Aufnahme mit ihrem Text abgeben, den Auftrag verfolgen, Ton und Texte holen. Angemeldet über
den Verbund des Appkerns (App-Schlüssel, Zertifikatsstelle). Hier steht nur der Weg zur Vertonung; was mit Folgen geschieht, weiß
`folgenvertonung`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from appkern.verbund import Verbund, VerbundFehler
from pydantic import BaseModel

from ..einstellungen import Klang

ABFRAGE = httpx.Timeout(60.0, connect=10.0)
HOCHLADEN = httpx.Timeout(300.0, connect=10.0, write=300.0)


class Spurtext(BaseModel):
    start: float
    ende: float
    text: str
    sprecher: str | None = None


class Textspur(BaseModel):
    sprache: str = ""
    segmente: list[Spurtext] = []


class Texte(BaseModel):
    """`transkript`: was die Vertonung selbst gehört hat; `uebersetzung`: der Text der neuen Tonspur an seinen Zeiten."""
    transkript: Textspur | None = None
    uebersetzung: Textspur | None = None
    #: solange der Auftrag läuft: was schon übersetzt ist, an den Zeiten der Aufnahme
    vorab: Textspur | None = None


class Auftragsstand(BaseModel):
    zustand: str
    fortschritt: float | None = None
    schritt: str = ""
    fehler: str | None = None
    ergebnis: dict[str, Any] | None = None

    @property
    def laeuft(self) -> bool:
        return self.zustand in ("wartet", "laeuft")


class Vertonungsdienst:
    def __init__(self, verbund: Verbund, adresse: str) -> None:
        self.verbund, self.adresse = verbund, adresse.strip().rstrip("/")

    async def abgeben(self, ton: Path, name: str, ausgang: str | None, sprache: str, stimme: dict[str, str], *, original: bool,
                      segmente: list[Spurtext] | None, klang: Klang = "auto") -> str:
        """Kennung des Auftrags. `original`: je Sprecher seine Stimme aus der Aufnahme, `stimme` als Ersatz; dann hört die Vertonung
        selbst, weil sie die Sprecher trennen muss."""
        daten = {"name": name[:200], "sprache": sprache, "format": "m4a", "behalten": "false", "stimme": json.dumps(stimme),
                 "stimmen": "original" if original else "fest", "klonmodus": klang}
        if ausgang:
            daten["ausgangssprache"] = ausgang
        if segmente and not original:
            daten["segmente"] = json.dumps([s.model_dump(exclude_none=True) for s in segmente], ensure_ascii=False)
        with ton.open("rb") as offen:
            antwort = await self.verbund.anfrage("POST", self.adresse, "/api/v1/dienst/vertonen", timeout=HOCHLADEN, data=daten,
                                                 files={"datei": (ton.name, offen, "application/octet-stream")})
        return str(_daten(antwort).get("id") or "")

    async def stand(self, auftrag: str) -> Auftragsstand:
        return Auftragsstand.model_validate(_daten(await self._hole(f"/api/v1/auftraege/{auftrag}")))

    async def texte(self, auftrag: str) -> Texte:
        return Texte.model_validate(_daten(await self._hole(f"/api/v1/dienst/{auftrag}/texte")))

    async def ton(self, plan_id: str, ziel: Path) -> None:
        async with self.verbund.strom("GET", self.adresse, f"/api/v1/inhalt/plaene/{plan_id}/ergebnis") as antwort:
            with ziel.open("wb") as datei:
                async for stueck in antwort.aiter_bytes(1024 * 1024):
                    datei.write(stueck)

    async def abbrechen(self, auftrag: str) -> None:
        await self._sende(f"/api/v1/auftraege/{auftrag}/abbrechen")

    async def abgeholt(self, auftrag: str) -> None:
        """Die Vertonung darf ihre Kopie wegräumen."""
        await self._sende(f"/api/v1/dienst/{auftrag}/abgeholt")

    async def _hole(self, pfad: str) -> httpx.Response:
        return await self.verbund.anfrage("GET", self.adresse, pfad, timeout=ABFRAGE)

    async def _sende(self, pfad: str) -> None:
        await self.verbund.anfrage("POST", self.adresse, pfad, timeout=ABFRAGE)


def _daten(antwort: httpx.Response) -> dict[str, Any]:
    """Der JSON-Inhalt; eine Weiterleitung oder Seite statt der Antwort heißt, die Adresse stimmt nicht."""
    try:
        daten = antwort.json() if antwort.is_success else None
    except ValueError:
        daten = None
    if not isinstance(daten, dict):
        raise VerbundFehler(f"unerwartete Antwort ({antwort.status_code}), Adresse der Vertonung prüfen", 400)
    return daten


def voruebergehend(f: VerbundFehler) -> bool:
    """Die Vertonung ist gerade weg (Neustart, Netz); ihr Auftrag läuft danach weiter."""
    return f.status is None or f.status >= 500
