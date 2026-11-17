"""Sichtbarkeit je Sender: eine Wahrheit für die neue Abfrage und die alten Wege. Neu berechnet nach dem Abgleich, nach
jeder Regeländerung und nach Werbeentscheidung, Bewertung, Favorit, Einzelsperre oder Freigabe (dann nur für die
Gruppe des Senders).

Regel der Sichtbarkeit: ein Favorit ist immer sichtbar (als Ausnahme, wenn eine Regel ihn trifft oder er verschwunden
ist); eine Freigabe hebt Regeln auf, aber kein Verschwinden; sonst ist sichtbar, wer nicht verschwunden ist und keine
eingeschaltete Regel trifft. Je Gruppe von Varianten ist der beste sichtbare Sender der Vertreter (Favoriten zuerst)."""
from __future__ import annotations

import json
import sqlite3

from . import regeln, werbung
from .modelle import Bestand, Grund, RegelEntwurf, RegelVorschau, SenderKurz, Sichtbarkeit


def _bereich(nrs: list[int] | None, spalte: str = "nr") -> tuple[str, list[object]]:
    if nrs is None:
        return "", []
    return f" AND {spalte} IN (SELECT value FROM json_each(?))", [json.dumps(nrs)]


def _merkmale(v: sqlite3.Connection, nrs: list[int] | None) -> None:
    """Favorit, Freigabe und Werbestufe aus ihren Tabellen."""
    bereich, werte = _bereich(nrs)
    v.execute(f"""UPDATE sender_index SET
                    favorit = EXISTS (SELECT 1 FROM favorites f WHERE f.uuid = sender_index.uuid),
                    freigegeben = EXISTS (SELECT 1 FROM sender_freigabe g WHERE g.uuid = sender_index.uuid)
                  WHERE 1 = 1 {bereich}""", werte)
    uuids = None if nrs is None else [z[0] for z in v.execute(f"SELECT uuid FROM sender_index WHERE 1 = 1 {bereich}", werte)]
    stufen = werbung.stufen_lesen(v, uuids)
    v.execute(f"UPDATE sender_index SET werbe_stufe = 0 WHERE werbe_stufe <> 0 {bereich}", werte)
    v.executemany("UPDATE sender_index SET werbe_stufe = ? WHERE uuid = ?", [(s, u) for u, s in stufen.items() if s])


def treffer_berechnen(v: sqlite3.Connection, nrs: list[int] | None = None, regel_ids: list[str] | None = None) -> None:
    """Treffer der Regeln (alle oder die genannten, für alle Sender oder die genannten), ein- wie ausgeschaltet."""
    bereich, werte = _bereich(nrs)
    for z in v.execute("SELECT id, art, wert FROM regel").fetchall():
        if regel_ids is not None and z["id"] not in regel_ids:
            continue
        v.execute(f"DELETE FROM sender_ausblendung WHERE regel = ? {bereich}", [z["id"], *werte])
        sql, sql_werte = regeln.treffer_sql(z["art"], regeln.entwurf_lesen(z["art"], z["wert"]))
        v.execute(f"INSERT OR IGNORE INTO sender_ausblendung (regel, nr) SELECT ?, nr FROM ({sql}) WHERE 1 = 1 {bereich}",
                  [z["id"], *sql_werte, *werte])


