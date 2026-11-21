"""Feinschnitt einer Aufnahme (RAD-45): aus den Titelwechseln der Sendedaten, der Stille im Ton und den Werbestellen
die Stücke, wie man sie hören will.

Gemessen an Mangoradio (laut.fm, 21.11.2026): der neue Titel kommt in den Sendedaten 0,3 bis 1,5 s NACH dem echten
Wechsel, davor liegt fast immer echte Stille (0,1 bis 5 s); das neue Lied beginnt am Ende dieser Stille. Live teilt der
Aufnehmer beim Eintreffen der Angabe, darum hängt der Anfang des neuen Lieds am alten. Hier rückt jede Grenze an das
Ende der Stille, die dem Wechsel am nächsten liegt (bevorzugt kurz davor). Werbung ist ein Stück, auch wenn sie mehrere
Titel sendet (laut.fm: "o2online.de - Ein bisschen ...", "... zweite Halbzeit ..."); ein Einschub ohne Titel wird ein
eigenes kurzes Stück, damit Lieder sauber bleiben. Jedes Stück heißt nach dem Titel, der den größten Teil seiner Dauer
abdeckt.

Reine Rechnung ohne Ein- und Ausgabe: der Aufnehmer liefert Angaben, Stillen und Werbestellen, das Ergebnis geht als
Schnitt an die Aufnahme (ein Schritt mit Rückgängig).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Art = Literal["titel", "werbung", "einschub"]


@dataclass(frozen=True)
class Regeln:
    #: Stille, deren Ende so weit vor dem Wechsel liegt, kommt in Frage
    vor_s: float = 6.0
    #: ... oder so weit danach
    nach_s: float = 2.0
    #: so viel später als der echte Wechsel kommt die Angabe gewöhnlich (die Stille dort wird bevorzugt)
    verzug_s: float = 0.7
    #: längere Stille zählt mehr: je Sekunde Stille (bis `lange_bis_s`) wiegt sie so viele Sekunden Abstand auf. Eine
    #: echte Pause (ab etwa 0,1 s) schlägt so eine kurze Lücke mitten in Sprache oder Lied, auch wenn die Lücke näher am
    #: erwarteten Verzug liegt (gemessen: PayPal-Spot 29,30 s Lücke 30 ms gegen Pause 120 ms; Mikolas 646,08 gegen 645,25)
    gewicht_je_s: float = 8.0
    lange_bis_s: float = 0.5
    #: geschnitten wird in der Pause, so weit vor ihrem Ende (höchstens in ihrer Mitte): ohne Neukodieren schneidet
    #: FFmpeg an ganzen Rahmen (MP3 26 ms), am Ende der Pause rutschte sonst etwas vom Neuen ins Stück davor
    schnitt_vor_s: float = 0.15
    #: Grenzen, die näher beieinander liegen, sind eine
    naehe_s: float = 0.5
    #: kürzere Stücke gehen im nächsten auf (vor einer Werbung im vorigen)
    kuerzestes_s: float = 1.5
    #: Angaben so nah an einer Werbestelle setzen keine eigene Grenze: dort gilt die Grenze der Werbung (Titel und
    #: Werbung kommen aus derselben Angabe, ihre Grenzen lägen sonst knapp nebeneinander)
    werbung_rand_s: float = 2.0
    #: ein Titel, der zwischen zwei Angaben desselben anderen Titels höchstens so lange steht, ist eingestreut (Muster
    #: A, B, A: SWR3 sendet mitten im Lied den Sendungsnamen) und teilt nicht
    einstreu_hoechstens_s: float = 90.0
    #: so kurz eingestreut zählt immer als Einstreuung (Kontakt, Slogan); länger nur, wenn der Titel in der Aufnahme
    #: mindestens so oft vorkommt wie der, in den er eingestreut ist (ein Lied zwischen zwei Sendungsnamen bleibt)
    einstreu_kurz_s: float = 25.0
    #: ohne Stille: ein Pegeltal so weit vor oder nach der Angabe zählt (überblendende Sender, gemessen bis 4 s danach)
    tal_vor_s: float = 6.0
    tal_nach_s: float = 4.5
    #: so viel tiefer als der Median der Umgebung (30 s) muss das Tal sein (LU)
    tal_tiefe: float = 12.0
    #: der Momentanwert misst die letzten 400 ms: die Mitte des Fensters liegt so weit vor seiner Zeit
    tal_versatz_s: float = 0.2
    #: so viel seiner Dauer muss ein Titel abdecken, damit das Stück sicher nach ihm heißt
    sicher_anteil: float = 2 / 3


@dataclass(frozen=True)
class Angabe:
    """Ein Titelwechsel der Sendedaten an seiner Stelle im Ton."""
    t: float
    titel: str
    gesperrt: bool = False


@dataclass(frozen=True)
class Werbung:
    von: float
    bis: float
    text: str


@dataclass
class Stueck:
    von: float
    bis: float
    name: str
    art: Art = "titel"
    #: deckt der Titel mindestens `sicher_anteil` des Stücks ab
    sicher: bool = True
    quellen: list[str] = field(default_factory=list)

    @property
    def dauer(self) -> float:
        return self.bis - self.von


Pegel = list[tuple[float, float]]
"""Momentanlautheit: (Zeit in Sekunden, LUFS), etwa alle 100 ms"""


def tal(t: float, pegel: Pegel, r: Regeln = Regeln(), nach: float = float("-inf")) -> float | None:
    """Das tiefste Pegeltal um die Angabe bei `t`, wenn es deutlich unter der Umgebung liegt; sonst None."""
    if not pegel:
        return None
    fenster = [(zeit, wert) for zeit, wert in pegel if t - r.tal_vor_s <= zeit <= t + r.tal_nach_s and zeit - r.tal_versatz_s > nach + r.naehe_s]
    umgebung = sorted(wert for zeit, wert in pegel if t - 15 <= zeit <= t + 15)
    if not fenster or not umgebung:
        return None
    zeit, wert = min(fenster, key=lambda p: p[1])
    if wert > umgebung[len(umgebung) // 2] - r.tal_tiefe:
        return None
    return round(zeit - r.tal_versatz_s, 2)


def grenze(t: float, stillen: list[tuple[float, float]], r: Regeln = Regeln(), nach: float = float("-inf"),
           pegel: Pegel | None = None) -> float:
    """Wo der Wechsel zur Angabe bei `t` wirklich liegt: am Ende der passenden Stille; ohne Stille im tiefsten
    Pegeltal, wenn eines deutlich ist (überblendende Sender); sonst bei der Angabe. `nach`: die Grenze des vorigen
    Wechsels; die Stille muss dahinter enden (eine Stille dient nur einem Wechsel: sonst nähme der Titel nach einem
    kurzen Einspieler dieselbe lange Pause wie der Einspieler, Mangoradio 2:25)."""
    kandidaten = [s for s in stillen if t - r.vor_s <= s[1] <= t + r.nach_s and s[1] > nach + r.naehe_s]
    if not kandidaten:
        im_tal = tal(t, pegel or [], r, nach)
        return t if im_tal is None else im_tal
    wert = lambda s: abs(s[1] - (t - r.verzug_s)) - r.gewicht_je_s * min(s[1] - s[0], r.lange_bis_s)
    return min(kandidaten, key=wert)[1]


def schnittstelle(t: float, stillen: list[tuple[float, float]], r: Regeln = Regeln()) -> float:
    """Wo an einem Wechsel bei `t` (Ende einer Pause oder ohne Pause) geschnitten wird: in der Pause davor."""
    for a, b in stillen:
        if abs(b - t) < 1e-6:
            return round(max(a + (b - a) / 2, b - r.schnitt_vor_s), 3)
    return t


def einstreuungen_entfernen(angaben: list[Angabe], r: Regeln = Regeln()) -> list[Angabe]:
    """Muster A, B, A mit eingestreutem B (Sendungsname, Kontakt, Slogan): B gehört zu A, das zweite A ist dieselbe
    Stelle wie das erste. Eingestreut ist B, wenn es kurz steht oder in der Aufnahme mindestens so oft vorkommt wie A
    (SWR3 21.11.2026: der Sendungsname kommt zehnmal, ein Lied zwei- bis dreimal). Wiederholt, bis nichts mehr
    eingestreut ist (A, B, A, B, A wird A)."""
    liste = list(angaben)
    haeufig = {x.titel: sum(1 for y in angaben if y.titel == x.titel) for x in angaben}
    geaendert = True
    while geaendert:
        geaendert = False
        for i in range(1, len(liste) - 1):
            a, b, c = liste[i - 1], liste[i], liste[i + 1]
            dauer = c.t - b.t
            eingestreut = dauer <= r.einstreu_kurz_s or haeufig[b.titel] >= haeufig[a.titel]
            if a.titel == c.titel and b.titel != a.titel and dauer <= r.einstreu_hoechstens_s and eingestreut:
                del liste[i:i + 2]
                geaendert = True
                break
    return liste


def stuecke(dauer: float, angaben: list[Angabe], stillen: list[tuple[float, float]], werbung: list[Werbung],
            r: Regeln = Regeln(), einschub: str = "Einschub", pegel: Pegel | None = None) -> list[Stueck]:
    """Die Stücke einer Aufnahme von 0 bis `dauer` (Sekunden des aufgenommenen Tons)."""
    if dauer <= 0:
        return []
    werbung = sorted((w for w in werbung if w.bis > w.von), key=lambda w: w.von)
    # Grenzen aus Angaben in einer Werbestelle oder an ihrem Rand fallen weg: die Werbestelle hat dort ihre eigene
    in_werbung = lambda t: any(w.von - r.werbung_rand_s <= t <= w.bis + r.werbung_rand_s for w in werbung)
    gueltig = einstreuungen_entfernen(sorted((a for a in angaben if not a.gesperrt), key=lambda a: a.t), r)

    # Titel mit ihren Abschnitten: von ihrer Grenze bis zur Grenze des nächsten
    grenzen_t: list[float] = []
    for a in gueltig:
        grenzen_t.append(grenze(a.t, stillen, r, grenzen_t[-1] if grenzen_t else float("-inf"), pegel))
    abschnitte = [(g, grenzen_t[i + 1] if i + 1 < len(gueltig) else dauer, a.titel) for i, (g, a) in enumerate(zip(grenzen_t, gueltig))]

    punkte = {0.0, dauer}
    punkte |= {g for g in grenzen_t if 0 < g < dauer and not in_werbung(g)}
    punkte |= {min(max(w.von, 0.0), dauer) for w in werbung} | {min(max(w.bis, 0.0), dauer) for w in werbung}
    sortiert: list[float] = []
    for p in sorted(punkte):
        if not sortiert or p - sortiert[-1] >= r.naehe_s:
            sortiert.append(p)
        elif p == dauer:
            sortiert[-1] = dauer
    if sortiert[0] != 0.0:
        sortiert.insert(0, 0.0)

    ergebnis: list[Stueck] = []
    for von, bis in zip(sortiert, sortiert[1:]):
        ergebnis.append(_benennen(von, bis, abschnitte, werbung, r, einschub))
    ergebnis = _kurze_zusammenlegen(ergebnis, r)
    # geschnitten wird in der Pause vor jedem Wechsel, nicht genau an ihrem Ende
    for vorher, nachher in zip(ergebnis, ergebnis[1:]):
        vorher.bis = nachher.von = schnittstelle(nachher.von, stillen, r)
    return ergebnis


def _benennen(von: float, bis: float, abschnitte: list[tuple[float, float, str]], werbung: list[Werbung], r: Regeln,
              einschub: str) -> Stueck:
    laenge = bis - von
    ueber = lambda a, b: max(0.0, min(b, bis) - max(a, von))
    w = max(werbung, key=lambda x: ueber(x.von, x.bis), default=None)
    if w is not None and ueber(w.von, w.bis) >= laenge / 2:
        return Stueck(von, bis, f"Werbung: {w.text}" if w.text else "Werbung", "werbung", True, ["werbung"])
    anteile: dict[str, float] = {}
    for a, b, titel in abschnitte:
        anteile[titel] = anteile.get(titel, 0.0) + ueber(a, b)
    if not anteile or max(anteile.values()) <= 0:
        return Stueck(von, bis, einschub, "einschub", False, [])
    titel, anteil = max(anteile.items(), key=lambda x: x[1])
    if not titel.strip():
        return Stueck(von, bis, einschub, "einschub", anteil >= r.sicher_anteil * laenge, ["leer"])
    return Stueck(von, bis, titel, "titel", anteil >= r.sicher_anteil * laenge, ["sendedaten"])


def _kurze_zusammenlegen(liste: list[Stueck], r: Regeln) -> list[Stueck]:
    """Splitter unter `kuerzestes_s` gehen im nächsten Stück auf (zwei kurz aufeinanderfolgende Angaben: die spätere
    berichtigt die frühere), am Ende im vorigen; Werbung bleibt für sich."""
    ergebnis: list[Stueck] = []
    vorrat: Stueck | None = None            # Splitter, der auf das nächste Stück wartet
    for s in liste:
        if vorrat is not None and s.art != "werbung":
            s.von = vorrat.von
            vorrat = None
        elif vorrat is not None:            # vor einer Werbung: ins vorige Stück
            if ergebnis and ergebnis[-1].art != "werbung":
                ergebnis[-1].bis = vorrat.bis
            else:
                ergebnis.append(vorrat)
            vorrat = None
        if s.dauer < r.kuerzestes_s and s.art != "werbung":
            vorrat = s
            continue
        ergebnis.append(s)
    if vorrat is not None:
        if ergebnis and ergebnis[-1].art != "werbung":
            ergebnis[-1].bis = vorrat.bis
        else:
            ergebnis.append(vorrat)
    return ergebnis
