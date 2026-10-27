"""Ausführen: Dateien ablegen und prüfen (Größe und SHA-256 gegen den Stand in der Ablage), Datenbank nachziehen,
Stand je Datei festhalten, Fortschritt melden; Aufräumen der Quellordner in einen Papierkorb."""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from ..ablage.port import Ablage
from .plan import Datei

GB = 1024 ** 3
_STUECK = 1024 * 1024


def tabellen(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS umzug_dateien (
        quelle TEXT PRIMARY KEY, ziel TEXT NOT NULL, groesse INTEGER, sha256 TEXT, erledigt_am TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS umzug_laeufe (
        id INTEGER PRIMARY KEY AUTOINCREMENT, beginn TEXT, ende TEXT, dateien INTEGER, fehler INTEGER,
        vollstaendig INTEGER DEFAULT 0)""")
    conn.commit()


def sicherung(db: Path) -> Path | None:
    """Einmalige Kopie der Datenbank vor der ersten Änderung (bleibt liegen, wird nie überschrieben)."""
    ziel = db.with_name(f"{db.name}.vor-umzug")
    if ziel.exists():
        return None
    quelle = sqlite3.connect(str(db))
    kopie = sqlite3.connect(str(ziel))
    with kopie:
        quelle.backup(kopie)
    kopie.close()
    quelle.close()
    return ziel


def _sha_datei(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        while teil := f.read(_STUECK):
            h.update(teil)
    return h.hexdigest()


async def _sha_ablage(ablage: Ablage, pfad: str) -> str:
    h = hashlib.sha256()
    async for teil in ablage.lesen(pfad):
        h.update(teil)
    return h.hexdigest()


@dataclass
class Ergebnis:
    erledigt: int = 0
    schon_erledigt: int = 0
    uebernommen: int = 0   # lag schon gleich in der Ablage (etwa nach Abbruch zwischen Ablegen und Eintragen)
    fehler: int = 0
    bytes: int = 0


class Umzug:
    def __init__(self, conn: sqlite3.Connection, ablage: Ablage | None, ausgabe: Callable[[str], None] = print) -> None:
        """Ohne Ablage nur lesend (Trockenlauf, Prüfung vor dem Aufräumen); die Tabellen legt `tabellen` an."""
        self.conn = conn
        self.ablage = ablage
        self.ausgabe = ausgabe

    def _stand(self, quelle: Path):
        try:
            return self.conn.execute("SELECT * FROM umzug_dateien WHERE quelle = ?", (str(quelle),)).fetchone()
        except sqlite3.OperationalError:
            return None  # noch nie gelaufen

    def offen(self, dateien: list[Datei]) -> list[Datei]:
        return [d for d in dateien if not ((s := self._stand(d.quelle)) and s["erledigt_am"])]

    async def _gleich(self, ziel: str, groesse: int, sha: str) -> bool:
        eintrag = await self.ablage.eintrag(ziel)
        return bool(eintrag and not eintrag.ist_ordner and eintrag.groesse == groesse
                    and await _sha_ablage(self.ablage, ziel) == sha)

    async def _ziel(self, d: Datei, groesse: int, sha: str) -> tuple[str, bool]:
        """Ziel dieser Quelle: das gemerkte, sonst das geplante oder mit Zähler das nächste freie. True, wenn dort
        schon genau diese Datei liegt."""
        stand = self._stand(d.quelle)
        if stand:
            return stand["ziel"], await self._gleich(stand["ziel"], groesse, sha)
        stamm, punkt, endung = d.ziel.rpartition(".")
        kandidat, zaehler = d.ziel, 2
        while True:
            fremd = self.conn.execute("SELECT 1 FROM umzug_dateien WHERE ziel = ? AND quelle != ?",
                                      (kandidat, str(d.quelle))).fetchone()
            if not fremd:
                eintrag = await self.ablage.eintrag(kandidat)
                if eintrag is None:
                    return kandidat, False
                if await self._gleich(kandidat, groesse, sha):
                    return kandidat, True
            kandidat = f"{stamm} ({zaehler}).{endung}" if punkt else f"{d.ziel} ({zaehler})"
            zaehler += 1

    async def datei(self, d: Datei) -> str:
        """Eine Datei umziehen; liefert "erledigt", "schon_erledigt" oder "uebernommen"."""
        stand = self._stand(d.quelle)
        if stand and stand["erledigt_am"]:
            return "schon_erledigt"
        groesse = d.quelle.stat().st_size
        sha = await asyncio.to_thread(_sha_datei, d.quelle)
        ziel, schon_da = await self._ziel(d, groesse, sha)
        self.conn.execute("""INSERT INTO umzug_dateien (quelle, ziel, groesse, sha256) VALUES (?, ?, ?, ?)
                             ON CONFLICT(quelle) DO UPDATE SET groesse = excluded.groesse, sha256 = excluded.sha256""",
                          (str(d.quelle), ziel, groesse, sha))
        self.conn.commit()
        if not schon_da:
            await self.ablage.ablegen(ziel, d.quelle)
            if not await self._gleich(ziel, groesse, sha):
                raise RuntimeError(f"Prüfung fehlgeschlagen: {ziel} weicht von der Quelle ab")
        with self.conn:
            if d.eintragen:
                d.eintragen(self.conn, ziel, groesse)
            self.conn.execute("UPDATE umzug_dateien SET erledigt_am = ? WHERE quelle = ?",
                              (datetime.now().isoformat(timespec="seconds"), str(d.quelle)))
        return "uebernommen" if schon_da else "erledigt"

    async def alle(self, dateien: list[Datei]) -> Ergebnis:
        ergebnis = Ergebnis()
        offen = self.offen(dateien)
        ergebnis.schon_erledigt = len(dateien) - len(offen)
        gesamt = sum(d.quelle.stat().st_size for d in offen) or 1
        lauf = self.conn.execute("INSERT INTO umzug_laeufe (beginn, dateien) VALUES (?, ?)",
                                 (datetime.now().isoformat(timespec="seconds"), len(offen))).lastrowid
        self.conn.commit()
        beginn = time.monotonic()
        self.ausgabe(f"Umzug: {len(offen)} Dateien offen ({gesamt / GB:.2f} GB), {ergebnis.schon_erledigt} schon erledigt")
        for d in offen:
            groesse = d.quelle.stat().st_size
            try:
                art = await self.datei(d)
                setattr(ergebnis, art, getattr(ergebnis, art) + 1)
                zeichen = "ok"
            except Exception as f:  # die nächste Datei soll trotzdem drankommen
                ergebnis.fehler += 1
                zeichen = f"FEHLER {f}"
            ergebnis.bytes += groesse
            dauer = time.monotonic() - beginn
            rest = dauer / ergebnis.bytes * (gesamt - ergebnis.bytes) if ergebnis.bytes else 0
            self.ausgabe(f"[{100 * ergebnis.bytes / gesamt:5.1f} %] {ergebnis.bytes / GB:6.2f} von {gesamt / GB:.2f} GB, "
                         f"noch etwa {rest / 60:.0f} min  {d.teil}: {d.quelle.name} -> {zeichen}")
        with self.conn:
            self.conn.execute("UPDATE umzug_laeufe SET ende = ?, fehler = ?, vollstaendig = ? WHERE id = ?",
                              (datetime.now().isoformat(timespec="seconds"), ergebnis.fehler,
                               int(ergebnis.fehler == 0), lauf))
        return ergebnis

    def vollstaendig(self) -> bool:
        try:
            letzter = self.conn.execute("SELECT vollstaendig FROM umzug_laeufe ORDER BY id DESC LIMIT 1").fetchone()
        except sqlite3.OperationalError:
            return False
        return bool(letzter and letzter["vollstaendig"])


def aufraeumen(quellen: dict[str, Path], papierkorb_wurzel: Path, heute: date | None = None) -> list[Path]:
    """Quellordner in `<papierkorb_wurzel>/papierkorb-radiohub-<datum>/<name>` verschieben, nie löschen."""
    ziel_ordner = papierkorb_wurzel / f"papierkorb-radiohub-{(heute or date.today()).isoformat()}"
    verschoben = []
    for name, quelle in quellen.items():
        if not quelle.exists():
            continue
        ziel = ziel_ordner / name
        if ziel.exists():
            raise FileExistsError(f"{ziel} gibt es schon, nichts verschoben")
        ziel_ordner.mkdir(parents=True, exist_ok=True)
        shutil.move(str(quelle), str(ziel))
        verschoben.append(ziel)
    return verschoben
