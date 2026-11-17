"""Abgleich mit dem Senderverzeichnis als Auftrag des Appkerns (Vorgabe 4): nächtlich zur eingestellten Uhrzeit und auf
Anstoß, mit Fortschritt. Lädt alle Sender seitenweise (auch die, die die letzte Prüfung des Verzeichnisses nicht
bestanden haben, damit lastcheckok stimmt), fragt bei einem Ausfall den nächsten Server der Einstellung
service_radio_browser_servers, übernimmt jede Seite sofort (neu oder aktualisiert, nie ersetzt), markiert danach
Verschwundene (nie löschen) und bereitet den Bestand samt Sichtbarkeit neu auf.

Verschwunden ist, wer in diesem und im vorigen vollständigen Abgleich fehlt; so kostet ein Sender, der beim Blättern
gerade die Seite wechselt, nichts. Liefert das Verzeichnis weniger als die Hälfte des Bestands, bricht der Abgleich
ab, ohne etwas als verschwunden zu markieren."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from appkern.auftraege import Art, AuftragFehler, Kontext, Phase

from ... import database, einstellungen
from ...config import VERSION
from ...senderdaten import Verzeichnisdatensatz
from . import bestand, dienst

log = logging.getLogger("radiohub.abgleich")

ART = "sender_abgleich"
ART_AUFBEREITEN = "sender_aufbereiten"
SEITE = 10_000
MINDESTANTEIL = 0.5
BEGINN_SCHLUESSEL = "abgleich_beginn"    # in cache_meta: Beginn des letzten vollständigen Abgleichs

ClientBauen = Callable[[], httpx.AsyncClient]


class AbgleichEingabe(BaseModel):
    anlass: Literal["zeitplan", "hand", "start"] = "hand"


class AbgleichErgebnis(BaseModel):
    geladen: int
    verschwunden: int
    server: str
    aufbereitet: int


async def _seite(client: httpx.AsyncClient, server: list[str], bevorzugt: int, versatz: int) -> tuple[list[dict[str, Any]], int]:
    """Eine Seite des Verzeichnisses; beginnt beim zuletzt erfolgreichen Server und nimmt bei Fehlern den nächsten."""
    fehler = []
    for schritt in range(len(server)):
        nummer = (bevorzugt + schritt) % len(server)
        adresse = server[nummer].rstrip("/") + "/json/stations"
        try:
            antwort = await client.get(adresse, params={"limit": SEITE, "offset": versatz, "hidebroken": "false",
                                                         "order": "name"})
            antwort.raise_for_status()
            daten = antwort.json()
            if not isinstance(daten, list):
                raise ValueError("keine Liste")
            return daten, nummer
        except (httpx.HTTPError, ValueError) as f:
            fehler.append(f"{server[nummer]}: {f}")
            log.warning("Senderverzeichnis %s antwortet nicht: %s", server[nummer], f)
    raise AuftragFehler("Kein Server des Senderverzeichnisses erreichbar (" + "; ".join(fehler) + ")")


def server_liste() -> list[str]:
    """Server des Senderverzeichnisses in der Reihenfolge der Einstellung (der erste, der antwortet, bleibt)."""
    return [s for s in einstellungen.stand().service_radio_browser_servers if s.strip()]


async def abgleichen(kontext: Kontext, client_bauen: ClientBauen) -> AbgleichErgebnis:
    server = server_liste()
    if not server:
        raise AuftragFehler("Kein Server des Senderverzeichnisses eingestellt (service_radio_browser_servers)")
    beginn = bestand.jetzt()
    geladen, nummer, versatz = 0, 0, 0
    await kontext.fortschritt(None, "Senderverzeichnis laden", phase="laden")
    async with client_bauen() as client:
        while True:
            await kontext.pruefen()
            roh, nummer = await _seite(client, server, nummer, versatz)
            saetze = []
            for eintrag in roh:
                try:
                    saetze.append(Verzeichnisdatensatz.model_validate(eintrag))
                except ValueError:
                    continue
            geladen += await database.schreiben(lambda v, s=saetze: bestand.stationen_speichern(v, s, beginn))
            await kontext.fortschritt(None, f"{geladen} Sender geladen von {server[nummer]}")
            if len(roh) < SEITE:
                break
            versatz += SEITE

    def abschliessen(v) -> int:
        vorhanden = v.execute("SELECT COUNT(*) FROM stations WHERE verschwunden_am IS NULL").fetchone()[0]
        if geladen < vorhanden * MINDESTANTEIL:
            raise AuftragFehler(f"Das Verzeichnis lieferte nur {geladen} von {vorhanden} Sendern; nichts als verschwunden "
                                "markiert")
        zeile = v.execute("SELECT value FROM cache_meta WHERE key = ?", (BEGINN_SCHLUESSEL,)).fetchone()
        verschwunden = bestand.verschwundene_markieren(v, zeile[0], bestand.jetzt()) if zeile else 0
        v.execute("INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)", (BEGINN_SCHLUESSEL, beginn))
        return verschwunden
    await kontext.fortschritt(None, "Verschwundene markieren", phase="speichern")
    verschwunden = await database.schreiben(abschliessen)
    await kontext.pruefen()
    await kontext.fortschritt(None, "Senderdaten aufbereiten und Sichtbarkeit berechnen", phase="aufbereiten")
    aufbereitet = await dienst.aufbereiten()
    await database.schreiben(lambda v: v.execute("INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
                                                 (bestand.ABGLEICH_SCHLUESSEL, bestand.jetzt())))
    log.info("Abgleich: %s Sender geladen, %s verschwunden", geladen, verschwunden)
    return AbgleichErgebnis(geladen=geladen, verschwunden=verschwunden, server=server[nummer], aufbereitet=aufbereitet)


def arten(client_bauen: ClientBauen) -> list[Art]:
    """Die Aufträge der Senderquelle: Abgleich (lädt und bereitet auf) und Aufbereiten allein (neue Fassung der
    Tabellen des Bausteins)."""
    async def abgleich(kontext: Kontext) -> AbgleichErgebnis:
        return await abgleichen(kontext, client_bauen)

    async def aufbereiten(kontext: Kontext) -> dict[str, int]:
        await kontext.fortschritt(None, "Senderdaten aufbereiten und Sichtbarkeit berechnen", phase="aufbereiten")
        return {"aufbereitet": await dienst.aufbereiten()}

    return [
        Art(name=ART, titel="Abgleich mit dem Senderverzeichnis", arbeit=abgleich, eingabe=AbgleichEingabe,
            phasen=[Phase(schluessel="laden", titel="Verzeichnis laden", symbol="download"),
                    Phase(schluessel="speichern", titel="Verschwundene markieren", symbol="eye-slash"),
                    Phase(schluessel="aufbereiten", titel="Aufbereiten", symbol="filter")],
            hoechstens=1, gegenstand=lambda _e: "senderverzeichnis"),
        Art(name=ART_AUFBEREITEN, titel="Senderdaten aufbereiten", arbeit=aufbereiten,
            phasen=[Phase(schluessel="aufbereiten", titel="Aufbereiten", symbol="filter")],
            hoechstens=1, nach_neustart="fortsetzen", gegenstand=lambda _e: "senderbestand"),
    ]


def client_fabrik(transport: httpx.AsyncBaseTransport | None) -> ClientBauen:
    def bauen() -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0), transport=transport,
                                 headers={"User-Agent": f"RadioHub/{VERSION}"})
    return bauen
