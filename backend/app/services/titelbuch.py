"""Titelbuch: führt die Titelwechsel eines Senders aus den Angaben des Stromlesers (RAD-33).

Früher verband sich dafür ein eigener Leser mit dem Sender (IcyMetadataLogger); jetzt kommen die Angaben aus derselben
Verbindung wie der Ton. Jeder Eintrag trägt seine Stelle im Ton: `b` die Ton-Bytes davor, `t` dieselbe Stelle in
Millisekunden (über die Bitrate des Stroms), `wand` die Uhrzeit seit dem Start (nur zur Auskunft). Titel auf der
Sperrliste (icy_title_ignore) werden vermerkt, angezeigt bleibt der letzte gültige. Die Datei (Titelliste) behält ihr
Format: {metaint, total_audio_bytes, entries}.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Awaitable, Callable, Optional

from .messung import messung
from .stromleser import Angabe

logger = logging.getLogger("radiohub.titelbuch")

#: async fn(titel, ton_ms, ton_bytes), nur bei echten Wechseln (nicht bei gesperrten Titeln)
BeiWechsel = Callable[[str, int, int], Awaitable[None]]


class Titelbuch:
    def __init__(self, sperrliste: list[dict] | None = None, bei_wechsel: Optional[BeiWechsel] = None,
                 datei: Optional[Path] = None, metaint: int = 0):
        self.entries: list[dict] = []
        #: jeder Wechsel der Sendedaten, auch zu einem leeren Titel (Einspieler, RAD-45): Sekunde, Titel, gesperrt;
        #: für den Feinschnitt, der Einschübe ohne Titel als eigene Stücke braucht. Teilt nichts und zeigt nichts.
        self.wechsel: list[tuple[float, str, bool]] = []
        self._letzter_roh: Optional[str] = None
        self._sperrliste = sperrliste or []
        self._bei_wechsel = bei_wechsel
        self._datei = datei
        self.metaint = metaint
        self._ton_bytes = 0
        self._letzter = ""
        self._letzter_gueltiger = ""

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    async def angabe(self, a: Angabe) -> None:
        self._ton_bytes = a.ton_bytes
        titel = titel_aus(a.roh)
        if "StreamTitle=" in a.roh and titel != self._letzter_roh:
            self._letzter_roh = titel
            messung.merken("angabe", ton_s=round(a.sekunde, 2), roh=a.roh[:300])
            self.wechsel.append((a.sekunde, titel, bool(titel) and self._gesperrt(titel)))
        if not titel or titel == self._letzter:
            return
        self._letzter = titel
        gesperrt = self._gesperrt(titel)
        anzeige = (self._letzter_gueltiger or titel) if gesperrt else titel
        if not gesperrt:
            self._letzter_gueltiger = titel
        ton_ms = int(a.sekunde * 1000)
        self.entries.append({"t": ton_ms, "b": a.ton_bytes, "wand": a.wand_ms, "title": anzeige, "raw_title": titel,
                             "ignored": gesperrt, "raw": a.roh})
        logger.info(f"Titel bei {ton_ms / 1000:.1f} s{' (gesperrt)' if gesperrt else ''}: {titel}")
        self.speichern()
        if not gesperrt and self._bei_wechsel:
            try:
                await self._bei_wechsel(anzeige, ton_ms, a.ton_bytes)
            except Exception as f:
                logger.warning(f"Titelwechsel nicht verarbeitet: {f}")

    def abschliessen(self, ton_bytes: int) -> None:
        """Am Ende: die Gesamtzahl der Ton-Bytes festhalten (der Schnitt rechnet Stellen aus dem Verhältnis)."""
        self._ton_bytes = ton_bytes
        self.speichern()

    def speichern(self) -> None:
        if not self._datei or not self.entries:
            return
        try:
            self._datei.parent.mkdir(parents=True, exist_ok=True)
            self._datei.write_text(json.dumps({"metaint": self.metaint, "total_audio_bytes": self._ton_bytes,
                                               "entries": self.entries}, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as f:
            logger.warning(f"Titelliste nicht gespeichert: {f}")

    def _gesperrt(self, titel: str) -> bool:
        gross = titel.upper()
        for regel in self._sperrliste:
            muster = regel.get("pattern", "").upper()
            if muster and (muster in gross if regel.get("match_type") == "contains" else gross == muster):
                return True
        return False


def titel_aus(roh: str) -> str:
    """Titel aus "StreamTitle='...';": bis zum Abschluss "';", damit Apostrophe im Titel bleiben (Don't ...)."""
    treffer = re.search(r"StreamTitle='(.*?)';", roh) or re.search(r"StreamTitle='(.*)'\s*$", roh)
    return treffer.group(1).strip() if treffer else ""
