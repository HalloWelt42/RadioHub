"""Durchleiter: reicht den Audiostrom eines bekannten Senders oder einer bekannten Podcast-Folge an die Oberfläche
durch (unter HTTPS darf der Browser keinen http-Strom laden, und viele Sender erlauben keinen Abruf von fremden Seiten).

Nie für beliebige Adressen: die Oberfläche nennt nur die Kennung des Senders bzw. der Folge, die Adresse kommt aus der
Datenbank. Für einen Sender gilt die eigene Adresse (station_custom_urls) vor der aufgelösten (url_resolved) vor der
eingetragenen (url), aus dem Senderbestand, sonst aus den Favoriten. TLS wird geprüft; Weiterleitungen werden einzeln
verfolgt und nur auf http und https zugelassen. Range und die Köpfe des Stroms (Länge, Bereich, ICY) gehen durch.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit

import httpx
from fastapi.responses import StreamingResponse

from ..database import db_session

SCHEMATA = ("http", "https")
HOECHSTENS_WEITERLEITUNGEN = 5
KOEPFE = ("content-length", "content-range", "accept-ranges", "icy-metaint", "icy-name", "icy-genre", "icy-br")
KENNUNG = "RadioHub/1.0"


class DurchleiterFehler(Exception):
    """Fachfehler mit HTTP-Status für die Schnittstelle."""

    status = 502


class Unbekannt(DurchleiterFehler):
    status = 404


class UnerlaubteAdresse(DurchleiterFehler):
    status = 400


class NichtErreichbar(DurchleiterFehler):
    status = 502


class GegenstelleFehler(DurchleiterFehler):
    def __init__(self, status: int, text: str) -> None:
        super().__init__(text)
        self.status = status


def sender_adresse(uuid: str) -> str:
    """Die Adresse, unter der ein bekannter Sender gespielt wird; Unbekannt, wenn es ihn nicht gibt."""
    with db_session() as c:
        eigene = c.execute("SELECT custom_url FROM station_custom_urls WHERE station_uuid = ?", (uuid,)).fetchone()
        if eigene and (eigene["custom_url"] or "").strip():
            return eigene["custom_url"].strip()
        for tabelle in ("stations", "favorites"):
            zeile = c.execute(f"SELECT url_resolved, url FROM {tabelle} WHERE uuid = ?", (uuid,)).fetchone()
            if zeile:
                adresse = (zeile["url_resolved"] or zeile["url"] or "").strip()
                if adresse:
                    return adresse
    raise Unbekannt("Sender unbekannt")


def pruefen(adresse: str) -> str:
    """Nur http und https mit Rechnernamen; sonst UnerlaubteAdresse."""
    teile = urlsplit(adresse)
    if teile.scheme.lower() not in SCHEMATA or not teile.hostname:
        raise UnerlaubteAdresse(f"Adresse nicht erlaubt (nur http und https): {teile.scheme or 'ohne Schema'}")
    return adresse


def _client() -> httpx.AsyncClient:
    """Client des Durchleiters: TLS geprüft (Vorgabe von httpx), Weiterleitungen nicht von selbst, kein Lese-Zeitlimit
    (ein Radiostrom endet nie)."""
    return httpx.AsyncClient(follow_redirects=False, timeout=httpx.Timeout(connect=15.0, read=None, write=None, pool=None))


async def oeffnen(adresse: str, bereich: str | None = None) -> tuple[httpx.AsyncClient, httpx.Response]:
    """Verbindung zur Gegenstelle mit offenem Strom; Weiterleitungen nur auf http und https, höchstens fünf."""
    kopf = {"User-Agent": KENNUNG}
    if bereich:
        kopf["Range"] = bereich
    client = _client()
    ziel = pruefen(adresse)
    try:
        for _ in range(HOECHSTENS_WEITERLEITUNGEN + 1):
            antwort = await client.send(client.build_request("GET", ziel, headers=kopf), stream=True)
            if not antwort.is_redirect:
                break
            weiter = antwort.headers.get("location", "")
            await antwort.aclose()
            ziel = pruefen(urljoin(ziel, weiter))
        else:
            raise NichtErreichbar("Zu viele Weiterleitungen")
    except httpx.HTTPError as f:
        await client.aclose()
        raise NichtErreichbar(f"Strom nicht erreichbar: {f}") from f
    except DurchleiterFehler:
        await client.aclose()
        raise
    if antwort.status_code >= 400:
        await antwort.aclose()
        await client.aclose()
        raise GegenstelleFehler(antwort.status_code, "Fehler der Gegenstelle")
    return client, antwort


async def durchleiten(adresse: str, bereich: str | None = None, zusatz: dict[str, str] | None = None) -> StreamingResponse:
    """Strom als Antwort, mit den Köpfen der Gegenstelle (KOEPFE) und `zusatz` (etwa Cache-Control)."""
    client, antwort = await oeffnen(adresse, bereich)
    koepfe = {k: antwort.headers[k] for k in KOEPFE if k in antwort.headers} | (zusatz or {})

    async def stuecke():
        try:
            async for stueck in antwort.aiter_bytes(chunk_size=65536):
                yield stueck
        finally:
            await antwort.aclose()
            await client.aclose()

    return StreamingResponse(stuecke(), status_code=antwort.status_code,
                             media_type=antwort.headers.get("content-type", "audio/mpeg"), headers=koepfe)
