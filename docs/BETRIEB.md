# RadioHub PRO: Technik und Betrieb

Einrichtung, Betrieb auf dem Pi und auf anderen Rechnern, Ablage in der Kellerwolke, Umzug des Altbestands,
Telefon und Weckeransicht, Zeitansage und Entwicklung. Die Übersicht steht in der [README](../README.md).

## Technik

| Komponente | Technologie |
|------------|-------------|
| Frontend | Svelte 5 (Runes) mit TypeScript, Vite, hls.js, Schale und Vorlagen des Appkerns |
| Backend | Python, FastAPI, FFmpeg |
| Audio | HLS-Streaming, ICY-Metadata, LUFS-Normalisierung |
| Datenbank | SQLite |
| Icons | Font Awesome (über den Appkern) |
| Fonts | Orbitron (Schriftzug), Barlow (Text), Chakra Petch (Zahlen) |

## Architektur

```
frontend/             Svelte 5 SPA (im Betrieb vom Backend ausgeliefert, beim Entwickeln Vite)
  src/ziel/           was die Bauziele unterscheidet: voll (Backend, Anmeldung) oder web (statische Liste)
backend/              FastAPI REST-API (Python 3.12, Paket app nach dem Schema des Appkerns)
  app/
    ablage/           Ablage der Dateien (Schnittstelle, Kellerwolke, Testablage, Ordnerstruktur)
    routers/          API-Endpunkte
    services/         Business-Logik, Audio-Verarbeitung
    database.py       SQLite-Anbindung
    fassung.py        Fassung aus version.json
  tests/              Prüfungen des Backends (pytest)
architektur/          harte Architekturregeln (regeln.toml), geprüft vor jedem Commit und beim Ausrollen
deploy/               Vorschaltdienst (Caddyfile), Ziel des Ausrollens, Probelauf des Handbuchs
docs/                 Architektur, Handbuchseite, Plan der Überarbeitung
tools/                Git-Haken, Fassung, Ausrollen, Umzug, Symbole, Zertifikat
web/daten/            statische Senderliste der Webversion (per Werkzeug erzeugt)
.github/workflows/    Bau und Auslieferung der Webversion auf GitHub Pages
compose.pi.yml        Betrieb auf dem Pi
docker-compose.yml    Betrieb auf einem anderen Rechner
version.json          die eine Fassung für Backend und Oberfläche
```

Schichten, Regeln und die Regeln der kommenden Etappen stehen in [docs/ARCHITEKTUR.md](ARCHITEKTUR.md),
Einrichtung, Sicherung und Fehlerbilder in [docs/handbuch.md](handbuch.md).

## Betrieb auf dem Pi

Ausgerollt wird vom Mac aus mit einem Befehl:

```bash
./einrichten.sh            # einmal: Python-Umgebung, Pakete der Oberfläche, Git-Haken
tools/ausrollen.sh         # prüft, baut auf dem Pi, sichert die Datenbanken, besorgt die Zugänge, startet neu, prüft
```

Rechner, Ordner (`/mnt/data/radiohub`) und Namen kommen aus dem Verzeichnis des Handbuchs (`handbuch ziel radiohub`).
Das Ausrollen nimmt nur gepushte Stände mit grünen Tests und eingehaltenen Architekturregeln, stellt das Zertifikat
des Vorschaltdienstes aus der Hausstelle aus und wartet eine laufende Aufnahme ab. Lag RadioHub noch im alten Ordner,
zieht `tools/umzug-mnt-data.sh` es einmalig um (vorher `--probe`).

Aufruf:

- App: `https://radio.<Rufname des Pi>.lan` (über den Vorbau des Pi) oder `https://<Pi>:9093`
- Schnittstelle: angemeldet unter `/api/v1/schnittstelle` (OpenAPI); `/docs` nur in der Entwicklung mit
  `RADIOHUB_SCHNITTSTELLEN_DOKU=1`

Angemeldet wird mit dem Konto der Kellerwolke, dem der App-Schlüssel gehört (Gerüst des Appkerns); ein Telefon koppelt
man einmal mit einem Code aus der Kellerwolke (Einstellungen, Geräte), am iPhone in der Web-App vom Startbildschirm.
Alle Wege unter `/api` brauchen die Anmeldung, frei sind nur `/health`, `/api/v1/app` und die Anmeldung selbst.

