"""Ordnerstruktur in der Ablage, die einzige Stelle für Ordner- und Dateinamen.

    Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/001 <Titel>.mp3      eine Aufnahme mit ihren Stücken
    Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/Titelliste.json      Titelwechsel und Ereignisse der Aufnahme
    Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/Wellenform.peaks     Wellenform für den Schnitt (entsteht bei Bedarf)
    Aufnahmen/<Ordner>/<Sender>/<JJJJ-MM-TT HH-MM-SS>/...         eine Aufnahme in einem eigenen Aufnahmeordner
    Podcasts/<Abo>/<JJJJ-MM-TT> <Folge>.mp3                       eine heruntergeladene Folge
    Zeitansage/es-ist.mp3, stunde-05.mp3, minute-34.mp3          Bausteine der Zeitansage
"""

from __future__ import annotations

import re
from datetime import datetime

AUFNAHMEN = "Aufnahmen"
PODCASTS = "Podcasts"
TITELLISTE = "Titelliste.json"
WELLENFORM = "Wellenform.peaks"

_UNERLAUBT = re.compile(r'[/\\:*?"<>|\x00-\x1f]+')


def name(text: str, laenge: int = 80, ersatz: str = "Ohne Namen") -> str:
    """Lesbarer Datei- oder Ordnername: Umlaute und Leerzeichen bleiben, Trennzeichen und Steuerzeichen nicht."""
    sauber = _UNERLAUBT.sub(" ", str(text or ""))
    sauber = re.sub(r"\s+", " ", sauber).strip().strip(".")
    return sauber[:laenge].strip() or ersatz


def zeitpunkt(wert: datetime | str | None) -> str:
    """`2026-10-28 14-00-05` aus einer Zeit (ISO-Text oder datetime)."""
    if isinstance(wert, str):
        try:
            wert = datetime.fromisoformat(wert)
        except ValueError:
            wert = None
    return (wert or datetime.now()).strftime("%Y-%m-%d %H-%M-%S")


def aufnahmeordner(sender: str, beginn: datetime | str | None, ordner: str | None = None) -> str:
    teile = [AUFNAHMEN] + ([name(ordner)] if ordner else []) + [name(sender, ersatz="Unbekannter Sender"), zeitpunkt(beginn)]
    return "/".join(teile)


def eigener_ordner(ordner: str) -> str:
    """Aufnahmeordner, den der Mensch angelegt hat."""
    return f"{AUFNAHMEN}/{name(ordner)}"


def stueck(sitzungsordner: str, index: int, titel: str, endung: str) -> str:
    endung = endung if endung.startswith(".") else f".{endung}"
    return f"{sitzungsordner}/{index + 1:03d} {name(titel, ersatz='Teil')}{endung.lower()}"


def titelliste(sitzungsordner: str) -> str:
    return f"{sitzungsordner}/{TITELLISTE}"


def wellenform(sitzungsordner: str) -> str:
    return f"{sitzungsordner}/{WELLENFORM}"


def podcastordner(abo: str) -> str:
    return f"{PODCASTS}/{name(abo, ersatz='Unbekannter Podcast')}"


def folge(abo: str, titel: str, veroeffentlicht: str | None, endung: str) -> str:
    datum = (veroeffentlicht or "")[:10]
    datum = datum if re.fullmatch(r"\d{4}-\d{2}-\d{2}", datum) else ""
    stamm = f"{datum} {name(titel, ersatz='Folge')}".strip()
    return f"{podcastordner(abo)}/{stamm}{endung.lower()}"


ZEITANSAGE = "Zeitansage"


def zeitansage(baustein: str) -> str:
    """Ein Baustein der Zeitansage (`es-ist`, `stunde-05`, `minute-34`) als MP3."""
    return f"{ZEITANSAGE}/{baustein}.mp3"
