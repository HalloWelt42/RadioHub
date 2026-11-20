# RAD-11: Bestand aller Einstellungen

Stand 21.11.2026, vor der Neugestaltung der Einstellungsseite. Jede Zeile unten ist eine Funktion, die im neuen Entwurf
wieder da sein oder ausdrücklich entfallen muss.

## Lesehilfe

- Datei:Zeile: Frontend relativ zu `frontend/src`, Backend relativ zu `backend/app` (mit Vorsilbe `backend/`).
- Ausgabe: PRO ist das Bauziel voll (`ziel/voll`, mit Backend und Anmeldung), Basic die Webversion (`ziel/web`, ohne
  Backend, eigene Angaben im Browser). "beide" heißt: derselbe Baustein läuft in beiden Ausgaben, nur die Ablage
  unterscheidet sich.
- Speicherorte:
  - "Tabelle config": Tabelle `config` in `radiohub.db` im Datenordner (Stand der Oberfläche, gilt für alle Geräte),
    geschrieben über `PUT /api/config` mit `{ updates: {...} }` (backend/routers/config.py:40, backend/services/config_service.py:68).
  - "Appkern-Einstellung": Feld von `AppEinstellungen` (backend/einstellungen.py:43), gespeichert in der Datenbank des
    Gerüsts `<Datenordner>/appkern/radiohub.sqlite`, sonst Umgebung `RADIOHUB_<FELD>`, fest mit `RADIOHUB_FEST_<FELD>`
    (dann 409 beim Ändern). Die Felder in `CONFIG_FELDER` (backend/einstellungen.py:115) sind zusätzlich über
    `/api/config` les- und schreibbar; alle Felder über die Schnittstelle des Appkerns `GET` und `PATCH /api/v1/einstellungen`.
  - "Basic-Angaben": `localStorage`-Schlüssel `radiohub.web.angaben` (ein JSON mit `favoriten`, `bewertungen`, `regeln`,
    `sperren`, `freigaben`, `laender_leiste`; lib/radio/statisch/angaben.ts:27, lib/radio/statisch/statische-quelle.ts:21).

## Übersicht

| Bereich | Ort heute | Einstellungen und Bedienelemente | Ausgabe |
| --- | --- | --- | --- |
| Allgemein | Einstellungen > Allgemein | 6, dazu 5 Lese- und Aktionsreiter (7 Zeilen, davon 3 Bedienelemente) | PRO |
| Radio | Einstellungen > Radio (7 Reiter) | 33 | beide (Reiter je nach Fähigkeit) |
| Podcast | Einstellungen > Podcast | 2 | PRO |
| Aufnahmen | Einstellungen > Aufnahmen | 11 | PRO |
| Speicher | Einstellungen > Speicher | 6 | PRO |
| Dienste | Einstellungen > Dienste | 6 | PRO |
| Darstellung und Konto | Tafel im Kopf, Blatt am Telefon | 6 | beide (Konto nur PRO) |
| Telefon-Einstellungen | Blatt am Telefon | 13, dazu 2 eingebettete Teile | beide (Teile nur PRO oder nur Basic) |
| Wecker | /wecker am Telefon | 15 | beide (Folge als Quelle nur PRO) |
| Weckansicht | Weckansicht am Telefon quer | 3 | beide |
| Kanzel und Gerätezustand | Abspielleiste, Listen | 10 | beide (Zeitversatz, Tempo nur PRO) |
| Server ohne Bedienelement | nur Schnittstelle des Appkerns | 11 | PRO |
| Hausempfang | noch nicht gebaut | 0 | - |
| Summe | | 122 | |

Gezählt ist je Tabellenzeile ein Bedienelement, das etwas einstellt oder auslöst; reine Anzeigen stehen in den Tabellen,
zählen aber nicht mit (Allgemein: die Lesereiter getrennt angegeben; im Telefonblatt zählen die eingebetteten Teile Darstellung und Eigene Daten nicht doppelt).

## Aufbau und Wege

| Funktion | Verhalten | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- |
| Pfad | `/einstellungen/<bereich>/<reiter>`; Bereich-Kennung `settings` im Zustand | beide | lib/router.js:32 |
| Bereiche (Leiste links) | allgemein, radio, podcast, aufnahmen, speicher, dienste | PRO | components/SettingsTab.svelte:13 |
| Vorgabe ohne Bereich | `/einstellungen` führt zu `/einstellungen/allgemein/einstellungen` | PRO | components/SettingsTab.svelte:31, lib/router.js:49 |
| Vorgabe-Reiter je Bereich | allgemein: einstellungen, radio: regeln; die übrigen Bereiche haben keinen Reiter im Pfad | beide | lib/router.js:49 |
| Ungültiger Reiter in Allgemein | fällt auf einstellungen zurück, `/einstellungen/allgemein` wird ergänzt | PRO | components/setup/SetupAllgemein.svelte:19, :28 |
| Ungültiger oder früherer Reiter in Radio | `filter` wird `regeln`, `sender` wird `werbung`, sonst `regeln`; Adresse wird ersetzt | beide | components/setup/SetupRadio.svelte:27, :33 |
| Alte Hash-Adressen | `#/setup/...` wird `/einstellungen/...` | beide | lib/router.js:44 |
| Basic | nur Einstellungen > Radio; jeder andere Bereich führt zu `/einstellungen/radio/regeln` | Basic | schale/WebWurzel.svelte:34, :54 |
| Sprung aus dem Kopf | Herz führt zu `/einstellungen/allgemein/bedanken` (Basic: externe Spendenseite) | PRO | schale/Kopf.svelte:74 |
| Sprung aus der Radioliste | "Regeln ansehen" zu `/einstellungen/radio/regeln` | beide | components/radio/Werkzeugleiste.svelte:47, :79 |
| Sprung aus der Seitenleiste | Länder wählen zu `/einstellungen/radio/laender`, Kategorien verwalten zu `/einstellungen/radio/kategorien` | beide, Kategorien PRO | components/radio/Seitenleiste.svelte:82, :120 |
| Sprung aus Podcasts | "Abstand ändern" zu `/einstellungen/podcast` | PRO | components/podcast/PodcastWerkzeug.svelte:90, components/podcast/PodcastAnsicht.svelte:195 |
| Telefon | Knopf Einstellungen öffnet ein Blatt ohne eigene Adresse | beide | components/telefon/Telefon.svelte:142, :174 |
| Ziffern 1 bis n | wählen die Bereiche der Navigation, Einstellungen ist die 4 (Basic: 2) | beide | schale/tastatur.ts:13 |

## 1 Allgemein (PRO)

Hülle mit Unterreitern: components/setup/SetupAllgemein.svelte:42. Werte holt `GET /api/config` beim Öffnen des Reiters.

