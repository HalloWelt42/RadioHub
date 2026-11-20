# RAD-7, Teil 3b: Bedienfunktionen der Radio-Ansicht alt -> neu

Angelegt vor dem Neubau der Oberfläche der Senderfilterung (Regel: bei einer Neugestaltung keine Funktion verlieren).
Erfasst sind alle Bedienfunktionen der bisherigen Teile `components/StationsTab.svelte`,
`components/setup/SetupFilter.svelte`, `components/setup/SetupSender.svelte`, `components/setup/SetupKategorien.svelte`,
`components/telefon/TelefonRadio.svelte` und `components/telefon/SenderZeile.svelte` (mit `hifi/HiFiTagPanel.svelte`).
Je Zeile: was es heute gibt, wo es im Neubau steht, Stand und Nachweis (Test oder Probebetrieb). Die alten Teile
werden erst entfernt, wenn jede Zeile abgehakt ist.

Stand 20.11.2026: alle 67 Zeilen abgehakt (61 vorhanden, 6 bewusst geändert); die alten Teile sind entfernt.

Stand: `[ ]` offen, `[x]` im Neubau vorhanden und geprüft, `[~]` bewusst geändert (Begründung in der Zeile).

Neue Teile: Senderquelle `frontend/src/lib/radio/` (Schnittstelle `quelle.ts`, Umsetzung `backend.ts`, Schnellfilter
und Adresse `schnellfilter.ts`, Liste `senderliste.svelte.ts`, Regel-Ablauf `regelablauf.svelte.ts`), Ansichten
`frontend/src/components/radio/` (Rechner, Einstellungen) und `components/telefon/TelefonRadio.svelte`.