Im Heimnetz ist nur der Vorschaltdienst (Caddy, HTTPS) erreichbar; die App (ein Container, das Backend liefert die
Oberfläche aus) spricht nur im eigenen Netz der Container und läuft als Nutzer 1000. Die frühere Adresse ohne TLS
leitet der Vorbau auf HTTPS um.

Datenbank, Cache und Zwischenstände liegen in `data/` im Ordner der App (die Einstellungen, das Protokoll und die
Aufträge des Appkerns in `data/appkern/`), Sicherungen in `sicherungen/`; Aufnahmen und heruntergeladene
Podcast-Folgen liegen in der Kellerwolke (siehe "Ablage in der Kellerwolke").

## Betrieb auf einem anderen Rechner

Voraussetzung: Docker mit Compose-Plugin und ein Zertifikat für den Rechner (etwa mit mkcert) als
`zertifikate/radiohub.pem` und `zertifikate/radiohub-schluessel.pem`.

```bash
git clone https://github.com/HalloWelt42/RadioHub.git
cd RadioHub
docker compose up -d --build
```

Danach ist die App unter `https://<Rechner>:9093` erreichbar.

## Ablage in der Kellerwolke

Jede Datei des RadioHub liegt in der Kellerwolke unter `Apps/RadioHub`: Aufnahmen (von Hand und
zeitgesteuert), ihre Stücke nach dem Schnitt, Titellisten, Wellenformen und heruntergeladene Podcast-Folgen.
Lokal hält das RadioHub nur Zwischenstände im Arbeitsordner (`data/cache/arbeit`): die laufende Aufnahme,
einen laufenden Download und die Arbeitskopie zum Schneiden. Danach geht alles in die Kellerwolke und lokal weg.
Favoriten, Abos und gemerkte Folgen bleiben in der Datenbank des RadioHub.

Ordnerstruktur in der Kellerwolke:

```
Apps/RadioHub/
  Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/001 <Titel>.mp3     Stücke einer Aufnahme
  Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/Titelliste.json     Titelwechsel und Ereignisse
  Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/Wellenform.peaks    Wellenform für den Schnitt
  Aufnahmen/<Aufnahmeordner>/<Sender>/<JJJJ-MM-TT HH-MM-SS>/   Aufnahme in einem eigenen Ordner
  Podcasts/<Abo>/<JJJJ-MM-TT> <Folge>.mp3                      heruntergeladene Folge
```

So arbeiten die Funktionen mit der Ablage:

- Wiedergabe von Stücken und Folgen läuft über das Backend aus der Kellerwolke, mit Bereichsanfragen (Spulen)
- Schneiden, Normalisieren und Umwandeln arbeiten an einer lokalen Arbeitskopie; gleicher Dateiname wird eine
  neue Version in der Kellerwolke, ein anderes Format eine neue Datei (die alte geht in den Papierkorb)
- Löschen legt in den Papierkorb der Kellerwolke (wiederherstellbar)
- Ist die Kellerwolke beim Ablegen nicht erreichbar, wartet das RadioHub (Einstellung "Geduld beim Ablegen",
  `RADIOHUB_KELLERWOLKE_GEDULD_S`); was dann noch fehlt, bleibt im Arbeitsordner und wird beim nächsten Start nachgeholt

Einrichtung (einmal je Rechner; auf dem Pi besorgt das Ausrollen Adresse und App-Schlüssel selbst, `[zugaenge]` in
`deploy/ausrollen.toml`):

1. App-Schlüssel auf dem Rechner der Kellerwolke anlegen; er geht nur in eine Datei mit den Rechten 600 und von dort
   als `RADIOHUB_KELLERWOLKE_SCHLUESSEL` in die `.env` (oder in der App bei der ersten Einrichtung eintragen):

   ```bash
   cd <Ordner der Kellerwolke>
   backend/.venv/bin/python tools/app_zugang.py --konto <Konto> --app RadioHub --datei <Datei>
   ```

2. Zertifikatsstelle der Hausstelle als `zertifikate/rootCA.pem` im Ordner der App ablegen
   (auf dem Pi legt das Ausrollen sie mit dem Zertifikat des Vorschaltdienstes ab)
