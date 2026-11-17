"""Dienst der Senderquelle: was Schnittstelle, alte Wege und Werkzeuge aufrufen. Lesen läuft im Vorrat der
Leseverbindungen, jede Änderung in einer Transaktion samt neu berechneter Sichtbarkeit (alles oder nichts)."""
from __future__ import annotations

import logging
from collections.abc import Callable

from ... import database
from ..config_service import config_service
from . import abfrage, ausgeblendet, bestand, regeln, sichtbarkeit
from .modelle import (Abfrageergebnis, AusgeblendetAnfrage, AusgeblendetSeite, Kandidat, RegelAenderung, RegelEntwurf,
                      RegelFolgen, Regeluebersicht, RegelVorschau, SenderEintrag, Sichtbarkeit, StationQuery)

log = logging.getLogger("radiohub.senderquelle")


class Fehler(ValueError):
    """Fachlicher Fehler mit HTTP-Status für die Schnittstelle."""

    def __init__(self, text: str, status: int = 400) -> None:
        super().__init__(text)
        self.status = status


class NichtGefunden(Fehler):
    def __init__(self, text: str) -> None:
        super().__init__(text, 404)


# ----- Lesen ---------------------------------------------------------------------------------------------------------------

async def uebersicht() -> Regeluebersicht:
    return await database.lesen(lambda v: Regeluebersicht(bestand=sichtbarkeit.bestand(v), regeln=regeln.alle(v)))


async def vorschau(entwurf: RegelEntwurf) -> RegelVorschau:
    return await database.lesen(lambda v: sichtbarkeit.vorschau(v, entwurf))


async def folgen(regel_id: str) -> RegelFolgen:
    def arbeit(v) -> RegelFolgen:
        regel = regeln.holen(v, regel_id)
        if regel is None:
            raise NichtGefunden("Regel nicht gefunden")
        anzahl, beispiele = sichtbarkeit.folgen(v, regel_id)
        return RegelFolgen(regel=regel, wieder_sichtbar=anzahl, beispiele=beispiele)
    return await database.lesen(arbeit)


async def kandidaten(art: str, suche: str, grenze: int) -> list[Kandidat]:
    try:
        return await database.lesen(lambda v: ausgeblendet.kandidaten(v, art, suche, grenze))
    except ValueError as f:
        raise Fehler(str(f)) from f


def laender_der_seitenleiste() -> list[str]:
    """Länder der Seitenleiste aus den Einstellungen der Oberfläche (Entscheidung 6: legt nur Facetten fest)."""
    werte = config_service.get("sidebar_countries") or []
    return [str(w).upper() for w in werte if isinstance(w, str) and len(w) == 2]


async def abfragen(q: StationQuery) -> Abfrageergebnis:
    leiste = laender_der_seitenleiste()
    try:
        return await database.lesen(lambda v: abfrage.abfragen(v, q, leiste))
    except abfrage.FalscherZeiger as f:
        raise Fehler(str(f)) from f


async def varianten(uuid: str) -> list[SenderEintrag]:
    return await database.lesen(lambda v: abfrage.varianten(v, uuid))


async def erklaeren(uuid: str) -> Sichtbarkeit:
    ergebnis = await database.lesen(lambda v: sichtbarkeit.erklaeren(v, uuid))
    if ergebnis is None:
        raise NichtGefunden("Sender nicht gefunden")
    return ergebnis


async def ausgeblendete(a: AusgeblendetAnfrage) -> AusgeblendetSeite:
    return await database.lesen(lambda v: ausgeblendet.seite(v, a))


# ----- Regeln ändern -------------------------------------------------------------------------------------------------------

def _sichtbar(v) -> int:
    return v.execute("SELECT COUNT(*) FROM sender_index WHERE sichtbar = 1").fetchone()[0]


async def _aendern(arbeit: Callable[[object], str | None], *, treffer: bool, nur_regel: bool) -> RegelAenderung:
    """`arbeit` ändert Regeln in der Transaktion und liefert die Kennung der betroffenen Regel; danach Sichtbarkeit
    neu (mit `nur_regel` nur die Treffer dieser Regel) und die Zahlen vorher und nachher."""
    def huelle(v) -> RegelAenderung:
        vorher = _sichtbar(v)
        regel_id = arbeit(v)
        sichtbarkeit.neu_berechnen(v, treffer=treffer, regel_ids=[regel_id] if nur_regel and regel_id else None)
        nachher = _sichtbar(v)
        return RegelAenderung(regel=regeln.holen(v, regel_id) if regel_id else None, bestand=sichtbarkeit.bestand(v),
                              ausgeblendet=max(0, vorher - nachher), wieder_sichtbar=max(0, nachher - vorher))
    return await database.schreiben(huelle)


