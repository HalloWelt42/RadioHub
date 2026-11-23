"""Anschluss an den Propaganda-Filter (HELF-256): der eigene Dienst am Mac, der Werbung in Ton findet.

Erste Funktion: zwei Fassungen derselben Folge vergleichen. RadioHub reicht die gespeicherte Datei ein (Fassung A, nur
für sie gelten die Zeiten), der Filter holt dieselbe Folge selbst noch einmal beim Anbieter (Fassung B) und nennt die
Abschnitte, die nur in A vorkommen: beim Abruf eingesetzte Werbung. Er rechnet als Auftrag; RadioHub fragt den Stand ab
und meldet ihn als Fortschritt weiter. Die gefundenen Stellen hebt der Filter als Signaturen auf.

Einstellung `propaganda_filter_adresse` (Dienste); angemeldet wird mit dem App-Schlüssel der Kellerwolke, geprüft mit
derselben Zertifikatsstelle wie die übrigen Dienste im Haus. Ohne Adresse bietet RadioHub den Vergleich nicht an.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

import httpx
from pydantic import BaseModel

from ..ablage.kellerwolke import tls_pruefung
from ..einstellungen import AppEinstellungen
from ..einstellungen import stand as einstellungen_stand

Melden = Callable[[float, str], None]
"""Anteil (0 bis 1) und Schritt, wie der Filter ihn nennt"""


class FilterFehler(Exception):
    pass


@dataclass(frozen=True)
class FilterEinstellungen:
    adresse: str = ""
    schluessel: str = ""
    ca_datei: str = ""
    abfragen_s: float = 2.0
    hoechstens_s: float = 3600.0

    @property
    def eingerichtet(self) -> bool:
        return bool(self.adresse and self.schluessel)

    @classmethod
    def aus(cls, stand: AppEinstellungen) -> FilterEinstellungen:
        return cls(adresse=stand.propaganda_filter_adresse.strip().rstrip("/"),
                   schluessel=stand.kellerwolke_schluessel.get_secret_value().strip(), ca_datei=stand.ca_datei.strip())

    @classmethod
    def jetzt(cls) -> FilterEinstellungen:
        return cls.aus(einstellungen_stand())


def verbindung(e: FilterEinstellungen, transport: httpx.AsyncBaseTransport | None = None, *, lesen_s: float = 60.0) -> httpx.AsyncClient:
    """Angemeldete Verbindung zum Filter (Wege ab /api/v1)."""
    if not e.eingerichtet:
        raise FilterFehler("Der Propaganda-Filter ist nicht eingerichtet (Einstellungen > Dienste)")
    return httpx.AsyncClient(base_url=e.adresse, headers={"Authorization": f"Bearer {e.schluessel}"}, verify=tls_pruefung(e.ca_datei),
                             transport=transport, timeout=httpx.Timeout(lesen_s, connect=10.0, write=600.0))


async def fragen(methode: str, pfad: str, *, transport: httpx.AsyncBaseTransport | None = None, **art) -> httpx.Response:
    """Eine Anfrage an den Filter; jede Absage und jede Störung wird zum FilterFehler."""
    try:
        async with verbindung(FilterEinstellungen.jetzt(), transport, lesen_s=20.0) as c:
            antwort = await c.request(methode, f"/api/v1/{pfad}", **art)
    except httpx.HTTPError as f:
        raise FilterFehler(f"Propaganda-Filter nicht erreichbar: {type(f).__name__}") from f
    if antwort.status_code >= 400:
        raise FilterFehler(f"Propaganda-Filter lehnt ab ({antwort.status_code}): {_meldung(antwort)}")
    return antwort


class Fundstelle(BaseModel):
    von: float
    bis: float
    signatur: str | None = None


class Vergleichsergebnis(BaseModel):
    gleich: bool
    verwertbar: bool
    anteil_gemeinsam: float | None = None
    nur_in_a: list[Fundstelle] = []
    nur_in_b: list[Fundstelle] = []
    hinweis: str | None = None


async def vergleichen(e: FilterEinstellungen, fassung_a: AsyncIterator[bytes], zweite: str, quelle: str,
                      melden: Melden = lambda *_: None, *, transport: httpx.AsyncBaseTransport | None = None,
                      uhr: Callable[[], float] = time.monotonic) -> Vergleichsergebnis:
    """Fassung A (Strom der gespeicherten Datei) mit der Folge unter `zweite` vergleichen lassen."""
    async with verbindung(e, transport) as c:
        try:
            antwort = await c.post("/api/v1/vergleiche", params={"zweite": zweite, "quelle": quelle[:300]},
                                   content=fassung_a, headers={"Content-Type": "application/octet-stream"})
            if antwort.status_code != 202:
                raise FilterFehler(f"Propaganda-Filter lehnt ab ({antwort.status_code}): {_meldung(antwort)}")
            auftrag = antwort.json()
            ende = uhr() + e.hoechstens_s
            while auftrag["zustand"] in ("wartet", "laeuft"):
                melden(float(auftrag.get("fortschritt") or 0), str(auftrag.get("schritt") or ""))
                if uhr() > ende:
                    raise FilterFehler("Der Vergleich dauert zu lange")
                await asyncio.sleep(e.abfragen_s)
                antwort = await c.get(f"/api/v1/vergleiche/{auftrag['id']}")
                if antwort.status_code != 200:
                    raise FilterFehler(f"Propaganda-Filter antwortet mit {antwort.status_code}: {_meldung(antwort)}")
                auftrag = antwort.json()
        except httpx.HTTPError as f:
            raise FilterFehler(f"Propaganda-Filter nicht erreichbar: {type(f).__name__}") from f
    if auftrag["zustand"] != "fertig":
        raise FilterFehler(f"Vergleich fehlgeschlagen: {auftrag.get('fehler') or auftrag['zustand']}")
    return Vergleichsergebnis.model_validate(auftrag["ergebnis"])


def _meldung(antwort: httpx.Response) -> str:
    try:
        return str(antwort.json().get("detail"))[:200]
    except ValueError:
        return antwort.text[:200]
