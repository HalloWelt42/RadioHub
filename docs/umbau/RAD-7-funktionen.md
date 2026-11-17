# RAD-7, Teil 3b: Bedienfunktionen der Radio-Ansicht alt -> neu

Angelegt vor dem Neubau der Oberfläche der Senderfilterung (Regel: bei einer Neugestaltung keine Funktion verlieren).
Erfasst sind alle Bedienfunktionen der bisherigen Teile `components/StationsTab.svelte`,
`components/setup/SetupFilter.svelte`, `components/setup/SetupSender.svelte`, `components/setup/SetupKategorien.svelte`,
`components/telefon/TelefonRadio.svelte` und `components/telefon/SenderZeile.svelte` (mit `hifi/HiFiTagPanel.svelte`).
Je Zeile: was es heute gibt, wo es im Neubau steht, Stand und Nachweis (Test oder Probebetrieb). Die alten Teile
werden erst entfernt, wenn jede Zeile abgehakt ist.

Stand: `[ ]` offen, `[x]` im Neubau vorhanden und geprüft, `[~]` bewusst geändert (Begründung in der Zeile).

Neue Teile: Senderquelle `frontend/src/lib/radio/` (Schnittstelle `quelle.ts`, Umsetzung `backend.ts`, Schnellfilter
und Adresse `schnellfilter.ts`, Liste `senderliste.svelte.ts`, Regel-Ablauf `regelablauf.svelte.ts`), Ansichten
`frontend/src/components/radio/` (Rechner, Einstellungen) und `components/telefon/TelefonRadio.svelte`.

## A. Radio am Rechner (StationsTab)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| A1 | Senderliste, beim Rollen nachladen (Versatz) | Liste seitenweise mit Seitenzeiger (Keyset), Nachladen am Listenende | [ ] | |
| A2 | Zähler zeigt geladene Sender | Segmentanzeige mit echter Gesamtzahl der Treffer, dazu "von N sichtbaren" | [ ] | |
| A3 | Suche nach Name, entprellt, ab 2 Zeichen | Suche (Name, Genre, Ort) entprellt, steht in der Adresse | [ ] | |
| A4 | Suchverlauf: 10 letzte, wählen, Verlauf löschen | Suchfeld mit Verlauf, gleiche Funktionen, gleicher Schlüssel im Browser | [ ] | |
| A5 | Suche leeren (X) | Knopf im Suchfeld und Chip "Suche" | [ ] | |
| A6 | Adresse /radio/search/<suche> | bleibt gültig, wird zur Suche in der Adresse | [ ] | |
| A7 | Direktlink /radio/<uuid>: Sender wählen, nachladen, hinrollen | gleich: Details offen, nicht geladene Sender vorn eingefügt | [ ] | |
| A8 | Länderfilter der Seitenleiste mit Zahlen, Mehrfachwahl | Facette Länder mit Zahlen unter allen übrigen Filtern | [ ] | |
| A9 | Hinweis "Länder konfigurieren" | Verweis "Länder wählen" in den Einstellungen | [ ] | |
| A10 | Kategorienfilter, Hinweis "Kategorien erstellen" | Facette Eigene Kategorien, Verweis "Verwalten" | [ ] | |
| A11 | Bitrate in sechs Bereichen | Mindestbitrate als Leuchtbalken, dazu Facetten Qualität und Codec | [ ] | |
| A12 | Stimmen in sechs Bereichen | Mindeststimmen als Drehwahl | [ ] | |
| A13 | Nur Favoriten (im Browser gemerkt) | Taster Nur Favoriten, steht in der Adresse, wirkt mit allen Filtern (Vorgabe 2) | [ ] | |
| A14 | Filter zurücksetzen (X) | "Alle zurücksetzen", Chips einzeln, Zurücksetzen im Kopf der Seitenleiste | [ ] | |
| A15 | Knopf zu den Filter-Einstellungen | Hinweis "n Sender durch Ausschlussregeln ausgeblendet" mit Sprung zu den Regeln | [ ] | |
| A16 | Sortierung per Spaltenkopf: Name, Land, Bitrate, Stimmen, auf und ab | Sortierung Stimmen, Name, Qualität, Bitrate | [ ] | |
| A17 | Aktualisieren: Senderverzeichnis abgleichen und Filter zurücksetzen | "Neu laden" lädt nur die Liste (Vorgabe 4); Abgleich als Auftrag in den Einstellungen | [ ] | |
| A18 | Abspielen über Leuchte oder Name | Klick auf die Senderzeile | [ ] | |
| A19 | Details auf- und zuklappen (Adresse /radio/<uuid>) | Knopf Details, Adresse wie bisher | [ ] | |
| A20 | Leuchte: blau spielt, rot blinkt bei Aufnahme, gelb gewählt | gleich | [ ] | |
| A21 | Favorit umschalten | Stern in der Zeile | [ ] | |
| A22 | Auge blendet aus und startet den Nachbarsender | Auge mit Rückgängig-Band, startet keinen Sender (Vorgabe 5) | [ ] | |
| A23 | Tastatur: Pfeil hoch und runter, Eingabe und Leertaste spielen, Escape schließt | gleich | [ ] | |
| A24 | Nach 90 s ohne Bedienung zum spielenden Sender rollen | gleich | [ ] | |
| A25 | Sprung von der Spielerleiste zur Quelle (appState.sourceJumpRequest) | gleich | [ ] | |
| A26 | Auswahl folgt dem Senderwechsel über Vor und Zurück | gleich | [ ] | |
| A27 | Vor und Zurück über die geladene Liste (appState.stations) | über die sichtbare Liste (Vorgabe 7) | [ ] | |
| A28 | Bitratenprobe und Werbeprüfung beim Abspielen, Messwert nach 10 s in der Zeile | gleich, über die Senderquelle | [ ] | |
| A29 | Senderlogo (Favicon) | Logo in der Zeile, ohne Logo das Kürzel auf Lackfläche | [ ] | |
| A30 | Codec und Bitrate als Marken | Qualitätsleiste in der Zeile, Codec im Steckbrief | [ ] | |
| A31 | ICY-Marke mit Bewertung genaue oder ungenaue Schnitte (umschalten) | Steckbrief: Titelangaben im Strom mit Umschalter | [ ] | |
| A32 | Werbestatus als Marke (Verdacht in Prozent) | Steckbrief: Werbung mit Stufe und eigener Entscheidung | [ ] | |
| A33 | Land, Stimmen, Klickzahl als Marken | Land und Ort im Steckbrief, Stimmen in der Zeile | [ ] | |
| A34 | Läuft gerade (Titel aus dem Strom, Klick kopiert) | Titel in der Zeile des spielenden Senders, im Steckbrief mit Kopieren | [ ] | |
| A35 | Homepage | Steckbrief | [ ] | |
| A36 | Tags | Genres (aufbereitet) in Zeile und Steckbrief | [ ] | |
| A37 | Sprache | Sprachen im Steckbrief | [ ] | |
| A38 | Stream-Adresse kopieren | Steckbrief | [ ] | |
| A39 | Eigene Stream-Adresse bearbeiten, speichern, zurücksetzen; spielt der Sender, startet er neu | gleich | [ ] | |
| A40 | Kategorien zuordnen (Tafel) | Chips Eigene Kategorien im Detail | [ ] | |
| A41 | Bewertung (Tafel): Werbung, Kein Werbeverdacht, Religiös, Extrem, Populistisch, Ab 18, Qualität, Instabil, Offline, Talk, Daumen | Sterne 1 bis 3 und alle Markierungen als Chips | [ ] | |
| A42 | Laden (Drehkreis), "NO STATIONS FOUND" | Ladezustand, ohne Treffer ein Hinweis mit "Alle zurücksetzen" | [ ] | |
| A43 | Werbestatus der sichtbaren Sender nachladen | steht im Eintrag der Senderquelle | [ ] | |
| A44 | Klickgeräusche an Knöpfen | gleich (Einstellung Klickgeräusche) | [ ] | |