### 1.1 Reiter Einstellungen

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Bedientöne: Klicktöne | Schalter (Pillenknopf mit Leuchte) | an, aus; Vorgabe an | `PUT /api/config` Schlüssel `ui_click_sounds`, Tabelle config; beim Start gelesen (lib/store.svelte.js:111) | PRO | components/setup/SetupAllgemein.svelte:199 |
| Entwickler-Modus | Schalter (Pillenknopf, Text AN oder AUS) | an, aus; Vorgabe aus; zeigt Güte und Lücken in Aufnahmen | `localStorage` `radiohub_devmode` (lib/store.svelte.js:29, :103) | PRO | components/setup/SetupAllgemein.svelte:213 |
| Sprache | Auswahl (20 Knöpfe mit Flagge und Kürzel) | de, en, fr, es, it, pt, nl, pl, cs, sk, da, sv, no, fi, hu, ro, tr, ru, ja, zh; Vorgabe de | `PUT /api/config` Schlüssel `language`, Tabelle config (backend/services/config_service.py:21) | PRO | components/setup/SetupAllgemein.svelte:233, lib/i18n.js:121 |
| Zeitversatz-Puffer: kleinste Bitrate | Drehregler | 32 bis 128 kbps, Schritt 16; Vorgabe 32 (Backend erlaubt 8 bis 512) | `PUT /api/config` `hls_min_bitrate`, Appkern-Einstellung (backend/einstellungen.py:83); wirkt in backend/routers/hls.py:57 | PRO | components/setup/SetupAllgemein.svelte:254 |
| Zeitversatz-Puffer: größte Bitrate | Drehregler | 64 bis 320 kbps, Schritt 32; Vorgabe 320 (Backend 8 bis 512) | `PUT /api/config` `hls_max_bitrate`, Appkern-Einstellung (backend/einstellungen.py:86) | PRO | components/setup/SetupAllgemein.svelte:260 |
| HLS-Aufnahme: Rückblick | Drehregler | 1 bis 120 min, Schritt 1; Vorgabe 5 (nur im Frontend, lib/store.svelte.js:75) | `PUT /api/config` `hls_rec_lookback_minutes`, Tabelle config; gelesen nur beim Öffnen dieses Reiters, wirkt in lib/playerEngine.js:824 | PRO | components/setup/SetupAllgemein.svelte:282 |

### 1.2 Reiter Tastatur, Info, Lizenz, Recht, Bedanken

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Tastaturkürzel | Anzeige (Tabelle, 11 Tasten in 3 Gruppen) | Leertaste, S, M, Pfeile, 1 bis 4; fest im Code | - | PRO | components/setup/SetupAllgemein.svelte:51, :310 |
| Technische Informationen | Anzeige (Markdown und Beispiel-Marken) | Text aus `/legal/<sprache>/info.md`, Rückfall en, de | statische Datei frontend/public/legal | PRO | components/setup/SetupAllgemein.svelte:328 |
| Lizenz | Anzeige (Markdown) | `/legal/<sprache>/lizenz.md` | statische Datei | PRO | components/setup/SetupAllgemein.svelte:425 |
| Datenschutz und Nutzungsbedingungen | Anzeige (Markdown) | `datenschutz.md` und `agb.md` hintereinander | statische Datei | PRO | components/setup/SetupAllgemein.svelte:445 |
| Bedanken: Spendenseite | Verweis (Knopf) | öffnet `ko-fi.com/HalloWelt42` in neuem Fenster | - | PRO | components/setup/SetupSpende.svelte:44 |
| Bedanken: Kryptowährung wählen | Auswahl (3 Karten `BTC`, `DOGE`, `ETH`) | keine Vorwahl; zeigt Adresse und Bildcode | fest im Code | PRO | components/setup/SetupSpende.svelte:9, :59 |
| Bedanken: Adresse kopieren | Knopf | kopiert in die Zwischenablage | - | PRO | components/setup/SetupSpende.svelte:83 |

## 2 Radio (Einstellungen > Radio)

Hülle mit Reitern über dem Rollfeld, schon im neuen Aussehen: components/setup/SetupRadio.svelte:18. Welche Reiter es
gibt, sagt `senderquelle.faehig` (PRO: lib/radio/backend.ts:67, Basic: lib/radio/statisch/statische-quelle.ts:32).

### 2.1 Reiter Ausschlussregeln (beide)

Oben das Gerät Bestand (gesamt, sichtbar, durch Regeln aus, verschwunden; nur Anzeige, components/radio/einstellungen/RegelnReiter.svelte:88).

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Art der Regel | Segmentwahl | Sprache, Genre, Tag, Mindeststimmen, Werbung, Meine Einschätzung, Einzelsender; Vorgabe Sprache | - (Entwurf) | beide, Werbung nur PRO | components/radio/einstellungen/NeueRegel.svelte:23, :120 |
| Wert suchen und wählen (Sprache, Genre, Tag, Einzelsender) | Eingabe mit Trefferliste, Mehrfachwahl als Chips (Einzelsender: einer) | höchstens 8 Treffer; ohne Wahl gilt der beste Treffer | Treffer: PRO `GET /api/radio/regeln/kandidaten`; Basic aus der Senderliste | beide | components/radio/einstellungen/NeueRegel.svelte:137, :148 |
| Meine Einschätzung wählen | Liste (Mehrfachwahl) | Sehr gut, Gut, Geht so, Werbung, Religiös und weitere | wie oben | beide | components/radio/einstellungen/NeueRegel.svelte:50, :148 |
| Ausblenden bei Stimmen | Schieber mit Raster | unter 1, 3, 5, 10, 25, 50, 100; Vorgabe 1 | - (Entwurf) | beide | components/radio/einstellungen/NeueRegel.svelte:26, :127 |
| Werbeverdacht ab | Wahl | eigene Entscheidung, hoch, mittel, jeder Verdacht; Vorgabe hoch | - (Entwurf) | PRO | components/radio/einstellungen/NeueRegel.svelte:27, :131 |
| Vorschau | Anzeige (Zahl, Favoriten, Beispiele) | zeigt vorher, was ausgeblendet würde | PRO `POST /api/radio/regeln/vorschau` | beide | components/radio/einstellungen/NeueRegel.svelte:162 |
| Regel anlegen | Knopf (danach Band mit Rückgängig) | - | PRO `POST /api/radio/regeln`, Tabellen `regel` und `sender_ausblendung`; Einzelsender `POST /api/radio/sperren`, Tabelle `sender_sperre`; Basic: Basic-Angaben | beide | components/radio/einstellungen/NeueRegel.svelte:194 |
| Verwerfen | Knopf | leert den Entwurf | - | beide | components/radio/einstellungen/NeueRegel.svelte:195 |
| Regel an oder aus | Schalter je Regel (Band mit Rückgängig) | an, aus | PRO `PATCH /api/radio/regeln/{id}`, Tabelle `regel`; Basic-Angaben | beide | components/radio/einstellungen/RegelZeile.svelte:58 |
| Regel entfernen | Knopf mit Rückfrage und Folgenvorschau | - | PRO `GET /api/radio/regeln/{id}/folgen`, dann `DELETE /api/radio/regeln/{id}?bestaetigt=true` | beide | components/radio/einstellungen/RegelZeile.svelte:62 |
| Weitere Regeln laden | Knopf (Nachladen) | 40 je Schritt | - | beide | components/radio/einstellungen/RegelnReiter.svelte:110 |

### 2.2 Reiter Ausgeblendete Sender (beide)

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Ausgeblendete durchsuchen | Eingabe (Suche, 250 ms entprellt) | frei; leer | - (Abfrage PRO `POST /api/radio/ausgeblendet`) | beide | components/radio/einstellungen/AusgeblendetReiter.svelte:79 |
| Grund | Auswahl | Alle Gründe oder eine Regel mit Anzahl; Vorgabe alle | - | beide | components/radio/einstellungen/AusgeblendetReiter.svelte:82 |
| Freigeben | Knopf je Sender (Band mit Rückgängig) | - | PRO `POST /api/radio/freigaben`, Tabelle `sender_freigabe`; Basic-Angaben | beide | components/radio/einstellungen/AusgeblendetReiter.svelte:100 |
| Wieder aus | Knopf je freigegebenem Sender | - | PRO `DELETE /api/radio/freigaben/{uuid}`; Basic-Angaben | beide | components/radio/einstellungen/AusgeblendetReiter.svelte:98 |
| Zurück, Weiter | Knöpfe (Seiten) | 25 je Seite | - | beide | components/radio/einstellungen/AusgeblendetReiter.svelte:110, :112 |

