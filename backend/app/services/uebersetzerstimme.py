"""Die Übersetzerstimme beim Mitlesen (RAD-130): ein fertig übersetzter Absatz wird von der Vertonung gesprochen, über den Verbund
des Appkerns (App-Schlüssel, Zertifikatsstelle), als MP3 ohne Stille am Rand. Welche Stimme, sagt die Einstellung
`uebersetzerstimme` (leer: die Zeitstimme); die Stimmen und ihre Freigaben hält die Vertonung, gerechnet wird über die Leitstelle."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from appkern.verbund import Verbund, VerbundFehler
from appkern.vorlesen import stimmwahl

from ..einstellungen import AppEinstellungen
from ..einstellungen import stand as einstellungen_stand
from .zeitansage import kuerzen

ZEIT = httpx.Timeout(120.0, connect=10.0)
ZEICHEN_HOECHSTENS = 2000         # mehr nimmt die Vertonung am Stück nicht


class StimmeFehler(Exception):
    """Es konnte nicht gesprochen werden. `dauerhaft`: es hilft nicht, es mit dem nächsten Absatz wieder zu versuchen."""

    def __init__(self, meldung: str, dauerhaft: bool) -> None:
        super().__init__(meldung)
        self.dauerhaft = dauerhaft


@dataclass(frozen=True)
class Gesprochen:
    ton: bytes
    dauer_s: float


def stimme_aus(e: AppEinstellungen) -> str:
    return e.uebersetzerstimme.strip() or e.zeitstimme.strip()


def eingerichtet() -> bool:
    e = einstellungen_stand()
    return bool(e.vertonung_adresse.strip() and stimme_aus(e) and e.kellerwolke_schluessel.get_secret_value().strip())


async def sprechen(verbund: Verbund, text: str, sprache: str) -> Gesprochen:
    e = einstellungen_stand()
    wahl = stimmwahl(stimme_aus(e))
    if wahl is None or not e.vertonung_adresse.strip():
        raise StimmeFehler("Vertonung oder Stimme fehlt (Einstellungen)", True)
    try:
        antwort = await verbund.anfrage("POST", e.vertonung_adresse.strip().rstrip("/"), "/api/v1/sprechen", timeout=ZEIT,
                                        json={"text": text[:ZEICHEN_HOECHSTENS], "stimme": wahl, "sprache": sprache,
                                              "tempo": e.zeitstimme_tempo, "ausschreiben": True})
        ton = await kuerzen(antwort.content)
    except VerbundFehler as f:
        raise StimmeFehler(f"Vertonung: {f.meldung}", f.status is not None and 400 <= f.status < 500 and f.status != 429) from f
    except RuntimeError as f:
        raise StimmeFehler(str(f), False) from f
    return Gesprochen(ton, float(antwort.headers.get("x-dauer") or len(ton) / 12000))
