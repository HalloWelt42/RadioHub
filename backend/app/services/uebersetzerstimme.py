"""Die Übersetzerstimme beim Mitlesen (RAD-130): ein fertig übersetzter Absatz wird von der Vertonung mit der Zeitstimme gesprochen,
als MP3 ohne Stille am Rand. Was dabei ankommt, spielt die Oberfläche; der Ton des Senders bleibt davon unberührt."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..einstellungen import stand as einstellungen_stand
from .zeitansage import ZeitansageEinstellungen, client_fuer, kuerzen, stimme_der_app

ZEIT = httpx.Timeout(120.0, connect=10.0)


class StimmeFehler(Exception):
    """Es konnte nicht gesprochen werden. `dauerhaft`: es hilft nicht, es mit dem nächsten Absatz wieder zu versuchen."""

    def __init__(self, meldung: str, dauerhaft: bool) -> None:
        super().__init__(meldung)
        self.dauerhaft = dauerhaft


@dataclass(frozen=True)
class Gesprochen:
    ton: bytes
    dauer_s: float


def eingerichtet() -> bool:
    return ZeitansageEinstellungen.aus(einstellungen_stand()).eingerichtet


async def sprechen(text: str, sprache: str, *, transport: httpx.AsyncBaseTransport | None = None,
                   einstellungen: ZeitansageEinstellungen | None = None) -> Gesprochen:
    e = einstellungen or ZeitansageEinstellungen.aus(einstellungen_stand())
    if not e.eingerichtet:
        raise StimmeFehler("Vertonung oder Zeitstimme fehlt (Einstellungen)", True)
    try:
        async with client_fuer(e, transport) as c:
            antwort = await c.post(f"{e.adresse}/api/v1/sprechen", headers={"Authorization": f"Bearer {e.schluessel}"}, timeout=ZEIT,
                                   json={"text": text[:2000], "stimme": stimme_der_app(e), "sprache": sprache, "tempo": e.tempo, "ausschreiben": True})
    except httpx.HTTPError as f:
        raise StimmeFehler(f"Vertonung nicht erreichbar: {type(f).__name__}", False) from f
    if antwort.status_code != 200:
        raise StimmeFehler(f"Vertonung antwortet {antwort.status_code}", 400 <= antwort.status_code < 500 and antwort.status_code != 429)
    try:
        ton = await kuerzen(antwort.content)
    except RuntimeError as f:
        raise StimmeFehler(str(f), False) from f
    return Gesprochen(ton, float(antwort.headers.get("x-dauer") or len(ton) / 12000))