### 2.3 Reiter Länder der Seitenleiste (beide)

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Land suchen | Eingabe | frei | - | beide | components/radio/einstellungen/LaenderReiter.svelte:45 |
| Land in der Seitenleiste | Kontrollkästchen je Land (Mehrfachwahl), nach Senderzahl sortiert | Ländercodes; Vorgabe keine Wahl, dann stehen alle Länder da; speichert 400 ms nach der letzten Änderung | PRO `PUT /api/config` `sidebar_countries`, Tabelle config (lib/radio/backend.ts:295); Basic-Angaben `laender_leiste` | beide | components/radio/einstellungen/LaenderReiter.svelte:52 |
| Auswahl leeren | Knopf | setzt auf keine Wahl | wie oben | beide | components/radio/einstellungen/LaenderReiter.svelte:47 |

### 2.4 Reiter Werbeerkennung (PRO)

Oben das Gerät Stand (geprüft, sauber, verdächtig, Werbung aus; `GET /api/ad-detection/summary/overview`, nur Anzeige).

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Alle prüfen | Knopf mit Fortschritt | Runden zu 50 Sendern, bis keiner übrig ist; nur wenn die Erkennung an ist | `GET /api/ad-detection/scan-stream?batch_size=50`, Tabellen `station_ad_status`, `ad_detections_log` | PRO | components/radio/einstellungen/WerbungReiter.svelte:98 |
| Stopp | Knopf (während der Prüfung) | bricht ab | - | PRO | components/radio/einstellungen/WerbungReiter.svelte:96 |
| Alle ausblenden | Knopf | entscheidet alle Verdächtigen als Werbung | `POST /api/ad-detection/decide` (action block) je Sender, Tabelle `station_ad_status` | PRO | components/radio/einstellungen/WerbungReiter.svelte:115 |
| Alle keine Werbung | Knopf | nimmt den Verdacht bei allen zurück | `POST /api/ad-detection/decide` (action allow) | PRO | components/radio/einstellungen/WerbungReiter.svelte:116 |
| Ausblenden, Keine Werbung | Knöpfe je Verdächtigem | höchstens 100 Zeilen sichtbar | wie oben | PRO | components/radio/einstellungen/WerbungReiter.svelte:126, :127 |
| Werbeerkennung | Schalter | an, aus; Vorgabe an | `PUT /api/config` `ad_detection_enabled`, Tabelle config; gelesen in backend/services/ad_detector.py:365 | PRO | components/radio/einstellungen/WerbungReiter.svelte:140 |
| Adressprüfung | Schalter (nur bei Erkennung an) | an, aus; Vorgabe an | `ad_detection_methods` enthält `url_check`, Tabelle config | PRO | components/radio/einstellungen/WerbungReiter.svelte:143 |
| Serverprüfung | Schalter (nur bei Erkennung an) | an, aus; Vorgabe an | `ad_detection_methods` enthält `header_check`, Tabelle config | PRO | components/radio/einstellungen/WerbungReiter.svelte:145 |
| Ab wann verdächtig | Schieber mit Raster | 40, 50, 60, 70, 80, 90, 100 %; Vorgabe 80 % | `ad_detection_threshold`, Tabelle config | PRO | components/radio/einstellungen/WerbungReiter.svelte:147 |

### 2.5 Reiter Senderverzeichnis, Abgleich (PRO)

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Letzter Lauf, Uhrzeit | Anzeige | Uhrzeit aus der Appkern-Einstellung `abgleich_uhrzeit` (Vorgabe 04:30), hier nicht änderbar | `GET /api/radio/abgleich` | PRO | components/radio/einstellungen/AbgleichReiter.svelte:61, :62 |
| Jetzt abgleichen | Knopf mit Auftragsfortschritt (alle 2 s abgefragt) | gesperrt, solange ein Auftrag läuft | `POST /api/radio/abgleich` startet einen Auftrag des Appkerns, Stand über `/auftraege/{id}` | PRO | components/radio/einstellungen/AbgleichReiter.svelte:76 |

### 2.6 Reiter Kategorien (PRO, altes Aussehen)

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Neue Kategorie | Knopf, dann Eingabe Name mit Speichern und Abbrechen (Eingabe, Escape) | Name nicht leer | `POST /api/categories` (scope radio), Tabelle `categories` (backend/routers/categories.py:139) | PRO | components/setup/SetupKategorien.svelte:116, :131, :140 |
| Bearbeiten (umbenennen) | Knopf je Kategorie | - | `PUT /api/categories/{id}` (backend/routers/categories.py:157) | PRO | components/setup/SetupKategorien.svelte:161 |
| Löschen | Knopf je Kategorie, ohne Rückfrage | - | `DELETE /api/categories/{id}`, entfernt Zuordnungen in `category_stations` mit (backend/routers/categories.py:187) | PRO | components/setup/SetupKategorien.svelte:162 |

### 2.7 Reiter Eigene Daten (Basic)

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Als Datei sichern | Knopf | lädt `radiohub-eigene-daten-<datum>.json` herunter | liest Basic-Angaben | Basic | components/radio/einstellungen/DateiReiter.svelte:79 |
| Datei einspielen | Knopf, Dateiwahl, Rückfrage mit Folgenvorschau (was ersetzt wird) | nur JSON | ersetzt Basic-Angaben | Basic | components/radio/einstellungen/DateiReiter.svelte:80, :84 |

## 3 Podcast (PRO)

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Auto-Aktualisierung | Schalter (Text AKTIV oder AUS) | an, aus; Vorgabe an | `PUT /api/config` `podcast_auto_refresh`, Appkern-Einstellung (backend/einstellungen.py:93); wirkt in backend/services/podcast.py:58 | PRO | components/setup/SetupPodcast.svelte:63 |
| Aktualisierungsintervall | Drehregler | 1 bis 48 h, Schritt 1; Vorgabe 6 h; gespeichert in Sekunden (Backend 60 s bis 7 Tage) | `PUT /api/config` `podcast_refresh_interval`, Appkern-Einstellung (backend/einstellungen.py:95) | PRO | components/setup/SetupPodcast.svelte:85 |

