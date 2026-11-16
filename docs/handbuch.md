---
zweck: "Internetradio, Podcasts, Aufnahmen und Wecker im HiFi-Look: Senderverzeichnis mit Filtern und Favoriten, Zeitversatz, Aufnahmen mit Schnitt, Podcast-Abos, Weckeransicht mit Zeitansage am Telefon; Aufnahmen und Folgen liegen in der Kellerwolke."
geraet: [pi]
abhaengigkeiten: [kellerwolke]
daten:
  - "Pi: `{{wurzel}}/data/radiohub.db` (Sender, Favoriten, Filter und Sperren, Index der Aufnahmen, Abos und Folgen, Wecker, Stand der Oberfläche), `{{wurzel}}/data/appkern/radiohub.sqlite` (Einstellungen, Protokoll, Aufträge des Appkerns), `{{wurzel}}/data/cache` (Senderlogos, Zwischenstände, Arbeitsordner laufender Aufnahmen und Downloads), `{{wurzel}}/data/storage.json` (Speicherzonen)"
  - "Kellerwolke, Ordner `Apps/RadioHub`: Aufnahmen mit Titelliste und Wellenform, heruntergeladene Podcast-Folgen, Bausteine der Zeitansage"
sicherung:
  - "nach der Regel des Appkerns eine Kopie von `radiohub.db` nach `{{wurzel}}/sicherungen` und eine der Datenbank des Gerüsts nach `{{wurzel}}/sicherungen/appkern`: regelmäßig von der App (Vorgabe alle 7 Tage) und vor jedem Ausrollen (nur wenn die jüngste älter als 24 Stunden ist und sich etwas geändert hat, höchstens drei je Datenbank)"
  - "Aufnahmen, Folgen und Bausteine hängen an der Sicherung der Kellerwolke"
schluessel_orte:
  - "Pi: `{{wurzel}}/.env`, Modus 0600: App-Schlüssel und Adresse der Kellerwolke als feste Einstellungen (RADIOHUB_FEST_KELLERWOLKE_SCHLUESSEL und _ADRESSE, vom Ausrollen), dazu Adressen der Kellerwolke und der Vertonung, Zertifikatsstelle, Kennung der Zeit-Stimme"
  - "Pi: `{{wurzel}}/data/kellerwolke.schluessel`, Modus 0600: der App-Schlüssel von vor RAD-6; gilt nur noch, solange die .env keinen festen hat"
  - "Pi: `{{wurzel}}/zertifikate/`, Blattzertifikat mit Schlüssel aus der Hausstelle (vom Ausrollen)"
einrichten: einrichten.sh
stand: 97e05e6
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
HTTPS um. Die App (Backend auf dem Gerüst des [[Appkern]], liefert die Oberfläche selbst aus) ist nur im eigenen Netz
der Container erreichbar. Angemeldet wird mit dem Konto der [[Kellerwolke]], dem der App-Schlüssel gehört; Telefone
koppelt man einmal mit einem Code aus der Kellerwolke. Architektur und harte Regeln stehen in `docs/ARCHITEKTUR.md`,
der Plan der Überarbeitung in `docs/umbau/PLAN.md`.

## Was sie braucht

- Den Pi ({{rechner}}) nach [[Grundlage Pi]] mit Docker und dem gemeinsamen Netz `haus`; RadioHub läuft dort mit
  `compose.pi.yml` in zwei Containern: die App (FastAPI auf dem Gerüst des Appkerns mit der gebauten Oberfläche,
  FFmpeg, Nutzer 1000) und der Vorschaltdienst (Caddy); veröffentlicht ist nur der Vorschaltdienst.
- Die [[Kellerwolke]] für Anmeldung und Ablage (App RadioHub mit eigenem App-Schlüssel im Konto admin, besorgt vom
  Ausrollen); ohne sie wartet RadioHub auf die erste Einrichtung.
- Ohne die es auch geht: OSMLocal für die Ortssuche der Sonnenzeiten (über das Netz `haus`, Name `osmlocal`) und die
  [[Vertonung]] für die Bausteine der Zeitansage.
- Ein Zertifikat aus der Hausstelle für den Vorschaltdienst (stellt das Ausrollen aus, mit der Adresse des Pi, damit
  der Vorbau es prüfen kann).
