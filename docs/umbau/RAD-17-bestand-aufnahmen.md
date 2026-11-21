# RAD-17: Bestand Aufnahmen und Schnitt

Stand 21.11.2026, vor Entwurf und Neubau. Vertieft die Zeilen A1 bis A5 und S1 bis S4 aus `RAD-17-bestand.md`. Jede
Funktion unten muss nach dem Umbau wieder da sein oder ausdrücklich entfallen. Zeilenangaben beziehen sich auf den
Stand dieses Tages; Pfade der Oberfläche relativ zu `frontend/src`, Pfade des Servers relativ zu `backend/app`.

Abkürzungen in den Tabellen: RT = `components/RecordingsTab.svelte`, SL = `components/recordings/RecordingSidebar.svelte`,
CV = `components/recordings/CutterView.svelte`, FE = `components/shared/FileExplorer.svelte`, PE = `lib/playerEngine.js`,
ST = `lib/store.svelte.js`. Server: `rec` = `/api/recording`, `ord` = `/api/recording/folders`, `files` = `/api/files`.

## 1. Begriffe

- **Sitzung** (Tabelle `sessions`, database.py:113): eine Aufnahme eines Senders von Start bis Stopp. Kennung
  `rec_JJJJMMTT_HHMMSS` (direkte Aufnahme, services/recorder.py:316) oder `hlsrec_JJJJMMTT_HHMMSS` (Aufnahme aus dem
  Puffer, services/hls_recorder.py:148). Felder: Sender (`station_uuid`, `station_name`, `stream_url`, `bitrate`),
  `start_time`, `end_time`, `duration`, `file_size`, `status` (`recording`, `completed`, `interrupted`, `stalled`),
  `codec`, `file_format`, `rec_type` (`direct` oder `hls-rec`), `folder_id`, `quality_json` (Lücken, Codecwechsel,
  Abbrüche, Bewertung grün/gelb/rot, services/recorder.py:750). `file_path` ist der **Ordner** der Sitzung in der
  Ablage, `meta_file_path` die Titelliste darin.
- **Segment** (Tabelle `segments`, database.py:247), in der Oberfläche auch "Titel", "Teil", "Track" oder "Stück":
  eine Audiodatei einer Sitzung mit `segment_index`, `title`, `start_ms`, `end_ms`, `duration_ms`, `file_path`,
  `file_size`. Jede abgeschlossene Sitzung hat mindestens ein Segment ("Teil 1"), auch ohne Titelwechsel.
- **Titelliste** (`Titelliste.json`): die beim Aufnehmen erkannten Titelwechsel des Senders (ICY-Angaben) mit Zeitpunkt
  `t` in Millisekunden, Rohtitel und Merker `ignored`, dazu Ereignisse (Lücken). Grundlage für Teilen nach Titeln,
  Marker aus Titeln und Titelbereiche in der Wellenform.
- **Sperrliste** (Tabelle `icy_title_ignore`, database.py:304): Titelmuster (`exact` oder `contains`), die keinen
  Schnitt auslösen (Werbung, Pausen). Drei eingebaute Muster (`source = builtin`, database.py:311), eigene mit
  `source = user`.
- **Ordner** (Tabelle `recording_folders`, database.py:239): vom Menschen angelegter Aufnahmeordner mit `name`, `path`
  (`Aufnahmen/<Name>`), `is_active`, `sort_order`. Höchstens einer ist "aktiv": neue Aufnahmen landen darin
  (config.py:52). Sitzungen ohne Ordner liegen in der Wurzel der Aufnahmen ("unzugeordnet").
- **Aufnahme aus dem Puffer** (HLS-Aufnahme): läuft der Zeitversatz (Puffer im Server), nimmt die Aufnahme-Taste
  aus dem Puffer auf, mit Rückblick (Einstellung `hls_rec_lookback_minutes`, 1 bis 120 Minuten, höchstens so lang
  wie der Puffer, einstellungen.py:109 und :192). Sie sammelt Puffer-Stücke, fügt sie beim Stopp zu einer Datei
  zusammen und teilt erst dann nach Titeln (services/hls_recorder.py:267 bis 420). Ohne Zeitversatz läuft die
  direkte Aufnahme, die schon während der Aufnahme bei jedem Titelwechsel ein neues Segment beginnt
  (services/recorder.py:522).
- **Arbeitskopie** und **Wellenform**: zum Schneiden lädt der Server alle Segmente einer Sitzung aus der Ablage und
  fügt sie lokal zu einer Datei zusammen (`arbeit/schnitt/<id>.<endung>`, services/aufnahmen.py:194, bleibt 6 Stunden
  ohne Nutzung). Aus ihr entsteht die Wellenform `Wellenform.peaks` (100 Werte je Sekunde als Gleitkommazahlen,
  services/peaks_generator.py:17), die in der Ablage neben den Segmenten liegt (services/aufnahmen.py:241).
- **Ablage in der Kellerwolke**: jede Datei liegt in der Kellerwolke unter dem Wurzelordner der App (Vorgabe
  `Apps/RadioHub`, ablage/einstellungen.py:13). Aufbau (ablage/orte.py:1 bis 9):

  ```
  Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/001 <Titel>.mp3       Segmente einer Sitzung
  Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/Titelliste.json
  Aufnahmen/<Sender>/<JJJJ-MM-TT HH-MM-SS>/Wellenform.peaks      entsteht beim ersten Schnitt
  Aufnahmen/<Ordner>/<Sender>/<JJJJ-MM-TT HH-MM-SS>/...          Sitzung in einem eigenen Ordner
  Podcasts/<Abo>/<JJJJ-MM-TT> <Folge>.mp3
  Zeitansage/<Stimme>/...                                         nicht sichtbar für Explorer und Wiedergabe
  ```

  Lokal liegen nur Zwischenstände: die laufende Aufnahme (`arbeit/aufnahmen/<id>`), Arbeitskopie, Zwischendateien
  für ZIP und Bearbeitung. Was ein Neustart unterbricht, legt der nächste Start nach (services/aufnahmen.py:161).
  Löschen heißt überall: in den Papierkorb der Kellerwolke (ablage/port.py:99). Neu geschnittene oder bearbeitete
  Dateien mit gleichem Namen werden neue Versionen der alten Datei (ablage/kellerwolke.py:107).
- **Datenbank und Ablage**: die Datenbank kennt Sitzungen und Segmente mit ihren Pfaden; der Explorer zeigt dagegen,
  was wirklich in der Ablage liegt. Ordner unter `Aufnahmen/`, die keine Sitzung und kein Aufnahmeordner kennt,
  heißen "verwaist" (routers/file_explorer.py:71).

