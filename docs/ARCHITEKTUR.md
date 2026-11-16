# RadioHub: Architektur

Stand 16.11.2026 (RAD-5, Etappe 1, und RAD-6, Teil 2b: Backend auf dem Appkern). Dieses Dokument beschreibt Aufbau, Schichten und harte Regeln von
RadioHub. Die Regeln stehen maschinenlesbar in `architektur/regeln.toml`; der Git-Haken und das Ausrollen setzen sie
durch. Entscheidungen und Etappen der Überarbeitung stehen in `docs/umbau/PLAN.md`, der Befund davor in
`docs/umbau/BEFUND.md`.

## Leitgedanken

1. **Eine Wahrheit je Sache.** Die Fassung steht nur in `version.json`, die Ziele des Betriebs nur in der privaten
   Wahrheit des Handbuchs (`handbuch ziel radiohub`), die Senderdaten nur in der Datenbank.
2. **Die Schnittstelle nutzt Dienste, nie umgekehrt.** Fachlogik hängt nicht an FastAPI; die Ablage ist ein Port mit
   austauschbarem Adapter (Kellerwolke im Betrieb, Speicher in den Tests).
3. **Logik ohne Oberfläche.** Zustand, Wiedergabe, Zugriff aufs Backend und Zeitpläne liegen in `src/lib` und kennen
   keine Svelte-Bausteine; so sind sie testbar und für Rechner, Telefon und später die Webversion dieselben.
4. **Nach außen nur das Nötige.** Im Heimnetz ist nur der Vorschaltdienst erreichbar (HTTPS); die App (ein Container,
   das Backend liefert die Oberfläche aus) spricht nur im eigenen Netz der Container. Alle Wege unter /api brauchen die
   Anmeldung mit dem Konto der Kellerwolke; frei sind nur /health und, was das Gerüst freigibt (/api/v1/app, Anmeldung,
   erste Einrichtung). Der Durchleiter nimmt nur bekannte Sender und Folgen an.
5. **Erzwingen statt dran denken.** Was eine Regel ist, prüft der Haken; Ausnahmen gibt nur der Nutzer frei.

## Schichten heute

Backend (FastAPI auf dem Gerüst des Appkerns, Paket `app` in `backend/app`, Python 3.12):

```
schnittstelle   routers/**, main.py, betrieb.py   Endpunkte, Eingaben prüfen; Gerüst und Betrieb des Radios als
   │                                             Begleiter (Start, Zugänge, Ende)
   │  darf dienste, ablage, grundlagen
werkzeuge       umzug/**, werkzeuge/**         Befehle für Umzug und Pflege (python -m app.umzug ...)
   │  darf dienste, ablage, grundlagen
dienste         services/**                    Aufnahme, Puffer, Podcasts, Sender, Werbung, Zeitansage, Durchleiter
   │  darf ablage, grundlagen
ablage          ablage/**                      Port und Adapter für Aufnahmen und Folgen (Kellerwolke über den Zugang
   │                                           des Gerüsts, Speicher)
   │  darf grundlagen
grundlagen      config.py, database.py, storage.py, fassung.py, sender_merkmale.py, einstellungen.py, uebergang.py,
                ort.py
```

Was das Gerüst des Appkerns übernimmt: Einstellungen (`einstellungen.AppEinstellungen`, eine Quelle: gespeichert, dann
Umgebung `RADIOHUB_*`, dann Vorgabe; fest `RADIOHUB_FEST_*` vom Ausrollen), Protokoll, Aufträge, Anmeldung mit dem Konto
der Kellerwolke, Sicherung, Auslieferung der Oberfläche. Seine Datenbank liegt in `data/appkern/radiohub.sqlite`, die des
Radios bleibt `data/radiohub.db` und kommt über die Datenbank des Appkerns in Stufen (`database.STUFEN`, Stufe 1 ist der
Bestand bis 0.15.6). Frühere Namen und Formen der Einstellungen gelten über `uebergang.py`. Offene Frage an den Appkern:
eine Datei für beide (Name der Datenbank im Gerüst wählbar) und ein Haken für eigene SQL-Funktionen in seinen
Verbindungen (`merkmal_trifft`); bis dahin lesen und schreiben die Dienste über `database.get_db`.

Oberfläche (Svelte 5, `frontend/src`):

