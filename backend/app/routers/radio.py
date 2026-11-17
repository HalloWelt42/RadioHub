"""Senderquelle unter /api/radio (RAD-7): Abfrage mit Facetten, lebende Ausschlussregeln mit Vorschau und Folgen,
ausgeblendete Sender mit Grund, Einzelsperren und Freigaben, Abgleich mit dem Senderverzeichnis. Ohne SQL: alles geht
über den Dienst der Senderquelle (services/senderquelle/dienst.py)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response

from appkern.auftraege import Auftrag

from ..services.senderquelle import abgleich, dienst
from ..services.senderquelle.dienst import Fehler
from ..services.senderquelle.modelle import (Abfrageergebnis, Abgleichstand, AusgeblendetAnfrage, AusgeblendetSeite,
                                             Kandidat, RegelAenderung, RegelEntwurf, RegelFolgen, RegelSchalten,
                                             Regeluebersicht, RegelVorschau, SenderAnfrage, SenderEintrag, Sichtbarkeit,
                                             StationQuery)
from .. import einstellungen

router = APIRouter(prefix="/api/radio", tags=["radio"])
KandidatenArt = Literal["sprache", "genre", "tag", "bewertung", "einzeln"]


def _http(f: Fehler) -> HTTPException:
    return HTTPException(status_code=f.status, detail=str(f))


# ----- Abfrage ---------------------------------------------------------------------------------------------------------

@router.post("/abfrage", response_model=Abfrageergebnis)
async def abfrage(q: StationQuery) -> Abfrageergebnis:
    """Senderliste mit Schnellfiltern, Gesamtzahl, Einträgen samt Zusatzdaten und Facetten (erste Seite)."""
    try:
        return await dienst.abfragen(q)
    except Fehler as f:
        raise _http(f) from f


@router.get("/sender/{uuid}/varianten", response_model=list[SenderEintrag])
async def varianten(uuid: str) -> list[SenderEintrag]:
    """Alle sichtbaren Varianten der Gruppe eines Senders, die beste vorn."""
    return await dienst.varianten(uuid)


@router.get("/sender/{uuid}/sichtbarkeit", response_model=Sichtbarkeit)
async def sichtbarkeit(uuid: str) -> Sichtbarkeit:
    """Warum ein Sender sichtbar ist oder nicht."""
    try:
        return await dienst.erklaeren(uuid)
    except Fehler as f:
        raise _http(f) from f


# ----- Regeln ----------------------------------------------------------------------------------------------------------

@router.get("/regeln", response_model=Regeluebersicht)
async def regeln() -> Regeluebersicht:
    """Bestand (gesamt, sichtbar, ausgeblendet, verschwunden) und alle Regeln mit ihren Zahlen."""
    return await dienst.uebersicht()


@router.post("/regeln/vorschau", response_model=RegelVorschau)
async def regel_vorschau(entwurf: RegelEntwurf) -> RegelVorschau:
    """Was eine neue Regel bewirken würde (Anzahl, davon Favoriten, Beispiele); ändert nichts."""
    return await dienst.vorschau(entwurf)


@router.post("/regeln", response_model=RegelAenderung, status_code=201)
async def regel_anlegen(entwurf: RegelEntwurf) -> RegelAenderung:
    """Regel anlegen (nach der Vorschau); Rückgängig ist das Entfernen der neuen Regel."""
    try:
        return await dienst.anlegen(entwurf)
    except Fehler as f:
        raise _http(f) from f


@router.patch("/regeln/{regel_id}", response_model=RegelAenderung)
async def regel_schalten(regel_id: str, schalten: RegelSchalten) -> RegelAenderung:
    """Regel ein- oder ausschalten (Freigabe je Regel)."""
    try:
        return await dienst.schalten(regel_id, schalten.an)
    except Fehler as f:
        raise _http(f) from f


@router.get("/regeln/{regel_id}/folgen", response_model=RegelFolgen)
async def regel_folgen(regel_id: str) -> RegelFolgen:
    """Folgenvorschau vor dem Entfernen oder Ausschalten: so viele Sender würden wieder sichtbar."""
    try:
        return await dienst.folgen(regel_id)
    except Fehler as f:
        raise _http(f) from f


@router.delete("/regeln/{regel_id}", response_model=RegelAenderung)
async def regel_entfernen(regel_id: str, bestaetigt: bool = Query(False)) -> RegelAenderung:
    """Regel entfernen; nur mit `bestaetigt=true` nach der Folgenvorschau (Vorgabe 9)."""
    if not bestaetigt:
        raise HTTPException(status_code=428, detail="Erst die Folgen ansehen (GET .../folgen), dann mit bestaetigt=true")
    try:
        return await dienst.entfernen(regel_id)
    except Fehler as f:
        raise _http(f) from f


@router.get("/regeln/kandidaten", response_model=list[Kandidat])
async def kandidaten(art: KandidatenArt, suche: str = Query("", max_length=100),
                     grenze: int = Query(20, ge=1, le=100)) -> list[Kandidat]:
    """Mögliche Werte einer neuen Regel mit Zahl der Sender und davon Favoriten."""
    try:
        return await dienst.kandidaten(art, suche, grenze)
    except Fehler as f:
        raise _http(f) from f


# ----- Ausgeblendete Sender, Einzelsperren, Freigaben -------------------------------------------------------------------

@router.post("/ausgeblendet", response_model=AusgeblendetSeite)
async def ausgeblendet(anfrage: AusgeblendetAnfrage) -> AusgeblendetSeite:
    """Ausgeblendete Sender seitenweise, durchsuchbar, je Sender mit Grund."""
    return await dienst.ausgeblendete(anfrage)


async def _einzeln(arbeit, uuid: str) -> Sichtbarkeit:
    try:
        return await arbeit(uuid)
    except Fehler as f:
        raise _http(f) from f


@router.post("/sperren", response_model=Sichtbarkeit)
async def sperren(anfrage: SenderAnfrage) -> Sichtbarkeit:
    """Einzelsperre (Auge); startet nichts, Rückgängig mit DELETE."""
    return await _einzeln(dienst.sperren, anfrage.uuid)


@router.delete("/sperren/{uuid}", response_model=Sichtbarkeit)
async def entsperren(uuid: str) -> Sichtbarkeit:
    return await _einzeln(dienst.entsperren, uuid)


@router.post("/freigaben", response_model=Sichtbarkeit)
async def freigeben(anfrage: SenderAnfrage) -> Sichtbarkeit:
    """Ausgeblendeten Sender als Ausnahme wieder sichtbar machen (Einzelsperre fällt weg)."""
    return await _einzeln(dienst.freigeben, anfrage.uuid)


@router.delete("/freigaben/{uuid}", response_model=Sichtbarkeit)
async def freigabe_zuruecknehmen(uuid: str) -> Sichtbarkeit:
    return await _einzeln(dienst.freigabe_zuruecknehmen, uuid)


# ----- Abgleich ----------------------------------------------------------------------------------------------------------

@router.get("/abgleich", response_model=Abgleichstand)
async def abgleich_stand(request: Request) -> Abgleichstand:
    """Ende des letzten Abgleichs, eingestellte Uhrzeit, offener Auftrag."""
    auftraege = request.app.state.geruest.auftraege
    offen = (await auftraege.liste(zustand=("wartet", "laeuft"), art=abgleich.ART, grenze=1)).eintraege
    return Abgleichstand(zuletzt=await dienst.abgleich_zuletzt(), uhrzeit=einstellungen.stand().abgleich_uhrzeit,
                         auftrag=offen[0].id if offen else None)


@router.post("/abgleich", response_model=Auftrag, status_code=202)
async def abgleich_starten(request: Request, response: Response) -> Auftrag:
    """Abgleich mit dem Senderverzeichnis jetzt (als Auftrag mit Fortschritt; läuft schon einer, kommt dieser)."""
    response.headers["Location"] = "/api/v1/auftraege"
    return await request.app.state.geruest.auftraege.einreihen(abgleich.ART, {"anlass": "hand"}, von="RadioHub")
