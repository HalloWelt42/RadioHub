"""Anpassung der Senderliste (RAD-12): Sender, die nicht zum Katalog gehören, als Liste von Kennungen in
`anpassung.txt` neben diesem Modul. Je Zeile eine Kennung: SHA-256 der uuid des Senders, hexadezimal. Was die Liste
trifft, gibt es im Bestand von PRO (Abgleich und Aufbereitung) und in der Liste von Basic schlicht nicht.

Ohne Datenbank und ohne FastAPI wie der ganze Baustein; Backend und Werkzeug der statischen Liste prüfen damit gleich."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

DATEI = Path(__file__).with_name("anpassung.txt")
_KENNUNG = re.compile(r"[0-9a-f]{64}")


def kennung(uuid: str) -> str:
    return hashlib.sha256(uuid.strip().lower().encode()).hexdigest()


class Anpassung(BaseModel):
    kennungen: frozenset[str] = frozenset()

    def trifft(self, uuid: str) -> bool:
        """Gehört der Sender nicht zum Katalog?"""
        return bool(uuid) and kennung(uuid) in self.kennungen


def aus_text(text: str) -> Anpassung:
    """Liest die Kennungen; leere Zeilen zählen nicht, alles andere muss eine Kennung sein (sonst ValueError)."""
    zeilen = [z.strip() for z in text.splitlines() if z.strip()]
    falsch = [n for n, z in enumerate(zeilen, 1) if not _KENNUNG.fullmatch(z)]
    if falsch:
        raise ValueError(f"Keine Kennung in Zeile {falsch[0]} der Anpassung")
    return Anpassung(kennungen=frozenset(zeilen))


@lru_cache(maxsize=1)
def laden() -> Anpassung:
    """Die Anpassung der App (einmal gelesen)."""
    return aus_text(DATEI.read_text(encoding="utf-8")) if DATEI.is_file() else Anpassung()
