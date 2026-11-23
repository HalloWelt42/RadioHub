"""Modelle der Senderquelle (RAD-7): Regeln, Abfrage, Facetten, ausgeblendete Sender. Sie sind die Schnittstelle unter
/api/radio und die Vorlage der Typen der Oberfläche (frontend/src/lib/radio/typen.ts)."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator

from ...senderdaten import Qualitaet

RegelArt = Literal["sprache", "genre", "tag", "stimmen", "werbung", "bewertung", "einzeln", "altsperren"]
Herkunft = Literal["nutzer", "ueberfuehrt", "bestand"]
WerbeStufe = Literal["eigene", "hoch", "mittel", "verdacht"]
Sortierung = Literal["stimmen", "name", "qualitaet", "bitrate"]

# Stufe des Werbeverdachts je Sender (sender_index.werbe_stufe); eine Regel blendet ab ihrer Stufe aus
WERBE_STUFEN: dict[str, int] = {"keine": 0, "verdacht": 1, "mittel": 2, "hoch": 3, "eigene": 4}

# Eigene Bewertungen (Tabelle station_tags, Quelle user): Sterne als "sterne:<n>", Markierungen mit ihrem Schlüssel
BEWERTUNGEN: dict[str, str] = {
    "sterne:3": "Sehr gut", "sterne:2": "Gut", "sterne:1": "Geht so", "werbung": "Werbung",
    "religioes": "Religiös", "politisch_extrem": "Politisch extrem", "populistisch": "Populistisch",
    "nicht_jugendfrei": "Nicht jugendfrei", "schlechte_qualitaet": "Schlechte Qualität",
    "schwankende_qualitaet": "Schwankende Qualität", "haeufig_offline": "Häufig nicht erreichbar",
    "hoher_sprachanteil": "Hoher Sprachanteil",
}
Bewertung = Annotated[str, Field(pattern=r"^(sterne:[123]|[a-z_]{3,40})$")]
Kennung = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[\w-]+$")]
Land = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
Kurztext = Annotated[str, Field(min_length=1, max_length=120)]


def _bewertungen_pruefen(werte: list[str]) -> list[str]:
    unbekannt = [w for w in werte if w not in BEWERTUNGEN]
    if unbekannt:
        raise ValueError(f"Unbekannte Bewertung: {', '.join(unbekannt)}")
    return werte


# ----- Regeln ----------------------------------------------------------------------------------------------------------

class SpracheEntwurf(BaseModel):
    """Sprache: `schluessel` sind Codes ("ru") oder freie Einträge ("frei:asunción") wie in der Kandidatenliste; sie
    treffen jede Schreibweise der Sprache. `eintraege` treffen genau den Eintrag des Verzeichnisses (so überführt die
    frühere Sprachliste ohne Unterschied). Sender ohne Sprachangabe bleiben sichtbar."""

    art: Literal["sprache"] = "sprache"
    schluessel: list[Kurztext] = Field(default_factory=list, max_length=100)
    eintraege: list[Kurztext] = Field(default_factory=list, max_length=2000)

    @field_validator("eintraege", "schluessel")
    @classmethod
    def _klein(cls, werte: list[str]) -> list[str]:
        return sorted({w.strip().lower() for w in werte if w.strip()})


class GenreEntwurf(BaseModel):
    """Genre aus der gepflegten Tabelle: trifft alle Schreibweisen."""

    art: Literal["genre"] = "genre"
    genres: list[Kurztext] = Field(min_length=1, max_length=50)


class TagEntwurf(BaseModel):
    """Tag des Verzeichnisses, genau (klein, ohne Rand)."""

    art: Literal["tag"] = "tag"
    tags: list[Kurztext] = Field(min_length=1, max_length=500)

    @field_validator("tags")
    @classmethod
    def _klein(cls, werte: list[str]) -> list[str]:
        return sorted({" ".join(w.strip().lower().lstrip("#").split()) for w in werte if w.strip()})


class StimmenEntwurf(BaseModel):
    """Sender mit weniger Stimmen als `mindeststimmen` (gilt auch für neue Sender)."""

    art: Literal["stimmen"] = "stimmen"
    mindeststimmen: int = Field(ge=1, le=1_000_000)


class WerbungEntwurf(BaseModel):
    """Werbung ab einer Stufe: eigene (nur eigene Entscheidungen), hoch (dazu eigene Markierungen und starke Zeichen),
    mittel, verdacht (jeder Verdacht; der Cache-Kopf allein zählt nicht)."""

    art: Literal["werbung"] = "werbung"
    stufe: WerbeStufe


class BewertungEntwurf(BaseModel):
    """Eigene Bewertungen (Sterne oder Markierungen)."""

    art: Literal["bewertung"] = "bewertung"
    bewertungen: list[Bewertung] = Field(min_length=1, max_length=20)

    @field_validator("bewertungen")
    @classmethod
    def _bekannt(cls, werte: list[str]) -> list[str]:
        return _bewertungen_pruefen(werte)


RegelEntwurf = Annotated[Union[SpracheEntwurf, GenreEntwurf, TagEntwurf, StimmenEntwurf, WerbungEntwurf, BewertungEntwurf],
                         Field(discriminator="art")]


class Regel(BaseModel):
    """Eine lebende Ausschlussregel mit ihren Zahlen (ohne verschwundene Sender). `nur_diese`: Sender, die allein diese
    Regel ausblendet (so viele werden sichtbar, wenn sie aus ist oder entfernt wird; Favoriten und Freigaben sind
    ohnehin sichtbar)."""

    id: str
    art: RegelArt
    an: bool
    herkunft: Herkunft
    titel: str
    erklaerung: str
    entwurf: RegelEntwurf | None = None        # None bei Einzelsperren und Altbestand
    betroffen: int = 0
    favoriten: int = 0
    nur_diese: int = 0
    angelegt_am: str
    geaendert_am: str


class Bestand(BaseModel):
    gesamt: int
    sichtbar: int
    ausgeblendet: int
    verschwunden: int
    favoriten: int
    ausnahmen: int          # sichtbar, obwohl eine Regel trifft (Favoriten, Freigaben)


class Regeluebersicht(BaseModel):
    bestand: Bestand
    regeln: list[Regel]


class SenderKurz(BaseModel):
    uuid: str
    name: str
    land: str
    stimmen: int
    logo: str = ""


class RegelVorschau(BaseModel):
    """Was eine neue Regel bewirken würde, bevor etwas geschieht."""

    titel: str
    betroffen: int               # trifft so viele Sender
    neu_ausgeblendet: int        # davon heute sichtbar und danach nicht
    favoriten: int               # davon Favoriten (bleiben als Ausnahme sichtbar)
    favoriten_namen: list[str]
    beispiele: list[SenderKurz]
    gleiche_regel: str | None = None   # Kennung einer bestehenden Regel mit demselben Inhalt


class RegelFolgen(BaseModel):
    """Folgen, wenn eine Regel ausgeschaltet oder entfernt wird."""

    regel: Regel
    wieder_sichtbar: int
    beispiele: list[SenderKurz]


class RegelAenderung(BaseModel):
    """Ergebnis einer Änderung (für Band und Rückgängig)."""

    regel: Regel | None
    bestand: Bestand
    ausgeblendet: int = 0          # durch diese Änderung neu ausgeblendet
    wieder_sichtbar: int = 0       # durch diese Änderung wieder sichtbar


class RegelSchalten(BaseModel):
    an: bool


class Kandidat(BaseModel):
    """Ein möglicher Wert für eine neue Regel mit seinen Zahlen."""

    schluessel: str
    name: str
    code: str | None = None
    anzahl: int
    favoriten: int


# ----- Abfrage ---------------------------------------------------------------------------------------------------------

class StationQuery(BaseModel):
    """Schnellfilter der Senderliste (Entscheidung 4, Vorgaben 1 bis 3). Alle Filter wirken zusammen, auch "nur
    Favoriten". Seiten über den Zeiger `nach` aus der vorigen Antwort (Sortierwert und uuid)."""

    suche: str = Field("", max_length=100)
    laender: list[Land] = Field(default_factory=list, max_length=60)
    genres: list[Kurztext] = Field(default_factory=list, max_length=60)
    qualitaet: list[Qualitaet] = Field(default_factory=list, max_length=5)
    codecs: list[Annotated[str, Field(max_length=20)]] = Field(default_factory=list, max_length=12)
    bitrate_min: int | None = Field(None, ge=0, le=10_000)
    bitrate_max: int | None = Field(None, ge=0, le=10_000)
    stimmen_min: int | None = Field(None, ge=0, le=10_000_000)
    stimmen_max: int | None = Field(None, ge=0, le=10_000_000)
    bewertungen: list[Bewertung] = Field(default_factory=list, max_length=20)
    kategorien: list[int] = Field(default_factory=list, max_length=60)
    nur_favoriten: bool = False
    nur_erreichbar: bool = True            # ohne Sender, die die letzte Prüfung des Verzeichnisses nicht bestanden
    #                                        (Favoriten bleiben)
    sortierung: Sortierung = "stimmen"
    umgekehrt: bool = False                # die Reihenfolge der Sortierung von hinten
    varianten_buendeln: bool = True
    nach: str | None = Field(None, max_length=600)
    anzahl: int = Field(50, ge=1, le=200)
    mit_facetten: bool | None = None       # ohne Angabe: nur auf der ersten Seite

    @field_validator("bewertungen")
    @classmethod
    def _bekannt(cls, werte: list[str]) -> list[str]:
        return _bewertungen_pruefen(werte)