## 2. Funktionen je Bereich

### 2.1 Aufnehmen

| Funktion (Bedienelement, Beschriftung) | Was sie tut | Server | Datei:Zeile |
| --- | --- | --- | --- |
| Kanzel: Taste Aufnahme (roter Glastaster, Kreis) | startet die Aufnahme des spielenden Senders; nur wenn ein Sender spielt und keine Aufnahme oder Folge läuft, sonst gesperrt mit Hilfetext; blinkt während der Aufnahme | (über PE) | spieler/Steuerung.svelte:56; spieler/kanzel.ts:295; spieler/aktionen.ts:33 |
| Wahl direkt oder aus dem Puffer | bei aktivem Zeitversatz Aufnahme aus dem Puffer mit Rückblick, sonst direkte Aufnahme | `POST rec/hls-start` oder `POST rec/start` | PE:779 bis 843; routers/recording.py:264 und :42 |
| Rückblick einstellen | Minuten Rückblick für die Aufnahme aus dem Puffer (Einstellungen, Bereich Zeitversatz) | `PUT /api/config` | components/einstellungen/EinstellungenSeite.svelte:69; lib/einstellungen/wirkung.ts:11 |
| Aktiver Aufnahmeordner | neue Aufnahmen landen im aktiven Ordner (siehe 2.2) | `PUT ord/{id}/activate` | config.py:52; services/recorder.py:313 |
| Meldung Start | Hinweis "Aufnahme gestartet" oder "Aufnahme fehlgeschlagen" | | ST:172 |
| Kanzel: Taste Stopp | beendet Hören und Aufnahme zugleich (ohne Meldung "Aufnahme gespeichert") | `POST rec/stop` oder `POST rec/hls-stop` | spieler/aktionen.ts:28; PE:435 und :992 |
| Aufnahmen: Knopf Stopp (Quadrat) im Kopf der laufenden Sitzung | beendet nur die Aufnahme, Meldung "Aufnahme gespeichert (n s)" | wie oben | RT:679; ST:181 |
| Kanzel: Anzeige während der Aufnahme | Zustand "Aufnahme" mit laufender Zeit, Bitrate und Zahl erkannter Titel, Hinweis "Wechsel gesperrt" | | spieler/kanzel.ts:142, :150, :181; spieler/Anzeige.svelte:27 |
| Sperren während der Aufnahme | Senderwechsel, Pause, Spulen, Vor und Zurück gesperrt; Aufnahmen hören geht nicht ("Aufnahme läuft - erst stoppen") | | spieler/aktionen.ts:14, :39; spieler/QuelleZeit.svelte:22; PE:319 |
| Sprung zur Quelle (Klick auf die Quelle in der Kanzel) | während der Aufnahme zum aufnehmenden Sender; beim Hören einer Aufnahme nach `/aufnahmen/<id>` | | spieler/aktionen.ts:91 bis 108 |
| Abfrage des Aufnahmestands (alle 5 s) | übernimmt live erkannte Titel, Ereignisse, Senderttitel, Codec; setzt zurück, wenn der Server keine Aufnahme mehr meldet | `GET rec/status`, `GET rec/hls-status` | PE:850 bis 890 |
| Wiederherstellen nach Neuladen | erkennt eine laufende Aufnahme beim Start der Seite und stellt Zeit, Titel, Sender wieder her | beide Status | PE:921; spieler/Tonausgang.svelte:21 |
| Live-Titel in der Sitzungsansicht ("ERKANNTE TITEL (n)") | Liste der erkannten Titel mit Zeit; gesperrte Titel blass mit Abzeichen "SPERR" | | RT:701 bis 718 |
| Lückenhinweis (nur Entwicklermodus) | Band "Dropout erkannt" (offen) oder "n Dropout(s) erkannt"; nur direkte Aufnahme liefert Ereignisse | | RT:689 bis 700; services/recorder.py:666 bis 715 |
| Qualitätsabzeichen (nur Entwicklermodus) | OK, n Warnungen oder Abbruch aus `quality_json`, Hilfetext mit Lücken, Codecwechseln, Abbrüchen | | RT:636 bis 644 |
| Abfrage der Sitzungsliste alle 3 s | während der Aufnahme Liste und gewählte Sitzung neu laden; nach dem Ende Speicherstand | `GET rec/sessions`, `GET /api/recordings/stats` | RT:120 bis 147 |
| Server: Live-Teilen bei Titelwechsel | neues Segment je Titelwechsel, mindestens 5 s, Sperrliste beachtet, Segment sofort in die Ablage | | services/recorder.py:522 bis 577 |
| Server: Stillstand | nach 60 s ohne Daten Abbruch, Status `stalled` | | services/recorder.py:700 bis 706 |
| Server: Platzprüfung | mindestens 100 MB frei im Arbeitsordner | | services/recorder.py:37, :303; services/hls_recorder.py:129 |
| Server: Liegengebliebenes ablegen | beim Start unterbrochene Aufnahmen nachträglich in die Ablage | | services/aufnahmen.py:161 |
| Server: Puffer zu Aufnahme | startet eine direkte Aufnahme des gepufferten Senders | `POST /api/buffer/to-recording` | routers/buffer.py:102 (ohne Bedienung) |

### 2.2 Liste der Aufnahmen (Seitenleiste)

