# RAD-1: Plan für die Überarbeitung des Radios

Geklärt mit dem Nutzer am 16.11.2026 ("grill mich", 23 Fragen). Grundlage: [BEFUND.md](BEFUND.md).
Ticket: RAD-1 im Board Radio (RAD) der Pinnwand. Sicherung vor dem Umbau: `backups/2026-11-16-RAD-1/`,
Git-Marke `vor-RAD-1`.

## Entscheidungen

### Design und Grundlage

| Nr | Frage | Entscheidung |
|---|---|---|
| 1 | Leitdesign | HiFi überall: ein Baukasten für Rechner, Telefon und Wecker, am Telefon reduziert, aber mit denselben Bauteilen |
| 2 | Vorgehen | Schrittweise im Betrieb, jede Etappe einzeln ausrollbar, die App läuft immer |
| 7 | Baukasten | Appkern + Vorlage HiFi: die Vorlage aus hifi-regler wandert in den Appkern; Regler und Anzeigen von dort, wo sie besser sind; Radio-eigene Bausteine darauf |
| 8 | Backend | Ganz auf Appkern: Einstellungen, Datenbank mit Versionsstufen, Protokoll, Aufträge, Anmeldung mit Kellerwolke-Konto |
| 20 | Telefon und Wecker | Mitwachsen je Etappe: jeder Bereich kommt für Rechner und Telefon zugleich; Wecker als eigene Etappe nach dem Player |
| 21 | Betrieb | Ganz angleichen: Ordner frontend/backend, Haken, version.json, Ausrollen mit Prüfungen, Handbuch; Umzug nach /mnt/data/radiohub beim ersten Ausrollen |

### Filterung

| Nr | Frage | Entscheidung |
|---|---|---|
| 3 | Reihenfolge | Filterung zuerst nach dem Baukasten, dann Player, dann die übrigen Bereiche |
| 4 | Filterorte | Zwei Ebenen: im Radio nur Schnellfilter für jetzt (flüchtig, in der Adresse, Chips); dauerhafte Ausschlüsse nur in den Einstellungen, Änderung erst nach Vorschau mit Anzahl und mit Rückgängig |
| 5 | Ausschlüsse | Lebende Regeln (Sprache, Tag, Mindeststimmen, Werbung, Bewertung, Einzelsender), gelten auch für neue Sender, Grund je Sender sichtbar; alte Sperren werden überführt, Einzelsperren bleiben Einzelsperren |
| 6 | Länder | Die Länderwahl legt nur die Schnellfilter der Seitenleiste fest; nie mehr stiller Ausschluss |
| 18 | Bewertungen | Als Schnellfilter und als dauerhafte Regel nutzbar; "Werbung" fließt in die Werbeerkennung |

### Player, Abspielleiste, Streams

| Nr | Frage | Entscheidung |
|---|---|---|
| 9 | Mehrere Geräte | Ein Hausempfang: alle Geräte teilen die Wiedergabe, ein Wechsel gilt überall |
| 10 | Tonausgabe | Nur ein Gerät spielt; ein anderes übernimmt ("Holen") oder bekommt den Ton ("Abspielen auf"), wie in TubeVault |
| 11 | Umfang | Für alles: Radio, Podcast-Folge, Aufnahme |
| 12 | Wecker | Eigenständig: vom Hausempfang ausgenommen, spielt immer für sich |
| 13 | Übergabe | Vermittler und Oberflächenbaustein aus TubeVault wandern in den Appkern; Radio nutzt sie zuerst, TubeVault zieht später nach |
| 14 | Zeitversatz | Läuft immer mit, aber im Arbeitsspeicher mit Größengrenze und nur einmal je Sender |
| 15 | Aufnahme | Wie heute (Stopp beendet Hören und Aufnahme, kein Senderwechsel während der Aufnahme), aber sauber: keine halben Segmente, kein verlorenes Ende |
| 16 | Podcasts | Direkt mit Spulen über Byte-Bereiche, kein Umkodieren; Heruntergeladenes aus der Ablage |

### Vorgaben (Frage 17, alle übernommen)

