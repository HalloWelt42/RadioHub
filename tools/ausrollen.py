"""Ausrollen von RadioHub auf den Pi, vom Mac aus über tools/ausrollen.sh. Ablauf und Bausteine wie im Appkern
(appkern.werkzeuge.ausrollen: Ziel, Zertifikat, Stand holen, Bauen, Zugänge, Aufräumen); eigen sind nur die Teile, die
am Aufbau des Radios hängen (Daten in data/ mit radiohub.db und dem Gerüst in data/appkern, laufende Aufnahmen statt
Aufträgen). Bricht beim ersten Fehler ab:

1. Stand und Tests am Mac: Oberfläche und Backend am selben veröffentlichten Commit des Appkerns (nicht aus
   frontend/vendor), sauberer Baum, gepusht, harte Architekturregeln über das ganze Repo, Tests des Backends, Tests,
   Typen (svelte-check) und Bau der Oberfläche; entschieden wird am Rückgabewert, nie an der Ausgabe
2. Pi: Docker Compose und das gemeinsame Netz haus; liegt RadioHub noch im Ordner vor dem Umzug, Abbruch mit Verweis
   auf tools/umzug-mnt-data.sh
3. Zertifikat der Hausstelle für den Vorschaltdienst (noch mindestens 60 Tage gültig, sonst neu)
4. Stand holen, Abbilder bauen (der alte Stand läuft weiter)
5. keine laufende Aufnahme abschießen: warten, bis keine läuft (--sofort überspringt das)
6. beide Datenbanken sichern nach der Regel des Appkerns (appkern.sicherung im eben gebauten Abbild: nur, wenn die
   jüngste älter als 24 Stunden ist und sich etwas geändert hat; höchstens drei bleiben): radiohub.db nach sicherungen/,
   die des Gerüsts nach sicherungen/appkern/
7. Zugänge ([zugaenge]): Adresse und App-Schlüssel der Kellerwolke als feste Einstellungen in die .env, solange sie dort
   fehlen (appkern.werkzeuge.ausrollen.zugaenge_besorgen)
8. neu starten (die Container von vor RAD-6 gehen als verwaiste mit), der Vorschaltdienst jedes Mal (geänderte
   eingehängte Dateien bemerkt Docker nicht)
9. über HTTPS: Server (/health, /api/v1/app) und ausgelieferte Oberfläche (Meta app-fassung) melden die Fassung aus
   version.json, die Seite kommt über HTTP/2, Symbole und Manifest antworten richtig, Startbildschirm-Symbole deckend
10. nur nach Erfolg: verwaiste Abbilder und Baucache auf dem Pi aufräumen

    python tools/ausrollen.py --ergaenzung DATEI [--sofort]
    python tools/ausrollen.py --nur-tests          nur Schritt 1 ohne Git-Prüfung (Regeln, Tests, Bau)
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

from pydantic import BaseModel

from appkern.werkzeuge.ausrollen import (DECKEND, SYMBOLE, ZIEL_DATEI, Abbruch, Ziel, _curl, _deckend, _lauf, _schritt,
                                         _ssh, aufraeumen, bauen, fehlerzeilen, laden, pi_pruefen, stand_holen,
                                         testprotokoll, zertifikat, zugaenge_besorgen)
from appkern.werkzeuge.regeln import regeln_pruefen

WURZEL = Path(__file__).resolve().parents[1]
SICHERUNGEN = "sicherungen"
IM_ABBILD = "/sicherung"
RUHE_HOECHSTENS_S = 4 * 3600
UMZUG_FERTIG = ".umzug-fertig"   # Merkzeichen von tools/umzug-mnt-data.sh im neuen Ordner


class Radio(BaseModel):
    """Angaben unter [radio] in deploy/ausrollen.toml."""

    app: str                   # Dienst der App in compose.pi.yml (dort läuft die Sicherung)
    datenbank: str             # Datenbank des Radios relativ zum Ordner der App
    geruest: str               # Datenbank des Gerüsts (Einstellungen, Protokoll, Aufträge) relativ zum Ordner der App
    einrichtungscode: str      # Datei des Einrichtungscodes relativ zum Ordner der App
    umzug_von: str | None = None   # Ordner vor dem Umzug (Entscheidung 21)


def radio_angaben(wurzel: Path = WURZEL) -> Radio:
    return Radio.model_validate(tomllib.loads((wurzel / ZIEL_DATEI).read_text(encoding="utf-8"))["radio"])


# ----- 1. Stand und Tests ----------------------------------------------------------------------------------------------

FARBE = re.compile(r"\x1b\[[0-9;]*m")
ERGEBNISSE = (re.compile(r"\b(passed|failed)\b"), re.compile(r"\bbuilt in\b"))


def zusammenfassung(ausgabe: str) -> str:
    """Die Zeile mit dem Ergebnis eines Laufs (pytest, vitest, vite build), sonst die letzte."""
    zeilen = [z.strip() for z in FARBE.sub("", ausgabe).splitlines() if z.strip()]
    for muster in ERGEBNISSE:
        treffer = next((z for z in reversed(zeilen) if muster.search(z)), None)
        if treffer:
            return treffer[:160]
    return zeilen[-1][:160] if zeilen else ""


def _pruefen_lassen(titel: str, befehl: list[str], ort: Path) -> None:
    lauf = subprocess.run(befehl, cwd=ort, capture_output=True, text=True)
    ausgabe = lauf.stdout + lauf.stderr
    print(f"{titel}: {zusammenfassung(ausgabe)}")
    if lauf.returncode != 0:
        print(fehlerzeilen(lauf.stdout))
        raise Abbruch(f"{titel} nicht grün (ganze Ausgabe: {testprotokoll(f'radiohub-{titel.lower()}', ausgabe)})")


def tests(wurzel: Path = WURZEL) -> None:
    """Alle Prüfungen, die am Mac laufen; jede entscheidet über ihren Rückgabewert."""
    befunde = regeln_pruefen([wurzel / n for n in _lauf(["git", "ls-files"], ort=wurzel).splitlines()], wurzel)
    if befunde:
        print("\n".join(str(b) for b in befunde[:20]))
        raise Abbruch(f"{len(befunde)} Befunde der Architekturregeln (python -m appkern.werkzeuge regeln)")
    print("Architekturregeln eingehalten")
    backend, oberflaeche = wurzel / "backend", wurzel / "frontend"
    _pruefen_lassen("Backend", [".venv/bin/python", "-m", "pytest", "--tb=short"], backend)   # -q steht in pytest.ini
    _pruefen_lassen("Oberflaeche", ["npx", "vitest", "run"], oberflaeche)
    _pruefen_lassen("Typen", ["npm", "run", "check"], oberflaeche)
    _pruefen_lassen("Bau", ["npm", "run", "build"], oberflaeche)


def appkern_gebunden(wurzel: Path = WURZEL) -> None:
    """Oberfläche und Backend nutzen den Appkern vom selben veröffentlichten Commit (Lehre 5 des Appkerns). Solange die
    Oberfläche ihn aus frontend/vendor nimmt (Fassung vor der Veröffentlichung), rollt nichts aus."""
    paket = json.loads((wurzel / "frontend" / "package.json").read_text())["dependencies"]["appkern-oberflaeche"]
    if paket.startswith("file:"):
        raise Abbruch(f"Oberfläche des Appkerns noch aus {paket[5:]}: Appkern veröffentlichen, in frontend/package.json "
                      "github:HalloWelt42/appkern#<commit> eintragen (derselbe wie in backend/requirements.txt), vendor löschen")
    vorne = re.search(r"#([0-9a-f]{7,40})$", paket)
    hinten = re.search(r"appkern/archive/([0-9a-f]{7,40})\.tar\.gz", (wurzel / "backend" / "requirements.txt").read_text())
    if not vorne or not hinten or not hinten.group(1).startswith(vorne.group(1)):
        raise Abbruch(f"Appkern nicht an einen Commit gebunden: Oberfläche {paket}, Backend {hinten.group(1) if hinten else '?'}")


def stand_und_tests(z: Ziel, wurzel: Path = WURZEL) -> None:
    _schritt("Stand und Tests")
    appkern_gebunden(wurzel)
    if _lauf(["git", "status", "--porcelain"], ort=wurzel):
        raise Abbruch("Erst committen.")
    _lauf(["git", "fetch", "-q", "origin"], ort=wurzel)
    if _lauf(["git", "rev-parse", "HEAD"], ort=wurzel) != _lauf(["git", "rev-parse", f"origin/{z.zweig}"], ort=wurzel):
        raise Abbruch(f"Erst pushen ({z.zweig} ist nicht auf origin).")
    tests(wurzel)


# ----- 2. Pi und Ordner ------------------------------------------------------------------------------------------------

def ordner_pruefen(z: Ziel, r: Radio) -> None:
    """Das Netz haus braucht die Ortssuche; liegt RadioHub noch im alten Ordner (kein Merkzeichen eines fertigen Umzugs im
    neuen), zuerst umziehen: nie stillschweigend einen zweiten, leeren oder halb kopierten Betrieb daneben aufbauen."""
    _schritt("Ordner")
    print(_ssh(z, "docker network inspect haus >/dev/null 2>&1 || { echo 'Das Netz haus fehlt (docker network create haus,"
                  " Handbuch: Grundlage Pi)'; exit 1; }; echo 'Netz haus vorhanden'"))
    w = shlex.quote(z.wurzel)
    if r.umzug_von:
        alt = shlex.quote(r.umzug_von)
        stand = _ssh(z, f"if [ -f {w}/{UMZUG_FERTIG} ]; then echo neu; elif [ -d {alt}/data ]; then echo alt; else echo leer; fi")
        if stand == "alt":
            raise Abbruch(f"RadioHub liegt noch in {r.umzug_von}: erst umziehen (tools/umzug-mnt-data.sh --probe, dann "
                          f"tools/umzug-mnt-data.sh), danach ausrollen")
        print(f"Ordner {z.wurzel}" + (" (ohne Umzug)" if stand == "leer" else ""))
    if _ssh(z, f"test -f {w}/.env && echo da || echo fehlt") == "fehlt":
        print(f"WARNUNG: {z.wurzel}/.env fehlt; die Zugänge zur Kellerwolke legt das Ausrollen an, Vertonung und "
              "Zeit-Stimme fehlen ohne sie (Werte: handbuch ziel radiohub --env, oder in der App unter Einstellungen)")


# ----- 5. bis 7. Ruhe, Sicherung, Start --------------------------------------------------------------------------------

# /health sagt seit RAD-6 ohne Anmeldung, ob eine Aufnahme läuft; die Wege /api/recording/... fragen nur einen Stand von
# davor (ohne Anmeldung), bei dem /health das noch nicht sagt
RUHE_SKRIPT = """laeuft() {
  curl -sf -m 10 --cacert %(ca)s %(adresse)s/health | grep -q '"aufnahme": *true' && return 0
  for p in status hls-status; do
    curl -sf -m 10 --cacert %(ca)s %(adresse)s/api/recording/$p | grep -q '"recording": *true' && return 0; done; return 1; }