| Funktion (Bedienelement, Beschriftung) | Was sie tut | Server | Datei:Zeile |
| --- | --- | --- | --- |
| Liste laden | höchstens 50 Sitzungen, neueste zuerst, mit Segmentzahl; hängende `recording` werden `interrupted` | `GET rec/sessions` | RT:168; routers/recording.py:75; services/recorder.py:1030 |
| Sitzungszeile | LED (rot blinkt = nimmt auf, bernstein = abgebrochen, grün = spielt, blau = gewählt), Sender, Datum, "n Seg.", Dauer, Codec | | SL:176 bis 214 |
| Sitzung wählen (Klick) | lädt Segmente und Titelliste, wählt alle Segmente, wechselt zur Sitzungsansicht | `GET rec/sessions/{id}/segments`, `GET rec/sessions/{id}/metadata` | SL:190; RT:94 |
| Segmentliste unter der gewählten Sitzung | Zeile "Alle (n)" und je Segment LED, Nummer, Titel, Dauer; Klick wählt ab oder an (Auswahl für Wiedergabeliste, Normalisieren, Umwandeln) | | SL:242 bis 259, :163 bis 173 |
| Suche (Lupe, Feld "Sendername...") | filtert nach Sendername oder Kennung; ab 2 Zeichen Adresse `/aufnahmen/search/<q>`; Esc leert und schließt | | SL:267, :324 bis 337, :64 bis 71; RT:438, :546; Deep-Link RT:55 |
| Neuer Ordner (Ordner mit Plus, Feld "Neuer Ordnername...") | Eingabe bestätigt anlegen, Esc bricht ab | `POST ord` | SL:290, :310 bis 322; RT:183; routers/recording_folders.py:47 |
| Ordnergruppe | Ordnerkopf mit Pfeil, LED aktiv, Name, Zahl; Klick klappt ein oder aus (im Browser gemerkt) | `GET ord` | SL:351 bis 416, :51 bis 58 |
| Ordner als Aufnahmeziel (Kreis oder Haken) | an: dieser Ordner wird aktiv; aus: Wurzel | `PUT ord/{id}/activate`, `PUT ord/deactivate` | SL:383; RT:213, :220; routers/recording_folders.py:113, :102 |
| Ordner umbenennen (Stift) | Eingabe im Kopf, Eingabe bestätigt, Esc bricht ab; Ordner in der Ablage zieht mit, Pfade in der Datenbank folgen | `PUT ord/{id}` | SL:390, :100 bis 111; RT:193; routers/recording_folders.py:130; services/aufnahmen.py:447 |
| Ordner löschen (Papierkorb) | nur leer, sonst Fehlermeldung mit Zahl; leerer Ordner in der Ablage in den Papierkorb | `DELETE ord/{id}` | SL:397; RT:203; routers/recording_folders.py:72; services/aufnahmen.py:461 |
| Gruppe "UNZUGEORDNET" | Sitzungen ohne Ordner | | SL:419 bis 429 |
| Verschieben aus der Zeile (Ordner offen, erscheint beim Zeigen) | Menü mit "Kein Ordner" und allen anderen Ordnern; Dateien ziehen in der Ablage um | `PUT ord/move-session/{id}` | SL:215 bis 240, :82 bis 98; RT:227; routers/recording_folders.py:172; services/aufnahmen.py:427 |
| Verschieben aus dem Sitzungskopf | zweites Menü gleicher Wirkung, öffnet nur beim Zeigen mit der Maus | wie oben | RT:651 bis 671, :1176 |
| Schere | öffnet den Schnitt der gewählten Sitzung (Adresse `/aufnahmen/cutter`) | | SL:275; RT:514 |
| Ordnerbaum | öffnet oder schließt den Explorer (Adresse `/aufnahmen/files`) | | SL:282; RT:450 |
| Aktualisieren (Wolke mit Pfeil) | lädt Speicherstand, Sitzungen, Ordner neu | `GET /api/recordings/stats`, `GET rec/sessions`, `GET ord` | SL:298; RT:156 |
| Kennzahlen unten | Zahl der Segmentdateien, belegte MB (Summe in der Datenbank), freie GB des Arbeitsordners | `GET /api/recordings/stats` | SL:437 bis 455; routers/recordings.py:19 |
| Breite ziehen | 200 bis 500 Pixel, im Browser gemerkt | | SL:459, :128 bis 152; RT:41, :541 |
| Spielende Sitzung zeigen | rollt zur spielenden Sitzung, öffnet sie beim Abspielen | | SL:114; RT:68 bis 92 |

### 2.3 Eine Sitzung

| Funktion (Bedienelement, Beschriftung) | Was sie tut | Server | Datei:Zeile |
| --- | --- | --- | --- |
| Kopf der Sitzung | LED, Sender, "ABGEBR." bei `stalled`, Datum, Segmentzahl, Dauer, Größe, Bitrate (oder berechnet) | | RT:617 bis 635 |
| Abspielen oder Stoppen (Dreieck, Quadrat) | spielt das erste Segment, die gewählten Segmente werden Wiedergabeliste; spielt sie schon: Stopp | `GET rec/segments/{id}/play` | RT:648, :237 bis 264 |
| Abspielen ohne Segmente (Rückfall) | baut eine Adresse `radio/<Datei>`, die der Server ablehnt (siehe Auffälligkeiten) | `GET /api/recordings/play` | RT:250 bis 263 |
| Vor und Zurück in der Kanzel | blättert in der Wiedergabeliste der Segmente; Reihenfolge linear, rückwärts, Schleife, Zufall (Zufall: alle Segmente aller Sitzungen) | `GET rec/segments` (bei Zufall) | ST:260 bis 280, :317 bis 337; RT:321 |
| Zu einem Titel springen (Titelliste, Klick auf "[mm:ss] Titel") | spielt die Sitzung und springt nach 0,5 s an die Stelle | | RT:760 bis 765, :266 |
| Laden (Pfeil nach unten) | mit Segmenten: ZIP aller Segmente mit Titelliste (ungepackt); ohne: Gesamtdatei | `GET rec/sessions/{id}/download-zip`, `GET rec/sessions/{id}/download-full` | RT:672, :298; routers/recording.py:228, :210 |
| Löschen (Papierkorb) | ohne Rückfrage; stoppt die Wiedergabe, Ordner der Sitzung in den Papierkorb der Ablage, Einträge weg | `DELETE rec/sessions/{id}` | RT:675, :276; routers/recording.py:91; services/aufnahmen.py:376 |
| Nach Titeln teilen ("SEGMENTE ERZEUGEN", Schere) | teilt eine ungeteilte Sitzung an den Titelwechseln der Titelliste | `POST rec/sessions/{id}/split` | RT:750 bis 758, :415; routers/recording.py:180; services/aufnahmen.py:323 |
| Hinweise ohne Inhalt | "Lade Metadaten...", "Keine ICY-Metadaten vorhanden", Begrüßung "Aufnahme in der Seitenliste auswählen" | | RT:719, :767, :773 |
| Server: Einzelne Sitzung | | `GET rec/sessions/{id}` | routers/recording.py:82 (ohne Bedienung) |
| Server: Reparieren | Segmente ohne Datei in der Ablage austragen, je Sitzung oder alle | `POST rec/sessions/{id}/repair`, `POST rec/repair-all` | routers/recording.py:156, :165 (ohne Bedienung) |
| Server: Kategorien für Sitzungen | Sitzung einer Kategorie zuordnen, lösen, Zuordnungen lesen; Aufrufe in `lib/api.js:194` bis 211 vorhanden | `POST /api/categories/{cat}/sessions/{id}`, `DELETE` dazu, `POST /api/categories/session-assignments` | routers/categories.py:258, :273, :86 (ohne Bedienung) |

### 2.4 Segmente