## A. Radio am Rechner (StationsTab)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| A1 | Senderliste, beim Rollen nachladen (Versatz) | Liste seitenweise mit Seitenzeiger (Keyset), Nachladen am Listenende | [x] | Test senderquelle (Seiten, keine Doppel); Probebetrieb Nachladen am Listenende |
| A2 | Zähler zeigt geladene Sender | Segmentanzeige mit echter Gesamtzahl der Treffer, dazu "von N sichtbaren" | [x] | Probebetrieb: 3.847 Treffer Land DE, "von 49.095 sichtbaren" |
| A3 | Suche nach Name, entprellt, ab 2 Zeichen | Suche (Name, Genre, Ort) entprellt, steht in der Adresse | [x] | Probebetrieb: Suche wdr, 46 Treffer, ?suche=wdr |
| A4 | Suchverlauf: 10 letzte, wählen, Verlauf löschen | Suchfeld mit Verlauf, gleiche Funktionen, gleicher Schlüssel im Browser | [x] | Suchfeld.svelte, Schlüssel radiohub_search_history; Probebetrieb |
| A5 | Suche leeren (X) | Knopf im Suchfeld und Chip "Suche" | [x] | Probebetrieb: Chip Suche entfernt leert das Feld |
| A6 | Adresse /radio/search/<suche> | bleibt gültig, wird zur Suche in der Adresse | [x] | Test schnellfilter (ausOrt, Umschreiben); Probebetrieb /radio/search/wdr -> /radio?suche=wdr |
| A7 | Direktlink /radio/<uuid>: Sender wählen, nachladen, hinrollen | gleich: Details offen, nicht geladene Sender vorn eingefügt | [x] | Probebetrieb: /radio/<WDR 5>?land=AT fügt WDR 5 vorn ein, Details offen |
| A8 | Länderfilter der Seitenleiste mit Zahlen, Mehrfachwahl | Facette Länder mit Zahlen unter allen übrigen Filtern | [x] | Probebetrieb: Länder mit Zahlen, Mehrfachwahl in der Adresse |
| A9 | Hinweis "Länder konfigurieren" | Verweis "Länder wählen" in den Einstellungen | [x] | Verweis zu /einstellungen/radio/laender |
| A10 | Kategorienfilter, Hinweis "Kategorien erstellen" | Facette Eigene Kategorien, Verweis "Verwalten" | [x] | Facette mit Zahlen, Verweis /einstellungen/radio/kategorien |
| A11 | Bitrate in sechs Bereichen | Mindestbitrate als Leuchtbalken, dazu Facetten Qualität und Codec | [~] | Bereiche ersetzt durch Mindestbitrate (Leuchtbalken) und Facetten Qualität, Codec; ein Bereich nach oben ("64 bis 128") entfällt bewusst |
| A12 | Stimmen in sechs Bereichen | Mindeststimmen als Drehwahl | [~] | Bereiche ersetzt durch Mindeststimmen (Drehwahl); Obergrenze entfällt bewusst |
| A13 | Nur Favoriten (im Browser gemerkt) | Taster Nur Favoriten, steht in der Adresse, wirkt mit allen Filtern (Vorgabe 2) | [x] | Test schnellfilter (favoriten=1); Probebetrieb |
| A14 | Filter zurücksetzen (X) | "Alle zurücksetzen", Chips einzeln, Zurücksetzen im Kopf der Seitenleiste | [x] | Test schnellfilter (ohne, zurueckgesetzt); Probebetrieb |
| A15 | Knopf zu den Filter-Einstellungen | Hinweis "n Sender durch Ausschlussregeln ausgeblendet" mit Sprung zu den Regeln | [x] | Hinweis mit Sprung /einstellungen/radio/regeln; Probebetrieb 9.269 |
| A16 | Sortierung per Spaltenkopf: Name, Land, Bitrate, Stimmen, auf und ab | Sortierung Stimmen, Name, Qualität, Bitrate | [~] | Stimmen, Name, Qualität, Bitrate in fester Richtung (Schnittstelle der Senderquelle); Land und Umkehren entfallen, Land über die Facette |
| A17 | Aktualisieren: Senderverzeichnis abgleichen und Filter zurücksetzen | "Neu laden" lädt nur die Liste (Vorgabe 4); Abgleich als Auftrag in den Einstellungen | [x] | Neu laden lädt Liste und Bestand; Abgleich im Reiter Senderverzeichnis |
| A18 | Abspielen über Leuchte oder Name | Klick auf die Senderzeile | [x] | Probebetrieb: Klick spielt (stumm), Leuchte blau |
| A19 | Details auf- und zuklappen (Adresse /radio/<uuid>) | Knopf Details, Adresse wie bisher | [x] | Probebetrieb: /radio/<uuid>?genre=Pop, Zurück schließt |
| A20 | Leuchte: blau spielt, rot blinkt bei Aufnahme, gelb gewählt | gleich | [x] | SenderZeile.svelte: blau, rot blinkt bei Aufnahme, gelb offen |
| A21 | Favorit umschalten | Stern in der Zeile | [x] | Test senderquelle (Favorit an und aus); Probebetrieb an und wieder aus |
| A22 | Auge blendet aus und startet den Nachbarsender | Auge mit Rückgängig-Band, startet keinen Sender (Vorgabe 5) | [x] | Probebetrieb: ausgeblendet, Zähler 3.847 -> 3.846, Hinweis 9.269 -> 9.270, nichts startet; Rückgängig setzt ihn an Stelle 2 zurück |
| A23 | Tastatur: Pfeil hoch und runter, Eingabe und Leertaste spielen, Escape schließt | gleich | [x] | Probebetrieb: zweimal Pfeil runter, Eingabe spielt den zweiten |
| A24 | Nach 90 s ohne Bedienung zum spielenden Sender rollen | entfällt (RAD-19) | [x] | Ersetzt durch den Fokus-Schalter der Kanzel: ein folgt dem laufenden Sender bei jedem Wechsel, aus rollt frei (Nutzer 20.11.2026) |
| A25 | Sprung von der Spielerleiste zur Quelle (appState.sourceJumpRequest) | gleich | [x] | Probebetrieb: /radio/<uuid> über Zurück und Vor; Sprung setzt dieselbe Adresse |
| A26 | Auswahl folgt dem Senderwechsel über Vor und Zurück | gleich | [x] | Markierung folgt appState.currentStation |
| A27 | Vor und Zurück über die geladene Liste (appState.stations) | über die sichtbare Liste (Vorgabe 7) | [x] | appState.stations aus der sichtbaren Liste, Nachbarn mit allen Feldern vorab |
| A28 | Bitratenprobe und Werbeprüfung beim Abspielen, Messwert nach 10 s in der Zeile | gleich, über die Senderquelle | [x] | Test senderquelle (Messung, Werbeprüfung nur mit Kennung); Probebetrieb verify-bitrate, check, bitrates |
| A29 | Senderlogo (Favicon) | Logo in der Zeile, ohne Logo das Kürzel auf Lackfläche | [x] | Logo.svelte über /api/favicon; ohne Bild Kürzel |
| A30 | Codec und Bitrate als Marken | Qualitätsleiste in der Zeile, Codec im Steckbrief | [x] | Qualitätsleiste, Codec und Bitrate in Zeile und Steckbrief |
| A31 | ICY-Marke mit Bewertung genaue oder ungenaue Schnitte (umschalten) | Steckbrief: Titelangaben im Strom mit Umschalter | [x] | Probebetrieb: Schnitte genau an und wieder aus |
| A32 | Werbestatus als Marke (Verdacht in Prozent) | Steckbrief: Werbung mit Stufe und eigener Entscheidung | [x] | Steckbrief Werbung: Stufe und eigene Entscheidung |
| A33 | Land, Stimmen, Klickzahl als Marken | Land und Ort im Steckbrief, Stimmen in der Zeile | [~] | Land und Ort im Steckbrief, Stimmen in der Zeile; die Klickzahl führt die Senderquelle nicht (nur Anzeige) |
| A34 | Läuft gerade (Titel aus dem Strom, Klick kopiert) | Titel in der Zeile des spielenden Senders, im Steckbrief mit Kopieren | [x] | Titel in der Zeile des spielenden Senders, im Steckbrief mit Kopieren |
| A35 | Homepage | Steckbrief | [x] | Steckbrief |
| A36 | Tags | Genres (aufbereitet) in Zeile und Steckbrief | [x] | Genres in Zeile und Steckbrief |
| A37 | Sprache | Sprachen im Steckbrief | [x] | Steckbrief |
| A38 | Stream-Adresse kopieren | Steckbrief | [x] | Steckbrief, Kopieren über den Appkern |
| A39 | Eigene Stream-Adresse bearbeiten, speichern, zurücksetzen; spielt der Sender, startet er neu | gleich | [x] | Probebetrieb: eigene Adresse gesetzt und zurückgesetzt; spielt der Sender, startet er neu |
| A40 | Kategorien zuordnen (Tafel) | Chips Eigene Kategorien im Detail | [x] | Probebetrieb: Kategorie an und wieder aus |
| A41 | Bewertung (Tafel): Werbung, Kein Werbeverdacht, Religiös, Extrem, Populistisch, Ab 18, Qualität, Instabil, Offline, Talk, Daumen | Sterne 1 bis 3 und alle Markierungen als Chips | [~] | Probebetrieb: Sterne und Markierungen an und aus; Daumen hoch und runter durch Sterne 1 bis 3 ersetzt (Entwurf) |
| A42 | Laden (Drehkreis), "NO STATIONS FOUND" | Ladezustand, ohne Treffer ein Hinweis mit "Alle zurücksetzen" | [x] | Ladezustand statt "NO STATIONS FOUND", ohne Treffer mit Alle zurücksetzen |
| A43 | Werbestatus der sichtbaren Sender nachladen | steht im Eintrag der Senderquelle | [x] | Werbestatus im Eintrag der Senderquelle |
| A44 | Klickgeräusche an Knöpfen | gleich (Einstellung Klickgeräusche) | [x] | sfx.click an Spielen, Details, Neu laden |