## 4 Aufnahmen (PRO)

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Neuer Ordner | Knopf, öffnet Eingabe | - | - | PRO | components/setup/SetupAufnahmen.svelte:174 |
| Ordnername | Eingabe (Eingabe speichert, Escape bricht ab) | nicht leer, eindeutig | `POST /api/recording/folders`, Tabelle `recording_folders` (backend/routers/recording_folders.py:47) | PRO | components/setup/SetupAufnahmen.svelte:186 |
| Speichern, Abbrechen | Knöpfe | - | wie oben, beim Bearbeiten `PUT /api/recording/folders/{id}` | PRO | components/setup/SetupAufnahmen.svelte:195, :198 |
| Ordner aktivieren (neue Aufnahmen gehen dorthin) | Knopf je Ordner | genau einer aktiv oder keiner | `PUT /api/recording/folders/{id}/activate`, Spalte `is_active` | PRO | components/setup/SetupAufnahmen.svelte:231 |
| Stammverzeichnis (keinen Ordner aktiv) | Knopf | Vorgabe: kein Ordner aktiv | `PUT /api/recording/folders/deactivate` | PRO | components/setup/SetupAufnahmen.svelte:210 |
| Bearbeiten (umbenennen) | Knopf je Ordner | - | `PUT /api/recording/folders/{id}` (backend/routers/recording_folders.py:130) | PRO | components/setup/SetupAufnahmen.svelte:233 |
| Löschen | Knopf je Ordner, ohne Rückfrage | Backend lehnt ab, wenn Aufnahmen darin liegen | `DELETE /api/recording/folders/{id}` (backend/routers/recording_folders.py:72) | PRO | components/setup/SetupAufnahmen.svelte:234 |
| Ignorierte ICY-Titel: Muster | Eingabe (Eingabe fügt hinzu) | frei | - | PRO | components/setup/SetupAufnahmen.svelte:261 |
| Art des Musters | Auswahl | Exakt, Enthält; Vorgabe Exakt | - | PRO | components/setup/SetupAufnahmen.svelte:268 |
| Hinzufügen | Knopf | - | `POST /api/recording/icy-ignore`, Tabelle `icy_title_ignore` (backend/routers/recording.py:312) | PRO | components/setup/SetupAufnahmen.svelte:272 |
| Löschen je Muster | Knopf, ohne Rückfrage, auch für Muster der Quelle System | - | `DELETE /api/recording/icy-ignore/{id}` (backend/routers/recording.py:334) | PRO | components/setup/SetupAufnahmen.svelte:292 |
| Liste der Muster | Anzeige (Muster, Typ, Quelle System oder Benutzer) | - | `GET /api/recording/icy-ignore` | PRO | components/setup/SetupAufnahmen.svelte:279 |

## 5 Speicher (PRO)

Zonen fest im Backend: Datenbank, Cache/Buffer, Konfiguration (backend/storage.py:33, :40).

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Aktualisieren | Knopf | lädt Zonen, Belegung, Dateizahl | `GET /api/storage/zones` | PRO | components/setup/SetupSpeicher.svelte:88 |
| Pfad ändern | Knopf (Stift) je Zone | - | - | PRO | components/setup/SetupSpeicher.svelte:122 |
| Pfad | Eingabe (Eingabe prüft, Escape bricht ab) | absoluter Pfad; Vorgabe Datenordner beziehungsweise `<Datenordner>/cache` | - | PRO | components/setup/SetupSpeicher.svelte:129 |
| Prüfen | Knopf | meldet beschreibbar, frei, angelegt | `GET /api/storage/validate?path=` (legt den Ordner an) | PRO | components/setup/SetupSpeicher.svelte:136 |
| Speichern | Knopf (erst nach erfolgreicher Prüfung) | verschiebt keine Daten | `PUT /api/storage/zones/{zone}`, Datei `storage.json` im Datenordner oder `STORAGE_CONFIG` (backend/storage.py:140, :225) | PRO | components/setup/SetupSpeicher.svelte:159 |
| Abbrechen | Knopf | - | - | PRO | components/setup/SetupSpeicher.svelte:158 |

## 6 Dienste (PRO)

Dienste fest im Backend (backend/routers/services.py:16): änderbar `radio_browser` (mehrere Adressen), `itunes_search`,
`fyyd_search`; nur Anzeige Podcast-Feeds, ICY-Titel, Werbeerkennung.

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Aktualisieren | Knopf | - | `GET /api/services` | PRO | components/setup/SetupDienste.svelte:115 |
| Endpunkt ändern | Knopf (Stift) je änderbarem Dienst | - | - | PRO | components/setup/SetupDienste.svelte:161 |
| Adressen des Senderverzeichnisses | mehrzeilige Eingabe, eine Adresse je Zeile | Vorgabe drei Server (backend/einstellungen.py:39) | `PUT /api/services/radio_browser`, Appkern-Einstellung `service_radio_browser_servers` | PRO | components/setup/SetupDienste.svelte:169 |
| Adresse der Podcast-Suche (zwei Dienste) | Eingabe (Eingabe speichert) | Vorgaben backend/einstellungen.py:107, :109 | `PUT /api/services/{id}`, Appkern-Einstellungen `service_itunes_search_url`, `service_fyyd_search_url` | PRO | components/setup/SetupDienste.svelte:177 |
| Standard | Knopf, ohne Rückfrage | setzt auf die Vorgabe | `POST /api/services/{id}/reset` (backend/routers/services.py:142) | PRO | components/setup/SetupDienste.svelte:187 |
| Speichern, Abbrechen | Knöpfe | - | `PUT /api/services/{id}` (backend/routers/services.py:120) | PRO | components/setup/SetupDienste.svelte:186, :190 |

## 7 Darstellung und Konto (außerhalb der Seite)

Am Rechner die Tafel hinter dem Knopf Darstellung im Kopf (schale/Kopf.svelte:103), am Telefon im Einstellungsblatt
(components/telefon/TelefonEinstellungen.svelte:156). Gilt je Gerät sofort, angewendet schon vor dem Einhängen
(lib/darstellung-vorab.ts:35).

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Vorlage | Auswahl | Klassisch, Futur, Glas, Papyrus, Klar, Plakat, HiFi (aus dem Appkern); Vorgabe HiFi | `localStorage` `appkern_vorlage` | beide | schale/Darstellung.svelte:16, lib/darstellung-vorab.ts:25 |
| Thema | Segmentwahl | Hell, Dunkel, System; Vorgabe System; früherer Schlüssel `radiohub-theme` wird übernommen | `localStorage` `radiohub_thema` | beide | schale/Darstellung.svelte:22 |
| Schrift kleiner, größer | zwei Knöpfe mit Anzeige der Stufe | Normal, Groß, Sehr groß; Vorgabe Normal (`mittel`) | `localStorage` `radiohub_schrift` | beide | schale/Darstellung.svelte:31, :34 |
| Konto: Abmelden | Knopf (bei Anmeldung mit Passwort), ohne Rückfrage | - | Sitzung des Appkerns | PRO | schale/Konto.svelte:32 |
| Konto: Trennen | Knopf mit Rückfrage (gekoppeltes Gerät) | - | Sitzung des Appkerns | PRO | schale/Konto.svelte:30, :36 |
| Verweis auf PRO | Verweis BASIC im Kopf und im Telefonblatt | - | - | Basic | schale/Kopf.svelte:78, components/telefon/TelefonEinstellungen.svelte:161 |

Anzeige ohne Bedienung in der Tafel: Kontoname, Art der Anmeldung, Fassung (schale/Konto.svelte:26).

## 8 Telefon: Einstellungsblatt (außerhalb der Seite)