| Funktion (Bedienelement, Beschriftung) | Was sie tut | Server | Datei:Zeile |
| --- | --- | --- | --- |
| Segmentliste ("SEGMENTE (n Tracks)") | je Zeile Startzeit, Titel, Dauer, Größe; spielendes hervorgehoben | `GET rec/sessions/{id}/segments` | RT:721 bis 745 |
| Abspielen (Klick oder Eingabe auf die Zeile) | spielt das Segment mit Bereichsanfragen zum Spulen; Wiedergabeliste aus den gewählten Segmenten | `GET rec/segments/{id}/play` | RT:725, :316 bis 345; routers/recording.py:135 |
| Laden (Pfeil nach unten) | lädt die Datei herunter (neues Fenster) | `GET rec/segments/{id}/download` | RT:733, :347; routers/recording.py:141 |
| Löschen (Papierkorb) | ohne Rückfrage; stoppt die Wiedergabe der Sitzung; letztes Segment löscht die ganze Sitzung | `DELETE rec/sessions/{sid}/segments/{id}` | RT:736, :393; routers/recording.py:147; services/aufnahmen.py:392 |
| Titel sperren oder entsperren (Auge) | trägt den Titel genau als Muster in die Sperrliste ein oder entfernt ihn; wirkt nur auf künftige Aufnahmen | `POST rec/icy-ignore`, `POST rec/icy-ignore/remove-by-pattern`, `GET rec/icy-ignore` | RT:739, :353 bis 391; routers/recording.py:295, :312, :353 |
| Sperrliste in den Einstellungen | alle Muster sehen, eigene anlegen (genau oder enthält), eigene entfernen | `GET`, `POST rec/icy-ignore`, `DELETE rec/icy-ignore/{id}` | components/einstellungen/MusterTeil.svelte:19, :29, :62; routers/recording.py:334 |
| Auswahl der Segmente | in der Seitenleiste (siehe 2.2); bestimmt Wiedergabeliste, Normalisieren und Umwandeln | | SL:242; RT:537 |
| Server: Alle Segmente | alle Segmente aller Sitzungen (nur für Zufallswiedergabe) | `GET rec/segments` | routers/recording.py:112 |

### 2.5 Dateien (Explorer)

| Funktion (Bedienelement, Beschriftung) | Was sie tut | Server | Datei:Zeile |
| --- | --- | --- | --- |
| Was er zeigt | je Ordner der ersten Ebene unter `Aufnahmen/` (Sender oder eigener Ordner) alle Audiodateien darunter, auch aus Unterordnern (Name relativ, etwa `2026-10-28 14-00-05/001 Titel.mp3`), Größe, Änderungszeit; Ordner mit Anzeigename, Sendernamen, Zeitraum, Merker "verwaist"; keine Titellisten, keine Wellenformen | `GET files/recordings` | FE:308 bis 357; routers/file_explorer.py:98 |
| Kopfzahlen | Zahl Ordner, Dateien, Gesamtgröße | | FE:228 bis 236 |
| Sortieren (Schrift, Kalender, Festplatte, Raute) | nach Name, Datum, Größe, Anzahl; zweiter Klick dreht die Richtung | | FE:271 bis 296, :68 |
| Ordner auf- und zuklappen | Klick auf den Ordnerkopf | | FE:311, :77 |
| Auswahl | LED je Datei, LED je Ordner (alle, teilweise, keine), "n ausgewählt (Größe)", Auswahl aufheben (X) | | FE:312, :337, :240 bis 245 |
| Auswahl der gewählten Sitzung | klappt den Ordner der gewählten Sitzung auf und wählt alle seine Dateien | | FE:185 bis 203 |
| Abspielen (Dreieck) | spielt die Datei; mit Auswahl wird die Auswahl Wiedergabeliste | `GET /api/recordings/play?path=` | FE:344; RT:497; routers/recordings.py:33 |
| Spielende Datei zeigen | klappt auf und rollt zur Zeile | | FE:206 bis 222 |
| Löschen (Papierkorb) | ohne Rückfrage; Segment einer Sitzung wird wie in 2.4 gelöscht, sonst nur die Datei | `DELETE files/delete?path=` | FE:347; RT:472; routers/file_explorer.py:128 |
| ZIP (Reißverschluss) | gewählte Dateien als ZIP mit M3U-Liste (ab 2 Dateien), im Browser als Ganzes geladen | `POST files/download-zip` | FE:246 bis 253, :140 bis 157; routers/file_explorer.py:181 |
| Verwaiste löschen (Papierkorb mit Zahl) | ohne Rückfrage; löscht verwaiste Ordner ohne Audio, überspringt welche mit Audio | `DELETE files/delete-orphaned` | FE:259 bis 263; RT:484; routers/file_explorer.py:149 |
| Schere ("Ausgewählte Aufnahmen schneiden") | öffnet den Schnitt der in der Seitenleiste gewählten Sitzung, nicht der gewählten Dateien | | FE:254 bis 258; RT:514 |
| Aktualisieren (Pfeile) | lädt die Dateiliste neu | `GET files/recordings` | FE:264 |
| Server: Podcast-Dateien | gleiche Darstellung für `Podcasts/` | `GET files/podcasts` | routers/file_explorer.py:45 |

### 2.6 Schnitt

Der Schnitt arbeitet immer auf einer ganzen Sitzung: die Arbeitskopie (alle Segmente zusammengefügt) wird angezeigt,
abgespielt und neu geschnitten.