1. Suchfilter stehen in der Adresse und überleben Neuladen.
2. "Nur Favoriten" wirkt zusammen mit den anderen Filtern.
3. Gemessene Bitrate gilt vor der Verzeichnisangabe; Codec-Filter kommt dazu.
4. "Aktualisieren" lädt nur die Liste; Abgleich mit dem Senderverzeichnis nächtlich als Auftrag.
5. Ausblenden per Auge startet keinen anderen Sender und hat Rückgängig.
6. Der Durchleiter nimmt nur bekannte Sender und Folgen an.
7. Vor/Zurück folgt überall der sichtbaren Liste.
8. Nach dem Wecken geht die Lautstärke auf den alten Wert zurück.
9. Jedes Löschen mit Folgenvorschau und abschließender Bestätigung.
10. Die stillgelegte Tour entfällt.
11. Alle 20 Sprachen bleiben; fehlende Texte übersetzt die lokale KI über die Leitstelle.

### Senderdaten (Frage 19, alle gewählt)

- Pflicht: exakter Sprachabgleich über Sprachcodes, täglicher Abgleich, verschwundene Sender markieren, fehlende
  Felder übernehmen (languagecodes, geo, state, hls, ssl_error, clicktrend, lastcheckoktime).
- Dubletten als Gruppe mit bester Variante; Qualitätsstufe je Sender, Messung im Hintergrund (Favoriten zuerst).
- Genres aus dem Tag-Chaos normalisieren; ähnliche Sender und Vorschläge passend zu den Favoriten.
- Titelverlauf aus dem Strom (was lief wann), Größe begrenzt.
- Fehlende Logos aus der Homepage nachholen; Karte nach Region.
- Werbeverdacht neu gewichten (Cache-Kopf allein reicht nicht).

## Etappen

Jede Etappe endet mit Tests, Ausrollen nach grünem Lauf, Bildschirmfotos am Ticket. Rechner und Telefon wachsen
gemeinsam (Entscheidung 20).

| Etappe | Inhalt |
|---|---|
| 0 Sofortfix (Frage 22) | Sprachfilter exakt vergleichen, Filtersperren mit Folgenvorschau neu berechnen (Hand- und Werbesperren unberührt), Sperrgrund nur als Treffer; Abo ohne Löschen der Folgen; Adresse springt nicht mehr auf /radio |
| 1 Fundament | Ordner frontend/backend, Git-Haken, version.json, Architekturregeln, Ausrollen, Handbuch, LICENSE und README nach Vorlage; Absichern (Ports nur über den Vorbau, kein CORS, Durchleiter per Kennung, Container nicht als root); Umzug nach /mnt/data/radiohub |
| 2 Appkern-Grundlage | Vorlage HiFi und Instrumente in den Appkern; Oberfläche auf die Appkern-Schale (TypeScript, Darstellung mit Schriftstufen und Hell/Dunkel/System, Telefonrahmen, Rückfrage, Meldungen); Backend auf Appkern-Unterbau mit Anmeldung |
| 3 Filterung | Entwurf zuerst (Frage 23); Regeln, Abfrage mit Facetten und Adresse, Ausgeblendete Sender mit Grund, Bewertungen, Werbung; Senderdaten (Felder, Abgleich, Dubletten, Qualität, Genres) |
| 4 Player | Ein Tonausgang, Zustandsmaschine, Quellen-Schnittstelle, Hausempfang mit Übergabe (Appkern-Baustein), Zeitversatz im Speicher, Aufnahme sauber, Podcasts direkt, Ereignisstrom statt drei Abfragen, Titelverlauf |
| 5 Wecker | Modernisiert im HiFi-Baukasten, eigenständig, zuverlässig auch bei gesperrtem Ton |
| 6 Übrige Bereiche | Aufnahmen, Schnitt, Podcasts, Einstellungen auf die Bausteine; Löschen mit Folgenvorschau; Übersetzungen |
| 7 Mehrwert | Ähnliche Sender, Logos, Karte |
| Abschluss | Drehbuch der Browsertests, Abnahme, Design-Dauerkarten im Board |

## Nächste Schritte

1. Etappe 0 nach Freigabe des Nutzers.
2. Entwurf "Radio mit Filterung" (Rechner und Telefon, hell und dunkel) mit Appkern, Vorlage HiFi und Reglern aus
   hifi-regler, unter `mockups/`.