components/telefon/TelefonEinstellungen.svelte; geöffnet über components/telefon/Telefon.svelte:142. Zeitansage und
Wecker gibt es in beiden Ausgaben (schale/WebWurzel.svelte:19).

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Bildschirm wach halten | Kontrollkästchen (gesperrt ohne Unterstützung) | an, aus; Vorgabe aus | `localStorage` `radiohub_wach_halten` (lib/telefon/wachHalten.svelte.js:7) | beide | components/telefon/TelefonEinstellungen.svelte:99 |
| Zeitansage | Kontrollkästchen | an, aus; Vorgabe an | `localStorage` `radiohub_zeitansage` (lib/telefon/zeitansage.svelte.js:16) | beide | components/telefon/TelefonEinstellungen.svelte:109 |
| Alle wie viele Minuten | Wahl (5 Knöpfe) | 5, 10, 15, 30, 60; Vorgabe 5 | `localStorage` `radiohub_zeitansage_plan` (JSON abstand, von, bis, bedingung; lib/telefon/zeitplan.js:12) | beide | components/telefon/TelefonEinstellungen.svelte:116 |
| Zeitraum von, bis | zwei Auswahlen | leer oder 00:00 bis 23:30 im 30-Minuten-Raster; Vorgabe leer (rund um die Uhr) | wie oben | beide | components/telefon/TelefonEinstellungen.svelte:124 |
| Wann | Wahl (2 Knöpfe) | Nur mit Wecker, Immer; Vorgabe Nur mit Wecker | wie oben | beide | components/telefon/TelefonEinstellungen.svelte:135 |
| Zeitansage bei Nachtrot | Wahl (3 Knöpfe) | Normal, Leise, Aus; Vorgabe Leise | `localStorage` `radiohub_zeitansage_nachts` | beide | components/telefon/TelefonEinstellungen.svelte:142 |
| Bausteine erzeugen | Knopf (nur wenn Bausteine fehlen) | - | `POST /api/zeitansage/erzeugen`, Stand `GET /api/zeitansage`; Ablage in der Kellerwolke | PRO | components/telefon/TelefonEinstellungen.svelte:149 |
| Stadt suchen | Eingabe mit Knopf Suchen, Trefferliste | mindestens 2 Zeichen | `GET /api/wecker/orte?q=` (braucht die Appkern-Einstellung `ortssuche_adresse`) | PRO | components/telefon/TelefonEinstellungen.svelte:172, :179 |
| Meinen Standort übernehmen | Knopf (Standort des Geräts) | speichert sofort | wie Speichern | beide | components/telefon/TelefonEinstellungen.svelte:184 |
| Ort: Name | Eingabe | frei | wie Speichern | beide | components/telefon/TelefonEinstellungen.svelte:185 |
| Ort: Breite | Eingabe (Zahl, Komma erlaubt) | -90 bis 90; Vorgabe leer | wie Speichern | beide | components/telefon/TelefonEinstellungen.svelte:187 |
| Ort: Länge | Eingabe (Zahl) | -180 bis 180; Vorgabe leer | wie Speichern | beide | components/telefon/TelefonEinstellungen.svelte:188 |
| Ort speichern | Knopf | - | PRO `PUT /api/wecker/ort`, Tabelle config Schlüssel `ort_name`, `ort_breite`, `ort_laenge` (backend/routers/wecker.py:113); Basic `localStorage` `radiohub_wecker_ort` (lib/telefon/weckerablage-browser.ts:9) | beide | components/telefon/TelefonEinstellungen.svelte:190 |
| Eigene Daten | eingebetteter Reiter Eigene Daten (siehe 2.7) | - | Basic-Angaben | Basic | components/telefon/TelefonEinstellungen.svelte:157 |
| Darstellung und Konto | eingebettet (siehe 7) | - | - | beide, Konto PRO | components/telefon/TelefonEinstellungen.svelte:156 |

Anzeige ohne Bedienung: Stand der Ablage (`GET /api/storage/ablage`, PRO, components/telefon/TelefonEinstellungen.svelte:195).

## 9 Wecker (Telefon, /wecker)

components/telefon/TelefonWeckerListe.svelte. PRO: Tabelle `wecker` über `/api/wecker` (backend/routers/wecker.py:121
bis :147); Basic: `localStorage` `radiohub_wecker` (lib/telefon/weckerablage-browser.ts:8).

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Wecker an oder aus | Kontrollkästchen je Wecker | an, aus | PRO `PUT /api/wecker/{id}`; Basic `radiohub_wecker` | beide | components/telefon/TelefonWeckerListe.svelte:172 |
| Wecker bearbeiten | Zeile antippen | - | - | beide | components/telefon/TelefonWeckerListe.svelte:164 |
| Neuer Wecker | Knopf | Vorgabe 07:00, Mo bis Fr, erster Favorit | - | beide | components/telefon/TelefonWeckerListe.svelte:29, :176 |
| Uhrzeit: Stunde | Auswahl | 00 bis 23; Vorgabe 07 | Feld `zeit` | beide | components/telefon/TelefonWeckerListe.svelte:97 |
| Uhrzeit: Minute | Auswahl | 00 bis 59; Vorgabe 00 | Feld `zeit` | beide | components/telefon/TelefonWeckerListe.svelte:101 |
| Tage | Mehrfachwahl (7 Knöpfe) | Mo bis So; Vorgabe Mo bis Fr | Feld `tage` | beide | components/telefon/TelefonWeckerListe.svelte:108 |
| Quelle | Wahl (2 Knöpfe) | Sender, Folge; Vorgabe Sender | Feld `quelle` | PRO (Basic nur Sender) | components/telefon/TelefonWeckerListe.svelte:116 |
| Sender | Auswahl aus den Favoriten | Vorgabe erster Favorit | Feld `sender` | beide | components/telefon/TelefonWeckerListe.svelte:121 |
| Abo (neueste Folge) | Auswahl der Abos | Vorgabe erstes Abo | Feld `podcast_id` | PRO | components/telefon/TelefonWeckerListe.svelte:129 |
| Weckton | Auswahl | Doppelpiep, Digitalwecker, Glocke, Glockenspiel, Vogelstimmen, Sanft, Mechanischer Wecker, Harfe, Kuckuck; Vorgabe Doppelpiep | Feld `weckton` | beide | components/telefon/TelefonWeckerListe.svelte:136, lib/telefon/wecktoene.js:8 |
| Hörprobe | Knopf (spielen, anhalten) | - | - | beide | components/telefon/TelefonWeckerListe.svelte:139 |
| Lautstärke | Regler | 5 bis 100 %, Schritt 5; Vorgabe 60 | Feld `lautstaerke` | beide | components/telefon/TelefonWeckerListe.svelte:146 |
| Langsam lauter | Regler | 0 bis 300 s, Schritt 15; Vorgabe 60 (Backend erlaubt bis 600) | Feld `anstieg_s` | beide | components/telefon/TelefonWeckerListe.svelte:148 |
| Speichern, Abbrechen | Knöpfe | - | PRO `POST /api/wecker` oder `PUT /api/wecker/{id}`; Basic `radiohub_wecker` | beide | components/telefon/TelefonWeckerListe.svelte:152, :153 |
| Löschen | Knopf, ohne Rückfrage | - | PRO `DELETE /api/wecker/{id}`; Basic `radiohub_wecker` | beide | components/telefon/TelefonWeckerListe.svelte:156 |

Ohne Bedienelement: Schlummerdauer `schlummern_min` (Vorgabe 9, Backend 1 bis 60; backend/routers/wecker.py:32).

## 10 Weckansicht (Telefon quer)