| Funktion (Bedienelement, Beschriftung) | Was sie tut | Server | Datei:Zeile |
| --- | --- | --- | --- |
| Öffnen | Schere in Seitenleiste oder Explorer; nur mit gewählter, nicht laufender Sitzung | | RT:514, :586 |
| Wellenform laden | Eckdaten, dann Abschnitte zu 5 Minuten als Binärdaten, Nachladen vor dem Rand; erzeugt beim ersten Mal Arbeitskopie und Wellenform (ohne Fortschritt, nur "Lade Waveform-Daten...") | `GET rec/sessions/{id}/peaks/info`, `GET rec/sessions/{id}/peaks?start&duration` | CV:107 bis 132; lib/peaksLoader.js:23, :40, :85; routers/peaks.py:28, :39; services/aufnahmen.py:241 |
| Wellenform zeichnen | Hintergrund, Zeitleiste, Titelbereiche abwechselnd gefärbt mit Titel, Marker mit Nummer, Abspielkopf | | lib/waveformRenderer.js:92 bis 296; CV:219 bis 253 |
| Infozeile | Sender, Datum, Gesamtdauer, Codec, Bitrate, Ladeanzeige | | CV:815 bis 826 |
| Zoom rein, Zoom raus (Lupe plus, minus) | Stufen 5 s bis 60 min sichtbar, um die Mitte | | CV:731, :734, :55, :256 bis 274 |
| Alles zeigen (Pfeile zur Linie) | ganze Aufnahme sichtbar | | CV:737, :276 |
| Zoom mit Strg und Mausrad, Rollen mit dem Mausrad | | | CV:389 bis 401 |
| Anzeige Ausschnitt | sichtbare Dauer | | CV:740 |
| Gain ("Amplitude -", "Amplitude +", Anzeige 1x bis 16x) | nur Darstellung der Wellenform, nicht der Ton | | CV:742 bis 748, :59, :285 bis 297 |
| Auto-Play ("Autom. Wiedergabe", an oder aus) | Klick in die Wellenform spielt ab der Stelle oder setzt nur den Kopf | | CV:750 bis 757, :491 |
| Klick in die Wellenform | springt an die Stelle (lädt beim ersten Mal die Arbeitskopie als Ton) | `GET rec/sessions/{id}/audio` | CV:308 bis 329, :491 bis 523; routers/peaks.py:19 |
| Mitlaufen | Abspielkopf bleibt bei 70 Prozent, Wellenform gleitet mit (25 Bilder je Sekunde) | | CV:140 bis 181 |
| Übersicht (Minimap) | ganze Aufnahme mit Ausschnittrahmen; Klick zentriert und spielt; Marker darin ziehen | | CV:850 bis 858, :404 bis 464 |
| Marker setzen ("MARKER", Stecknadel) | Marker in der Mitte des Ausschnitts | | CV:761, :467 |
| Marker per Doppelklick | Marker an der Stelle, auf 0,1 s gerundet | | CV:843, :381, :472 |
| Marker ziehen | in Wellenform und Übersicht, danach sortiert; Klick ohne Ziehen spielt ab dem Marker | | CV:331 bis 379 |
| Marker aus Titeln ("ICY", Etiketten) | ersetzt alle Marker durch die Titelwechsel der Titelliste | | CV:764 bis 768, :573 |
| Alle Marker entfernen ("X (n)") | ohne Rückfrage | | CV:769 bis 773, :485 |
| Markerliste ("Schnittpunkte:") | je Marker Nummer, Zeit, Abspielen ("Ab hier abspielen"), Entfernen | | CV:914 bis 930 |
| Anfang weg ("ANFANG", an oder aus) | beim Schneiden das erste Stück verwerfen (nur mit mehr als einem Stück) | | CV:777 bis 784 |
| Ende weg ("ENDE", an oder aus) | beim Schneiden das letzte Stück verwerfen | | CV:785 bis 792 |
| Schneiden ("SCHNEIDEN (n Teile)", Schere) | ersetzt alle Segmente der Sitzung durch die Stücke zwischen den Markern, Titel aus der Titelliste; ohne Rückfrage, ohne Fortschritt; danach zurück zur Sitzung | `POST rec/sessions/{id}/custom-split` | CV:793 bis 802, :526; routers/recording.py:193; services/aufnahmen.py:294 |
| Auto-Split ("Auto", Zauberstab) | nach Titeln teilen; nur sichtbar ohne Segmente | `POST rec/sessions/{id}/split` | CV:803 bis 807, :551 |
| Schließen ("Schließen") | zurück zur Sitzung | | CV:808 |
| Auswahlanzeige ("n/m Seg.") | wie viele Segmente die Werkzeuge treffen | | CV:862 bis 867 |
| Normalisieren ("NORMALISIEREN", Lautsprecher) | auf -16 LUFS (fest); alle Segmente gemeinsam gemessen, bei Teilauswahl jedes für sich (Hinweis); Fortschritt als Strom | `POST rec/sessions/{id}/normalize` (Ereignisstrom) | CV:868, :612 bis 676; routers/audio_processing.py:97 |
| Umwandeln ("KONVERTIEREN", Feld mit Format MP3, OGG, AAC, Bitrate je Format, Mono) | wandelt gewählte Segmente um; andere Endung wird neue Datei, die alte geht in den Papierkorb | `POST rec/sessions/{id}/convert` (Ereignisstrom) | CV:871, :883 bis 911, :595 bis 610, :678 bis 713; routers/audio_processing.py:119 |
| Fortschritt | Kreisel mit Meldung des Servers | | CV:874 bis 879 |
| Farben nach Hell und Dunkel | liest Farben beim Wechsel neu | | CV:88 bis 94, :194 |
| Was gespeichert wird und wo | Schneiden und Teilen: neue Segmente im Sitzungsordner der Ablage (`001 Titel.mp3` ...), gleiche Namen als neue Version, übrige alte in den Papierkorb, Tabelle `segments` neu, Wellenform und Arbeitskopie verworfen (services/aufnahmen.py:265 bis 289, :236). Normalisieren und Umwandeln: je Segment neue Version oder neue Datei (services/aufnahmen.py:343 bis 372). Marker, Zoom, Gain, Auswahl werden nicht gespeichert. | | |
| Rückgängig | gibt es in der App nicht. Alte Fassungen liegen nur als Versionen oder im Papierkorb der Kellerwolke und lassen sich nur dort zurückholen. | | |
| Server ohne Bedienung | Tondaten lesen, nur Mono, Bitraten je Format | `GET rec/sessions/{id}/audio-info`, `POST rec/sessions/{id}/to-mono`, `GET rec/audio-processing/presets` | routers/audio_processing.py:88, :134, :149 |

### 2.7 Telefon

| Funktion | Was sie tut | Server | Datei:Zeile |
| --- | --- | --- | --- |
| Aufnahmen am Telefon | gibt es nicht: Reiter nur Radio und Podcasts, keine Aufnahme-Taste im Spieler, keine Liste, kein Schnitt | | components/telefon/Telefon.svelte:162 bis 169; components/telefon/TelefonSpieler.svelte |
| Webversion | ohne Aufnahme (Weg `direkt` mit `aufnahme: false`), eigene Wurzel nur mit Radio | | ziel/web/wurzel.ts:1; lib/wiedergabeweg.js:30 |

### Zahl der Funktionen

| Bereich | mit Bedienung | Server ohne Bedienung |
| --- | --- | --- |
| Aufnehmen | 17 | 1 (Puffer zu Aufnahme) |
| Liste der Aufnahmen | 18 | 0 |
| Eine Sitzung | 8 | 3 (einzelne Sitzung, Reparieren, Kategorien) |
| Segmente | 7 | 0 |
| Dateien | 12 | 1 (Podcast-Dateien, am Rechner entfallen) |
| Schnitt | 31 | 3 (Tondaten, Mono, Bitraten) |
| Telefon | 0 | |

