# RAD-1: Befund vor dem Umbau (16.11.2026)

Stand: Git-Marke `vor-RAD-1` (4d54ac7), Frontend 0.14.2. Sicherung: `backups/2026-11-16-RAD-1/` (Pi und Mac).
Schwerpunkte des Nutzers: uneinheitliches Design, redundanter Code und zu wenige Bausteine, Filterung,
Zusammenspiel von Abspielleiste, Player, Komponenten und Streams, Telefon- und Weckeransicht modernisieren.

Pfade: FE = radiohub-frontend/src, BE = radiohub-backend/backend.

## 1. In der laufenden App beobachtet

- Direkter Aufruf und Neuladen jeder Adresse springt auf /radio zurück: die Sendersuche schreibt beim Start die
  Adresse (FE components/StationsTab.svelte:365).
- Beim Start blitzen OFFLINE und das fest eingebaute "NO STATIONS FOUND" (StationsTab.svelte:1131) statt eines
  Ladezustands.
- Ein Klick in der Sprachliste der Filter-Einstellungen schließt sofort dauerhaft aus, ohne Vorschau und Rückgängig.
- Telefonansicht: eigenes flaches Design (eigene Tokens `--t-*`), zeigt keine Favoriten trotz 69 gespeicherter.
- Reiter "Aufnahme"/"Podcast", Pfade /aufnahmen und /podcasts; Sprachnamen englisch und klein.

## 2. Design und Bausteine (Frontend)

- Zwei Designsysteme nebeneinander: von hifi-components.css (1857 Zeilen) sind rund 80 % tot; die echte Optik
  steckt dupliziert im Komponenten-CSS (Pill-Knopf 6x, `.action-btn` 9x mit abweichenden Werten, `section-label`
  4x, Suchfeld doppelt).
- 8 benutzte, aber undefinierte Variablen (`--hifi-text-muted` 15x, `--hifi-border`, `--hifi-red` ...).
- Rund 430 feste px-Schriftgrößen (113x 10px, 64x 9px, 15x 8px); keine Schriftstufen, kein Modus System,
  `data-theme="dark"` fest in index.html (Aufblitzen), Thema an drei Stellen umschaltbar.
- Feste Breiten (Seitenleiste 224px, Spalten 160/90/60, Spielerteile) schneiden bei größerer Schrift ab.
- Gott-Komponenten: StationsTab 2366 Zeilen / 27 API-Aufrufe, RecordingsTab 31, PodcastsTab 24, CutterView 1267,
  SetupSender 1203. Kein Typ (`@typedef`), rohes fetch an api.js vorbei an 5 Stellen.
- Mehrere Wahrheiten: Abos doppelt, Konfiguration doppelt geladen, Weiterleitungen schreiben `routeSegments`
  direkt, rund 22 verstreute localStorage-Schlüssel.
- Übersetzungen: 18 Sprachen fehlen je 130 Schlüssel (105x telefon.*), feste deutsche Texte in Ansichten.
- Löschen ohne Folgenvorschau an 7 Stellen (Sitzung, Segment, Datei, verwaiste Ordner, Abo, Kategorie, Ordner).
- Tot: Tour (Knopf auskommentiert, Engine läuft), Vintage-Thema, Roboto/Share-Tech, Entwürfe in dist,
  Google-Fonts-@import in public/mockups.

## 3. Filterung

- Fehler: Favoriten mit Sortierung nach Stimmen ergibt SQL-Fehler (BE services/cache.py:251) und ignoriert Suche,
  Land, Sperrliste, Seiten; Länder außerhalb der 30 größten fallen still weg, schränken aber ein; "Alle"/"Keine"
  bei Ländern vertauscht; X zum Zurücksetzen bleibt stehen; Werbe-Scan zielt auf localhost:9091; Freigabe per
  `LIKE %grund%` trifft fremde Einträge; Sprache/Tag als Teilstring ("german" trifft "swiss german"); Stufen von
  Bitrate und Stimmen werden zur Hülle verschmolzen; Bitrate mit drei Wahrheiten; Seiten ohne stabilen
  Nebenschlüssel; Kategorien aller Bereiche im Tuner; Auge startet ungefragt den Nachbarsender; Zähler zeigt
  geladene statt Treffer.