async def anlegen(entwurf: RegelEntwurf, herkunft: str = "nutzer") -> RegelAenderung:
    def arbeit(v) -> str:
        if gleich := regeln.gleiche(v, entwurf):
            raise Fehler(f"Diese Regel gibt es schon ({gleich})", 409)
        return regeln.anlegen(v, entwurf, bestand.jetzt(), herkunft)
    return await _aendern(arbeit, treffer=True, nur_regel=True)


async def schalten(regel_id: str, an: bool) -> RegelAenderung:
    def arbeit(v) -> str:
        if not regeln.schalten(v, regel_id, an, bestand.jetzt()):
            raise NichtGefunden("Regel nicht gefunden")
        return regel_id
    return await _aendern(arbeit, treffer=False, nur_regel=False)


async def entfernen(regel_id: str) -> RegelAenderung:
    def arbeit(v) -> None:
        try:
            gefunden = regeln.entfernen(v, regel_id)
        except ValueError as f:
            raise Fehler(str(f)) from f
        if not gefunden:
            raise NichtGefunden("Regel nicht gefunden")
        return None
    return await _aendern(arbeit, treffer=False, nur_regel=False)


# ----- Einzelne Sender -----------------------------------------------------------------------------------------------------

async def _fuer_sender(uuid: str, arbeit: Callable[[object], bool]) -> Sichtbarkeit:
    def huelle(v) -> Sichtbarkeit:
        if not arbeit(v):
            raise NichtGefunden("Sender nicht gefunden")
        sichtbarkeit.neu_berechnen(v, sichtbarkeit.nrs_von(v, [uuid]))
        ergebnis = sichtbarkeit.erklaeren(v, uuid)
        if ergebnis is None:
            raise NichtGefunden("Sender nicht gefunden")
        return ergebnis
    return await database.schreiben(huelle)


async def sperren(uuid: str) -> Sichtbarkeit:
    """Einzelsperre per Auge (Vorgabe 5: startet nichts, Rückgängig ist `entsperren`)."""
    return await _fuer_sender(uuid, lambda v: ausgeblendet.sperren(v, uuid, bestand.jetzt()))


async def entsperren(uuid: str) -> Sichtbarkeit:
    return await _fuer_sender(uuid, lambda v: ausgeblendet.entsperren(v, uuid) or True)


async def freigeben(uuid: str) -> Sichtbarkeit:
    return await _fuer_sender(uuid, lambda v: ausgeblendet.freigeben(v, uuid, bestand.jetzt()))


async def freigabe_zuruecknehmen(uuid: str) -> Sichtbarkeit:
    return await _fuer_sender(uuid, lambda v: ausgeblendet.freigabe_zuruecknehmen(v, uuid) or True)


async def neu_fuer(uuids: list[str]) -> None:
    """Nach Favorit, Bewertung oder Werbeentscheidung: Sichtbarkeit dieser Sender und ihrer Gruppen neu. Ohne geöffnete
    Datenbank (Werkzeuge, Tests einzelner Dienste) geschieht nichts; der nächste volle Lauf holt es nach."""
    if not uuids:
        return
    try:
        database.radio_db()
    except RuntimeError:
        return
    await database.schreiben(lambda v: sichtbarkeit.neu_berechnen(v, sichtbarkeit.nrs_von(v, uuids)))


async def alles_neu() -> None:
    await database.schreiben(lambda v: sichtbarkeit.neu_berechnen(v))


async def abgleich_zuletzt() -> str | None:
    """Ende des letzten vollständigen Abgleichs mit dem Senderverzeichnis."""
    def arbeit(v) -> str | None:
        zeile = v.execute("SELECT value FROM cache_meta WHERE key = ?", (bestand.ABGLEICH_SCHLUESSEL,)).fetchone()
        return zeile[0] if zeile else None
    return await database.lesen(arbeit)


# ----- Aufbereitung ----------------------------------------------------------------------------------------------------------

async def aufbereitung_noetig() -> str | None:
    return await database.lesen(bestand.aufbereitung_noetig)


async def aufbereiten() -> int:
    """Den ganzen Bestand neu aufbereiten (rechnen im Lesen, schreiben in einem Zug) und die Sichtbarkeit neu."""
    sender, verschwunden = await database.lesen(bestand.alle_aufbereiten)

    def schreiben(v) -> int:
        anzahl = bestand.index_schreiben(v, sender, verschwunden)
        sichtbarkeit.neu_berechnen(v)
        return anzahl
    anzahl = await database.schreiben(schreiben)
    abfrage.landnamen_vergessen()
    log.info("Senderbestand aufbereitet: %s Sender", anzahl)
    return anzahl
