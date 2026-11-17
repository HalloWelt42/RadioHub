"""Die alten Wege der heutigen Oberfläche (/api/filters/*, /api/blocklist) auf der neuen Sichtbarkeit, bis die neue
Oberfläche sie ablöst (Etappe 3b). Es gibt nur eine Wahrheit: was früher in die Sperrliste geschrieben wurde, wird hier
zur Regel, Einzelsperre, Freigabe oder Werbeentscheidung.

    Vorschau und Ausblenden der Filter-Einstellungen   neue Regeln nur für Einträge, die noch keine Regel trifft
    Liste der ausgeblendeten Sender                     aus den Treffern der eingeschalteten Regeln
    Freigeben einzeln / je Grund / alle                 Freigabe je Sender / Regel aus / alle Regeln aus
    Sperren von Hand / als Werbung                      Einzelsperre / Werbeentscheidung "sperren"
"""
from __future__ import annotations

import json
import sqlite3

from pydantic import BaseModel

from ... import database
from . import bestand, dienst, regeln, sichtbarkeit
from .modelle import RegelEntwurf, SpracheEntwurf, StimmenEntwurf, TagEntwurf

_KATEGORIE = {"einzeln": "manual", "werbung": "ad", "altsperren": "manual"}


class AlteKriterien(BaseModel):
    sprachen: list[str] = []
    tags: list[str] = []
    mindeststimmen: int = 0


class AlteSperre(BaseModel):
    """Ein ausgeblendeter Sender in der Form der früheren Sperrliste."""

    uuid: str
    name: str
    reason: str
    category: str
    blocked_at: str | None


class SenderProbe(BaseModel):
    uuid: str
    name: str
    country: str
    language: str
    tags: str
    votes: int


# ----- Kriterien der Filter-Einstellungen -> Regeln ---------------------------------------------------------------------

def _neue_entwuerfe(v: sqlite3.Connection, k: AlteKriterien) -> list[RegelEntwurf]:
    """Regeln für die Teile der Kriterien, die noch keine Regel abdeckt (das frühere Ausblenden kam nur dazu)."""
    gedeckt_sprachen, gedeckt_tags, stimmen = set(), set(), 0
    for z in v.execute("SELECT art, wert FROM regel WHERE an = 1 AND art IN ('sprache', 'tag', 'stimmen')"):
        entwurf = regeln.entwurf_lesen(z["art"], z["wert"])
        if isinstance(entwurf, SpracheEntwurf):
            gedeckt_sprachen |= set(entwurf.eintraege)
        elif isinstance(entwurf, TagEntwurf):
            gedeckt_tags |= set(entwurf.tags)
        elif isinstance(entwurf, StimmenEntwurf):
            stimmen = max(stimmen, entwurf.mindeststimmen)
    entwuerfe: list[RegelEntwurf] = []
    sprachen = sorted({s.strip().lower() for s in k.sprachen if s.strip()} - gedeckt_sprachen)
    if sprachen:
        entwuerfe.append(SpracheEntwurf(eintraege=sprachen))
    tags = sorted(set(TagEntwurf(tags=k.tags).tags) - gedeckt_tags) if k.tags else []
    if tags:
        entwuerfe.append(TagEntwurf(tags=tags))
    if k.mindeststimmen > stimmen:
        entwuerfe.append(StimmenEntwurf(mindeststimmen=k.mindeststimmen))
    return entwuerfe


def _getroffen_sql(entwuerfe: list[RegelEntwurf]) -> tuple[str, list[object]]:
    teile, werte = [], []
    for e in entwuerfe:
        sql, w = regeln.treffer_sql(e.art, e)
        teile.append(sql)
        werte += w
    return " UNION ".join(teile), werte


async def vorschau(k: AlteKriterien) -> tuple[int, list[SenderProbe]]:
    """Wie viele heute sichtbare Sender die Kriterien zusätzlich ausblenden würden, mit bis zu 20 Beispielen."""
    def arbeit(v: sqlite3.Connection) -> tuple[int, list[SenderProbe]]:
        entwuerfe = _neue_entwuerfe(v, k)
        if not entwuerfe:
            return 0, []
        sql, werte = _getroffen_sql(entwuerfe)
        neu = f"""SELECT i.nr FROM sender_index i WHERE i.sichtbar = 1 AND i.favorit = 0 AND i.freigegeben = 0
                  AND i.nr IN ({sql})"""
        anzahl = v.execute(f"SELECT COUNT(*) FROM ({neu})", werte).fetchone()[0]
        proben = [SenderProbe(uuid=z["uuid"], name=z["name"] or "", country=z["country"] or "", language=z["language"] or "",
                              tags=z["tags"] or "", votes=z["votes"] or 0)
                  for z in v.execute(f"""SELECT s.uuid, s.name, s.country, s.language, s.tags, s.votes FROM stations s
                                         JOIN sender_index i ON i.uuid = s.uuid WHERE i.nr IN ({neu})
                                         ORDER BY s.votes DESC LIMIT 20""", werte)]
        return anzahl, proben
    return await database.lesen(arbeit)


async def ausblenden(k: AlteKriterien) -> tuple[int, int]:
    """Legt die nötigen Regeln an; liefert (neu ausgeblendet, ausgeblendet insgesamt)."""
    entwuerfe = await database.lesen(lambda v: _neue_entwuerfe(v, k))
    neu = 0
    for entwurf in entwuerfe:
        neu += (await dienst.anlegen(entwurf)).ausgeblendet
    bestand_ = (await dienst.uebersicht()).bestand
    return neu, bestand_.ausgeblendet