3. `.env` im Ordner der App anlegen (Modus 600):

   ```bash
   RADIOHUB_KELLERWOLKE_ADRESSE=https://<Rechner der Kellerwolke>:<Port>
   RADIOHUB_KELLERWOLKE_CA=/zertifikate/rootCA.pem
   ```

   Wahlweise `RADIOHUB_ORTSSUCHE_ADRESSE`: Adresse der hauseigenen Kartensuche für die Ortssuche der Sonnenzeiten;
   leer heißt keine Suche, der Standort des Telefons geht trotzdem.

4. Ausrollen (auf dem Pi `tools/ausrollen.sh`, sonst `docker compose up -d --build`); das Protokoll der App nennt
   `Verbunden als App RadioHub ...`, den Stand zeigt auch `GET /api/storage/ablage`

Einstellungen: eine Quelle, die Einstellungen des Appkerns (`backend/app/einstellungen.py`). Ein Wert kommt aus der App
(gespeichert), sonst aus der Umgebung (`RADIOHUB_<FELD>`, in Docker über `.env`), sonst aus der Vorgabe; fest ist er
mit `RADIOHUB_FEST_<FELD>` (vom Ausrollen). Die wichtigsten:

| Variable | Bedeutung | Vorgabe |
|----------|-----------|---------|
| `RADIOHUB_KELLERWOLKE_ADRESSE` | Adresse der Kellerwolke (Anmeldung und Ablage) | leer (dann erste Einrichtung) |
| `RADIOHUB_KELLERWOLKE_SCHLUESSEL` | App-Schlüssel; wie früher auch der Pfad einer Datei mit ihm | leer, dann `data/kellerwolke.schluessel`, wenn es sie gibt |
| `RADIOHUB_KELLERWOLKE_WURZEL` | Wurzelordner in der Kellerwolke | `Apps/RadioHub` |
| `RADIOHUB_CA_DATEI` | Zertifikatsstelle (PEM), früher `RADIOHUB_KELLERWOLKE_CA` (gilt weiter) | leer (übliche Stellen und Hausstelle) |
| `RADIOHUB_KELLERWOLKE_GEDULD_S` | Wartezeit beim Ablegen, wenn die Kellerwolke fehlt | `900` |
| `RADIOHUB_ORTSSUCHE_ADRESSE`, `RADIOHUB_VERTONUNG_ADRESSE`, `RADIOHUB_ZEITSTIMME`, `RADIOHUB_ZEITSTIMME_TEMPO` | Ortssuche, Vertonung und Stimme der Zeitansage | leer, `1.0` |
| `RADIOHUB_DATEN`, `RADIOHUB_SICHERUNGEN` | Datenordner (früher `DATA_PATH`, gilt weiter) und Ordner der Sicherungen | `data/`, `sicherungen/` |

Werte, die früher in der Tabelle `config` standen und Einstellungen des Servers sind (Abruf der Podcasts, Bitraten,
Adressen der Verzeichnisse), übernimmt der erste Start einmal; `/api/config` zeigt und ändert sie weiter.

Prüfungen des Backends (mit einer Testablage im Speicher, nie mit echten Daten):

```bash
cd backend
.venv/bin/python -m pytest
```

Mit `RADIOHUB_PROBE_KELLERWOLKE=1` und den Einstellungen oben laufen die Prüfungen der Ablage zusätzlich gegen
eine echte Kellerwolke, in einem eigenen Probeordner unter dem Wurzelordner, der danach in den Papierkorb geht.

## Umzug des Altbestands

Das Werkzeug `python -m app.umzug` bringt den Altbestand in die Kellerwolke und in die Datenbank:

- heutiges RadioHub: Podcast-Folgen und Aufnahmen unter `data/recordings`; die Pfade in der Datenbank zeigen danach
  auf die Kellerwolke, Ton ohne Eintrag zieht mit (`Podcasts/<Abo>/` oder `Aufnahmen/Ohne Zuordnung/`), Cover
  kommen in den Cache
- altes Radio (`--altes-radio`, Ordner mit `pyradio.db` und `recordings/`): Favoriten, Abos, Folgen und gemerkte
  Folgen in die Datenbank, ohne Doppel (Favoriten nach uuid oder Adresse, Abos nach Feed-Adresse, Folgen nach guid);
  gemerkte Folgen werden heruntergeladene Folgen in `Podcasts/<Abo>/`, eigene Aufnahmen werden Aufnahmen
  "Altes Radio" unter `Aufnahmen/Altes Radio/`; nicht übernommen werden Senderliste, Wecker, `config.json` und
  `backups/`

