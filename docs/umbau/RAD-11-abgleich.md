# RAD-11: Abgleich alt gegen neu

Stand 21.11.2026. Jede Zeile des Bestands ([RAD-11-bestand.md](RAD-11-bestand.md)) mit ihrem neuen Ort oder dem Grund,
warum sie entfällt. Neu heißt: Einstellungen > Bereich > Reiter. "Server" heißt: Feld im Modell `AppEinstellungen`,
gezeichnet als Zeile, gespeichert über die Leiste Speichern.

## Allgemein

| Alt | Neu |
| --- | --- |
| Klicktöne (Tabelle config) | Allgemein > Bedienung, Server `ui_click_sounds`, wirkt sofort nach Speichern |
| Entwickler-Modus | Allgemein > Bedienung, "Entwickleransicht", dieses Gerät |
| Sprache (20 Knöpfe) | Allgemein > Bedienung, Server `language`, Aufklappliste mit Namen |
| Kleinste und größte Bitrate des Zeitversatzes | Wiedergabe, Server, Grenzen jetzt wie im Modell (8 bis 512), Regel kleinste höchstens größte |
| Rückblick der Puffer-Aufnahme | Wiedergabe, Server `hls_rec_lookback_minutes`; gilt ab dem Start, nicht erst nach dem Öffnen der Einstellungen |
| Tastatur (Tabelle von Hand) | Allgemein > Tastatur, aus `schale/tastatur.ts` abgeleitet; Sperren während einer Aufnahme stimmen jetzt |
| Info, Lizenz, Recht | Allgemein > Über, je Text gekürzt mit Mehr zeigen |
| Bedanken: Spendenseite, drei Adressen, Kopieren | Allgemein > Bedanken |

## Radio

| Alt | Neu |
| --- | --- |
| Ausschlussregeln, Ausgeblendete Sender, Länder | unverändert (schon im neuen Aussehen), Radio > gleiche Reiter |
| Werbeerkennung (Stand, Prüfung, Verdächtige, Einstellungen) | Radio > Werbeerkennung; Werte jetzt im Modell (Verfahren als echte Liste, Schwelle in Prozent) |
| Senderverzeichnis: Abgleich | Radio > Senderverzeichnis; die Uhrzeit ist jetzt einstellbar (Server `abgleich_uhrzeit`) |
| Kategorien (altes Aussehen) | Radio > Kategorien im neuen Aussehen; Löschen fragt mit Zahl der Zuordnungen |
| Eigene Daten (Basic) | Radio > Eigene Daten |

## Podcast, Aufnahmen, Speicher, Dienste

| Alt | Neu |
| --- | --- |
| Auto-Aktualisierung, Intervall | Podcasts; Abstand in Stunden gezeigt, bis 7 Tage wie im Modell |
| Aufnahmeordner: anlegen, umbenennen, aktivieren, Stammordner, löschen | Aufnahmen > Ordner; löschen fragt, ein voller Ordner sagt vorher, dass er erst leer sein muss |
| Ignorierte Titel: Muster, Art, hinzufügen, löschen | Aufnahmen > Titel ignorieren; eingebaute Muster geschützt (auch im Server), eigene mit Rückfrage |
| Speicherzonen: Pfad ändern, prüfen, speichern | entfällt (Entscheidung): Ablage zeigt Datenordner und Belegung; Pfade setzt das Ausrollen |
| Zone Konfiguration | entfällt, wurde nie gelesen |
| Dienste: Senderverzeichnis, Podcast-Verzeichnisse, Standard | Dienste, Server; "Vorgabe" fragt vorher und nennt die eigene Angabe; Titel ohne fremde Marken |

## Außerhalb der Seite

| Alt | Neu |
| --- | --- |
| Darstellung (Vorlage, Thema, Schrift) | bleibt im Kopf, zusätzlich Darstellung (dieselben Werte) |
| Bildschirm wach halten | Darstellung > Bildschirm, dazu weiter im Telefonblatt |
| Zeitansage: an, Abstand, Zeitraum, Wann, Nachtrot | Wecker und Zeitansage > Zeitansage (jetzt auch am Rechner), dieses Gerät; weiter im Telefonblatt |
| Ort: suchen, Standort, Name, Breite, Länge | Wecker und Zeitansage > Ort; wartet in der Leiste Speichern; PRO Server (Regel: Breite und Länge zusammen), Basic Browser |
| Bausteine erzeugen | Wecker und Zeitansage > Zeitansage > Stimme |
| Wecker (Liste, Editor) | unverändert am Telefon; neu im Editor: Schlummerdauer (1 bis 60 min), Langsam lauter bis 600 s wie im Server |
| Konto: Abmelden, Trennen | unverändert in der Tafel im Kopf |
| Kanzel: Lautstärke, Bitrate, Fokus, Tempo, Reihenfolge | unverändert in der Kanzel; die Drehwahl Bitrate ist unter Wiedergabe erklärt |

## Server-Einstellungen bisher ohne Bedienung

| Alt | Neu |
| --- | --- |
| Ordner in der Kellerwolke, Geduld beim Ablegen | Ablage > Kellerwolke (Geduld in Minuten, bis 60) |
| Ortssuche, Vertonung | Dienste > Helfer im Haus |
| Zeit-Stimme, Tempo | Wecker und Zeitansage > Zeitansage > Stimme (Stimmen aus der Vertonung) |
| Fremde Ursprünge | Dienste > Zugang |
| Bitrate der Aufnahme, Aufnahme protokollieren | Aufnahmen > Technik |
| Abtastrate | Wiedergabe (Wahl aus 22.050, 32.000, 44.100, 48.000 Hz) |
| Uhrzeit des Abgleichs | Radio > Senderverzeichnis |
| Länge des Puffers (fest 120 min) | Wiedergabe, Server `hls_puffer_minuten` |

## Ohne Bedienung entfallen

`recording_format` (nie gelesen), `POST /api/config/reset` (setzte ohne Rückfrage alles zurück), Speicherzonen ändern
und prüfen, 16 ungenutzte Textabschnitte in allen Sprachen.

## Bewusst nicht in RAD-11

- Einstellungsblatt am Telefon: bleibt, wie es ist, mit denselben Modulen; neues Aussehen mit RAD-14.
- Hausempfang: erst mit RAD-18.
- Grundeinstellungen des Appkerns (Kellerwolke-Zugang, Anmeldung, Sicherung): bleiben in der Einrichtung des Appkerns.