## 3. Die vielen Schnittwerkzeuge

Wo heute Ton geteilt, gekürzt, zusammengefügt oder verändert wird:

| Weg | Auslöser | Wirkung | Datei:Zeile |
| --- | --- | --- | --- |
| Live-Teilen | automatisch bei Titelwechsel (direkte Aufnahme) | ein Segment je Titel | services/recorder.py:522 |
| Teilen beim Stopp | automatisch beim Stopp der Aufnahme aus dem Puffer | Zusammenfügen der Puffer-Stücke, Teilen nach Titelliste | services/hls_recorder.py:299 bis 380 |
| Nach Titeln teilen | Knopf "SEGMENTE ERZEUGEN" in der Sitzung und Knopf "Auto" im Schnitt (zwei Bedienwege, ein Endpunkt `split`) | nur für ungeteilte Sitzungen | RT:750; CV:803; services/aufnahmen.py:323 |
| Schneiden an Markern | Schnitt, "SCHNEIDEN" | ersetzt alle Segmente | CV:526; services/aufnahmen.py:294 |
| Trimmen | Schalter "ANFANG" und "ENDE" im Schnitt | verwirft nur ganze erste oder letzte Stücke, kein freies Kürzen | CV:777; services/aufnahmen.py:310 |
| Segment löschen | Papierkorb in der Segmentliste und im Explorer (zwei Bedienwege, ein Dienst) | entfernt ein Stück, nummeriert neu | RT:393; RT:472; services/aufnahmen.py:392 |
| Zusammenfügen | Arbeitskopie für Schnitt, Wellenform, Ton im Schnitt, Gesamtdatei | alle Segmente zu einer Datei | services/aufnahmen.py:194; routers/recording.py:210; routers/peaks.py:19 |
| Normalisieren | Schnitt | Lautheit -16 LUFS | routers/audio_processing.py:97 |
| Umwandeln | Schnitt, Feld Format, Bitrate, Mono | Format, Bitrate, Mono | routers/audio_processing.py:119 |
| Nur Mono | ohne Bedienung (Mono steckt auch in Umwandeln) | Stereo zu Mono | routers/audio_processing.py:134 |
| Tondaten, Bitraten | ohne Bedienung; die Bitraten stehen doppelt im Schnitt | | routers/audio_processing.py:88, :149; CV:595; services/audio_processor.py:19 |
| Reparieren | ohne Bedienung | trägt fehlende Segmente aus | routers/recording.py:156, :165 |
| Nachholen beim Start | automatisch | legt Reste ab | services/aufnahmen.py:138, :161 |

Zum Zusammenlegen: ein Schnittdienst mit einer Schnittstelle "Teile bestimmen" (Titelliste, Marker, Live) und
"Ergebnis ablegen", ein Bearbeitungsdienst (Normalisieren, Umwandeln, Mono als Optionen eines Auftrags), eine
Arbeitskopie. Alle langen Vorgänge als Auftrag mit Fortschritt (heute: Schneiden und Teilen ohne Fortschritt,
Normalisieren und Umwandeln als Ereignisstrom über eine POST-Anfrage).

## 4. Kellerwolke

### Was der Server heute kann

- Schnittstelle der Ablage (ablage/port.py:71 bis 149): Eintrag lesen (:75), direkte Kinder eines Ordners (:79),
  ablegen und schreiben als neue Datei oder neue Version (:83, :87), lesen mit Bereich (:91), verschieben und
  umbenennen (:95), in den Papierkorb (:99), Stand (:103); daraus abgeleitet ganz lesen, herunterladen, alle Dateien
  darunter (rekursiv), freier Name (:111 bis 149).
- Alle Pfade gelten relativ zum Wurzelordner der App (Vorgabe `Apps/RadioHub`, Einstellung `kellerwolke_wurzel`);
  `_voll` setzt die Wurzel immer davor (ablage/kellerwolke.py:57). Außerhalb der Wurzel kommt der Server nicht.
- Über HTTP sichtbar sind nur die Bereiche `Aufnahmen` und `Podcasts` (ablage/orte.py:18, :25): Explorer
  (`GET files/recordings`, `GET files/podcasts`, nur erste Ordnerebene mit allen Audiodateien darunter, alles auf
  einmal), Abspielen mit Bereichsanfrage (`GET /api/recordings/play?path=`, ablage/wiedergabe.py:42), Löschen, ZIP,
  Stand der Ablage (`GET /api/storage/ablage`, routers/storage.py:19).
- Audioendungen: `.mp3 .m4a .ogg .opus .wav .flac .aac` (config.py:68).
- Der Zugang des Appkerns (`appkern.kellerwolke.Kellerwolke`, festgelegte Fassung in requirements.txt:3) kann mehr,
  als die Ablage nutzt: Kinder seitenweise (zugang.py:187), oberste Ebene des Kontos und Volltextsuche über die ganze
  Wolke mit der Freigabe "Alles lesen" (:360, :365), Suche nach Feldern (:352), Dateiwahl mit der Anmeldung des
  Menschen (`wahl`, `waehlen`, :447, :453), Versionen lesen (:226, :231), Papierkorb und Wiederherstellen (:296,
  :316), Löschfolgen (:342), Begleitdateien neben einer Hauptdatei (:378 bis 405), Herkunft (:461), Bearbeitungssperre
  (:475), Änderungen beobachten (:485, :520), Prüfsumme (:330), Verweise (:336). Pfade in
  `backend/.venv/lib/python3.12/site-packages/appkern/kellerwolke/zugang.py`.

### Was fehlt, damit der Schnitt beliebige Audiodateien öffnen und durch Ordner gehen kann

1. **Ordner durchgehen**: ein Endpunkt, der eine Ebene eines Ordners liefert (Ordner und Audiodateien, seitenweise,
   mit Elternkette), statt der heutigen rekursiven Komplettliste der zwei Bereiche.
2. **Zugriff außerhalb der App-Wurzel**: die Ablage kennt nur Pfade unter ihrer Wurzel. Für fremde Ordner braucht es
   entweder die Freigabe "Alles lesen" am App-Zugang (`wurzel`, `volltext`, Zugriff über Knoten-Kennung) oder die
   Dateiwahl mit der Anmeldung des Menschen (`wahl`); dazu ein Lesezugang über Knoten-Kennung statt Pfad. Die
   Bereichsprüfung `im_bereich` müsste für den Schnitt ersetzt werden.