class SpracheKurz(BaseModel):
    schluessel: str
    name: str


class Werbestatus(BaseModel):
    stufe: Literal["keine", "verdacht", "mittel", "hoch", "eigene"]
    entscheidung: Literal["gesperrt", "erlaubt"] | None = None


class Grund(BaseModel):
    """Warum ein Sender ausgeblendet ist (oder wäre): eine Regel mit ihrem Titel."""

    regel: str
    art: RegelArt
    titel: str


class SenderEintrag(BaseModel):
    """Ein Sender der Liste mit allem, was die Zeile braucht, in einer Antwort."""

    uuid: str
    name: str
    logo: str
    homepage: str
    land: str
    land_name: str
    region: str
    bundesland: str
    sprachen: list[SpracheKurz]
    genres: list[str]
    codec: str
    kbps: int | None
    kbps_gemessen: bool
    qualitaet: Qualitaet
    stimmen: int
    erreichbar: bool
    hls: bool
    gruppe: str
    varianten: int
    favorit: bool
    ausnahme: list[Grund]                 # sichtbar trotz dieser Regeln (Favorit oder Freigabe)
    verschwunden: bool
    kategorien: list[int]
    bewertungen: list[str]
    werbung: Werbestatus
    eigene_adresse: str | None = None
    # Stream-Adressen aus dem Verzeichnis: die Zeile spielt ohne weitere Abfrage, auch Vor und Zurück über die Liste
    adresse: str = ""
    adresse_aufgeloest: str = ""