components/telefon/TelefonWecker.svelte; die Gestaltungen zeichnen die Tasten (etwa components/telefon/weckansicht/GHifi.svelte:41, :43).

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Gestaltung | Seitenwischen links, rechts (Punkte zeigen die Stelle) | Ruhig, Uhr, Matrix, HiFi, Segment, Sterne, Astro, Aurora, Röhren, Pixel; Vorgabe Ruhig | `localStorage` `radiohub_weckerlayout` | beide | components/telefon/TelefonWecker.svelte:42, :49, weckansicht/gestaltungen.ts:29 |
| Nachtschaltung | Taste mit drei Stufen im Kreis | Auto (nach Sonnenzeiten), Rot, Normal; Vorgabe Auto | `localStorage` `radiohub_nachtschaltung` | beide | components/telefon/TelefonWecker.svelte:40, :46, :359 |
| Zeitansage an oder aus | Taste (dieselbe Einstellung wie im Telefonblatt; erster Tipp gibt gesperrten Ton frei) | an, aus | `localStorage` `radiohub_zeitansage` | beide | components/telefon/TelefonWecker.svelte:240 |

Automatisch gemerkt: zuletzt gehörter Sender `radiohub.weckeransicht.sender` (components/telefon/TelefonWecker.svelte:68).

## 11 Kanzel und gemerkter Gerätezustand (außerhalb der Seite)

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Lautstärke | Drehregler in der Kanzel, Pfeiltasten, M | 0 bis 100 %; Vorgabe 70 (Store), Drehregler-Vorgabe 50; M stellt auf 0 oder 70 | `localStorage` `radiohub_volume` (lib/playerEngine.js:490) | beide | spieler/Lautstaerke.svelte:29, lib/store.svelte.js:28 |
| Bitrate des Zeitversatzes | Drehwahl in der Kanzel | wie gesendet, 32, 48, 64, 96, 128, 192, 256, 320; Vorgabe wie gesendet | `localStorage` `radiohub_bitrate_override`, geht als `override_bitrate` an `POST /api/hls/start` | PRO | spieler/Steuerung.svelte:87, spieler/kanzel.ts:398, lib/api.js:589 |
| Fokus auf den laufenden Sender | Taste Quelle in der Kanzel | an, aus; Vorgabe aus | `localStorage` `radiohub_fokus` | beide | spieler/Steuerung.svelte:70, spieler/fokus.svelte.ts:7 |
| Tempo der Folge | Drehwahl in der Kanzel | 0,75 bis 2; Vorgabe 1 | nicht gespeichert (`appState.podcastSpeed`) | PRO | spieler/Steuerung.svelte:83 |
| Reihenfolge | Taste in der Kanzel | linear, rückwärts, Schleife, Zufall; Vorgabe linear | nicht gespeichert (`appState.playMode`) | PRO | spieler/Steuerung.svelte:77, spieler/kanzel.ts:235 |
| Neue Folgen speichern je Abo | Taster im Kopf des Abos | an, aus | Spalte `auto_download` der Abos (Podcasts-Schnittstelle) | PRO | components/podcast/AboKopf.svelte:48 |
| Suchverlauf der Sendersuche | automatisch | Liste der letzten Suchen | `localStorage` `radiohub_search_history` | beide | lib/radio/suchverlauf.ts:50 |
| Breite der Aufnahme-Seitenleiste | Ziehen | Vorgabe 280 px | `localStorage` `radiohub_rec_sidebar_width` | PRO | components/RecordingsTab.svelte:41, :543 |
| Zugeklappte Aufnahmeordner | Klick auf Ordner | - | `localStorage` `radiohub_collapsed_folders` | PRO | components/recordings/RecordingSidebar.svelte:52 |
| Zuletzt gehörter Sender | automatisch | - | PRO `PUT /api/config` `last_station_uuid`, `last_station_name` (Tabelle config); Basic `localStorage` `radiohub.web.letzter_sender` | beide | lib/wiedergabeweg.js:23, :27, :37 |

Dazu kurzlebig: `sessionStorage` `radiohub_nach_aktualisierung` (Übergabe nach neuer Fassung, lib/aktualisierung.svelte.js:11).

## 12 Server-Einstellungen ohne Bedienelement in RadioHub (PRO)

Nur über die Schnittstelle des Appkerns (`GET` und `PATCH /api/v1/einstellungen`) oder die Umgebung `RADIOHUB_<FELD>`
änderbar; keine Seite in RadioHub zeigt sie.

| Einstellung | Art des Bedienelements | Werte, Bereich, Vorgabe | Gespeichert wo | Ausgabe | Datei:Zeile |
| --- | --- | --- | --- | --- | --- |
| Ordner in der Kellerwolke | keins | 1 bis 200 Zeichen; Vorgabe `Apps/RadioHub` | Appkern-Einstellung `kellerwolke_wurzel` | PRO | backend/einstellungen.py:45 |
| Geduld beim Ablegen | keins | 0 bis 86400 s; Vorgabe 900 | `kellerwolke_geduld_s` | PRO | backend/einstellungen.py:49 |
| Ortssuche (Adresse der Kartensuche) | keins | Vorgabe leer (dann keine Stadtsuche) | `ortssuche_adresse` | PRO | backend/einstellungen.py:55 |
| Vertonung (Adresse) | keins | Vorgabe leer | `vertonung_adresse` | PRO | backend/einstellungen.py:58 |
| Zeit-Stimme | keins | Vorgabe `katalog:sohee` | `zeitstimme` | PRO | backend/einstellungen.py:61 |
| Tempo der Zeit-Stimme | keins | 0,5 bis 2,0, Schritt 0,05; Vorgabe 1,0 | `zeitstimme_tempo` | PRO | backend/einstellungen.py:65 |
| Fremde Ursprünge | keins | Liste; Vorgabe leer; gilt nach Neustart | `erlaubte_urspruenge` | PRO | backend/einstellungen.py:69 |
| Bitrate der Aufnahme | keins | 8 bis 512 kbit/s; Vorgabe 192 | `recording_bitrate` (auch über `/api/config`) | PRO | backend/einstellungen.py:76 |
| Aufnahme protokollieren | keins | an, aus; Vorgabe aus | `recording_debug_log` (auch über `/api/config`) | PRO | backend/einstellungen.py:80 |
| Abtastrate des Zeitversatzes | keins | 8000 bis 192000 Hz; Vorgabe 44100 | `hls_sample_rate` (auch über `/api/config`) | PRO | backend/einstellungen.py:90 |
| Abgleich mit dem Senderverzeichnis (Uhrzeit) | keins (im Reiter 2.5 nur angezeigt) | HH:MM oder leer; Vorgabe 04:30 | `abgleich_uhrzeit` | PRO | backend/einstellungen.py:102 |

Dazu die Grundeinstellungen des Appkerns (Kellerwolke, Leitstelle, Anmeldung, Sicherung), backend/einstellungen.py:3.

## 13 Hausempfang

Noch nicht gebaut: keine Einstellung, kein Bedienelement, kein Speicherort. Nur geplant (docs/umbau/PLAN.md:35, :38,
:104) und in der Kanzel angekündigt (spieler/Kanzel.svelte:3).

## 14 Alle Speicherorte auf einen Blick