if ! laeuft; then echo "Keine laufende Aufnahme"; exit 0; fi
echo "Eine Aufnahme läuft, warte auf ihr Ende ..."
ende=$(( $(date +%%s) + %(hoechstens)d ))
while laeuft; do
  if [ "$(date +%%s)" -gt "$ende" ]; then echo "Aufnahme läuft noch"; exit 3; fi
  sleep 5
done
echo "Ruhig"
"""


def ruhe_abwarten(z: Ziel, sofort: bool) -> None:
    """Nie eine laufende Aufnahme abschießen: warten, bis keine läuft, unmittelbar vor dem Neustart."""
    if sofort:
        return
    _schritt("Laufende Aufnahme abwarten")
    skript = RUHE_SKRIPT % {"ca": shlex.quote(f"{z.wurzel}/zertifikate/rootCA.pem"), "adresse": shlex.quote(z.adresse),
                            "hoechstens": RUHE_HOECHSTENS_S}
    try:
        print(_ssh(z, skript))
    except Abbruch as f:
        raise Abbruch(f"Nach {RUHE_HOECHSTENS_S // 3600} Stunden läuft noch eine Aufnahme; mit --sofort trotzdem") from f


def sicherungs_skript(z: Ziel, r: Radio) -> str:
    """Ordner als Nutzer des Pi anlegen (sonst legte Docker sie für root an), dann die Sicherung des Appkerns im Abbild:
    radiohub.db nach sicherungen/, die Datenbank des Gerüsts nach sicherungen/appkern/ (getrennt, weil beide Kopien
    radiohub-<Zeit>.sqlite heißen und jede Regel nur ihre eigenen zählt)."""
    q = shlex.quote
    daten = Path(r.datenbank).parent
    geruest = Path(r.geruest)
    befehle = []
    for datei, ordner in ((Path(r.datenbank), SICHERUNGEN), (geruest, f"{SICHERUNGEN}/{geruest.parent.name}")):
        befehle.append(f"""docker compose -f {q(z.compose)} run --rm --no-deps -T \\
    -v {q(f"{z.wurzel}/{daten}")}:{IM_ABBILD}/daten -v {q(f"{z.wurzel}/{SICHERUNGEN}")}:{IM_ABBILD}/{SICHERUNGEN} \\
    {q(r.app)} python -m appkern.sicherung vor-ausrollen --kennung {q(z.kennung)} \\
    --datenbank {q(f"{IM_ABBILD}/daten/{datei.relative_to(daten)}")} --ordner {q(f"{IM_ABBILD}/{ordner}")}""")
    return f"""set -e
  cd {q(z.wurzel)}
  mkdir -p {q(str(daten))} {q(str(geruest.parent))} {SICHERUNGEN} {q(f"{SICHERUNGEN}/{geruest.parent.name}")}
  """ + "\n  ".join(befehle)


def sichern(z: Ziel, r: Radio) -> None:
    _schritt("Datenbank sichern")
    print(_ssh(z, sicherungs_skript(z, r)))


def starten(z: Ziel, r: Radio) -> None:
    """Mit dem Ort des Einrichtungscodes für Menschen (rechner:ordner, gehört dem Haus und steht nicht in compose.pi.yml);
    --remove-orphans nimmt die Container von vor RAD-6 (Backend, Oberfläche) mit."""
    _schritt("Starten")
    c = shlex.quote(z.compose)
    ort = shlex.quote(f"{z.rechner}:{z.wurzel}/{r.einrichtungscode}")
    _ssh(z, f"cd {shlex.quote(z.wurzel)} && EINRICHTUNGSCODE_ORT={ort} docker compose -f {c} up -d --remove-orphans && "
            f"docker compose -f {c} restart vorne")


# ----- 8. Prüfen -------------------------------------------------------------------------------------------------------

META = re.compile(r'<meta name="app-fassung" content="([^"]+)"')


def fassung_der_seite(html: str) -> str | None:
    treffer = META.search(html)
    return treffer.group(1) if treffer else None


def pruefen(z: Ziel, wurzel: Path = WURZEL) -> None:
    _schritt("Prüfen")
    w = shlex.quote(z.wurzel)
    _ssh(z, f"cd {w} && for i in $(seq 1 45); do curl -sf --cacert zertifikate/rootCA.pem {shlex.quote(z.adresse)}/health "
            ">/dev/null && exit 0; sleep 2; done; echo 'RadioHub antwortet nicht'; exit 1")
    server = json.loads(_ssh(z, f"curl -sf --cacert {w}/zertifikate/rootCA.pem {shlex.quote(z.adresse)}/health"))
    app = json.loads(_ssh(z, f"curl -sf --cacert {w}/zertifikate/rootCA.pem {shlex.quote(z.adresse)}/api/v1/app"))
    seite = fassung_der_seite(_curl(z, f"{z.adresse}/"))
    fassung = json.loads((wurzel / "version.json").read_text())["version"]
    print(f"Server {server.get('version')}, Oberfläche {seite} (laut App {app.get('oberflaeche')}), version.json {fassung}, "
          f"Datenbank {server.get('database')}, Appkern {app.get('appkern')}, Besitzer {app.get('besitzer')}")
    if not server.get("version") == fassung == seite == app.get("oberflaeche"):
        raise Abbruch("Fassungen passen nicht zusammen")
    if server.get("database") != "healthy":
        raise Abbruch(f"Die Datenbank antwortet nicht: docker compose -f {z.compose} logs radiohub")
    if app.get("einrichtung_noetig"):
        print("WARNUNG: RadioHub braucht die erste Einrichtung (Kellerwolke); der Zugang aus [zugaenge] kam nicht an")
    if _curl(z, "-o", "/dev/null", "-w", "%{http_version}", "--http2", f"{z.adresse}/") != "2":
        raise Abbruch(f"Die Seite kommt nicht über HTTP/2: Vorschaltdienst prüfen (docker compose -f {z.compose} logs vorne)")
    for pfad, typ in SYMBOLE.items():
        antwort = _curl(z, "-o", "/dev/null", "-w", "%{http_code} %{content_type}", f"{z.adresse}/{pfad}")
        if not antwort.startswith(f"200 {typ}"):
            raise Abbruch(f"Symbol {pfad}: {antwort} (erwartet 200 {typ})")
    hausstelle = Path(_lauf(["mkcert", "-CAROOT"])) / "rootCA.pem"
    for pfad in DECKEND:
        daten = subprocess.run(["curl", "-s", "--cacert", str(hausstelle), f"{z.adresse}/{pfad}"], capture_output=True).stdout
        if not _deckend(daten):
            raise Abbruch(f"Symbol {pfad} hat durchsichtige Stellen (iOS zeigt dann keins): python3 tools/symbole.py")
    print("HTTP/2 über den Vorschaltdienst, Symbole deckend, Manifest in Ordnung")


# ----- Ablauf ----------------------------------------------------------------------------------------------------------

def ausrollen(ergaenzung: Path, sofort: bool, wurzel: Path = WURZEL) -> int:
    try:
        z = laden(wurzel, ZIEL_DATEI, ergaenzung)
        r = radio_angaben(wurzel)
    except (OSError, ValueError, KeyError) as f:
        print(f"\nAbbruch: Ziel nicht lesbar: {f}", file=sys.stderr)
        return 1
    try:
        stand_und_tests(z, wurzel)
        pi_pruefen(z)
        ordner_pruefen(z, r)
        zertifikat(z)
        stand_holen(z)
        bauen(z)
        ruhe_abwarten(z, sofort)
        sichern(z, r)
        zugaenge_besorgen(z)
        starten(z, r)
        pruefen(z, wurzel)
    except Abbruch as f:
        print(f"\nAbbruch: {f}", file=sys.stderr)
        return 1
    aufraeumen(z)
    print(f"\nAusgerollt: {z.adresse}")
    return 0


def main(argv: list[str] | None = None) -> int:
    teiler = argparse.ArgumentParser(prog="tools/ausrollen.sh")
    teiler.add_argument("--ergaenzung", type=Path, help="private Angaben des Hauses (TOML, handbuch ziel)")
    teiler.add_argument("--sofort", action="store_true", help="nicht auf eine laufende Aufnahme warten (bricht sie ab)")
    teiler.add_argument("--nur-tests", action="store_true", help="nur die Prüfungen am Mac (Regeln, Tests, Bau)")
    a = teiler.parse_args(argv)
    if a.nur_tests:
        try:
            tests()
        except Abbruch as f:
            print(f"\nAbbruch: {f}", file=sys.stderr)
            return 1
        return 0
    if a.ergaenzung is None:
        teiler.error("--ergaenzung fehlt (tools/ausrollen.sh holt sie aus der privaten Wahrheit)")
    return ausrollen(a.ergaenzung, a.sofort)


if __name__ == "__main__":
    sys.exit(main())
