"""
RadioHub v0.8.0 - Zeitansage

Bausteine der Zeitansage ("Es ist", "fünf Uhr", "vierunddreißig"), einmal gesprochen von der hauseigenen Vertonung
mit der Zeit-Stimme und als MP3 in der Ablage unter Zeitansage/. Das Telefon setzt sie zusammen ("Es ist fünf Uhr
vierunddreißig", zur vollen Stunde ohne Minuten); so reichen 84 kurze Dateien statt einer je Minute.

Einstellungen (einstellungen.AppEinstellungen, in der Umgebung wie früher):
    vertonung_adresse   RADIOHUB_VERTONUNG_ADRESSE, Adresse der Vertonung, etwa https://<rechner>:8641
    zeitstimme          RADIOHUB_ZEITSTIMME, Kennung der Zeit-Stimme (Klonstimme der Vertonung; dort für die App RadioHub
                        unter "Private Stimmen für" freigeben)
    zeitstimme_tempo    RADIOHUB_ZEITSTIMME_TEMPO, Sprechtempo, Vorgabe 1.0
Angemeldet wird mit dem App-Schlüssel der Kellerwolke (Verbund der Apps), geprüft mit derselben Zertifikatsstelle.
"""
from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..einstellungen import stand as einstellungen_stand
from ..ablage import ablage, orte
from ..ablage.kellerwolke import tls_pruefung
from ..einstellungen import AppEinstellungen

_EINER = ["", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun"]
_ZEHN_BIS_NEUNZEHN = ["zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn",
                      "neunzehn"]
_ZEHNER = {2: "zwanzig", 3: "dreißig", 4: "vierzig", 5: "fünfzig"}


def zahlwort(n: int) -> str:
    """0 bis 59 als Zahlwort, wie man eine Uhrzeit spricht (1 = "eins", 21 = "einundzwanzig")."""
    if n == 0:
        return "null"
    if n < 10:
        return _EINER[n]
    if n < 20:
        return _ZEHN_BIS_NEUNZEHN[n - 10]
    zehner, einer = divmod(n, 10)
    if not einer:
        return _ZEHNER[zehner]
    return f"{'ein' if einer == 1 else _EINER[einer]}und{_ZEHNER[zehner]}"


def stunde_text(h: int) -> str:
    """"null Uhr", "ein Uhr", "zwei Uhr" ... "dreiundzwanzig Uhr"."""
    return f"{'ein' if h == 1 else zahlwort(h)} Uhr"


def bausteine() -> dict[str, str]:
    """Name des Bausteins -> gesprochener Text; die eine Liste für Erzeugen, Ausliefern und Telefon."""
    liste = {"es-ist": "Es ist"}
    liste.update({f"stunde-{h:02d}": stunde_text(h) for h in range(24)})
    liste.update({f"minute-{m:02d}": zahlwort(m) for m in range(1, 60)})
    return liste


def ansage(h: int, m: int) -> list[str]:
    """Bausteine einer Uhrzeit in Reihenfolge (zur vollen Stunde ohne Minuten)."""
    return ["es-ist", f"stunde-{h:02d}"] + ([f"minute-{m:02d}"] if m else [])


@dataclass
class ZeitansageEinstellungen:
    adresse: str = ""
    stimme: str = ""
    tempo: float = 1.0
    schluessel: str = ""        # App-Schlüssel der Kellerwolke, der Zugang zur Vertonung
    ca_datei: str = ""

    @property
    def eingerichtet(self) -> bool:
        return bool(self.adresse and self.stimme and self.schluessel)

    @classmethod
    def aus(cls, stand: AppEinstellungen) -> ZeitansageEinstellungen:
        return cls(adresse=stand.vertonung_adresse.strip().rstrip("/"), stimme=stand.zeitstimme.strip(),
                   tempo=stand.zeitstimme_tempo, schluessel=stand.kellerwolke_schluessel.get_secret_value().strip(),
                   ca_datei=stand.ca_datei.strip())


async def _kuerzen(wav: bytes) -> bytes:
    """Stille am Anfang und Ende weg, MP3 mono: die Bausteine schließen dann ohne Lücke aneinander an."""
    with tempfile.TemporaryDirectory() as ordner:
        ein, aus = Path(ordner) / "ein.wav", Path(ordner) / "aus.mp3"
        ein.write_bytes(wav)
        stille = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-v", "error", "-i", str(ein), "-af", f"{stille},areverse,{stille},areverse",
            "-ac", "1", "-c:a", "libmp3lame", "-b:a", "96k", str(aus),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, fehler = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg: {fehler.decode('utf-8', 'replace')[-200:]}")
        return aus.read_bytes()


class Zeitansage:
    def __init__(self) -> None:
        self.laeuft = False
        self.meldung = ""

    async def stand(self) -> dict:
        namen = list(bausteine())
        vorhanden = {e.name.removesuffix(".mp3") for e in await ablage().liste(orte.ZEITANSAGE)}
        return {"bausteine": namen, "fehlend": [n for n in namen if n not in vorhanden],
                "erzeugung": {"laeuft": self.laeuft, "meldung": self.meldung}}

    async def erzeugen(self, einstellungen: ZeitansageEinstellungen | None = None,
                       transport: httpx.AsyncBaseTransport | None = None) -> int:
        """Fehlende Bausteine sprechen lassen und ablegen; liefert die Zahl der neuen. Nur ein Lauf zugleich."""
        if self.laeuft:
            return 0
        e = einstellungen or ZeitansageEinstellungen.aus(einstellungen_stand())
        if not e.eingerichtet:
            self.meldung = ("Zeitansage nicht eingerichtet: Vertonung und Zeit-Stimme in den Einstellungen "
                            "(RADIOHUB_VERTONUNG_ADRESSE, RADIOHUB_ZEITSTIMME) und die Kellerwolke")
            return 0
        self.laeuft, neu = True, 0
        try:
            texte = bausteine()
            fehlend = (await self.stand())["fehlend"]
            schluessel = e.schluessel
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0), transport=transport,
                                         verify=tls_pruefung(e.ca_datei)) as client:
                for i, name in enumerate(fehlend, 1):
                    self.meldung = f"Spreche {name} ({i} von {len(fehlend)})"
                    antwort = await client.post(f"{e.adresse}/api/v1/sprechen", headers={"Authorization": f"Bearer {schluessel}"},
                                                json={"text": texte[name], "stimme": {"art": "klon", "knoten_id": e.stimme},
                                                      "sprache": "de", "tempo": e.tempo, "ausschreiben": False})
                    if antwort.status_code != 200:
                        hinweis = " (Stimme für RadioHub freigeben: Vertonung, Private Stimmen für)" \
                            if antwort.status_code in (403, 404) else ""
                        raise RuntimeError(f"Vertonung antwortet {antwort.status_code}{hinweis}: {antwort.text[:200]}")
                    await ablage().schreiben(orte.zeitansage(name), await _kuerzen(antwort.content))
                    neu += 1
            self.meldung = f"Fertig: {neu} Bausteine erzeugt"
        except Exception as f:  # Meldung für die Oberfläche; ein neuer Lauf macht den Rest
            self.meldung = f"Abgebrochen nach {neu} Bausteinen: {f}"
        finally:
            self.laeuft = False
        return neu


zeitansage = Zeitansage()