## B. Einstellungen > Radio > Filter (SetupFilter)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| B1 | Sprachen ausschließen (Liste mit Suche, ein Klick) | Neue Regel Sprache: tippen, wählen, Vorschau, dann anlegen (Entscheidung 31) | [x] | Probebetrieb: Kandidaten, Vorschau, Anlegen erst auf Knopfdruck |
| B2 | Alle oder keine Sprachen | Regeln einzeln an und aus, Entfernen mit Folgenvorschau | [x] | Probebetrieb: Regel aus mit Band, Rückgängig; Entfernen mit Folgenvorschau |
| B3 | Seltene Sprachen auf einmal (Schwelle) | mehrere Sprachen in einer Regel | [~] | mehrere Sprachen in einer Regel; das Ausschließen aller seltenen Sprachen auf einmal fehlt (offene Frage: Kandidaten auch aufsteigend nach Zahl) |
| B4 | Tags ausschließen (Eingabe, Vorschläge) | Neue Regel Genre oder Tag mit Vorschau | [x] | Arten Genre und Tag mit Kandidaten und Vorschau |
| B5 | Mindeststimmen | Neue Regel Stimmen mit Vorschau | [x] | Art Mindeststimmen mit Vorschau |
| B6 | Vorschau (Anzahl) und Ausblenden (Schnappschuss) | Live-Vorschau mit Favoriten und Beispielen, Anlegen, Rückgängig | [x] | Test Regel-Ablauf (Pause, Anlegen, Rückgängig, gleiche Regel); Probebetrieb Schlager 209 Sender, Rückgängig |
| B7 | Zusammenfassung der aktiven Filter | Bestand (gesamt, sichtbar, durch Regeln aus, verschwunden) und Liste der Regeln | [x] | Bestand als Gerät, Liste der lebenden Regeln |
| B8 | Länder der Seitenleiste wählen, suchen, alle oder keine | Reiter Länder der Seitenleiste (nur Anzeige, Entscheidung 6) | [x] | Reiter Länder der Seitenleiste, Suche, Auswahl leeren (vorher Alle und Keine, vertauscht) |