# ----- Ausgeblendete in der früheren Form -------------------------------------------------------------------------------

async def ausgeblendete(grund: str | None = None, kategorie: str | None = None) -> list[AlteSperre]:
    """Alle ausgeblendeten Sender mit ihren Gründen (je Sender eine Zeile; Grund: Titel der ersten Regel)."""
    def arbeit(v: sqlite3.Connection) -> list[AlteSperre]:
        zeilen = v.execute("""SELECT i.nr, i.uuid, s.name FROM sender_index i JOIN stations s ON s.uuid = i.uuid
                              WHERE i.sichtbar = 0 AND i.verschwunden = 0 ORDER BY i.stimmen DESC""").fetchall()
        gruende = sichtbarkeit.gruende(v, [z["nr"] for z in zeilen])
        sperrzeit = dict(v.execute("SELECT uuid, angelegt_am FROM sender_sperre").fetchall())
        ergebnis = []
        for z in zeilen:
            liste = gruende.get(z["nr"], [])
            if not liste:
                continue
            erster = liste[0]
            eintrag = AlteSperre(uuid=z["uuid"], name=z["name"] or "", reason=erster.titel,
                                 category=_KATEGORIE.get(erster.art, "filter"), blocked_at=sperrzeit.get(z["uuid"]))
            if (grund is None or grund in eintrag.reason) and (kategorie is None or eintrag.category == kategorie):
                ergebnis.append(eintrag)
        return ergebnis
    return await database.lesen(arbeit)


async def freigeben(uuids: list[str] | None = None, grund: str | None = None, alle: bool = False) -> int:
    """Freigeben wie früher: einzelne Sender (Freigabe), je Grund (die Regel dieses Titels aus) oder alle (alle
    Regeln aus). Nichts wird gelöscht; Rückgängig ist jederzeit möglich."""
    if uuids:
        frei = 0
        for uuid in uuids:
            try:
                frei += (await dienst.freigeben(uuid)).sichtbar
            except dienst.NichtGefunden:
                continue
        return frei
    uebersicht = await dienst.uebersicht()
    treffer = [r for r in uebersicht.regeln if r.an and (alle or r.titel == grund
                                                         or (grund == "manual" and r.art == "einzeln"))]
    frei = 0
    for regel in treffer:
        frei += (await dienst.schalten(regel.id, False)).wieder_sichtbar
    return frei


# ----- Sperren von Hand und als Werbung ----------------------------------------------------------------------------------

async def sperren(uuid: str, grund: str | None) -> None:
    """Früheres Sperren: "ad:..." wird zur Werbeentscheidung "sperren", alles andere zur Einzelsperre."""
    if (grund or "").startswith("ad:"):
        def entscheiden(v: sqlite3.Connection) -> None:
            v.execute("""INSERT INTO station_ad_status (station_uuid, block_status, user_action, blocked_at)
                         VALUES (?, 'manual_blocked', 'blocked', ?)
                         ON CONFLICT(station_uuid) DO UPDATE SET user_action = 'blocked', blocked_at = excluded.blocked_at""",
                      (uuid, bestand.jetzt()))
        await database.schreiben(entscheiden)
        await dienst.neu_fuer([uuid])
        return
    await dienst.sperren(uuid)


async def ist_ausgeblendet(uuid: str) -> bool:
    try:
        return not (await dienst.erklaeren(uuid)).sichtbar
    except dienst.NichtGefunden:
        return False


# ----- Listen der Filter-Einstellungen ---------------------------------------------------------------------------------

class Eintragszahl(BaseModel):
    name: str
    count: int


class Landzahl(BaseModel):
    code: str
    name: str
    count: int


async def spracheintraege() -> list[Eintragszahl]:
    """Sprachen, wie sie im Verzeichnis stehen (genaue Einträge), mit Zahl der Sender."""
    return await database.lesen(lambda v: [
        Eintragszahl(name=z[0], count=z[1]) for z in v.execute(
            "SELECT eintrag, COUNT(*) AS n FROM sender_spracheintrag WHERE length(eintrag) > 1 GROUP BY eintrag "
            "ORDER BY n DESC, eintrag")])


async def laender() -> list[Landzahl]:
    """Länder mit Zahl der sichtbaren Sender."""
    def arbeit(v: sqlite3.Connection) -> list[Landzahl]:
        zahlen = v.execute("SELECT land, COUNT(*) AS n FROM sender_index WHERE sichtbar = 1 AND land <> '' "
                           "GROUP BY land ORDER BY n DESC").fetchall()
        namen = dict(v.execute("SELECT countrycode, MAX(country) FROM stations WHERE countrycode IN "
                               "(SELECT value FROM json_each(?)) GROUP BY countrycode",
                               (json.dumps([z[0] for z in zahlen]),)).fetchall())
        return [Landzahl(code=z[0], name=namen.get(z[0]) or z[0], count=z[1]) for z in zahlen]
    return await database.lesen(arbeit)


__all__ = ["AlteKriterien", "AlteSperre", "Eintragszahl", "Landzahl", "SenderProbe", "ausblenden", "ausgeblendete",
           "freigeben", "ist_ausgeblendet", "laender", "sperren", "spracheintraege", "vorschau"]