```
oberflaeche     components/**, App.svelte, main.js     Ansichten für Rechner, Telefon und Wecker
   │  darf logik
logik           lib/**                                 Zustand, Wiedergabe (playerEngine), Backend (api.js), Router,
                                                       Übersetzungen, Zeitpläne, Erkennung neuer Fassungen
```

## Harte Regeln (geprüft)

| Regel | Inhalt |
|---|---|
| S1 | Schichten des Backends wie oben |
| S2 | Schichten der Oberfläche wie oben |
| G1 | Keine Bibliotheken aus dem Netz (CDN, Google Fonts) in Quellen und Startseite |
| G2 | Keine Browser-Dialoge (alert, confirm, prompt) |
| G3 | Keine feste Fassung im Code; nur `version.json` |
| G4 | Architektur, Plan, Regeln, Fassung, die Dateien des Betriebs (compose.pi.yml, deploy/) und Handbuchseite mit Einrichtungsskript sind da |
| B1 | Durchleiter nur über Senderkennung oder Folge, nie über eine rohe Adresse aus der Oberfläche |
| B2 | TLS-Prüfung bleibt an (kein `verify=False`) |
| B3 | Kein Abruf fremder Dienste aus der Oberfläche (die Fassungserkennung fragt nur die eigene Startseite) |
| B4 | Keine CORS-Freigabe für alle Ursprünge (Backend, Vorschaltdienst, Vite, Compose) |
| B5 | Die App nicht veröffentlicht; nach außen nur der Vorschaltdienst |
| P1 | Protokoll statt `print` im Backend (Log `radiohub.*`, Wichtiges ins Protokoll der App); ausgenommen Befehle der Kommandozeile |
| K1 | Einstellungen aus einer Quelle: `os.environ` nur in `ort.py` (Orte) und `uebergang.py` (frühere Namen) |
| D1 | Schema nur in Stufen: kein `ALTER TABLE` außerhalb von `database.py` |

Dazu prüft der Haken jede vorgemerkte Datei auf gerade Zeichen und auf den Stil (kein `!important`, keine einseitigen
Streifen); die Marken der Gestaltung werden nur gemeldet, bis die Oberfläche in Etappe 2 auf die Bausteine des
Appkerns umzieht.

## Ausnahmen

Eine Ausnahme steht in `architektur/ausnahmen.toml` (Regel, Dateien, Grund, Ticket) und gilt erst, wenn der Nutzer am
Ticket der Pinnwand selbst "Ausnahme freigegeben: <Regel>" kommentiert. Ohne Verbindung zur Pinnwand gilt keine
Ausnahme. Nie `--no-verify`, nie den Haken umstellen; bei einem Befund die Ursache beheben.

## Regeln der kommenden Etappen

Diese Regeln erfüllt der Code heute noch nicht; sie kommen mit der Etappe, die sie erfüllbar macht, in
`architektur/regeln.toml`.

| Etappe | Regel |
|---|---|
| 2 Appkern-Grundlage | Ordner `frontend/` nach dem Schema des Appkerns (Teil 2c; `backend/` ist umgestellt); Backend-Schichten api, fach, anschluesse, modell; Antworten als Pydantic-Modelle statt Dicts |
| 2 Appkern-Grundlage | Oberfläche in TypeScript mit svelte-check ohne Fehler; Marken der Gestaltung scharf (`gestaltung.toml`), keine festen Farben, Schriftgrößen und Schriften; Darstellung mit Schriftstufen und Hell, Dunkel, System |
| 2 Appkern-Grundlage | Kein rohes `fetch` außerhalb der Datenschicht (heute an fünf Stellen an `api.js` vorbei); keine Adressen wie `localhost:9091` in der Oberfläche |
| 3 Filterung | Router ohne SQL: jede Abfrage über die Datenschicht; Sender nur über die Schnittstelle Senderquelle (Backend oder statisch für die Webversion) |
| 3 Filterung | Werbeprüfung nur mit der Senderkennung (heute nimmt `/api/ad-detection/check` noch eine `stream_url` aus der Oberfläche an) |
| 4 Player | Ein Tonausgang: nur die Wiedergabe greift auf das `<audio>`-Element zu; Zeitversatz und Aufnahme starten nur mit der Senderkennung (heute senden `startHLS` und die Aufnahme noch `stream_url`, das Backend öffnet sie mit FFmpeg) |
| 6 Übrige Bereiche | Kleine Dateien (höchstens 400 Zeilen je Baustein und Modul); Löschen nur mit Folgenvorschau und abschließender Bestätigung |
