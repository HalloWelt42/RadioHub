"""Auswahl der Zeit-Stimme (RAD-15): die Stimmen der Vertonung für die Einstellung `zeitstimme`, jedes Mal frisch
(`GET /api/v1/stimmen`, mit dem App-Schlüssel über den Verbund): die privaten Stimmen, die sie RadioHub freigibt, und
ihr Katalog. Die Werte haben das Format des Appkerns (`katalog:<Name>` oder die Kennung einer privaten Stimme), das
auch `appkern.vorlesen.stimmwahl` liest. Vorgabe ist sohee aus dem Katalog, dieselbe Stimme wie in Basic."""
from __future__ import annotations

import httpx
from appkern.einstellungen import Angebot, Option
from appkern.verbund import VerbundFehler

from ..einstellungen import stand as einstellungen_stand

ABFRAGE = httpx.Timeout(15.0, connect=5.0)
BEREICHE = (("privat", "private Stimme, für RadioHub freigegeben"), ("katalog", "Katalog"))


async def angebot(verbund) -> Angebot:
    adresse = einstellungen_stand().vertonung_adresse.strip().rstrip("/")
    if not adresse:
        return Angebot(optionen=[], eigener_wert=False, stand="erst die Adresse der Vertonung eintragen")
    optionen: list[Option] = []
    stand = ""
    for bereich, hinweis in BEREICHE:
        try:
            antwort = await verbund.anfrage("GET", adresse, "/api/v1/stimmen", timeout=ABFRAGE, params={"bereich": bereich})
        except VerbundFehler as f:
            if f.status in (401, 403):           # private Stimmen gibt die Vertonung RadioHub nicht frei
                continue
            stand = f"Vertonung antwortet nicht: {f.meldung}"
            break
        optionen += [Option(wert=str(s["id"]), titel=str(s["name"]), hinweis=hinweis) for s in antwort.json()]
    return Angebot(optionen=optionen, eigener_wert=False, stand=stand or f"{len(optionen)} Stimmen")
