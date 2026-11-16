---
zweck: "Internetradio, Podcasts, Aufnahmen und Wecker im HiFi-Look: Senderverzeichnis mit Filtern und Favoriten, Zeitversatz, Aufnahmen mit Schnitt, Podcast-Abos, Weckeransicht mit Zeitansage am Telefon; Aufnahmen und Folgen liegen in der Kellerwolke."
geraet: [pi]
abhaengigkeiten: [kellerwolke]
daten:
  - "Pi: `{{wurzel}}/data/radiohub.db` (Sender, Favoriten, Filter und Sperren, Index der Aufnahmen, Abos und Folgen, Wecker, Einstellungen), `{{wurzel}}/data/cache` (Senderlogos, Zwischenstände, Arbeitsordner laufender Aufnahmen und Downloads), `{{wurzel}}/data/storage.json` (Speicherzonen)"
  - "Kellerwolke, Ordner `Apps/RadioHub`: Aufnahmen mit Titelliste und Wellenform, heruntergeladene Podcast-Folgen, Bausteine der Zeitansage"
sicherung:
  - "vor jedem Ausrollen nach der Regel des Appkerns eine Kopie von `radiohub.db` nach `{{wurzel}}/sicherungen` (nur wenn die jüngste älter als 24 Stunden ist und sich etwas geändert hat, höchstens drei)"
  - "Aufnahmen, Folgen und Bausteine hängen an der Sicherung der Kellerwolke"
schluessel_orte:
  - "Pi: `{{wurzel}}/data/kellerwolke.schluessel`, Modus 0600: App-Schlüssel der Kellerwolke (Variable RADIOHUB_KELLERWOLKE_SCHLUESSEL nennt den Pfad im Container)"
  - "Pi: `{{wurzel}}/.env`, Modus 0600: Adressen der Kellerwolke und der Vertonung, Zertifikatsstelle, Kennung der Zeit-Stimme (keine Schlüssel)"
  - "Pi: `{{wurzel}}/zertifikate/`, Blattzertifikat mit Schlüssel aus der Hausstelle (vom Ausrollen)"
einrichten: einrichten.sh
stand: 89ecc24
---

# RadioHub

## Zweck

RadioHub ist das Radio des Hauses, Fassung {{fassung}}: tausende Sender aus dem Senderverzeichnis mit Suche, Filtern,
Ausschlüssen und Favoriten, Zeitversatz (zurückspulen im laufenden Sender), Aufnahmen von Hand oder nach Zeitplan mit
Schnitt in der Wellenform, Podcast-Abos zum Hören und Herunterladen. Am Telefon gibt es eine eigene Ansicht und quer
gelegt die Weckeransicht für den Nachttisch mit Wecker, Sonnenband und Zeitansage. Aufnahmen und heruntergeladene
Folgen liegen in der [[Kellerwolke]]; RadioHub hält lokal nur die Datenbank und Zwischenstände.

Erreichbar über HTTPS am eigenen Vorschaltdienst auf Port {{port:ziel/vorne}} des Pi und im Heimnetz unter
`radio.<Rufname des Pi>.lan` über den [[Vorbau]]. Die frühere Adresse ohne TLS ({{adresse}}) leitet der Vorbau auf
HTTPS um. Backend und Oberfläche (nginx) sind nur im eigenen Netz der Container erreichbar. Architektur und harte
Regeln stehen in `docs/ARCHITEKTUR.md`, der Plan der Überarbeitung in `docs/umbau/PLAN.md`.

## Was sie braucht

- Den Pi ({{rechner}}) nach [[Grundlage Pi]] mit Docker und dem gemeinsamen Netz `haus`; RadioHub läuft dort mit
  `compose.pi.yml` in drei Containern: Backend (FastAPI, FFmpeg), Oberfläche (nginx) und Vorschaltdienst (Caddy).
- Die [[Kellerwolke]] als Ablage (App RadioHub mit eigenem App-Schlüssel); ohne sie läuft das Radio, aber Aufnehmen,
  Herunterladen und die Zeitansage melden, dass die Ablage fehlt.
- Ohne die es auch geht: OSMLocal für die Ortssuche der Sonnenzeiten (über das Netz `haus`, Name `osmlocal`) und die
  [[Vertonung]] für die Bausteine der Zeitansage.
- Ein Zertifikat aus der Hausstelle für den Vorschaltdienst (stellt das Ausrollen aus, mit der Adresse des Pi, damit
  der Vorbau es prüfen kann).
- Am Mac für Entwicklung und Ausrollen: Python 3.11 oder neuer, Node.js, Docker, mkcert mit der Hausstelle, das
  Werkzeug `handbuch` und der [[Appkern]] mit seiner Umgebung (Prüfungen vor jedem Commit, Bausteine des Ausrollens).

## Neu einrichten

Wahl: aus der Sicherung (Datenbank mit Favoriten, Filtern, Abos und Weckern zurück, Schlüssel der Kellerwolke wie
vorher) oder frisch (leere Datenbank, das Senderverzeichnis lädt beim ersten Start, neuer App-Schlüssel).

### 1. Entwicklung am Mac