- Doppelte Wahrheit: Ausschlüsse wirken live UND als Schnappschuss in der Sperrliste (35.871 von 58.364 Sendern
  gesperrt, ohne Einzelgrund); Ausblenden dreifach (Auge, Schnappschuss, Werbeentscheidung).
- Leistung: Vollscan mit `LIKE %..%`, Sortierung ohne passenden Index, `/api/filters/hidden` liefert 36.000 Zeilen,
  4 bis 5 Anfragen je Seite.
- Keine Tests zu Suche, Filtern, Sperrliste, Kategorien, Werbung.
- Telefonsuche ignoriert alle Filter.

## 4. Player, Abspielleiste, Streams

- Das eine `<audio>` gehört der sichtbaren Oberfläche (HiFiPlayer bzw. Telefon); Ansichtswechsel verliert die
  Tonquelle. Schnitt-Ansicht und Zeitansage greifen direkt aufs Element.
- Kein Zustand "puffert", keine Medienereignisse; `isPlaying=true` vor erfolgreichem `play()`; kein Wiederverbinden
  beim Radio.
- Geräte stören sich: ein Puffer global, Telefon stoppt Puffer und Zeitversatz-Aufnahme des Rechners.
- Wettlauf beim Start ohne Lock (zwei ffmpeg im selben Ordner), Prozesslecks bei Stop während des Starts.
- Rückfall auf Direktstrom nutzt rohe URL statt Proxy (scheitert unter HTTPS still).
- Zeitversatz-Aufnahme kopiert halbe Segmente; Stop-Reihenfolge verliert die letzten Segmente.
- Titel aus drei Abfragen (HLS 2s, ICY 15s, Aufnahme 5s), 4 bis 6 Verbindungen je Sender; ICY-Logger ohne TLS.
- Lautstärke mit drei Schreibern, Wecklautstärke überschreibt Wunschwert; auf iOS wirkungslos.
- Playlist-Logik dreifach (Engine, Store, HiFiPlayer). Puffer läuft bei jedem Senderstart (CPU, Schreiblast).
- Tot: stream_buffer.py, timeshift_buffer.py, routers/buffer.py, Puffer-Endpunkte in stream.py, `_userModeOverride`.

## 5. Backend

- Datenverlust: erneutes Abonnieren löscht per `INSERT OR REPLACE` + CASCADE alle Folgen mit Hörstand
  (services/podcast.py:171).
- `/health` macht `PRAGMA integrity_check` über 566 MB alle 30 s.
- Sicherheit: CORS `*` mit Credentials, offener Proxy `/api/stream/proxy?url=` mit `verify=False` (SSRF ins
  Heimnetz), `/api/recordings/play?path=` ohne Bereichsschutz, XML ohne Schutz, Container als root.
- Keine Datenschicht: SQL in 15 von 24 Routern, keine Schemaversion, ALTER in try/except; Konfiguration aus vier
  Quellen; 124 Funktionen geben Dicts zurück, kein `response_model`; 129 print.
- Synchrones SQLite in async-Handlern blockiert die Schleife, die auch HLS bedient (Abgleich 58.000 Zeilen).
- Speicherzonen-API kann die Datenbank verlegen (danach leer); Restore-Skript lässt -wal/-shm liegen.
- 35 Tests grün (Ablage, Aufnahmen, Podcast-Download, Umzug, Wecker, Zeitansage).

## 6. Was gut ist und bleibt

- Ablage als Port und Adapter (BE ablage/), Fachfehler `AufnahmeFehler`, zentrale Fehlerhandler.
- PWA mit eingebetteten Symbolen, 17px-Eingabefelder am Telefon, keine Browser-Dialoge, keine CDN-Links in der App.
- Die HiFi-Optik selbst (Kopf mit Pillen-Navigation, LED-Lichtsprache, Displays, Drehregler, Spielerkanzel).

## 7. Repo und Hausregeln im Vergleich zu den neueren Projekten

