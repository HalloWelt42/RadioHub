# RadioHub: Architektur

Stand 16.11.2026 (RAD-5, Etappe 1 der Überarbeitung). Dieses Dokument beschreibt Aufbau, Schichten und harte Regeln von
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
4. **Nach außen nur das Nötige.** Im Heimnetz ist nur der Vorschaltdienst erreichbar (HTTPS); Backend und nginx
   sprechen nur im eigenen Netz der Container. Der Durchleiter nimmt nur bekannte Sender und Folgen an.
5. **Erzwingen statt dran denken.** Was eine Regel ist, prüft der Haken; Ausnahmen gibt nur der Nutzer frei.

## Schichten heute

Backend (FastAPI, `radiohub-backend/backend`):

```
schnittstelle   routers/**, main.py            Endpunkte, Eingaben prüfen
   │  darf dienste, ablage, grundlagen
werkzeuge       umzug/**, werkzeuge/**         Befehle für Umzug und Pflege (python -m backend.umzug ...)
   │  darf dienste, ablage, grundlagen
dienste         services/**                    Aufnahme, Puffer, Podcasts, Sender, Werbung, Zeitansage, Durchleiter
   │  darf ablage, grundlagen
ablage          ablage/**                      Port und Adapter für Aufnahmen und Folgen (Kellerwolke, Speicher)
   │  darf grundlagen
grundlagen      config.py, database.py, storage.py, fassung.py, sender_merkmale.py
```

Oberfläche (Svelte 5, `radiohub-frontend/src`):

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
| G4 | Architektur, Plan, Regeln und Fassung sind da |

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
| 2 Appkern-Grundlage | Ordner `frontend/` und `backend/` nach dem Schema des Appkerns; Backend-Schichten api, fach, anschluesse, modell; Antworten als Pydantic-Modelle statt Dicts; Protokoll des Appkerns statt `print`; Konfiguration aus einer Quelle; Datenbank mit Versionsstufen statt `ALTER` in `try/except` |
| 2 Appkern-Grundlage | Oberfläche in TypeScript mit svelte-check ohne Fehler; Marken der Gestaltung scharf (`gestaltung.toml`), keine festen Farben, Schriftgrößen und Schriften; Darstellung mit Schriftstufen und Hell, Dunkel, System |
| 2 Appkern-Grundlage | Kein rohes `fetch` außerhalb der Datenschicht (heute an fünf Stellen an `api.js` vorbei); keine Adressen wie `localhost:9091` in der Oberfläche |
| 3 Filterung | Router ohne SQL: jede Abfrage über die Datenschicht; Sender nur über die Schnittstelle Senderquelle (Backend oder statisch für die Webversion) |
| 4 Player | Ein Tonausgang: nur die Wiedergabe greift auf das `<audio>`-Element zu; Zeitversatz und Aufnahme starten nur mit der Senderkennung (keine `stream_url` aus der Oberfläche) |
| 6 Übrige Bereiche | Kleine Dateien (höchstens 400 Zeilen je Baustein und Modul); Löschen nur mit Folgenvorschau und abschließender Bestätigung |