| Ort | Schlüssel |
| --- | --- |
| `localStorage` je Gerät | `appkern_vorlage`, `radiohub_thema`, `radiohub-theme` (früher), `radiohub_schrift`, `radiohub_devmode`, `radiohub_volume`, `radiohub_bitrate_override`, `radiohub_fokus`, `radiohub_search_history`, `radiohub_rec_sidebar_width`, `radiohub_collapsed_folders`, `radiohub_wach_halten`, `radiohub_zeitansage`, `radiohub_zeitansage_plan`, `radiohub_zeitansage_nachts`, `radiohub_nachtschaltung`, `radiohub_weckerlayout`, `radiohub.weckeransicht.sender`; Basic zusätzlich `radiohub.web.angaben`, `radiohub.web.angaben.unlesbar`, `radiohub.web.letzter_sender`, `radiohub_wecker`, `radiohub_wecker_ort`; PRO zusätzlich `radiohub_sitzung` (Sitzung des Appkerns, schale/Wurzel.svelte:2) |
| Tabelle config (PRO, für alle Geräte) | `language`, `ui_click_sounds`, `hls_rec_lookback_minutes`, `sidebar_countries`, `ad_detection_enabled`, `ad_detection_methods`, `ad_detection_threshold`, `ort_name`, `ort_breite`, `ort_laenge`, `last_station_uuid`, `last_station_name`, `recording_format` (ohne Nutzung) |
| Appkern-Einstellungen (PRO) | alle Felder in backend/einstellungen.py:43 bis :110 |
| eigene Tabellen (PRO) | `regel`, `sender_ausblendung`, `sender_sperre`, `sender_freigabe`, `station_ad_status`, `ad_detections_log`, `categories` mit `category_stations`, `recording_folders`, `icy_title_ignore`, `wecker` |
| Datei (PRO) | `storage.json` im Datenordner (Speicherzonen) |

## Unterreiter heute

| Bereich | Reiter | Inhalt |
| --- | --- | --- |
| Allgemein | Einstellungen | Klicktöne, Entwickler-Modus, Sprache, Bitratengrenzen des Zeitversatzes, Rückblick der Puffer-Aufnahme |
| Allgemein | Tastatur | feste Tabelle der Tastenkürzel (Wiedergabe, Navigation, Bereiche) |
| Allgemein | Info | technische Informationen aus `info.md`, dazu Erklärung der alten ICY- und Werbe-Marken |
| Allgemein | Lizenz | Lizenztext aus `lizenz.md` |
| Allgemein | Recht | Datenschutz und Nutzungsbedingungen aus `datenschutz.md` und `agb.md` |
| Allgemein | Bedanken | Spendenseite, drei Kryptowährungen mit Bildcode und Kopierknopf (die Vorgabe nannte "Gedanken"; der Reiter heißt Bedanken) |
| Radio | Ausschlussregeln | Bestand, neue Regel mit Vorschau, lebende Regeln an, aus, entfernen |
| Radio | Ausgeblendete Sender | Liste mit Suche und Grund, Freigeben mit Rückgängig, seitenweise |
| Radio | Länder der Seitenleiste | Auswahl der Schnellfilter-Länder, blendet nie Sender aus |
| Radio | Werbeerkennung (nur PRO) | Stand, Prüfung aller Sender, Verdächtige entscheiden, Einstellungen der Erkennung |
| Radio | Senderverzeichnis (nur PRO) | letzter Abgleich, Uhrzeit, jetzt abgleichen |
| Radio | Kategorien (nur PRO) | Kategorien der Sender anlegen, umbenennen, löschen (altes Aussehen) |
| Radio | Eigene Daten (nur Basic) | eigene Angaben als Datei sichern und einspielen |
| Podcast | keine Reiter | automatische Aktualisierung, Abstand |
| Aufnahmen | keine Reiter | Aufnahmeordner, ignorierte ICY-Titel |
| Speicher | keine Reiter | Speicherzonen mit Pfad, Belegung, Prüfen und Ändern |
| Dienste | keine Reiter | externe Dienste mit Richtung und änderbaren Adressen |

## Auffälligkeiten

### Doppelt oder an zwei Orten

- Bitrate des Zeitversatzes zweimal: Grenzen kleinste und größte Bitrate für alle Geräte in Allgemein
  (components/setup/SetupAllgemein.svelte:254, :260) und die Drehwahl je Gerät in der Kanzel (spieler/Steuerung.svelte:87);
  welche gewinnt, ist nirgends erklärt.
- Zeitansage an oder aus an zwei Stellen: Telefonblatt (components/telefon/TelefonEinstellungen.svelte:109) und Taste in
  der Weckansicht (components/telefon/TelefonWecker.svelte:240), gleicher Schlüssel.
- Tastenkürzel zweimal: wirksam in schale/tastatur.ts:8, beschrieben von Hand in components/setup/SetupAllgemein.svelte:51
  (siehe unten, die Texte stimmen nicht mehr).
- Darstellung eingebettet an zwei Orten (Kopf, Telefonblatt), dort mit Konto; der Reiter Eigene Daten steht ebenfalls
  zweimal (Radio-Reiter und Telefonblatt, components/telefon/TelefonEinstellungen.svelte:157).
- Uneinheitliche Geltung: Sprache und Klicktöne gelten serverweit (Tabelle config), Darstellung, Lautstärke,
  Entwickler-Modus und die ganze Zeitansage je Gerät (`localStorage`), Wecker und Ort wieder serverweit.
- Anzeige der Werbe-Marken doppelt erklärt: Info-Reiter (components/setup/SetupAllgemein.svelte:376) mit alten Marken
  `HiFiBadge`, die neue Radioliste zeigt andere Zeichen.

### Tote Regler, Werte ohne Wirkung, toter Bestand

- Speicherzone Konfiguration lässt sich ändern, wird aber nirgends gelesen (`get_zone_path("config")` ohne Aufruf;
  backend/storage.py:36, backend/config.py:29 nutzt nur database und cache).
- Pfad der Zone Datenbank wirkt erst nach Neustart (`DB_PATH` beim Import fest, backend/config.py:29) und verschiebt nichts:
  nach dem Neustart startet RadioHub mit einer leeren Datenbank am neuen Ort.
- Pfade außerhalb des Datenordners setzt das Backend beim nächsten Laden stillschweigend zurück, wenn keine
  `STORAGE_CONFIG` gesetzt ist (backend/storage.py:111 bis :115); die Eingabe wirkt dann nicht.
- Rückblick der Puffer-Aufnahme wird nur geladen, wenn Einstellungen > Allgemein geöffnet war (components/setup/SetupAllgemein.svelte:78);
  `initConfig` liest ihn nicht (lib/store.svelte.js:106), sonst gilt fest 5 Minuten (lib/playerEngine.js:824).
- `recording_format` (Vorgabe mp3) ohne Bedienelement und ohne Leser (backend/services/config_service.py:24).
- `POST /api/config/reset` ohne Bedienelement (backend/routers/config.py:47).
- Unbenutzte Textschlüssel (Reste früherer Seiten): `setup.filter`, `setup.sender` (lib/locales/de.js:169),
  `allgemein.displayTheme`, `dark`, `light` (lib/locales/de.js:183), `aufnahmen.aufnahmeFormat`, `bitrate`
  (lib/locales/de.js:253), ganze Abschnitte `filter` (lib/locales/de.js:283) und `senderSetup` (lib/locales/de.js:311).
- `SetupKategorien` kann die Bereiche podcast und recording (components/setup/SetupKategorien.svelte:7, :16), eingebunden ist nur radio.
- `ad_detection_methods` wird als JSON-Text in JSON gespeichert (lib/radio/werbeerkennung.ts:84, backend/services/config_service.py:75);
  der Leser bekommt einen Text statt einer Liste und prüft mit `in` zufällig richtig (backend/services/ad_detector.py:381, :416).

### Fest verdrahtet (sollte einstellbar oder an einer Stelle sein)

