# RadioHub: Architektur

Stand 17.11.2026 (RAD-5, Etappe 1; RAD-6, Teile 2b und 2c: Backend und Schale der Oberfläche auf dem Appkern; RAD-7,
Teil 3a: Backend der Filterung mit Senderdaten-Baustein und Senderquelle).
Dieses Dokument beschreibt Aufbau, Schichten und harte Regeln von RadioHub. Die Regeln stehen maschinenlesbar in
`architektur/regeln.toml`; der Git-Haken und das Ausrollen setzen sie durch. Entscheidungen und Etappen der
Überarbeitung stehen in `docs/umbau/PLAN.md`, der Befund davor in `docs/umbau/BEFUND.md`.

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
dienste         services/**                    Aufnahme, Puffer, Podcasts, Sender, Werbung, Zeitansage, Durchleiter;
   │                                           Senderquelle (services/senderquelle, siehe unten)
   │  darf ablage, grundlagen, senderdaten
ablage          ablage/**                      Port und Adapter für Aufnahmen und Folgen (Kellerwolke über den Zugang
   │                                           des Gerüsts, Speicher)
   │  darf grundlagen
grundlagen      config.py, database.py, storage.py, fassung.py, einstellungen.py, uebergang.py, ort.py

senderdaten     senderdaten/**                 Baustein ohne FastAPI und Datenbank: aus einem Datensatz des
                                               Senderverzeichnisses ein aufbereiteter Sender; bindet nichts aus der App
                                               ein (auch für das Skript der statischen Webversion, Etappe 3b)
```

Senderquelle (RAD-7, Entscheidungen 4 bis 6, 18, 19): eine Wahrheit für die Sichtbarkeit der Sender, die neue
Schnittstelle unter /api/radio und die alten Wege (/api/stations/search, /api/filters/*, /api/blocklist) lesen sie.

```
senderdaten/            sprachen (Code und deutscher Name, freier Text als eigener Eintrag; Tabelle sprachen.toml),
                        genres (gepflegte Abbildung genres.toml: Schreibweisen, Rauschen, Frequenzen, Jahrzehnte),
                        qualitaet (Codec, Bitrate in kbit/s, Stufe), dubletten (Gruppen, beste Variante); FASSUNG
services/senderquelle/  Datenschicht (Funktionen auf einer Verbindung, SQL nur hier):
                          bestand      stations und die Aufbereitung sender_index, sender_genre, sender_sprache,
                                       sender_spracheintrag, sender_tag, Volltextsuche sender_suche
                          regeln       lebende Regeln, je Art eine Abfrage der getroffenen Sender
                          sichtbarkeit Treffer, Sichtbarkeit, Vertreter je Gruppe, Gründe, Vorschau, Folgen
                          abfrage      Schnellfilter, Seitenzeiger (Sortierwert und uuid), Facetten
                          ausgeblendet ausgeblendete Sender, Einzelsperren, Freigaben, Kandidaten neuer Regeln
                          werbung      Werbeverdacht gewichtet (der Cache-Kopf allein zählt nicht)
                          alte_wege    die Wege der heutigen Oberfläche bis Etappe 3b
                          ueberfuehrung  heutige Sperren in Regeln (Werkzeug regeln_ueberfuehren)
                        dienst (asynchron: Lesen im Vorrat der Datenbank des Appkerns, jede Änderung in einer
                        Transaktion samt Sichtbarkeit), abgleich (Aufträge sender_abgleich und sender_aufbereiten)
routers/radio.py        Schnittstelle ohne SQL (Regel D2)
```

Sichtbar ist ein Sender, wenn er Favorit ist (dann als Ausnahme, auch wenn eine Regel trifft) oder nicht verschwunden
und von keiner eingeschalteten Regel getroffen ist; eine Freigabe hebt Regeln auf. Treffer stehen je Regel in
sender_ausblendung, auch für ausgeschaltete Regeln (ihre Zahlen bleiben sichtbar); Ein- und Ausschalten rechnet nur die
Sender der Regel und ihre Gruppen neu. Varianten eines Senders (gleiche Stream-Adresse oder gleicher bereinigter Name im
selben Land) bilden eine Gruppe, deren bester sichtbarer Sender der Vertreter in der gebündelten Liste ist.

Was das Gerüst des Appkerns übernimmt: Einstellungen (`einstellungen.AppEinstellungen`, eine Quelle: gespeichert, dann
Umgebung `RADIOHUB_*`, dann Vorgabe; fest `RADIOHUB_FEST_*` vom Ausrollen), Protokoll, Aufträge, Anmeldung mit dem Konto
der Kellerwolke, Sicherung, Auslieferung der Oberfläche. Seine Datenbank liegt in `data/appkern/radiohub.sqlite`, die des
Radios bleibt `data/radiohub.db` und kommt über die Datenbank des Appkerns in Stufen (`database.STUFEN`, Stufe 1 ist der
Bestand bis 0.15.6, Stufe 2 die Senderquelle). Frühere Namen und Formen der Einstellungen gelten über `uebergang.py`.
Die Senderquelle liest und schreibt über die Datenbank des Appkerns (`database.lesen`, `database.schreiben`), die
übrigen Dienste bis zu ihrem Neubau über `database.get_db`. Offene Fragen an den Appkern: eine Datei für beide (Name der
Datenbank im Gerüst wählbar) und mehrere Abfragen in einem Lesestand öffentlich (`Datenbank._lesen`, bis dahin an einer
Stelle in `database.lesen` genutzt).

Oberfläche (Svelte 5 mit TypeScript für neue Teile, `frontend/src`; svelte-check im Skript `check`):

```
oberflaeche     schale/**, components/**, App.svelte, main.ts
   │            schale/       Wurzel (Sitzung, Anmeldung, Koppeln, Einrichtung über den Appkern), Kopf mit
   │                          Pillen-Navigation, Darstellung, Konto, Meldung (Entwurf RAD-3)
   │            components/   die bisherigen Bereiche Radio, Aufnahmen, Podcasts, Einstellungen, Spieler und die
   │                          Telefonansichten, bis zu ihrem Neubau (Etappen 3, 4 und 6)
   │  darf logik
logik           lib/**        Zustand, Wiedergabe (playerEngine), Backend (api.js mit der Sitzung aus lib/sitzung.ts),
                              Router, Übersetzungen, Zeitpläne, Darstellung, Erkennung neuer Fassungen
```

Gestaltung in Schichten (Entscheidung 24): die Marken, Schale, Instrumente und Vorlagen des Appkerns
(`appkern-oberflaeche/stil.css`, `instrumente.css`, `vorlagen-alle-breiten.css`: jede Vorlage auch am Telefon), darauf
die Marken des Radios (`stil/radio-marken.css`, je Vorlage `stil/vorlagen/<name>.css`, `grund.css` für jede Vorlage ohne
eigene), Bausteine (`stil/bausteine.css`) und Anordnung (`stil/rechner.css`). Ein neues Thema braucht eine Marken-Datei
unter `stil/vorlagen/`. Die Darstellung (Vorlage, Thema Hell/Dunkel/System, Schriftstufe Normal/Groß/Sehr groß) gilt je
Gerät und wird vor dem Einhängen angewendet (`lib/darstellung-vorab.ts`, als Skript in den Kopf der Startseite gesetzt).

Brücke der alten Bereiche (`styles/bruecke.css`, bis zum Neubau): ihre Variablen `--hifi-*` und die der
Telefonansichten `--t-*` sind nur aus Marken abgeleitet; die Schriftstufe wirkt auf sie als Ganzes (`zoom` mit
`--rh-alt-zoom`), weil ihre Schriftgrößen und Breiten in Pixeln stehen. `styles/hifi-base.css` und
`styles/hifi-components.css` (nur noch genutzte Regeln) entfallen Bereich für Bereich. Klassen der Telefonansichten,
die der Appkern auch führt, tragen die Vorsilbe `tf-`.

Oberfläche und Backend nehmen den Appkern von GitHub am selben Commit (`frontend/package.json` und
`backend/requirements.txt`); das Ausrollen verweigert einen Stand, in dem die beiden abweichen oder die Oberfläche ihn
aus einer lokalen Datei nimmt (`tools/ausrollen.py`, `appkern_gebunden`).

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
| B6 | Werbeprüfung nur über die Senderkennung, die Adresse kommt aus der Datenbank |
| P1 | Protokoll statt `print` im Backend (Log `radiohub.*`, Wichtiges ins Protokoll der App); ausgenommen Befehle der Kommandozeile |
| K1 | Einstellungen aus einer Quelle: `os.environ` nur in `ort.py` (Orte) und `uebergang.py` (frühere Namen) |
| D1 | Schema nur in Stufen: kein `ALTER TABLE` außerhalb von `database.py` |
| D2 | Router ohne SQL: `routers/radio.py`, `filters.py`, `blocklist.py` rufen nur Dienste (die übrigen folgen mit ihrem Neubau) |
| S1 | dazu: der Senderdaten-Baustein bindet nichts aus der App ein |

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
| 2 Appkern-Grundlage | Backend-Schichten api, fach, anschluesse, modell; Antworten als Pydantic-Modelle statt Dicts (Ordner `frontend/` und `backend/` sind umgestellt, Teile 2b und 2c) |
| 3, 4 und 6 | Oberfläche ganz in TypeScript (svelte-check läuft schon, die alten Bereiche bleiben bis zum Neubau JavaScript); Marken der Gestaltung scharf (`gestaltung.toml`): keine festen Farben, Schriftgrößen und Schriften, sobald die Brücke entfällt (Schale und Darstellung mit Schriftstufen und Hell, Dunkel, System sind seit Teil 2c da) |
| 2 Appkern-Grundlage | Kein rohes `fetch` außerhalb der Datenschicht (heute an fünf Stellen an `api.js` vorbei); keine Adressen wie `localhost:9091` in der Oberfläche |
| 3b Webversion | Router ohne SQL für alle Router; Sender in der Oberfläche nur über die Schnittstelle Senderquelle (Backend oder statisch); die alten Wege und die Tabelle blocklist entfallen |
| 4 Player | Ein Tonausgang: nur die Wiedergabe greift auf das `<audio>`-Element zu; Zeitversatz und Aufnahme starten nur mit der Senderkennung (heute senden `startHLS` und die Aufnahme noch `stream_url`, das Backend öffnet sie mit FFmpeg) |
| 6 Übrige Bereiche | Kleine Dateien (höchstens 400 Zeilen je Baustein und Modul); Löschen nur mit Folgenvorschau und abschließender Bestätigung |