Im Ordner des Repos `./einrichten.sh` ausführen: Python-Umgebung des Backends mit den Testpaketen, Pakete der
Oberfläche und die Git-Haken (`tools/git-hooks`: Fassung zählen, Zeichen und Stil, harte Regeln aus
`architektur/regeln.toml`, Kennung RAD-n in jeder Commit-Nachricht).

Probe: `git config core.hooksPath` zeigt `tools/git-hooks`; `radiohub-backend/.venv/bin/python -m pytest` (im Ordner
`radiohub-backend`) und `npx vitest run` (im Ordner `radiohub-frontend`) melden alle Tests grün.

### 2. Einmalig: Umzug in den Ordner des Betriebs

Lag RadioHub noch im alten Ordner (`umzug_von` in `deploy/ausrollen.toml`), bricht das Ausrollen ab, bis umgezogen ist.
Erst `tools/umzug-mnt-data.sh --probe` (zeigt Größe, Platz, Besitzer und Stand, ändert nichts), dann
`tools/umzug-mnt-data.sh`: zwei Abschriften mit rsync (die zweite nach dem Anhalten, die Datenbank ist danach
stimmig), Besitz 1000:1000, denn die Container laufen nicht mehr als root, `.env` mit Modus 0600, die frühere
`docker-compose.override.yml` heißt danach `.vor-umzug`. Der alte Ordner bleibt als Rückweg stehen (Kopfkommentar des
Skripts). Danach ist RadioHub aus, bis Schritt 3 läuft.

Probe: im Ordner `{{wurzel}}` liegt `.umzug-fertig`; ein zweiter Lauf meldet "schon umgezogen".

### 3. Betrieb auf dem Pi

`tools/ausrollen.sh` ausführen. Es prüft Stand, harte Regeln und Tests (Backend, Oberfläche, Bau) am Mac, stellt das
Zertifikat aus, holt den Stand nach `{{wurzel}}`, baut, wartet eine laufende Aufnahme ab, sichert die Datenbank,
startet neu und prüft über HTTPS Fassung, HTTP/2 und Symbole. Vorher läuft die Freigabe des Handbuchs (Seite,
Einrichtungsskript, Probelauf).

Probe: die Ausgabe endet mit "Ausgerollt"; die Fußleiste der App nennt Fassung {{fassung}}, `/health` meldet dieselbe.

### 4. Einstellungen des Hauses

`.env` im Ordner `{{wurzel}}` (Modus 0600) mit `RADIOHUB_KELLERWOLKE_ADRESSE`, `RADIOHUB_KELLERWOLKE_CA`
(`/zertifikate/rootCA.pem`), `RADIOHUB_VERTONUNG_ADRESSE` und `RADIOHUB_ZEITSTIMME`; die Ortssuche setzt
`compose.pi.yml` fest auf OSMLocal im Netz `haus`. Aus der Sicherung: die alte `.env` zurücklegen. Frisch: Werte aus
den Seiten von [[Kellerwolke]] und [[Vertonung]], danach `tools/ausrollen.sh` erneut.

Probe: das Backend meldet beim Start "Ablage: Verbunden als App RadioHub"; die Kopfleiste zeigt die Ablage grün.

### 5. Schlüssel der Kellerwolke

Aus der Sicherung: `kellerwolke.schluessel` nach `{{wurzel}}/data/` (Modus 0600, Besitz 1000). Frisch: auf dem Rechner
der Kellerwolke `backend/.venv/bin/python tools/app_zugang.py --konto <Konto> --app RadioHub --datei <Datei>` und die
Datei dorthin legen.

Probe: `GET /api/storage/ablage` meldet verbunden; eine Aufnahme landet unter `Apps/RadioHub/Aufnahmen`.

## Sicherung und Rückspielen

Vor jedem Ausrollen entsteht nach der Regel des Appkerns eine Kopie der Datenbank in `{{wurzel}}/sicherungen`
(`radiohub-<Zeit>.sqlite`, höchstens drei). Aufnahmen, Folgen und die Bausteine der Zeitansage sichert die
[[Kellerwolke]]. Rückspielen: `docker compose -f compose.pi.yml stop radiohub-backend`, die Kopie als
`{{wurzel}}/data/radiohub.db` ablegen (alte `radiohub.db-wal` und `radiohub.db-shm` daneben entfernen, Besitz 1000),
`docker compose -f compose.pi.yml up -d`. Prüfen: Favoriten und Abos sind da, `/health` meldet die Datenbank gesund.

## Wenn etwas klemmt

- **Ausrollen bricht ab mit "liegt noch in ...":** Der Umzug fehlt; Schritt 2 ausführen.
- **Backend startet nicht, "Permission denied" unter /data:** Dateien gehören noch root (von den Containern vor dem
  Umzug); `sudo chown -R 1000:1000 {{wurzel}}/data` und neu starten.
- **Commit wird abgelehnt:** Der Haken nennt den Befund (Zeichen, Stil, harte Regel, Kennung RAD-n fehlt). Ursache
  beheben; eine Ausnahme von einer harten Regel gilt nur mit einem Kommentar des Nutzers am Ticket "Ausnahme
  freigegeben: <Regel>" und einem Eintrag in `architektur/ausnahmen.toml`.
- **Ortssuche findet nichts:** OSMLocal läuft nicht oder hängt nicht im Netz `haus`; der Standort des Telefons geht
  trotzdem.