Jede Datei wird abgelegt und gegen den Stand in der Kellerwolke geprüft (Größe und SHA-256); Ziel und Prüfsumme
stehen in der Tabelle `umzug_dateien`. Ein abgebrochener Lauf wird einfach wiederholt und macht nur den Rest. Vor der
ersten Änderung entsteht einmal `data/radiohub.db.vor-umzug`. Die Quellordner bleiben unangetastet, bis `--aufraeumen`
sie nach einem vollständigen Lauf in `papierkorb-radiohub-<datum>/` verschiebt (nie löschen).

Reihenfolge auf dem Pi (Schritt 2 und 3 zusammen; `dc` steht für `docker compose -f compose.pi.yml`):

```bash
cd <Ordner des RadioHub>
alias dc='docker compose -f compose.pi.yml'

# 1. App-Schlüssel (auf dem Rechner der Kellerwolke, nur in eine Datei mit 600; seit RAD-6 besorgt ihn das Ausrollen)
(cd <Ordner der Kellerwolke> && backend/.venv/bin/python tools/app_zugang.py --konto <Konto> --app RadioHub \
  --datei <Ordner des RadioHub>/data/kellerwolke.schluessel)

# 2. Zertifikatsstelle der Hausstelle
mkdir -p zertifikate && cp <rootCA.pem der Hausstelle> zertifikate/

# 3. .env im Ordner der App
printf 'RADIOHUB_KELLERWOLKE_ADRESSE=https://<Rechner der Kellerwolke>:<Port>\nRADIOHUB_KELLERWOLKE_CA=/zertifikate/rootCA.pem\n' > .env

# 4. Bauen; das laufende Backend für den Umzug anhalten
git pull && dc build radiohub && dc stop radiohub

# 5. Trockenlauf: zählt nur und zeigt die Zuordnung (Datenbank und Dateien bleiben, wie sie sind)
dc run --rm -T -v <Ordner des alten Radios>:/altes-radio:ro radiohub \
  python -u -m app.umzug --altes-radio /altes-radio --probe

# 6. Umzug im Hintergrund mit Protokoll (Fortschritt in Prozent und GB); bei Fehlern denselben Befehl wiederholen
nohup dc run --rm -T -v <Ordner des alten Radios>:/altes-radio:ro radiohub \
  python -u -m app.umzug --altes-radio /altes-radio > umzug.log 2>&1 &
tail -f umzug.log

# 7. Prüfung: der Trockenlauf aus 5. zeigt "0 offen"; dann starten und in der Oberfläche Folgen und Aufnahmen
#    abspielen und spulen, Explorer ansehen; in der Kellerwolke liegt alles unter Apps/RadioHub
dc up -d

# 8. Aufräumen: Quellordner (data/recordings, pyradio-daten/recordings) nach <Papierkorb-Ordner>/papierkorb-radiohub-<datum>
dc run --rm -T -v <Ordner des alten Radios>:/altes-radio -v <Papierkorb-Ordner>:/papierkorb \
  radiohub python -u -m app.umzug --altes-radio /altes-radio --aufraeumen --papierkorb /papierkorb
```

## Am Telefon: Ansicht und Web-App

Unter 900 Pixeln Breite, im Querformat und bei Fingerbedienung zeigt das RadioHub eine eigene Telefonansicht: nur
Radio und Podcasts, unten die Fußleiste, darüber die Spielerleiste; antippen öffnet den Spieler als Vollbild
(bei Folgen Position, 15 s zurück, 30 s vor; beim Radio voriger und nächster Sender der Liste und Stopp; der
große Knopf hält nur an und setzt fort). Am Sperrbildschirm stehen
Titel, Sender oder Abo und Bild; dort lässt sich anhalten, spulen und der Favorit wechseln. Aufnahmen, Schneiden
und die Einrichtung gibt es nur am Rechner.

Als Web-App auf den Startbildschirm (iPhone: Safari, Teilen, "Zum Home-Bildschirm"):

1. Das Telefon vertraut der Hausstelle (dasselbe Zertifikat wie bei Kellerwolke und Kiste; einmal als Profil
   installiert und unter Einstellungen, Allgemein, Info, Zertifikatsvertrauenseinstellungen eingeschaltet)
2. Die Adresse mit HTTPS öffnen: `https://radio.<Rufname des Pi>.lan` (Bildschirm wach halten und die Web-App
   brauchen den sicheren Kontext)