class Facette(BaseModel):
    wert: str
    name: str
    anzahl: int


class Facetten(BaseModel):
    """Zahlen unter den aktiven Regeln und den übrigen Filtern (je Gruppe ohne ihren eigenen Filter). Länder nur die
    der Seitenleiste (Einstellung) und die gewählten."""

    laender: list[Facette]
    genres: list[Facette]
    qualitaet: list[Facette]
    codecs: list[Facette]
    bewertungen: list[Facette]
    kategorien: list[Facette]


class Abfrageergebnis(BaseModel):
    gesamt: int | None             # Treffer insgesamt (nur auf der ersten Seite)
    eintraege: list[SenderEintrag]
    weiter: str | None             # Zeiger der nächsten Seite; None: keine weitere
    facetten: Facetten | None


# ----- Ausgeblendete Sender ---------------------------------------------------------------------------------------------

class AusgeblendetAnfrage(BaseModel):
    suche: str = Field("", max_length=100)
    regel: str | None = Field(None, max_length=64)
    seite: int = Field(0, ge=0, le=100_000)
    anzahl: int = Field(25, ge=1, le=100)


class AusgeblendeterSender(BaseModel):
    uuid: str
    name: str
    land: str
    stimmen: int
    logo: str
    gruende: list[Grund]


class GrundZahl(BaseModel):
    regel: str
    titel: str
    anzahl: int


class AusgeblendetSeite(BaseModel):
    gesamt: int
    seite: int
    seiten: int
    eintraege: list[AusgeblendeterSender]
    gruende: list[GrundZahl]


class Sichtbarkeit(BaseModel):
    """Warum ein Sender sichtbar ist oder nicht."""

    uuid: str
    sichtbar: bool
    verschwunden: bool
    favorit: bool
    freigegeben: bool
    gesperrt: bool                 # Einzelsperre
    gruende: list[Grund]           # aktive Regeln, die ihn treffen


class SenderAnfrage(BaseModel):
    uuid: Kennung


class Abgleichstand(BaseModel):
    zuletzt: str | None            # Ende des letzten vollständigen Abgleichs
    uhrzeit: str                   # Einstellung abgleich_uhrzeit
    auftrag: str | None            # Kennung eines offenen Abgleichs