3. **Schnitt ohne Sitzung**: Arbeitskopie, Wellenform, Ton und Schneiden hängen heute an `session_id`
   (services/aufnahmen.py:194, :241; routers/peaks.py; routers/recording.py:193). Nötig ist ein Schnittgegenstand
   "Datei" (Pfad oder Knoten-Kennung) mit eigener Arbeitskopie und Wellenform; Sitzungen werden ein Fall davon.
4. **Wellenform zu fremden Dateien**: heute `Wellenform.peaks` im Sitzungsordner. Für fremde Dateien als Begleitdatei
   der Kellerwolke (wandert mit Verschieben und Papierkorb) oder als Zwischenstand im Arbeitsordner.
5. **Wohin das Ergebnis geht**: heute ersetzt der Schnitt die Segmente der Sitzung. Für fremde Dateien braucht es eine
   Wahl: neue Version der Datei, neue Dateien daneben oder ein Zielordner; Schreibrecht in fremden Ordnern ist zu
   klären; Datenbankeinträge gibt es dafür keine.
6. **Abspielen beliebiger Dateien**: `ausliefern` kann jeden Ablagepfad mit Bereich liefern, der Endpunkt
   `/api/recordings/play` lässt aber nur die zwei Bereiche zu.
7. **Suche**: Volltextsuche des Zugangs ist da, ein Endpunkt dafür fehlt.
8. **Rückgängig**: Versionen und Papierkorb der Kellerwolke wären die Grundlage; die Ablage-Schnittstelle bietet
   weder Versionen lesen noch Wiederherstellen.
9. **Folgenvorschau beim Löschen**: `loeschfolgen` des Zugangs ist ungenutzt.
10. **Gleichzeitiges Bearbeiten**: Bearbeitungssperre des Zugangs ungenutzt; heute nur eine Sperre im Prozess
    (services/aufnahmen.py:56).
11. **Formate**: Umwandeln kennt nur MP3, OGG, AAC (services/audio_processor.py:19); WAV, FLAC, OPUS, M4A lassen sich
    öffnen, aber nicht als Ziel wählen.

## 5. Auffälligkeiten

### Tote oder unerreichbare Bedienung

- "SEGMENTE ERZEUGEN" und der Sprung zu einem Titel der Titelliste erscheinen nur, wenn eine Sitzung keine Segmente
  hat (RT:721 vor :746); jede abgeschlossene Sitzung hat aber mindestens "Teil 1". Ebenso "Auto" im Schnitt nur bei
  `segments.length === 0` (CV:803). Damit ist "Nach Titeln teilen" praktisch nicht bedienbar, obwohl der Server es bei
  genau einem Segment erlaubt (services/aufnahmen.py:327).
- "Laden" wählt die Gesamtdatei nur ohne Segmente (RT:299); weil es die nicht gibt, ist `download-full` aus der
  Oberfläche nicht erreichbar.
- Abspielen ohne geladene Segmente baut `radio/<Datei>` (RT:250 bis 252); der Server lehnt Pfade außerhalb der
  Bereiche mit 400 ab (routers/recordings.py:36).
- Explorer: Schere "Ausgewählte Aufnahmen schneiden" ignoriert die gewählten Dateien und öffnet die Sitzung der
  Seitenleiste (FE:254, RT:514).
- Explorer: der Regelausdruck `replace(/^.*\/recordings\//, '')` stammt aus der Zeit vor der Ablage und tut nichts
  mehr (RT:502, :509).
- `selectAll` im Explorer ohne Knopf (FE:121); `folderSessions` in der Seitenleiste ungenutzt (SL:62);
  `setSelection` des Zeichners ungenutzt (lib/waveformRenderer.js:79).
- Deep-Link `/aufnahmen/<id>` (Sprung zur Quelle, spieler/aktionen.ts:105) wählt die Sitzung nicht über die Adresse;
  es klappt nur, weil die Ansicht der spielenden Aufnahme folgt (RT:68).
- Die Sitzungsliste zeigt nur die 50 neuesten (routers/recording.py:76, `lib/api.js:312` ohne Grenze); ältere
  Aufnahmen sind in der Liste und in der Suche unsichtbar, nur im Explorer.
- Nach Normalisieren und Umwandeln lädt der Schnitt weder Segmente noch Wellenform neu (CV:656, :711), obwohl der
  Server Wellenform und Arbeitskopie verwirft (services/aufnahmen.py:371).
- Unbenutzte Texte: `verwaistLoeschenBestaetigung`, `alleAuswaehlen`, `bestehendeSegmente`, `trimAktiv`, alle
  `analyse*` und `uebergang*` des Schnitts, `hlsBufferLaeuft`, `ordnerAktiviert`, `standardOrdner`
  (lib/locales/de.js:246 bis 410).

### Endpunkte ohne Bedienung

`GET rec/sessions/{id}`, `POST rec/sessions/{id}/repair`, `POST rec/repair-all`, `GET rec/sessions/{id}/audio-info`,
`POST rec/sessions/{id}/to-mono`, `GET rec/audio-processing/presets`, `PUT ord/{id}` mit `sort_order` (keine
Umsortierung), alle Kategorien-Endpunkte für Sitzungen (routers/categories.py:86, :258, :273), der ganze Router
`/api/buffer` einschließlich `to-recording` (routers/buffer.py), `GET files/podcasts` am Rechner, die
Fehlersuch-Endpunkte `/api/hls/debug/*` (routers/hls.py:176, :202).

### Doppelte Wege

- Zwei Verschiebemenüs: in der Zeile (SL:225) und im Sitzungskopf (RT:651, öffnet nur beim Zeigen mit der Maus,
  RT:1176; mit Tastatur oder Finger nicht erreichbar).
- Zwei Stopp-Wege mit unterschiedlicher Rückmeldung: Kanzel ohne Meldung (spieler/aktionen.ts:28), Sitzungskopf mit
  Meldung (RT:679).
- Zwei Wege nach Titeln teilen (RT:750, CV:803), zwei Wege Segment löschen (RT:736, FE:347), zwei ZIP-Wege mit
  unterschiedlichem Inhalt (Sitzung mit Titelliste, routers/recording.py:228; Auswahl mit M3U,
  routers/file_explorer.py:181) und unterschiedlicher Technik (neues Fenster gegen ganze Datei im Browser, FE:146).
- Drei Abspielwege für dieselben Töne: Segment (`segments/{id}/play`), Datei (`recordings/play?path=`), Arbeitskopie
  im Schnitt (`sessions/{id}/audio`).
- Sperrliste an zwei Stellen (Auge in der Segmentliste, Einstellungen); das Auge erkennt nur genaue Muster
  (RT:362), ein passendes "enthält"-Muster zeigt es als nicht gesperrt.