- Länge des Zeitversatz-Puffers fest 120 Minuten (`max_minutes: 120`, lib/api.js:597); der Rückblick-Regler geht ebenfalls bis 120.
- Grenzen der Drehregler weichen vom Backend ab: kleinste Bitrate 32 bis 128, größte 64 bis 320 (Backend 8 bis 512, components/setup/SetupAllgemein.svelte:256, :262);
  Abstand der Podcasts 1 bis 48 h (Backend bis 7 Tage, components/setup/SetupPodcast.svelte:88); Langsam lauter bis 300 s (Backend 600,
  components/telefon/TelefonWeckerListe.svelte:148). Keine Prüfung, dass die kleinste Bitrate unter der größten liegt.
- Schlummerdauer ohne Bedienelement, immer 9 Minuten (components/telefon/TelefonWeckerListe.svelte:32, components/telefon/TelefonWecker.svelte:191).
- Wiederherstellen nach Stumm fest 70 (schale/tastatur.ts:42); Drehregler der Lautstärke hat Vorgabe 50 (spieler/Lautstaerke.svelte:29), der Store 70.
- Raster fest im Code: Stimmen 1 bis 100 (components/radio/einstellungen/NeueRegel.svelte:26), Schwellen 40 bis 100 %
  (components/radio/einstellungen/WerbungReiter.svelte:15), Prüfrunde 50 Sender (:14), 25 Ausgeblendete je Seite
  (components/radio/einstellungen/AusgeblendetReiter.svelte:14), Zeitansage-Abstände (lib/telefon/zeitplan.js:8).
- Stimme der Zeitansage in Basic fest `katalog:sohee` (ziel/web/telefon.ts:9).
- Spendenadressen, Bildcodes und Spendenseite fest im Code (components/setup/SetupSpende.svelte:9 bis :12, :44).
- Zonen und Dienste fest im Backend mit eigenen Beschreibungstexten (backend/storage.py:40, backend/routers/services.py:16),
  nicht übersetzbar.

### Texte: Englisch, Abkürzungen, Marken, veraltet

- Nicht übersetzt, fest deutsch im Code: "Entwickler-Modus", "AN", "AUS", "Zeigt erweiterte Diagnose-Infos bei Aufnahmen"
  (components/setup/SetupAllgemein.svelte:210, :215, :218); Platzhalter "Absoluter Pfad..." (components/setup/SetupSpeicher.svelte:133),
  "z.B. Jazz, Nachrichten..." (components/setup/SetupAufnahmen.svelte:189), "z.B. Rock, Jazz, Nachrichten..."
  (components/setup/SetupKategorien.svelte:134), Meldung "Fehler" (components/setup/SetupAufnahmen.svelte:140, :151).
- Englische Begriffe in der Oberfläche: Output, Input (lib/locales/de.js:191), HLS (:192, :195), Badge (:200), "good", "poor",
  Cutter (:209), Scan, Stream-URLs, Domains (:218), TABS (:226), Root (:259, :508), Cache / Buffer, SSD (backend/storage.py:48),
  Cache-Kopf (lib/locales/radio/de.js:215), Einheit kbps statt kbit/s (components/setup/SetupAllgemein.svelte:257, :263).
- Doppelter Bindestrich im Hinweis der ICY-Liste zwischen "ignoriert" und "der" (lib/locales/de.js:268).
- Abkürzungen: "z.B." (siehe oben), "inkl." (lib/locales/de.js:228), "MIN", "MAX" (:189, :190).
- Fremde Marken in sichtbaren Texten: Dienstnamen und Beschreibungen `Radio-Browser`, `iTunes Search`, `Apple iTunes`, `fyyd`,
  `Shoutcast/Icecast` (backend/routers/services.py:19, :29, :30, :39, :61), Titel `Podcast-Suche (Apple)` und `(fyyd)`
  (backend/einstellungen.py:107, :109), Spendenseite und Währungsnamen (components/setup/SetupSpende.svelte:10 bis :12, :44).
- Veraltet: Info nennt "Setup > Radio > Sender" für die Prüfung (lib/locales/de.js:218), heute Einstellungen > Radio > Werbeerkennung;
  Beschreibung des Dienstes Werbeerkennung spricht nur von einer Liste von Adressen (backend/routers/services.py:72), es gibt
  auch die Serverprüfung.
- Tastatur-Tabelle stimmt nicht: "Wiedergabe / Pause (nur HLS)" (lib/locales/de.js:227), die Leertaste wirkt immer; "Stopp
  (inkl. Aufnahme)" (:228), bei laufender Aufnahme sperrt S aber (schale/tastatur.ts:23); Pfeile links und rechts sind während der
  Aufnahme ebenfalls gesperrt, das steht nicht da; Ziffer 2 heißt "Aufnahme", der Bereich "Aufnahmen".
- Großschrift in den Texten statt Gestaltung (`'ALLGEMEIN'`, `'KLICKTÖNE'` und andere, lib/locales/de.js:161 bis :400).

### Bedienelemente ohne erkennbare Wirkung oder Rückmeldung

- Basic hat keine Sprachwahl und keine Klicktöne; die Einstellung Sprache gibt es nur in PRO am Rechner, nicht am Telefon.
- Zeitansage und Ort sind am Rechner nicht erreichbar (nur im Telefonblatt), auch nicht in PRO.
- Eigene Daten (Basic) sichern Wecker, Ort, Zeitansage und Darstellung nicht mit (lib/radio/statisch/statische-quelle.ts:363,
  lib/radio/statisch/angaben.ts:36).
- Grenzwerte der Server-Einstellungen (Abschnitt 12) wie Bitrate der Aufnahme oder Abgleich-Uhrzeit sind in RadioHub nicht
  einstellbar; die Abgleich-Uhrzeit wird im Reiter nur angezeigt (components/radio/einstellungen/AbgleichReiter.svelte:62).
- Tempo und Reihenfolge der Kanzel gehen beim Neuladen verloren (nicht gespeichert).

### Löschen und Zurücksetzen ohne Folgenvorschau

- Kategorie löschen ohne Rückfrage, entfernt alle Zuordnungen mit (components/setup/SetupKategorien.svelte:162, backend/routers/categories.py:187).
- Aufnahmeordner löschen ohne Rückfrage (components/setup/SetupAufnahmen.svelte:234); das Backend schützt nur volle Ordner.
- ICY-Muster löschen ohne Rückfrage, auch eingebaute Muster der Quelle System (components/setup/SetupAufnahmen.svelte:292).
- Wecker löschen ohne Rückfrage (components/telefon/TelefonWeckerListe.svelte:156).
- Dienst auf Standard zurücksetzen ohne Rückfrage, die eigene Adresse ist danach weg (components/setup/SetupDienste.svelte:187).
- Speicherpfad ändern ohne Folgenvorschau, obwohl die Datenbank danach leer startet (components/setup/SetupSpeicher.svelte:159).
- Länder-Auswahl leeren ohne Rückfrage oder Rückgängig (components/radio/einstellungen/LaenderReiter.svelte:47).
- Werbung: Alle ausblenden entscheidet alle Verdächtigen auf einmal, ohne Vorschau der Namen über die ersten 100 hinaus
  und ohne Rückgängig (components/radio/einstellungen/WerbungReiter.svelte:115).
- Abmelden ohne Rückfrage (schale/Konto.svelte:32); Trennen hat eine.
- Vorbild mit Folgenvorschau schon da: Regel entfernen (components/radio/einstellungen/RegelZeile.svelte:62) und Datei
  einspielen (components/radio/einstellungen/DateiReiter.svelte:84).