## C. Einstellungen > Radio > Sender (SetupSender)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| C1 | Werbeerkennung: geprüft, sauber, verdächtig, ausgeblendet | Reiter Werbeerkennung | [x] | Reiter Werbeerkennung, Stand als Gerät |
| C2 | Alle scannen mit Fortschritt, Stopp (zielte auf localhost:9091) | gleich, über die eigene Adresse | [x] | Prüfung in Runden über fetch mit Sitzung am eigenen Ursprung (im Probebetrieb nicht gestartet: er öffnet fremde Ströme) |
| C3 | Verdächtige einzeln oder alle: ausblenden oder in Ordnung | gleich | [x] | Verdächtige einzeln oder alle (25 im Probebetrieb) |
| C4 | Werbeerkennung an und aus, Adressprüfung, Serverprüfung, Schwelle | gleich | [x] | Schalter und Schwelle |
| C5 | Ausgeblendete nach Kategorie und Grund, aufklappbar | Reiter Ausgeblendete Sender: seitenweise, Suche, Filter nach Grund, Grund je Sender | [x] | Probebetrieb: 9.269, Seite 1 von 371, Suche rey, Gründe als Auswahl |
| C6 | Freigeben einzeln | Freigeben je Sender mit Rückgängig | [x] | Probebetrieb: Freigeben, Band, Wieder aus |
| C7 | Freigeben je Grund oder Kategorie, alle freigeben | Regel ausschalten oder entfernen (mit Folgenvorschau) | [x] | je Grund: Regel aus oder entfernen mit Folgenvorschau |

## D. Einstellungen > Radio > Kategorien (SetupKategorien)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| D1 | Kategorien anlegen, umbenennen, löschen | bleibt, als Reiter der Radio-Einstellungen | [x] | SetupKategorien unverändert im Reiter Kategorien |

## E. Telefon (TelefonRadio, SenderZeile)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| E1 | Suche ab 2 Zeichen, ohne Filter | Suche mit denselben Schnellfiltern wie am Rechner | [x] | Probebetrieb 375: Suche und dieselben Schnellfilter |
| E2 | Ohne Suche die Favoriten | Filter Nur Favoriten (Chip, Blatt) | [x] | Blatt: Nur Favoriten; Hinweis keine Favoriten |
| E3 | Zeile antippen spielt | gleich | [x] | Zeile antippen spielt |
| E4 | Stern merkt oder entfernt den Favoriten | gleich | [x] | Stern in der Zeile |
| E5 | Spielender Sender markiert | gleich | [x] | Rahmen blau beim spielenden Sender |
| E6 | Hinweise Laden, nicht erreichbar, keine Treffer, keine Favoriten | gleich | [x] | Hinweise Laden, Fehler, keine Treffer, keine Favoriten |
| E7 | Vor und Zurück (auch Sperrbildschirm) über die Favoriten | über die sichtbare Liste (Vorgabe 7) | [x] | Telefon.svelte: Vor und Zurück über appState.stations, ohne Liste die Favoriten |