- Am Mac für Entwicklung und Ausrollen: Python 3.12, Node.js, Docker, mkcert mit der Hausstelle, das
  Werkzeug `handbuch` und der [[Appkern]] mit seiner Umgebung (Prüfungen vor jedem Commit, Bausteine des Ausrollens).

## Neu einrichten

Wahl: aus der Sicherung (Datenbank mit Favoriten, Filtern, Abos und Weckern zurück, Schlüssel der Kellerwolke wie
vorher) oder frisch (leere Datenbank, das Senderverzeichnis lädt beim ersten Start, neuer App-Schlüssel).

### 1. Entwicklung am Mac

Im Ordner des Repos `./einrichten.sh` ausführen: Python-Umgebung des Backends mit den Testpaketen, Pakete der
Oberfläche und die Git-Haken (`tools/git-hooks`: Fassung zählen, Zeichen und Stil, harte Regeln aus
`architektur/regeln.toml`, Kennung RAD-n in jeder Commit-Nachricht).

Probe: `git config core.hooksPath` zeigt `tools/git-hooks`; `backend/.venv/bin/python -m pytest` (im Ordner
`backend`) und `npx vitest run` (im Ordner `frontend`) melden alle Tests grün.

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
Zertifikat aus, holt den Stand nach `{{wurzel}}`, baut, wartet eine laufende Aufnahme ab, sichert beide Datenbanken,
besorgt die Zugänge (Abschnitt `[zugaenge]`: Adresse und App-Schlüssel der Kellerwolke als feste Einstellungen in die
`.env`, solange sie dort fehlen), startet neu und prüft über HTTPS Fassung, Datenbank, HTTP/2 und Symbole. Vorher läuft
die Freigabe des Handbuchs (Seite, Einrichtungsskript, Probelauf). Beim ersten Ausrollen nach RAD-6 gehen die Container
von davor (Backend, Oberfläche mit nginx) als verwaiste mit; die Datenbank wird ohne Umbau als Stufe 1 übernommen.

Probe: die Ausgabe endet mit "Ausgerollt" und nennt den Besitzer; `/health` meldet Fassung {{fassung}} und die
Datenbank gesund; das Protokoll der App nennt "Bestand ohne Änderung als Stufe 1 übernommen".

### 4. Einstellungen des Hauses

Alle Einstellungen stehen an einer Stelle, den Einstellungen des Appkerns: gespeichert in der App, sonst aus der `.env`
im Ordner `{{wurzel}}` (Modus 0600, Namen `RADIOHUB_<FELD>`), sonst die Vorgabe; fest (nicht änderbar) sind die Werte
`RADIOHUB_FEST_*`, die das Ausrollen setzt. Für die Vertonung `RADIOHUB_VERTONUNG_ADRESSE` und `RADIOHUB_ZEITSTIMME`;
die Zertifikatsstelle (`RADIOHUB_CA_DATEI`) und die Ortssuche (OSMLocal im Netz `haus`) setzt `compose.pi.yml`. Die
Namen von vor RAD-6 gelten weiter (`RADIOHUB_KELLERWOLKE_CA`, `RADIOHUB_KELLERWOLKE_SCHLUESSEL` als Pfad einer Datei,
ohne Angabe `data/kellerwolke.schluessel`); Werte, die früher in der Tabelle `config` standen (Abruf der Podcasts,
Bitraten, Adressen der Verzeichnisse), übernimmt der erste Start einmal. Aus der Sicherung: die alte `.env` zurücklegen.
Frisch: Werte aus den Seiten von [[Kellerwolke]] und [[Vertonung]], danach `tools/ausrollen.sh` erneut.

Probe: das Protokoll der App nennt "Verbunden als App RadioHub im Konto admin"; `GET /api/storage/ablage` meldet
verbunden, eine Aufnahme landet unter `Apps/RadioHub/Aufnahmen`.

### 5. Anmelden und Telefone koppeln