## B. Einstellungen > Radio > Filter (SetupFilter)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| B1 | Sprachen ausschließen (Liste mit Suche, ein Klick) | Neue Regel Sprache: tippen, wählen, Vorschau, dann anlegen (Entscheidung 31) | [ ] | |
| B2 | Alle oder keine Sprachen | Regeln einzeln an und aus, Entfernen mit Folgenvorschau | [ ] | |
| B3 | Seltene Sprachen auf einmal (Schwelle) | mehrere Sprachen in einer Regel | [ ] | |
| B4 | Tags ausschließen (Eingabe, Vorschläge) | Neue Regel Genre oder Tag mit Vorschau | [ ] | |
| B5 | Mindeststimmen | Neue Regel Stimmen mit Vorschau | [ ] | |
| B6 | Vorschau (Anzahl) und Ausblenden (Schnappschuss) | Live-Vorschau mit Favoriten und Beispielen, Anlegen, Rückgängig | [ ] | |
| B7 | Zusammenfassung der aktiven Filter | Bestand (gesamt, sichtbar, durch Regeln aus, verschwunden) und Liste der Regeln | [ ] | |
| B8 | Länder der Seitenleiste wählen, suchen, alle oder keine | Reiter Länder der Seitenleiste (nur Anzeige, Entscheidung 6) | [ ] | |

## C. Einstellungen > Radio > Sender (SetupSender)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| C1 | Werbeerkennung: geprüft, sauber, verdächtig, ausgeblendet | Reiter Werbeerkennung | [ ] | |
| C2 | Alle scannen mit Fortschritt, Stopp (zielte auf localhost:9091) | gleich, über die eigene Adresse | [ ] | |
| C3 | Verdächtige einzeln oder alle: ausblenden oder in Ordnung | gleich | [ ] | |
| C4 | Werbeerkennung an und aus, Adressprüfung, Serverprüfung, Schwelle | gleich | [ ] | |
| C5 | Ausgeblendete nach Kategorie und Grund, aufklappbar | Reiter Ausgeblendete Sender: seitenweise, Suche, Filter nach Grund, Grund je Sender | [ ] | |
| C6 | Freigeben einzeln | Freigeben je Sender mit Rückgängig | [ ] | |
| C7 | Freigeben je Grund oder Kategorie, alle freigeben | Regel ausschalten oder entfernen (mit Folgenvorschau) | [ ] | |

## D. Einstellungen > Radio > Kategorien (SetupKategorien)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| D1 | Kategorien anlegen, umbenennen, löschen | bleibt, als Reiter der Radio-Einstellungen | [ ] | |

## E. Telefon (TelefonRadio, SenderZeile)

| Nr | Heute | Neu | Stand | Nachweis |
|---|---|---|---|---|
| E1 | Suche ab 2 Zeichen, ohne Filter | Suche mit denselben Schnellfiltern wie am Rechner | [ ] | |
| E2 | Ohne Suche die Favoriten | Filter Nur Favoriten (Chip, Blatt) | [ ] | |
| E3 | Zeile antippen spielt | gleich | [ ] | |
| E4 | Stern merkt oder entfernt den Favoriten | gleich | [ ] | |
| E5 | Spielender Sender markiert | gleich | [ ] | |
| E6 | Hinweise Laden, nicht erreichbar, keine Treffer, keine Favoriten | gleich | [ ] | |
| E7 | Vor und Zurück (auch Sperrbildschirm) über die Favoriten | über die sichtbare Liste (Vorgabe 7) | [ ] | |