def _sicht(v: sqlite3.Connection, nrs: list[int] | None) -> None:
    """Getroffen, sichtbar, Vertreter und Zahl der Varianten; geschrieben wird nur, was sich ändert."""
    bereich, werte = _bereich(nrs)
    getroffen = ("EXISTS (SELECT 1 FROM sender_ausblendung a JOIN regel r ON r.id = a.regel AND r.an = 1 "
                 "WHERE a.nr = sender_index.nr)")
    v.execute(f"UPDATE sender_index SET getroffen = {getroffen} WHERE getroffen <> {getroffen} {bereich}", werte)
    sichtbar = ("(CASE WHEN favorit = 1 THEN 1 WHEN verschwunden = 1 THEN 0 WHEN freigegeben = 1 THEN 1 "
                "WHEN getroffen = 1 THEN 0 ELSE 1 END)")
    v.execute(f"UPDATE sender_index SET sichtbar = {sichtbar} WHERE sichtbar <> {sichtbar} {bereich}", werte)
    # Vertreter je Gruppe (nur die Gruppen der genannten Sender): der beste sichtbare, Favoriten zuerst
    gruppen, g_werte = ("", []) if nrs is None else (
        " AND gruppe IN (SELECT gruppe FROM sender_index WHERE nr IN (SELECT value FROM json_each(?)))", [json.dumps(nrs)])
    v.execute("CREATE TEMP TABLE IF NOT EXISTS rang (nr INTEGER PRIMARY KEY, vertreter INTEGER, varianten INTEGER)")
    v.execute("DELETE FROM temp.rang")
    v.execute(f"""INSERT INTO temp.rang (nr, vertreter, varianten)
                  SELECT nr, sichtbar AND platz = 1, CASE WHEN sichtbar = 1 THEN n ELSE 0 END FROM (
                    SELECT nr, sichtbar,
                           ROW_NUMBER() OVER (PARTITION BY gruppe, sichtbar ORDER BY favorit DESC, qualitaet_rang DESC,
                                              kbps DESC, erreichbar DESC, stimmen DESC, uuid) AS platz,
                           COUNT(*) OVER (PARTITION BY gruppe, sichtbar) AS n
                    FROM sender_index WHERE 1 = 1 {gruppen})""", g_werte)
    v.execute("""UPDATE sender_index SET vertreter = r.vertreter, varianten = r.varianten FROM temp.rang r
                 WHERE r.nr = sender_index.nr AND (sender_index.vertreter <> r.vertreter
                                                   OR sender_index.varianten <> r.varianten)""")


def neu_berechnen(v: sqlite3.Connection, nrs: list[int] | None = None, *, treffer: bool = True,
                  regel_ids: list[str] | None = None) -> None:
    """Alles für alle Sender (nach Abgleich und Regeländerung) oder für die genannten und ihre Gruppen. Ohne
    `treffer` bleiben die Treffer der Regeln, wie sie sind (Regel nur ein- oder ausgeschaltet)."""
    _merkmale(v, nrs)
    if treffer:
        treffer_berechnen(v, nrs, regel_ids)
    _sicht(v, nrs)


def nrs_von(v: sqlite3.Connection, uuids: list[str]) -> list[int]:
    return [z[0] for z in v.execute("SELECT nr FROM sender_index WHERE uuid IN (SELECT value FROM json_each(?))",
                                    (json.dumps(uuids),))]


# ----- Lesen -------------------------------------------------------------------------------------------------------------

def bestand(v: sqlite3.Connection) -> Bestand:
    z = v.execute("""SELECT COUNT(*), SUM(sichtbar), SUM(sichtbar = 0 AND verschwunden = 0), SUM(verschwunden),
                            SUM(sichtbar = 1 AND (getroffen = 1 OR verschwunden = 1)) FROM sender_index""").fetchone()
    favoriten = v.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]
    return Bestand(gesamt=z[0], sichtbar=z[1] or 0, ausgeblendet=z[2] or 0, verschwunden=z[3] or 0,
                   favoriten=favoriten, ausnahmen=z[4] or 0)


def gruende(v: sqlite3.Connection, nrs: list[int]) -> dict[int, list[Grund]]:
    """Eingeschaltete Regeln je Sender."""
    if not nrs:
        return {}
    ergebnis: dict[int, list[Grund]] = {}
    for z in v.execute("""SELECT a.nr, r.id, r.art, r.wert FROM sender_ausblendung a JOIN regel r ON r.id = a.regel AND r.an = 1
                          WHERE a.nr IN (SELECT value FROM json_each(?)) ORDER BY r.angelegt_am""", (json.dumps(nrs),)):
        entwurf = regeln.entwurf_lesen(z["art"], z["wert"])
        ergebnis.setdefault(z["nr"], []).append(Grund(regel=z["id"], art=z["art"], titel=regeln.titel(z["art"], entwurf)))
    return ergebnis