Am Rechner mit Name und Passwort des Kontos, dem der App-Schlüssel gehört (weitere Konten in der App unter
Einstellungen, Zugang). Jedes Telefon einmal koppeln: in der [[Kellerwolke]] unter Einstellungen, Geräte einen Code
erzeugen (gilt zehn Minuten), am iPhone RadioHub als Web-App vom Startbildschirm öffnen (sie hat einen eigenen Speicher,
also dort koppeln, nicht in Safari) und "Mit Code koppeln" wählen. Das Gerät bleibt angemeldet, bis man es in der
Kellerwolke trennt; der Lesezugang für Ton und Bilder erneuert sich von selbst, auch in der Weckeransicht, die tagelang
offen bleibt. Fällt die Kellerwolke aus, gelten bestätigte Anmeldungen 24 Stunden weiter (Einstellung "Anmeldung bei
Ausfall").

Probe: nach dem Koppeln zeigt die Weckeransicht ihre Wecker; ein Neustart von RadioHub verlangt keine neue Anmeldung.

## Sicherung und Rückspielen

Regelmäßig (Vorgabe alle 7 Tage, Einstellungen, Sicherung) und vor jedem Ausrollen entsteht nach der Regel des
Appkerns eine Kopie von `radiohub.db` in `{{wurzel}}/sicherungen` und eine der Datenbank des Gerüsts in
`{{wurzel}}/sicherungen/appkern` (je `radiohub-<Zeit>.sqlite`, höchstens drei). Aufnahmen, Folgen und die Bausteine der
Zeitansage sichert die [[Kellerwolke]]. Rückspielen: `docker compose -f compose.pi.yml stop radiohub`, die Kopie als
`{{wurzel}}/data/radiohub.db` (oder `data/appkern/radiohub.sqlite`) ablegen (alte `-wal` und `-shm` daneben entfernen,
Besitz 1000), `docker compose -f compose.pi.yml up -d`. Eine Kopie von vor RAD-6 übernimmt der Start ohne Umbau als
Stufe 1. Prüfen: Favoriten und Abos sind da, `/health` meldet die Datenbank gesund.

## Wenn etwas klemmt

- **Ausrollen bricht ab mit "liegt noch in ...":** Der Umzug fehlt; Schritt 2 ausführen.
- **RadioHub startet nicht, "Permission denied" unter /data oder /sicherungen:** Dateien gehören noch root (von den
  Containern vor dem Umzug); `sudo chown -R 1000:1000 {{wurzel}}/data {{wurzel}}/sicherungen` und neu starten.
- **Anmeldung schlägt fehl, "Diese App gehört dem Konto ...":** Nur das Konto des App-Schlüssels darf sich anmelden;
  weitere Konten unter Einstellungen, Zugang eintragen. Ein Koppelcode gilt nur in der Kellerwolke, an der RadioHub
  hängt (die Anmeldeseite nennt ihre Adresse).
- **Die App zeigt "einrichten":** Adresse oder App-Schlüssel der Kellerwolke fehlen; `tools/ausrollen.sh` erneut (es
  besorgt sie) oder auf der Seite eintragen, von anderswo als dem Pi mit dem Einrichtungscode aus
  `{{wurzel}}/data/appkern/einrichtungscode`.
- **Commit wird abgelehnt:** Der Haken nennt den Befund (Zeichen, Stil, harte Regel, Kennung RAD-n fehlt). Ursache
  beheben; eine Ausnahme von einer harten Regel gilt nur mit einem Kommentar des Nutzers am Ticket "Ausnahme
  freigegeben: <Regel>" und einem Eintrag in `architektur/ausnahmen.toml`.
- **Ein Sender spielt nicht, andere schon:** Der Durchleiter spielt nur bekannte Sender (Kennung, die Adresse kommt aus
  der Datenbank), prüft TLS und folgt Weiterleitungen nur auf http und https; ein Sender mit abgelaufenem Zertifikat
  bleibt stumm (502 im Log, `docker compose -f compose.pi.yml logs radiohub`). In den Senderdetails eine eigene Adresse eintragen, sie gilt vor der
  aus dem Senderverzeichnis.
- **Die Datenbank soll ganz geprüft werden:** `/health` fragt nur, ob sie antwortet; die volle Prüfung über die ganze
  Datei ist `GET /api/datenbank/pruefung` (dauert bei der großen Datenbank eine Weile).
- **Ortssuche findet nichts:** OSMLocal läuft nicht oder hängt nicht im Netz `haus`; der Standort des Telefons geht
  trotzdem.