3. Teilen, "Zum Home-Bildschirm"; ein früher angelegtes Symbol vorher entfernen

Der HTTPS-Zugang ist ein Vorschaltdienst (`vorne`, Caddy) mit einem Blattzertifikat der Hausstelle in
`zertifikate/radiohub.pem` und `zertifikate/radiohub-schluessel.pem`. Auf dem Pi stellt das Ausrollen es aus, sobald
es fehlt oder in weniger als 60 Tagen abläuft. Für einen anderen Rechner auf dem Mac mit der Hausstelle (mkcert):

```bash
RADIOHUB_ZIEL=<nutzer>@<rechner> RADIOHUB_ORDNER=<Ordner des RadioHub> RADIOHUB_NAMEN="<ip> <rechnername>" tools/zertifikat.sh
docker compose up -d vorne
```

## Wecker und Weckeransicht

Telefon quer gelegt zeigt die Weckeransicht für den Nachttisch, in zwei Layouts (Entwürfe B und D in
lokaler Entwurf `querformat.html`), umschaltbar durch Wischen nach links oder rechts:

- Uhr mit Sonnenband: große Uhr, darunter 24 Stunden (Tag hell, Nacht dunkel, Strich für jetzt, Auf- und
  Untergang), rechts Sender, Wecker und die drei Knöpfe (Wiedergabe, Ansage an/aus, Nachtschaltung)
- Nur die Uhr: unten eine schmale Leiste mit Sender, Wecker und Sonne; die Knöpfe erscheinen nach Antippen

Antippen der Ziffern sagt die Zeit an. Ein scharfer Wecker steht als Glocke mit Weckzeit in Akzentfarbe da, ohne Wecker
eine durchgestrichene Glocke, beim Schlummern das Bett mit der Zeit. Zwischen Sonnenuntergang und -aufgang schaltet
die Ansicht auf Dunkelrot (Auto), von Hand geht Rot oder Normal. Der Bildschirm bleibt dabei wach.

Fällt der Sender aus oder bleibt stumm, verbindet die Weckeransicht neu (nach 2, 5, 10, 20 Sekunden, dann alle 30;
ohne Wecker höchstens sechsmal). Beim Wecken kommt ab dem dritten Versuch zusätzlich ein Weckton aus dem Gerät
(im Speicher erzeugt, ohne Netz), bis der Sender zu hören ist. Der Stand der Verbindung steht als Symbol beim Sender.

Wecker (Uhr-Symbol oben rechts, `/wecker`): Uhrzeit, Wochentage, ein Sender aus den Favoriten oder die neueste Folge
eines Abos, Lautstärke und wie lange sie ansteigt. Gespeichert werden sie im Backend. Geweckt wird nur, solange die
Weckeransicht offen ist: Web-Apps werden im Hintergrund nicht geweckt. Also Telefon quer legen, die Seite offen
lassen und vorher einmal etwas abspielen, damit der Browser Ton erlaubt. Schlummern und Aus sind große Knöpfe.

Den Ort für die Sonnenzeiten (Breite, Länge) trägt man in den Einstellungen am Telefon ein; berechnet wird lokal,
ohne fremden Dienst.

## Zeitansage

In der Weckeransicht sagt das RadioHub die Uhrzeit an ("Es ist fünf Uhr vierunddreißig", zur vollen Stunde ohne
Minuten), nur solange die Weckeransicht offen und sichtbar ist. Wann, steht in den Einstellungen am Telefon,
unabhängig vom Wecker und im Gerät gespeichert: an oder aus, alle 5, 10, 15, 30 oder 60 Minuten (ab Mitternacht
gezählt), ein Zeitraum von bis (auch über Mitternacht; ohne von und bis rund um die Uhr) und ob nur mit
eingeschaltetem Wecker oder immer. Beim Wecken gilt der Wecker, bis er aus ist: während er klingelt keine Ansage,
beim Schlummern alle 5 Minuten. Läuft Radio oder eine Folge, wird es sanft
leise gezogen (auf dem iPhone stumm, dort lässt der Browser die Lautstärke nicht stellen), nach der Ansage folgen
2 Sekunden Pause, dann wieder die alte Lautstärke. Der Knopf "Zeit ansagen" sagt sofort an; "Ansage an/aus" schaltet
die regelmäßige Ansage (gespeichert im Gerät). Bei Nachtrot ist die Ansage leise, normal oder aus (Einstellungen).