Vorbilder: Appkern (tools/git-hooks, version.json, Vorlage appkern/vorlage/dateien), Atelier, Nachschlag,
Strukturblick, KuchenParty.

| Punkt | Radio heute | Lücke |
|---|---|---|
| Git-Haken | keiner, core.hooksPath leer; 3 von 265 Commits mit Kennung, 8 Betreffzeilen mit Ersatzschreibung | pre-commit und commit-msg nach Appkern, Kennung RAD-n |
| Versionierung | package.json 0.14.2 von Hand, Backend fest 0.8.0 (config.py:15) | version.json + tools/version.sh, eine Fassung für alle |
| Architekturregeln | nur README-Abschnitt | architektur/regeln.toml + docs/ARCHITEKTUR.md, im Haken und beim Ausrollen geprüft |
| Ausrollen | git pull + docker compose auf dem Pi, Override nur auf dem Pi | tools/ausrollen.sh + deploy/ausrollen.toml (sauberer Baum, gepusht, Tests, Sicherung, Fassungsprobe) |
| Handbuch | nur [[ziel]] radiohub in verbund.toml | docs/handbuch.md, einrichten.sh --probe, [[app]]-Eintrag, Apps/RadioHub.md |
| README, Lizenz, Spende | keine LICENSE im Wurzelordner, kein Spendenblock, Adressen veraltet | nach Vorlage |
| Typen und Prüfung | reines JS, kein svelte-check; ansicht.json ohne tools/ansicht.sh; kein Drehbuch | TypeScript + svelte-check, Rauchtest, Drehbuch |
| Netz und Sicherheit | 9091/9092 auf allen Schnittstellen (nur Override hilft), root, CORS *, keine Anmeldung | compose.pi.yml nach Vorbild, user 1000, Anmeldung über Appkern |
| Neue Fassung | gleichwertig, aber zusätzlich Abruf von raw.githubusercontent alle 6 h | Abruf nach außen streichen |
| PWA-Symbole | vollständig | keine |
| Sonstiges | kein gestaltung.toml, stellwerk.toml, ABNAHME.md, .dockerignore; Ordner radiohub-frontend/-backend | Schema des Appkerns |

## 8. Senderdaten (Auswertung der Sicherungskopie, nur lesend)

- Sprachfilter mit Teilstrings: Kürzel wie `ger`, `us`, `ar` in der Ausschlussliste (563 Einträge) treffen
  "german" usw. Folge: 3.413 von 3.583 deutschen Sendern gesperrt, darunter 25 der 69 Favoriten; sichtbar bleiben
  22.493 Sender, davon 85 % ohne Sprachangabe.
- Sperrgrund speichert je Sender die ganze Filterliste (bis 11,8 kB): 226 MB der rund 590 MB Datenbank.
- Senderbestand seit 14.06.2026 nicht abgeglichen; Verschwundene werden nie entfernt (`INSERT OR REPLACE`).
- Abgleich speichert 14 von 36 Feldern; verworfen u. a. languagecodes, geo_lat/geo_long, state, iso_3166_2, hls,
  ssl_error, clicktrend, lastcheckoktime, has_extended_info. `lastcheck` ist immer 1 (hidebroken).
- Qualität: rund 12.000 Dubletten (20 %), Bitrate 0 bei 21 %, 332 Bitraten in bps statt kbps, 37 % ohne Logo
  (1.237x Text "null"), 11.429 Tag-Varianten (Hip-Hop in vier Schreibweisen, 80er dreifach).
- Eigene Messung: Bitrate nur bei 1,75 % der Sender, Werbeprüfung bei 4,7 %; 189 von 190 Verdachtsfällen nur wegen
  `Cache-Control max-age=0` (schwaches Signal, betrifft 24 Favoriten). ICY-Titel werden nicht gespeichert.
- Favoritenprofil: überwiegend DE, öffentlich-rechtliches Wort- und Kulturprogramm, Klassik, 80er/90er,
  elektronische Nischen, gern hohe Qualität (6 verlustfreie). 43 Favoriten stehen selbst auf der Sperrliste.
- Tabelle favorites kopiert Senderfelder (veraltet) statt auf stations zu verweisen.
