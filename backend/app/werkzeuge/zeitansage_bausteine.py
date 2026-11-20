"""Bausteine der Zeitansage in einen Ordner sprechen lassen, etwa für Basic (RAD-15): `web/daten/zeitansage/`.

Gesprochen wird wie in der App (services.zeitansage.baustein_sprechen: Vertonung mit dem App-Schlüssel der Kellerwolke,
deutsch, zugeschnitten als MP3 mono), mit der angegebenen Stimme. Basic liegt öffentlich, dort nur eine Katalogstimme.

Kurze Texte kippen bei manchen Stimmen: das Modell spricht mehr als den Text (andere Sprache, Gerede) oder verschluckt
ihn. Das zeigt sich an der Länge je Silbe. Liegt ein Baustein außerhalb von GRENZEN um den Mittelwert aller, spricht
die Vertonung ihn bis zu `--versuche` Mal, und die Fassung nächst dem Mittelwert bleibt. Ob alles deutsch und richtig
gesprochen ist, prüft danach ein Mensch beim Anhören.

Läuft dort, wo die Einstellungen der App liegen (im Container des Pi: `docker exec -w /app/backend radiohub python -m
app.werkzeuge.zeitansage_bausteine --stimme katalog:sohee --aus /tmp/zeitansage`), danach den Ordner nach
`web/daten/zeitansage/` holen.
"""
from __future__ import annotations

import argparse
import asyncio
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from appkern.vorlesen import stimmwahl

from ..einstellungen import stand as einstellungen_stand
from ..services.zeitansage import ZeitansageEinstellungen, baustein_sprechen, bausteine, client_fuer

GRENZEN = (0.6, 2.0)


def silben(text: str) -> int:
    return max(1, len(re.findall(r"[aeiouäöüy]+", text.lower())))


def dauer(datei: Path) -> float:
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                          str(datei)]))


def je_silbe(datei: Path, text: str) -> float:
    return dauer(datei) / silben(text)


def auffaellig(wert: float, mitte: float) -> bool:
    return not GRENZEN[0] <= wert / mitte <= GRENZEN[1]


async def sprechen(stimme: str, aus: Path, versuche: int) -> list[str]:
    """Spricht alle Bausteine nach `aus`; liefert die, die auch nach allen Versuchen auffällig blieben."""
    e = ZeitansageEinstellungen.aus(einstellungen_stand())
    if not (e.adresse and e.schluessel):
        raise SystemExit("Vertonung oder Schlüssel der Kellerwolke fehlen in den Einstellungen")
    wahl = stimmwahl(stimme)
    if wahl is None:
        raise SystemExit("--stimme fehlt")
    texte = bausteine()
    aus.mkdir(parents=True, exist_ok=True)
    async with client_fuer(e) as client:
        for i, (name, text) in enumerate(texte.items(), 1):
            (aus / f"{name}.mp3").write_bytes(await baustein_sprechen(client, e, text, wahl))
            print(f"{i:2}/{len(texte)} {name}", flush=True)
        mitte = sorted(je_silbe(aus / f"{n}.mp3", t) for n, t in texte.items())[len(texte) // 2]
        uebrig = []
        for name, text in texte.items():
            ziel = aus / f"{name}.mp3"
            if not auffaellig(je_silbe(ziel, text), mitte):
                continue
            bester = abs(math.log(je_silbe(ziel, text) / mitte))
            with tempfile.TemporaryDirectory() as ordner:
                for versuch in range(2, versuche + 1):
                    neu = Path(ordner) / f"{versuch}.mp3"
                    neu.write_bytes(await baustein_sprechen(client, e, text, wahl))
                    abstand = abs(math.log(je_silbe(neu, text) / mitte))
                    if abstand < bester:
                        bester = abstand
                        ziel.write_bytes(neu.read_bytes())
            verhaeltnis = je_silbe(ziel, text) / mitte
            print(f"{name}: {verhaeltnis:.2f} des Mittels nach {versuche} Versuchen", flush=True)
            if auffaellig(je_silbe(ziel, text), mitte):
                uebrig.append(name)
    return uebrig


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--stimme", required=True, help="katalog:<Name> oder Kennung einer privaten Stimme")
    p.add_argument("--aus", required=True, type=Path, help="Zielordner der MP3-Dateien")
    p.add_argument("--versuche", type=int, default=4, help="Fassungen je auffälligem Baustein (Vorgabe 4)")
    a = p.parse_args(argv)
    uebrig = asyncio.run(sprechen(a.stimme, a.aus, max(1, a.versuche)))
    if uebrig:
        print("Weiter auffällig (anhören): " + ", ".join(uebrig))
    return 0


if __name__ == "__main__":
    sys.exit(main())
