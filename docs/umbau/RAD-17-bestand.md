# RAD-17: Bestand von Podcasts, Aufnahmen und Schnitt

Stand 20.11.2026, vor dem Umbau nach dem Muster der Radioseite (Quelle mit `faehig`, Zustand in `lib/<bereich>/`,
schlanke Ansichten, Stil mit `rh-` und Bausteinen des Appkerns). Jede Bedienfunktion unten muss nach dem Umbau wieder
da sein oder ausdrücklich entfallen (Spalte Stand).

## Dateien (frontend/src)

| Bereich | Datei | Zeilen | Aufgabe |
| --- | --- | --- | --- |
| Podcasts | components/PodcastsTab.svelte | 962 | holt Daten, Filter, Sortierung, Batch-Download, Wiedergabe, Tasten |
| Podcasts | podcasts/PodcastSidebar.svelte | 757 | Abos mit Ziehen, Breite, Filter Heute/Woche/Alle, Vorschau |
| Podcasts | podcasts/PodcastSearch.svelte | 469 | Suche in Folgen, Abos und extern, sucht selbst |
| Podcasts | podcasts/PodcastSearchView.svelte | 185 | Treffer der externen Suche |
| Podcasts | podcasts/PodcastHeader.svelte | 305 | Kopf mit Kennzahlen und Knöpfen |
| Podcasts | podcasts/EpisodeList, EpisodeRow, EpisodeDetails | 649 | Folgentabelle, Zeile, aufgeklappte Folge |
| Podcasts | podcasts/DownloadJobPanel.svelte | 236 | Fortschritt "alles herunterladen" |
| Podcasts | setup/SetupPodcast.svelte | 139 | automatische Aktualisierung, Abstand |
| Telefon | telefon/TelefonPodcasts.svelte | 248 | Abos, Gemerkt, Folgen, Detail, alles in einer Datei |
| Aufnahmen | components/RecordingsTab.svelte | 1205 | Sitzungen, Ordner, Segmente, Sperrliste, Abfrage alle 3 s, Explorer, Wiedergabe |
| Aufnahmen | recordings/RecordingSidebar.svelte | 1014 | Ordner, Verschieben, Auswahl, Suche, Breite |
| Schnitt | recordings/CutterView.svelte | 1265 | Wellenform, Zoom, Gain, Marker, Trimmen, Schnitt, Auto-Split, Normalisieren, Umwandeln |
| Gemeinsam | shared/FileExplorer.svelte | 701 | Dateien abspielen, löschen, ZIP |
| Gemeinsam | hifi/HiFiBadge, HiFiLed, HiFiDisplay, HiFiKnob | | alte Instrumente, feste Farben |
| Gemeinsam | lib/peaksLoader.js, lib/waveformRenderer.js | 481 | Wellenform laden und zeichnen |

## Befunde

- Datenholen, Zustand, Darstellung und Wiedergabe liegen in denselben Komponenten; `api.*` direkt aus fast allen
  Komponenten (RecordingsTab 32-mal), `appState` 27-mal in RecordingsTab.
- Doppelt: zwei externe Suchen (Seitenleiste und Hauptbereich), zwei Abo-Listen (`subscriptions` und
  `appState.podcasts`), `loadEpisodes` und `loadAllEpisodes`, Auto-Download und Aktualisieren je zweimal, verstellbare
  Seitenleiste in Podcasts und Aufnahmen, Verschiebemenü zweimal, Abspielen aus dem Explorer in beiden Reitern,
  Vor und Zurück für Folge und Aufnahme im Store.
- Telefon: eigene Formatierer statt `formatters.js`, Filter anders als am Rechner (alle/ungehört/geladen gegen
  heute/Woche/alle), "Gemerkt" heißt dort "heruntergeladen", ohne Knopf zum Merken oder Laden (RAD-14).
- Der Batch-Download läuft als Warteschlange in der Komponente; den Endpunkt `download-batch` ruft niemand.
- Stil: keine `rh-`-Klasse, kein `ak-`-Baustein, durchgehend `hifi-*`, feste Schriftgrößen und Farben.
- Ungenutzte Endpunkte: Podcasts mark-all-played, download-batch, transcript, played-downloads, storage/stats;
  Audio audio-info, to-mono, presets.
- Tests: Backend 4 (Podcasts) und 11 (Aufnahmen); Frontend nur die Wiedergabe (playerEngine) und die Telefon-Route.

## Bedienfunktionen

