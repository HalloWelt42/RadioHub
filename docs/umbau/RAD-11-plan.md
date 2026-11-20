# RAD-11: Umbau der Einstellungen

Stand 21.11.2026. Grundlage ist der Bestand in [RAD-11-bestand.md](RAD-11-bestand.md) (122 Einstellungen). Die
Entscheidungen des Nutzers stehen am Ticket RAD-11.

## Entscheidungen

| Frage | Entscheidung |
| --- | --- |
| Grundlage | Eine Wahrheit: jede Server-Einstellung ist ein Feld von `AppEinstellungen` (Titel, Beschreibung, Grenzen, Einheit, Gruppe). Der Einstellungsbaustein des Appkerns zeichnet die Zeilen. |
| Geltung | Wie heute: Sprache und Klicktöne für alle Geräte; Darstellung, Lautstärke, Zeitansage, Bildschirm wach, Entwickleransicht je Gerät. |
| Speicher | Anzeigen statt ändern. Pfade setzt das Ausrollen; die Zone Konfiguration entfällt. |
| Verborgene Server-Einstellungen | Alle bekommen eine Zeile in ihrem Bereich; fest gesetzte stehen gesperrt mit Hinweis da. Dazu die Schlummerdauer. |

## Schichten

1. **Server: Modell.** `backend/app/einstellungen.py` bleibt die eine Quelle. Neu darin, aus der Tabelle `config`
   übernommen (Übergang wie in `uebergang.config_uebernehmen`): Sprache, Klicktöne, Rückblick der Puffer-Aufnahme,
   Werbeerkennung (an, Verfahren als echte Liste, Schwelle), Ort (Name, Breite, Länge). Neu als Feld, bisher fest im
   Code: Länge des Zeitversatz-Puffers (120 min), Schlummerdauer (9 min). Gruppen ordnen jedes Feld einem Bereich zu.
   Sichtbare Titel ohne fremde Marken (etwa "Podcast-Verzeichnis, weltweit" statt des Anbieternamens).
   `recording_format`, `POST /api/config/reset` und die Zone Konfiguration entfallen; `/api/config` bleibt nur für den
   zuletzt gehörten Sender und die Länder der Seitenleiste.
2. **Server: Prüfungen.** Kleinste Bitrate höchstens größte (Modellprüfung), Rückblick höchstens Pufferlänge.
3. **Oberfläche: Schicht `lib/einstellungen/`.**
   - `typen.ts`: Bereich, Geltung (`alle` oder `geraet`), Zeilenbeschreibung.
   - `server.ts`: liest und schreibt die Felder über die Einstellungsschnittstelle des Appkerns (Entwurf, Speichern,
     Verwerfen), wie `teile/Einstellungen.svelte`.
   - `geraet.svelte.ts`: alle Einstellungen je Gerät an einer Stelle (ein Eintrag je Schlüssel mit Vorgabe, Grenzen,
     Prüfung), statt verstreuter `localStorage`-Zugriffe.
   - Fähigkeiten je Ausgabe: PRO hat Server-Felder, Basic nur Gerät und eigene Daten. Basic bekommt keine toten Zeilen.
4. **Oberfläche: Ansichten `components/einstellungen/`.** Eine Hülle (Bereiche links, Pfad und Reiter oben, Rollfeld),
   je Bereich eine dünne Ansicht. Einfache Werte zeichnet die gemeinsame Zeile aus der Beschreibung; Sonderteile bleiben
   eigene Bausteine (Regeln, ausgeblendete Sender, Länder, Werbeerkennung, Kategorien, Aufnahmeordner, Muster der
   Titel, Ort, Tastatur, Über, Bedanken, Eigene Daten).
5. **Tastatur** wird aus `schale/tastatur.ts` abgeleitet, nicht mehr von Hand beschrieben.
6. **Löschen** überall mit Rückfrage und Folgen: Kategorie (Zahl der Zuordnungen), Aufnahmeordner, Muster der Titel
   (eingebaute geschützt), Wecker, Dienst auf Vorgabe, Länderauswahl leeren, Werbung alle ausblenden, Abmelden.

## Bereiche

| Bereich | Reiter | Inhalt | Ausgabe |
| --- | --- | --- | --- |
| Allgemein | Bedienung, Tastatur, Über, Bedanken | Sprache, Klicktöne, Entwickleransicht; Tastenkürzel; Info, Lizenz, Recht; Spenden | PRO (Basic: Tastatur, Über, Bedanken) |
| Darstellung | - | Vorlage, Thema, Schrift, Bildschirm wach halten (dieselbe Tafel wie im Kopf) | beide |
| Radio | wie heute, Kategorien im neuen Aussehen | Ausschlussregeln, Ausgeblendete, Länder, Werbeerkennung, Senderverzeichnis (Uhrzeit jetzt einstellbar), Kategorien, Eigene Daten | beide nach Fähigkeit |
| Wiedergabe | - | Zeitversatz: Grenzen der Bitrate (die Drehwahl der Kanzel wählt je Gerät darin), Abtastrate, Pufferlänge, Rückblick der Puffer-Aufnahme | PRO |
| Aufnahmen | Ordner, Titel ignorieren, Technik | Aufnahmeordner, Muster der Titel, Bitrate, Protokoll | PRO |
| Podcasts | - | Abos von selbst abrufen, Abstand | PRO |
| Wecker und Zeitansage | - | Zeitansage (je Gerät), Ort, Zeit-Stimme und Tempo, Bausteine, Schlummerdauer, Sprung zu den Weckern | beide (Stimme und Bausteine PRO) |
| Ablage | - | Datenordner und Belegung (nur Anzeige), Ordner in der Kellerwolke, Geduld beim Ablegen | PRO |
| Dienste | - | Senderverzeichnis, Podcast-Verzeichnisse, Ortssuche, Vertonung, fremde Ursprünge | PRO |

Hausempfang erscheint erst mit RAD-18.

## Reihenfolge

1. Entwurf aller Bereiche (`mockups/radio-filter/einstellungen.html`), Abnahme.
2. Server: Modell, Übergang, Prüfungen, Tests.
3. Schicht der Oberfläche mit Tests.
4. Hülle und Bereiche nach Entwurf, alte `components/setup/*` entfernen.
5. Abgleich alt gegen neu: jede Zeile des Bestands abgehakt oder ausdrücklich entfallen.
