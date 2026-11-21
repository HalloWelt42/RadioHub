# RAD-17: Abgleich Aufnahmen und Schnitt

Stand 21.11.2026, nach dem Neubau. Jede Funktion aus `RAD-17-bestand-aufnahmen.md` ist wieder da, anders gelöst oder
ausdrücklich entfallen. Neue Teile: `frontend/src/components/aufnahmen`, `lib/aufnahmen`, `lib/schnitt`,
`stil/aufnahmen.css`, `components/telefon/TelefonAufnahmen.svelte`; Server `routers/wolke.py`, `routers/schnitt.py`,
`services/schnitt.py`.

## Aufnehmen (2.1)

Unverändert im Abspielmotor und in der Kanzel. Neu in der Ansicht: Kopf der laufenden Aufnahme mit blinkendem Licht,
Art (direkt oder aus dem Puffer mit Rückblick), Ziel, live erkannten Titeln (gesperrte blass), Lücken in der
Entwickleransicht, Uhr als Segmentanzeige und "Aufnahme beenden" (beendet nur die Aufnahme). Die Liste holt während
der Aufnahme alle 5 Sekunden nach; am Ende sagt das Band, wo die Aufnahme liegt.

## Liste (2.2)

| Bisher | Jetzt |
|---|---|
| höchstens 50, neueste zuerst | seitenweise je 50 mit Nachladen, Zählwerk mit der Gesamtzahl; sortierbar über den Tabellenkopf (Sender, Datum, Länge, Größe), auch in der Adresse |
| Suche nach Sendername | Suche nach Sender und Titel, mit eigenem Suchverlauf; in der Adresse `?suche=` |
| Ordnergruppen zum Aufklappen | Ordner in der Seitenleiste als Filter (Alle, je Ordner, Ohne Ordner) mit Zahl |
| Aufnahmeziel (Kreis) | rotes Licht und Kreis je Ordner, Hinweis in der Werkzeugleiste |
| Umbenennen, Löschen | an Ort und Stelle; Löschen nur leer und mit Rückfrage, sonst Hinweis mit Zahl |
| Verschieben aus Zeile und Kopf (zwei Wege) | ein Weg: Auswahl im Kopf der Aufnahme |
| Kennzahlen unten | unverändert, fest am Fuß der Seitenleiste |
| Breite der Seitenleiste ziehen | entfällt: feste Leiste wie bei Radio und Podcasts |
| Spielende Sitzung zeigen (rollen) | entfällt vorerst; das spielende Stück leuchtet blau |

## Eine Aufnahme und ihre Titel (2.3, 2.4)

Kopf mit Logo, Datum, Art, Ordner, Titelzahl, Länge, Größe, Format und Güte (ohne Lücken, Lücken, abgebrochen). Hören
(Titel werden Wiedergabeliste für Vor und Zurück; ohne Titel die ganze Aufnahme, der frühere Rückfall auf eine
abgelehnte Adresse ist behoben), Schneiden, Nach Titeln teilen (nur ungeteilt und mit erkannten Wechseln; ein Weg statt
zwei), Titel als ZIP, als eine Datei, Ordner, Löschen mit Rückfrage und Folgen (Titelzahl, Größe, Papierkorb).
Je Titel: ab hier hören, laden, schneiden (öffnet den Schnitt an seiner Stelle), sperren, löschen mit Rückfrage (der
letzte nimmt die Aufnahme mit). Teilauswahl von Segmenten entfällt; Wiedergabe gilt für alle Titel.

## Dateien (2.5)

Der Explorer entfällt samt Endpunkten `/api/files/*`. An seine Stelle tritt die Quelle "Kellerwolke": die ganze Wolke
Ebene für Ebene (Pfad, Eine Ebene höher, Unterordner), nur Audiodateien, sortierbar nach Name, Datum, Größe, Suche im
Ordner, hören, schneiden, laden. Mehrfachauswahl, ZIP beliebiger Dateien und "Verwaiste löschen" entfallen; das ZIP
einer Aufnahme bleibt im Kopf.

## Schnitt (2.6)

| Bisher | Jetzt |
|---|---|
| nur Aufnahmen | Aufnahmen und jede Audiodatei der Kellerwolke (Ergebnis als neue Datei daneben, ohne Schreibrecht im eigenen Ordner `Schnitt/<Ordner>`) |
| Zoom, Alles, Ausschnitt | Lupe plus und minus, Alles, Anzeige der sichtbaren Dauer; Tasten Plus und Minus |
| Zoom mit Strg und Mausrad | entfällt |
| Gain 1x bis 16x | Auswahl "Höhe" (nur Darstellung) |
| Auto-Play | entfällt: Klick springt; läuft der Ton, spielt er ab dort weiter |
| Mitlaufen | Schalter mit Licht |
| Übersicht | Übersicht mit Rahmen; Klick verschiebt den Ausschnitt; Marker darin ziehen entfällt |
| Marker setzen, Doppelklick, ziehen, aus Titeln, alle entfernen | alles da; dazu Taste M, Entf für den nächsten Marker |
| Markerliste | ersetzt durch die Stückliste: je Stück Name, von, bis, Länge, Behalten oder Weg, hören |
| Anfang weg, Ende weg | ersetzt durch Behalten oder Weg je Stück (jedes Stück, nicht nur Rand) |
| Schneiden ohne Rückfrage | Schneiden mit Rückfrage, die Behalten, Verwerfen und Ziel nennt; die übrigen Stücke rücken zusammen, Länge der Aufnahme folgt |
| Normalisieren, Umwandeln | unverändert im Ergebnis, als Leiste unter den Stücken; Bitrate als Auswahl |
| Fortschritt als Kreisel | Fortschrittsband mit Schritt und Zahl |
| kein Rückgängig | Schritte mit Rückgängig: Aufnahmen behalten die vorige Fassung unter `Schritte/<Nr>`, Dateien der Wolke legen das Ergebnis neu an (Rückgängig legt es in den Papierkorb); die letzten 10 Schritte bleiben |
| Tastenkürzel | Leertaste, M, Entf, Plus, Minus, Pfeile; der Schnitt behält sie für sich, die Hilfe dazu auf Wunsch |

Entfallene Endpunkte: `rec/sessions/{id}/peaks*`, `/audio`, `/audio-info`, `/normalize`, `/convert`, `/to-mono`,
`rec/audio-processing/presets`, `rec/sessions/{id}/custom-split`, `rec/sessions/{id}/metadata`, `rec/segments`.

## Telefon (2.7)

Neu: Reiter "Aufnahmen" nur zum Hören. Suche, Ordner als Chips, Zählwerk, Aufnahme öffnen, Titel ab der Stelle,
"Alles hören". Verwalten und Schneiden bleiben am Rechner. Die Webversion hat weiter keine Aufnahmen.