| Nr. | Bereich | Funktion | Stand |
| --- | --- | --- | --- |
| P1 | Podcasts | abonnieren, Abo entfernen, Abos umsortieren (ziehen) | da (Abbestellen mit Rückgängig) |
| P2 | Podcasts | einen Feed und alle aktualisieren, Countdown bis zur nächsten automatischen Aktualisierung | da (Hinweis mit Zeit bis zur nächsten) |
| P3 | Podcasts | automatisch herunterladen je Abo | da (Taster Neue merken im Kopf des Abos) |
| P4 | Podcasts | suchen in Folgen, Abos und extern, Suchverlauf, Adressen /podcasts/search/q und /podcasts/id/folge | da: Volltext der Folgen, Verzeichnis, eigener Verlauf, Adressen (auch /podcasts/search/q); Suche in Abos entfällt (Abos stehen in der Seitenleiste) |
| P5 | Podcasts | alle Folgen, Filter heute/Woche/alle, sortieren nach Titel, Datum, Dauer, Nachladen | da; heute/Woche ersetzt durch Alle/Ungehört/Gemerkt (Nutzer: Gerät war zu viel) |
| P6 | Podcasts | Folge aufklappen, hören (Liste wird Wiedergabeliste), herunterladen, Download löschen, gehört/ungehört | da |
| P7 | Podcasts | alles herunterladen mit Pause, Fortsetzen, Abbruch | da (Folge für Folge mit Fortschritt) |
| P8 | Podcasts | Dateien: abspielen, löschen, ZIP | entfällt am Rechner: Gemerkt-Filter zeigt die Dateien, Freigeben löscht; ZIP entfällt |
| P9 | Podcasts | Sprung zum spielenden Podcast, Pfeiltasten, Eingabe, Esc | Sprung über /podcasts/abo; Pfeiltasten in der Liste noch offen |
| P10 | Podcasts | Einstellungen: automatische Aktualisierung, Abstand 1 bis 48 h | da (Verweis Abstand ändern in die Einstellungen) |
| T1 | Telefon | Abos mit Zahl ungehörter Folgen, gemerkte Folgen, filtern, mehr laden, abspielen, Detail, Fortschritt | |
| T2 | Telefon | RAD-14: suchen und abonnieren, laden und merken, neue Folgen zuerst | neu |
| A1 | Aufnahmen | stoppen, Titel und Lücken live (Entwicklermodus) | |
| A2 | Aufnahmen | Sitzung abspielen, zu einem Titel springen, als ZIP oder Gesamtdatei laden, löschen, nach Titeln teilen | |
| A3 | Aufnahmen | Ordner anlegen, umbenennen, löschen, als Ziel an/aus, Sitzung verschieben, einklappen (gemerkt) | |
| A4 | Aufnahmen | Segment abspielen, herunterladen, löschen, Titel sperren und entsperren | |
| A5 | Aufnahmen | Suche mit Adresse; Dateien: Mehrfachauswahl abspielen, löschen, verwaiste Ordner löschen, ZIP | |
| S1 | Schnitt | Zoom rein/raus, alles zeigen, Gain, Auto-Play, Übersicht (Minimap) | |
| S2 | Schnitt | Marker per Doppelklick setzen, ziehen, löschen; Marker aus Titelangaben | |
| S3 | Schnitt | Anfang und Ende trimmen, schneiden, Auto-Split | |
| S4 | Schnitt | Normalisieren (-16 LUFS), Umwandeln (Format, Bitrate, Mono) für gewählte Segmente | |

## Schnitt nach dem Radio-Muster

- Podcasts: `lib/podcasts/quelle.ts` (Schnittstelle Podcastquelle mit `faehig`), `backend.ts`; Zustand
  `abos.svelte.ts` (eine Liste), `folgenliste.svelte.ts` (Seiten wie die Senderliste), `podcastfilter.svelte.ts`,
  `bedienung.svelte.ts` (Wiedergabe, Downloads, alles laden über den Endpunkt). Rechner und Telefon auf derselben
  Quelle und demselben Zustand, ein gemeinsamer Filter.
- Aufnahmen: `lib/aufnahmen/` mit Quelle (Sitzungen, Segmente, Ordner, Sperrliste, Dateien), Zustand
  (Sitzungsliste mit Abfrage, Ordner, Bedienung).
- Schnitt: `lib/schnitt/` mit Quelle (Wellenform, Audio, Schnitt, Aufträge mit Fortschritt) und Zustand (Marker,
  Trimmen, Zoom, Gain, Auftrag).
- Querschnitt: ein Baustein für die verstellbare Seitenleiste, Dateien als eigene Quelle, Texte in eigene Bereiche.

Reihenfolge: erst die Schichten unter den Ansichten (Quelle und Zustand mit Tests); dann die Entwürfe im Stil der
Radioseite; dann die neuen Ansichten nach Entwurf auf denselben Schichten. Die alten Ansichten werden nicht erst auf
die Schicht umgestellt, weil die neuen sie ersetzen (sonst doppelte Arbeit, Nutzer 20.11.2026: "wir müssen mal
langsam zum ui kommen"). Stand: Podcasts am Rechner nach Entwurf gebaut (components/podcast, lib/podcasts, Tests in tests/podcasts.test.ts); die alte Ansicht ist entfernt.
