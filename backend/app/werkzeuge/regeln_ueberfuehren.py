"""Heutige Sperren in lebende Regeln überführen (RAD-7, Entscheidung 5)

Aus den Ausschlüssen der Filter-Einstellungen werden Regeln, aus Hand- und Werbesperren Einzelsperren und
Werbeentscheidungen; die Sperrliste selbst bleibt unverändert stehen. Die Vorschau rechnet alles in einer Transaktion
durch, die sie am Ende zurücknimmt, und nennt genau, welche Sender ihre Sichtbarkeit ändern würden (Anzahl, Gründe,
Beispiele, Favoriten). Erst --anwenden schreibt.

    python -m app.werkzeuge.regeln_ueberfuehren              Vorschau, ändert nichts
    python -m app.werkzeuge.regeln_ueberfuehren --anwenden   überführen (einmal; ein zweiter Lauf lehnt ab)

Datenbank: data/radiohub.db im Datenordner (RADIOHUB_DATEN). Im Betrieb im Container:
    docker exec radiohub python -m app.werkzeuge.regeln_ueberfuehren
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from .. import database
from ..config import DB_PATH
from ..services.senderquelle import bestand, dienst, ueberfuehrung

BEISPIELE = 5


class _Zurueck(Exception):
    """Trägt den Bericht der Vorschau aus der Transaktion, die dadurch zurückgenommen wird."""

    def __init__(self, bericht: ueberfuehrung.Bericht) -> None:
        super().__init__("Vorschau")
        self.bericht = bericht


def text(b: ueberfuehrung.Bericht) -> str:
    p = b.plan
    zeilen = [
        "Überführung " + ("angewendet" if b.angewendet else "Vorschau (nichts geändert)"),
        f"Bestand ohne Verschwundene: {b.gesamt}",
        f"Sichtbar heute: {b.vorher_sichtbar}   danach: {b.nachher_sichtbar}   "
        f"Unterschied: {b.nachher_sichtbar - b.vorher_sichtbar:+d}",
        f"Plan: {sum(len(e) for e in p.sprachgruppen.values())} Spracheinträge in {len(p.sprachgruppen)} Regeln, "
        f"{len(p.tags)} Tags ({', '.join(p.tags) or '-'}), Mindeststimmen {p.mindeststimmen or '-'}, "
        f"{len(p.einzelsperren)} Einzelsperren, {len(p.werbesperren)} Werbeentscheidungen",
        f"Wieder sichtbar: {sum(b.neu_sichtbar.values())}",
    ]
    for grund, anzahl in b.neu_sichtbar.most_common():
        zeilen.append(f"  {anzahl:6d}  {grund}: {', '.join(b.beispiele_sichtbar.get(grund, [])[:BEISPIELE])}")
    zeilen.append(f"Neu ausgeblendet: {sum(b.neu_ausgeblendet.values())}")
    for grund, anzahl in b.neu_ausgeblendet.most_common():
        zeilen.append(f"  {anzahl:6d}  {grund}: {', '.join(b.beispiele_ausgeblendet.get(grund, [])[:BEISPIELE])}")
    zeilen.append(f"Favoriten wieder sichtbar ({len(b.favoriten_neu_sichtbar)}): {', '.join(b.favoriten_neu_sichtbar)}")
    zeilen.append(f"Favoriten neu ausgeblendet ({len(b.favoriten_neu_ausgeblendet)}): "
                  f"{', '.join(b.favoriten_neu_ausgeblendet)}")
    zeilen.append(f"Regeln danach ({len(b.regeln)}), betroffene Sender und davon Favoriten:")
    zeilen += [f"  {betroffen:6d} {favoriten:3d}  {titel}"
               for titel, betroffen, favoriten in sorted(b.regeln, key=lambda r: (-r[1], r[0]))]
    return "\n".join(zeilen)


async def lauf(anwenden: bool) -> ueberfuehrung.Bericht:
    await database.einrichten(DB_PATH)
    await database.oeffnen(DB_PATH)
    try:
        if await dienst.aufbereitung_noetig() == "leer":
            await dienst.aufbereiten()
        zuvor = await database.lesen(ueberfuehrung.schon_ueberfuehrt)
        if zuvor and anwenden:
            raise SystemExit(f"Schon überführt am {zuvor}; ein zweiter Lauf würde Regeln doppeln")

        def arbeit(v) -> ueberfuehrung.Bericht:
            plan = ueberfuehrung.plan_lesen(v)
            vorher = ueberfuehrung.heute_sichtbar(v)
            ueberfuehrung.anwenden(v, plan, bestand.jetzt())
            bericht = ueberfuehrung.vergleichen(v, plan, vorher, anwenden)
            if not anwenden:
                raise _Zurueck(bericht)
            return bericht
        try:
            return await database.schreiben(arbeit)
        except _Zurueck as z:
            return z.bericht
    finally:
        await database.schliessen()


def main() -> None:
    teiler = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    teiler.add_argument("--anwenden", action="store_true", help="wirklich überführen")
    argumente = teiler.parse_args()
    bericht = asyncio.run(lauf(argumente.anwenden))
    print(text(bericht))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