def erklaeren(v: sqlite3.Connection, uuid: str) -> Sichtbarkeit | None:
    z = v.execute("SELECT nr, sichtbar, verschwunden, favorit, freigegeben FROM sender_index WHERE uuid = ?", (uuid,)).fetchone()
    if z is None:
        return None
    gesperrt = v.execute("SELECT 1 FROM sender_sperre WHERE uuid = ?", (uuid,)).fetchone() is not None
    return Sichtbarkeit(uuid=uuid, sichtbar=bool(z["sichtbar"]), verschwunden=bool(z["verschwunden"]),
                        favorit=bool(z["favorit"]), freigegeben=bool(z["freigegeben"]), gesperrt=gesperrt,
                        gruende=gruende(v, [z["nr"]]).get(z["nr"], []))


def _kurz(v: sqlite3.Connection, sql: str, werte: list[object], grenze: int = 5) -> list[SenderKurz]:
    return [SenderKurz(uuid=z["uuid"], name=z["name"] or "", land=z["land"], stimmen=z["stimmen"], logo=z["logo"] or "")
            for z in v.execute(f"""SELECT i.uuid, s.name, i.land, i.stimmen, s.favicon AS logo FROM sender_index i
                                   JOIN stations s ON s.uuid = i.uuid WHERE i.nr IN ({sql})
                                   ORDER BY i.stimmen DESC, i.uuid LIMIT {int(grenze)}""", werte)]


def vorschau(v: sqlite3.Connection, entwurf: RegelEntwurf) -> RegelVorschau:
    """Was eine neue Regel bewirken würde (ändert nichts)."""
    sql, werte = regeln.treffer_sql(entwurf.art, entwurf)
    z = v.execute(f"""SELECT COUNT(*), SUM(sichtbar = 1 AND favorit = 0 AND freigegeben = 0), SUM(favorit)
                      FROM sender_index WHERE verschwunden = 0 AND nr IN ({sql})""", werte).fetchone()
    namen = [n for (n,) in v.execute(f"""SELECT f.name FROM favorites f JOIN sender_index i ON i.uuid = f.uuid
                                         WHERE i.nr IN ({sql}) ORDER BY f.name LIMIT 10""", werte)]
    neu = f"SELECT nr FROM sender_index WHERE verschwunden = 0 AND sichtbar = 1 AND favorit = 0 AND freigegeben = 0 AND nr IN ({sql})"
    return RegelVorschau(titel=regeln.titel(entwurf.art, entwurf), betroffen=z[0], neu_ausgeblendet=z[1] or 0,
                         favoriten=z[2] or 0, favoriten_namen=namen, beispiele=_kurz(v, neu, werte),
                         gleiche_regel=regeln.gleiche(v, entwurf))


def wieder_sichtbar_sql(regel_id: str) -> tuple[str, list[object]]:
    """Sender, die sichtbar würden, wenn diese Regel nicht mehr gilt."""
    return ("""SELECT a.nr FROM sender_ausblendung a JOIN sender_index i ON i.nr = a.nr
               WHERE a.regel = ? AND i.sichtbar = 0 AND i.verschwunden = 0 AND NOT EXISTS (
                   SELECT 1 FROM sender_ausblendung b JOIN regel r ON r.id = b.regel AND r.an = 1
                   WHERE b.nr = a.nr AND b.regel <> a.regel)""", [regel_id])


def folgen(v: sqlite3.Connection, regel_id: str) -> tuple[int, list[SenderKurz]]:
    sql, werte = wieder_sichtbar_sql(regel_id)
    anzahl = v.execute(f"SELECT COUNT(*) FROM ({sql})", werte).fetchone()[0]
    return anzahl, _kurz(v, sql, werte)