Ton gibt der Browser erst nach einem Tippen frei. Die Weckeransicht hält ihn danach offen (eine stille Schleife), damit
die Ansage auch von selbst zu hören ist. Ist er gesperrt, etwa direkt nach dem Öffnen, steht am Ansage-Knopf ein
durchgestrichener Lautsprecher in Akzentfarbe: einmal irgendwo tippen gibt den Ton frei (ein Tipp auf den Knopf
selbst schaltet dann die Ansage nicht aus). Eine neue Fassung lädt nie von selbst; in der Weckeransicht steht auch
kein Hinweis darauf (er käme erst beim Verlassen), denn nach dem Neuladen wäre der Ton wieder gesperrt.

Gesprochen wird aus 84 Bausteinen ("Es ist", "null Uhr" bis "dreiundzwanzig Uhr", "eins" bis "neunundfünfzig") in
der Kellerwolke unter `Apps/RadioHub/Zeitansage/<Stimme>/`, je Stimme ein eigener Satz. Erzeugt werden fehlende
einmal über die hauseigene Vertonung mit der Zeit-Stimme (Einstellungen am Telefon, "Bausteine erzeugen", oder
`POST /api/zeitansage/erzeugen`):

- `.env`: `RADIOHUB_VERTONUNG_ADRESSE=https://<rechner>:8641`; die Zeit-Stimme wählt man in den Einstellungen
  (Telefon und Wecker, Zeit-Stimme) aus dem Katalog der Vertonung und den für RadioHub freigegebenen privaten Stimmen.
  Vorgabe ist `katalog:sohee`, dieselbe Stimme wie in Basic; `RADIOHUB_ZEITSTIMME` setzt sie in der Umgebung
  (`katalog:<Name>` oder die Kennung einer privaten Stimme) und gilt, bis in der App eine gewählt ist
- eine private Stimme in der Vertonung für die App RadioHub freigeben (Private Stimmen für); angemeldet wird mit dem
  App-Schlüssel der Kellerwolke
- Basic (Pages) spricht aus den Bausteinen im Repo (`web/daten/zeitansage/`, Katalogstimme sohee, das Repo ist
  öffentlich); neu sprechen lässt sie `app.werkzeuge.zeitansage_bausteine` (Kopf der Datei)
- Stand: `GET /api/zeitansage` (fehlende Bausteine, Meldung der Erzeugung)

## Neue Fassung

Die geöffnete App erkennt eine neue Fassung von selbst (alle 5 Minuten und beim Zurückkehren auf die Seite), in PRO
und in Basic. Sie lädt nie von selbst neu (RAD-20): unten erscheint ein Hinweis mit "Neu laden" und "Später". Neu
geladen wird nur auf Wunsch; der gewählte Sender bzw. die Folge wird übergeben, Pfad, Weckeransicht und Wachhalten
bleiben. "Später" blendet den Hinweis aus, bis eine noch neuere Fassung kommt.

## Lokale Entwicklung (ohne Docker)

Voraussetzungen: Python 3.11+, Node.js 18+, FFmpeg.

```bash
./einrichten.sh     # Python-Umgebung des Backends, Pakete der Oberfläche, Git-Haken
```

Starten:

```bash
# Backend (Port 9091)
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 9091 --reload

# Frontend Dev-Server (Port 5180, mit Vite-Proxy auf 9091)
cd frontend
npm run dev
```

Die App ist im Dev-Modus unter `http://localhost:5180` erreichbar (nur am eigenen Rechner).

Die Webversion braucht kein Backend:

```bash
cd frontend
npm run dev:web      # http://localhost:5190/RadioHub/
npm run build:web    # nach frontend/dist-web, wie auf GitHub Pages
```

## Fassung, Git-Haken und Regeln

Die Fassung steht nur in `version.json`; Backend (`/health`, API-Docs) und Oberfläche (Fußleiste) lesen sie. Vor jedem
Commit zählt der Haken den Patch hoch und prüft die vorgemerkten Dateien: gerade Zeichen, Stil, harte
Architekturregeln aus `architektur/regeln.toml`, Seite und Einrichtungsskript des Handbuchs. Jede Commit-Nachricht
beginnt mit der Kennung eines Tickets (`RAD-12: ...`). Ein Feature hebt die Fassung vorher mit `tools/version.sh minor`.