- Bitraten je Format doppelt (CV:595 und services/audio_processor.py:19), Peaks je Sekunde doppelt
  (lib/peaksLoader.js:10 und services/peaks_generator.py:17).
- Zwei Abfragen nebeneinander: Sitzungsliste alle 3 s (RT:121) und Aufnahmestand alle 5 s (PE:852).
- Zwei Schnittwerkzeuge in der Seitenleiste und im Explorer öffnen dasselbe (SL:276, FE:255).

### Löschen ohne Rückfrage oder Folgenvorschau

Sitzung löschen (RT:276), Segment löschen (RT:393), Datei im Explorer löschen (RT:472), verwaiste Ordner löschen
(RT:484, der Text für die Rückfrage ist da, aber ungenutzt; die Zahl am Knopf zählt auch Ordner mit Audio, die der
Server überspringt, routers/file_explorer.py:157), Schneiden ersetzt alle Segmente (CV:526), Normalisieren und
Umwandeln überschreiben (CV:612, :678), alle Marker entfernen (CV:485), Ordner löschen (SL:397). Die Hilfetexte sagen
"endgültig löschen" (lib/locales/de.js:283, :285, :403), tatsächlich geht alles in den Papierkorb der Kellerwolke.

### Englische und feste Texte

- In den Sprachdateien: "Tracks", "TRACKLIST", "Split fehlgeschlagen", "Auto-Split nach ICY-Titeln", "Root (kein
  Ordner)", "Session-Liste aktualisieren", "Lade Waveform-Daten...", "Datei-Explorer", "M3U-Playlist", "MARKER",
  "Seg." (lib/locales/de.js:274 bis 343, :387, :427).
- Fest im Code: `Dropout erkannt -- kein Datenstrom!` mit doppeltem Bindestrich (RT:695), "Dropout(s) erkannt"
  (RT:697), "Seg." und "kbps" (RT:632, :635), "OK", "Warn.", "Abbruch", "Gaps", "Codec", "Stalls" (RT:639 bis 642),
  "SPERR" (RT:710), "Tracks in einzelne Dateien schneiden" (RT:754), "n Ordner gelöscht" (RT:489), "Fehler: "
  (RT:388), "Alle (n)" und "Teil n" (SL:247, :254), "Amplitude -" und "Amplitude +" (CV:742, :746), "ICY" (CV:766),
  Trenner `--` (CV:817 bis 821), "OGG Vorbis" (CV:889), Markername "M1" (CV:475), "Segment n/m..." vom Server
  (routers/audio_processing.py:111, :127), Datumsformat fest `de-DE` (CV:818, FE:167).
- Fehlermeldungen des Servers landen als Meldung in der Oberfläche und sind teils englisch oder ohne Umlaut:
  "Session nicht gefunden", "Pattern darf nicht leer sein", "match_type muss ...", "Concat fehlgeschlagen",
  `Aufnahme laeuft bereits` (routers/recording.py:87, :316, :318; services/hls_recorder.py:337;
  services/recorder.py:294). Kommentare mit Ersatzschreibung (etwa `hinzufuegen`, `fuer`, `Pruefungen`) in
  routers/recording.py:314, :355 und services/recorder.py:40.
- Adressen englisch: `/aufnahmen/files`, `/aufnahmen/cutter`, `/aufnahmen/search/<q>` (RT:35 bis 37, :549).

### Feste Farben und Größen

- Keine `rh-`- und keine `ak-`-Klasse in RT, SL, CV, FE; durchgehend `hifi-*`.
- Feste Schriftgrößen in Pixeln: RT 19, SL 25, CV 14, FE 18 Stellen (etwa RT:812 mit 40 px, SL und CV mit 9 px).
  Damit greift die Schriftvergrößerung hier nicht.
- Feste Farben: RT 10, SL 7, CV 10, FE 5 Stellen (etwa RT:858, :1069; SL:766 bis 778; FE:662 bis 673). Im Zeichner
  der Wellenform alle Farben fest: Titelbereiche `#4fc3f7` und `#81c784`, Abspielkopf, Marker, Gitter, Rahmen der
  Übersicht (lib/waveformRenderer.js:10 bis 23, :137, :195, :209; CV:246), Rückfallfarben (CV:187 bis 209).
- Schrift im Zeichner fest `bold 8px` und `9px` mit Schriftart `Barlow` (lib/waveformRenderer.js:210, :292); im
  Explorer `Orbitron` und `Barlow` (FE:386, :459).
- Feste Werte im Schnitt, die einstellbar sein sollten: Zielwert -16 LUFS (CV:629), Zoomstufen (CV:55), Gainstufen
  (CV:59), Abspielkopf bei 70 Prozent (CV:44), Raster 0,1 s (CV:352), Abschnitt 5 Minuten (lib/peaksLoader.js:9).
- Seitenleiste 200 bis 500 Pixel, Vorgabe 280 (SL:142, RT:41); Breite und eingeklappte Ordner nur im Browser.

### Bauziele, Geräte, Bedienung

- Aufnehmen, Aufnahmen und Schnitt gibt es nur im Bauziel "voll" am Rechner; Webversion ohne Aufnahme
  (lib/wiedergabeweg.js:30), Telefon ohne Reiter und ohne Taste (components/telefon/Telefon.svelte:162).
- Der Schnitt ist nur mit Maus bedienbar: keine Tastenkürzel, keine Berührungsgesten (CV:836 bis 858); Marker nur per
  Doppelklick oder Knopf in der Mitte.
- Der Schnitt greift über `document.querySelector('audio')` auf das Tonelement der Kanzel zu (CV:147, :514;
  spieler/Tonausgang.svelte:2) und lädt Wellenformdaten mit eigenem `fetch` vorbei an `lib/api.js`
  (lib/peaksLoader.js:24, :50).
- Während einer Aufnahme lassen sich keine Aufnahmen anhören (PE:319).
- Lange Vorgänge ohne Auftrag: erster Schnitt (Arbeitskopie aus allen Segmenten laden und zusammenfügen, Wellenform
  berechnen), Schneiden und Teilen laufen als einfache Anfrage ohne Fortschritt; Normalisieren und Umwandeln als
  Ereignisstrom über POST, den ein Vorbau bei langen Strömen abbrechen kann (im Betrieb zu prüfen).
- Datenholen, Zustand und Darstellung in denselben Komponenten: RT ruft `api.*` 32-mal, CV hält Wiedergabe, Marker,
  Werkzeuge und Ereignisstrom-Lesen in einer Datei.
- Tests: Server 11 (tests/test_aufnahmen.py) und 11 (tests/test_ablage.py); für Seitenleiste, Explorer und Schnitt
  keine Tests der Oberfläche.
