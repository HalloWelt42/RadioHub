"""Umzug des Altbestands: Trockenlauf, Umzug, Aufräumen (siehe README, "Umzug des Altbestands").

    python -m backend.umzug --altes-radio /altes-radio --probe
    python -m backend.umzug --altes-radio /altes-radio
    python -m backend.umzug --altes-radio /altes-radio --aufraeumen --papierkorb /papierkorb
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

from ..config import DATA_DIR, DB_PATH, get_cache_dir
from ..database import get_db, init_db
from .lauf import GB, Umzug, aufraeumen, sicherung, tabellen
from .plan import (Bericht, Datei, altes_radio_dateien, altes_radio_datenbank, eindeutig, radiohub_bilder,
                   radiohub_dateien, radiohub_datenbank)


def _alt_oeffnen(ordner: Path) -> sqlite3.Connection:
    """pyradio.db nur lesend (unveränderlich geöffnet, schreibt auch keine -wal/-shm)."""
    conn = sqlite3.connect(f"file:{ordner / 'pyradio.db'}?immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def planen(conn: sqlite3.Connection, altes_radio: Path | None, schreiben: bool) -> tuple[list[Datei], Bericht]:
    """Datenbank übernehmen (nur mit `schreiben`) und die Dateien bestimmen, die umziehen."""
    bericht = Bericht()
    radiohub_datenbank(conn, DATA_DIR, schreiben, bericht)
    radiohub_bilder(DATA_DIR, get_cache_dir(), schreiben, bericht)
    dateien = radiohub_dateien(conn, DATA_DIR, bericht)
    if altes_radio:
        alt = _alt_oeffnen(altes_radio)
        try:
            altes_radio_datenbank(conn, alt, schreiben, bericht)
            dateien += altes_radio_dateien(conn, alt, altes_radio, bericht)
        finally:
            alt.close()
    return eindeutig(dateien), bericht


def zeigen(dateien: list[Datei], bericht: Bericht, umzug: Umzug) -> None:
    offen = umzug.offen(dateien)
    print("Datenbank:")
    for was, anzahl in sorted(bericht.zeilen.items()):
        print(f"  {was}: {anzahl}")
    print(f"Dateien: {len(dateien)} gesamt, {len(offen)} offen "
          f"({sum(d.quelle.stat().st_size for d in offen) / GB:.2f} GB)")
    teile: dict[str, list[Datei]] = {}
    for d in offen:
        teile.setdefault(d.teil, []).append(d)
    for teil, liste in sorted(teile.items()):
        print(f"  {teil}: {len(liste)} Dateien, {sum(d.quelle.stat().st_size for d in liste) / GB:.2f} GB")
        for d in liste[:3]:
            print(f"    {d.quelle} -> {d.ziel}")


def main(argv: list[str] | None = None) -> int:
    teiler = argparse.ArgumentParser(prog="python -m backend.umzug", description="Umzug des Altbestands")
    teiler.add_argument("--altes-radio", type=Path, help="Ordner des alten Radios (pyradio.db, recordings/)")
    art = teiler.add_mutually_exclusive_group()
    art.add_argument("--probe", action="store_true", help="Trockenlauf: nur zählen und die Zuordnung zeigen")
    art.add_argument("--aufraeumen", action="store_true",
                     help="nach vollständigem Lauf die Quellordner in den Papierkorb-Ordner verschieben")
    teiler.add_argument("--papierkorb", type=Path, help="Ordner, in dem papierkorb-radiohub-<datum> entsteht")
    a = teiler.parse_args(argv)

    if a.altes_radio and not (a.altes_radio / "pyradio.db").is_file():
        teiler.error(f"keine pyradio.db in {a.altes_radio}")
    conn = get_db()

    if a.probe:
        dateien, bericht = planen(conn, a.altes_radio, schreiben=False)
        zeigen(dateien, bericht, Umzug(conn, None))
        return 0
    if a.aufraeumen:
        return _aufraeumen(conn, a)
    init_db()
    tabellen(conn)
    return asyncio.run(_umziehen(conn, a.altes_radio))


async def _umziehen(conn: sqlite3.Connection, altes_radio: Path | None) -> int:
    from .. import ablage as ablage_paket
    ablage = ablage_paket.starten()
    try:
        zustand = await ablage.zustand()
        if not zustand.get("verbunden"):
            print(f"Abbruch: Ablage nicht bereit: {zustand.get('meldung')}", file=sys.stderr)
            return 2
        kopie = sicherung(DB_PATH)
        if kopie:
            print(f"Datenbank gesichert: {kopie}")
        dateien, bericht = planen(conn, altes_radio, schreiben=True)
        umzug = Umzug(conn, ablage)
        zeigen(dateien, bericht, umzug)
        ergebnis = await umzug.alle(dateien)
        print(f"Fertig: {ergebnis.erledigt} abgelegt, {ergebnis.uebernommen} lagen schon gleich in der Ablage, "
              f"{ergebnis.schon_erledigt} aus früheren Läufen, {ergebnis.fehler} Fehler")
        if ergebnis.fehler:
            print("Nicht vollständig: Lauf wiederholen, er macht nur den Rest", file=sys.stderr)
            return 1
        print("Vollständig. Danach prüfen und erst dann --aufraeumen")
        return 0
    finally:
        await ablage.schliessen()


def _aufraeumen(conn: sqlite3.Connection, a) -> int:
    """Nur nach vollständigem letzten Lauf und wenn der Plan nichts Offenes mehr zeigt."""
    if not a.papierkorb:
        print("Abbruch: --papierkorb fehlt", file=sys.stderr)
        return 1
    umzug = Umzug(conn, None)
    dateien, _ = planen(conn, a.altes_radio, schreiben=False)
    offen = umzug.offen(dateien)
    if not umzug.vollstaendig() or offen:
        print(f"Abbruch: Umzug nicht vollständig ({len(offen)} Dateien offen), nichts verschoben", file=sys.stderr)
        return 1
    quellen = {"radiohub-recordings": DATA_DIR / "recordings"}
    if a.altes_radio:
        quellen["altes-radio-recordings"] = a.altes_radio / "recordings"
    for ziel in aufraeumen(quellen, a.papierkorb):
        print(f"Verschoben nach {ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
