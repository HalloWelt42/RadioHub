"""Ordnerstruktur in der Ablage, die einzige Stelle für Ordner- und Dateinamen.

    Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/001 <Titel>.mp3      eine Aufnahme mit ihren Stücken
    Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/Titelliste.json      Titelwechsel und Ereignisse der Aufnahme
    Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/Wellenform.peaks     Wellenform für den Schnitt (entsteht bei Bedarf)
    Aufnahmen/<Ordner>/<Sender>/<JJJJ-MM-TT HH-MM-SS>/...         eine Aufnahme in einem eigenen Aufnahmeordner
    Podcasts/<Abo>/<JJJJ-MM-TT> <Folge>.mp3                       eine heruntergeladene Folge
    Mitlesen/<Sender>/<JJJJ-MM-TT HH-MM-SS>.mp3                   Ton eines Mitlesens, daneben seine Begleiter
                                                                  .sprache.mp3 (Übersetzung) und .transkript.json
    Zeitansage/<Stimme>/es-ist.mp3, stunde-05.mp3, minute-34.mp3  Bausteine der Zeitansage, je Stimme ein Ordner
"""

from __future__ import annotations

import re
from datetime import datetime

AUFNAHMEN = "Aufnahmen"
PODCASTS = "Podcasts"
BEREICHE = (AUFNAHMEN, PODCASTS)   # was Explorer und Wiedergabe zeigen dürfen (nicht etwa die Bausteine der Zeitansage)
TITELLISTE = "Titelliste.json"
#: Analyse der Aufnahme für den Feinschnitt (Wechsel, Stillen, Pegel, Werbung; RAD-45)
ANALYSE = "Analyse.json"
WELLENFORM = "Wellenform.peaks"

_UNERLAUBT = re.compile(r'[/\\:*?"<>|\x00-\x1f]+')


def im_bereich(pfad: str) -> str:
    """Pfad unter Aufnahmen oder Podcasts ohne leere Teile; ValueError bei "." oder ".." und außerhalb der Bereiche."""
    teile = [t for t in str(pfad).replace("\\", "/").split("/") if t]
    if not teile or teile[0] not in BEREICHE or any(t in (".", "..") for t in teile):
        raise ValueError(f"Pfad außerhalb der Aufnahmen und Podcasts: {pfad!r}")
    return "/".join(teile)


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


def analyse(sitzungsordner: str, abschnitt: int = 0) -> str:
    """Analyse der Aufnahme; lange Aufnahmen haben eine je Abschnitt (RAD-139)."""
    return f"{sitzungsordner}/{ANALYSE if not abschnitt else f'Analyse {abschnitt:04d}.json'}"


def ist_analyse(dateiname: str) -> bool:
    return dateiname.startswith("Analyse") and dateiname.endswith(".json")


def wellenform(sitzungsordner: str) -> str:
    return f"{sitzungsordner}/{WELLENFORM}"


def podcastordner(abo: str) -> str:
    return f"{PODCASTS}/{name(abo, ersatz='Unbekannter Podcast')}"


def folge(abo: str, titel: str, veroeffentlicht: str | None, endung: str) -> str:
    datum = (veroeffentlicht or "")[:10]
    datum = datum if re.fullmatch(r"\d{4}-\d{2}-\d{2}", datum) else ""
    stamm = f"{datum} {name(titel, ersatz='Folge')}".strip()
    return f"{podcastordner(abo)}/{stamm}{endung.lower()}"


MITLESEN = "Mitlesen"


def mitlesung(sender: str, beginn: datetime | str | None, endung: str) -> str:
    """Der Ton eines Mitlesens (RAD-131); seine Begleiter heißen wie er."""
    return f"{MITLESEN}/{name(sender, ersatz='Unbekannter Sender')}/{zeitpunkt(beginn)}{endung.lower()}"


ZEITANSAGE = "Zeitansage"


def zeitansage_ordner(stimme: str) -> str:
    """Die Bausteine einer Stimme (`katalog:sohee` oder die Kennung einer privaten Stimme): jede Stimme spricht ihren
    eigenen Satz, ein Wechsel der Stimme vermischt nichts."""
    return f"{ZEITANSAGE}/{re.sub(r'[^A-Za-z0-9_-]', '-', stimme)}"


def zeitansage(stimme: str, baustein: str) -> str:
    """Ein Baustein der Zeitansage (`es-ist`, `stunde-05`, `minute-34`) einer Stimme als MP3."""
    return f"{zeitansage_ordner(stimme)}/{baustein}.mp3"
