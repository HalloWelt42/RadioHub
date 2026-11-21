# RAD-33 Stufe 0: Werbung aus den Sendedaten

Stand 21.11.2026, Plan zur Abnahme. Grundlage ist der Versuch an 30 Sendern (Kommentar an RAD-33): 7 Sender kündigen
Werbung in den Sendedaten an, mit Kennung, Werbendem und oft der Länge in Millisekunden. Das Ende laut Angabe liegt
20 bis 50 ms neben der digitalen Stille nach dem Spot. Diese Stufe braucht keinen Mac und keinen Propaganda-Filter;
sie ist Datenarbeit auf dem Pi und liefert dem Filter später fertig beschriftete Signaturen (HELF-256).

## 1. Befund im heutigen Code

- Ton und Sendedaten kommen über zwei Verbindungen zum Sender: ffmpeg liest den Ton (`hls_buffer._build_ffmpeg_cmd`,
  `recorder`), `IcyMetadataLogger` verbindet sich ein zweites Mal nur für die Titel (`hls_buffer._start_icy_tracking`,
  `recorder` Zeile 365). Jede Verbindung bekommt ihren eigenen Spot beim Verbinden, und Werbung im Programm kann je
  Hörer verschieden sein. Die Angaben der zweiten Verbindung gehören also nicht zum Ton, den man hört, und ihre
  Byte-Stellen passen nicht zum Puffer.
- `IcyMetadataLogger` spricht rohes TCP mit Port 80: Sender über https bekommen heute keine Sendedaten.
- `IcyMetadataLogger` liest nur `StreamTitle`; die Werbeangaben (`adw_ad`, `durationMilliseconds`, `AdCreativeId`,
  `Advertiser`, `AdTitle`) stehen zwar im Rohtext (`raw`), werden aber nicht ausgewertet.
- `ad_detector` kennt schon "werbend" je Sender (Adresse, Köpfe des Stroms, Entscheidung des Nutzers), aber nicht
  aus dem Strom selbst.
- Werbestellen (RAD-32) gibt es nur für Podcast-Folgen (`werbestellen.folge_id`), der Werbesprung nur für Folgen.

## 2. Zielbild in Schichten

1. **Stromleser (eine Verbindung):** liest den Sender einmal (httpx, TLS geprüft, Weiterleitungen wie der
   Durchleiter), trennt Ton und Sendedaten und gibt den reinen Ton an ffmpeg (stdin) weiter. Jede Angabe bekommt
   ihre Stelle im Ton (Ton-Bytes bis dahin, umgerechnet in Sekunden über die Bitrate des Stroms). Ersetzt die zweite
   Verbindung im Zeitversatz und in der Aufnahme. Nutzen auch ohne Werbung: Titel stimmen zum Ton, https-Sender
   bekommen Titel.
2. **Werbeangaben (reine Funktionen, ohne Ein- und Ausgabe):** aus einer Angabe des Stroms wird eine `Werbeangabe`
   (Pydantic: art `verbinden` oder `programm`, kennung, werbender, titel, dauer_ms oder leer, format). Die Formate
   stehen als Regeln in einer Datei (`werbeangaben.toml`: je Format Erkennung, Felder, wie das Ende bestimmt wird),
   nicht im Code; heute bekannt: `adw_ad`, `AdCreativeId`, Werbung als Titel (laut.fm). Ein neues Format ist ein
   neuer Eintrag.
3. **Werbestellen der Sitzung:** aus Angaben werden Stellen mit von und bis in Sekunden des Puffers. Ende: die
   angekündigte Länge, sonst der nächste Wechsel der Angabe. Genaue Grenze: offen, siehe Rückfrage 1.
4. **Ablage:** Stellen einer laufenden Sitzung im Speicher (der Puffer rollt ohnehin), Stellen einer Aufnahme in der
   Datenbank. Bekannte Spots in einer eigenen Tabelle (`werbespots`: kennung, werbender, titel, dauer_ms, sender,
   zuerst, zuletzt, anzahl), daraus "werbend" je Sender im `ad_detector` (neuer Grund "Sendedaten") und später die
   Signaturen für den Filter.
5. **Schnittstelle:** Stellen der laufenden Sitzung im Status des Puffers (wie die Titel heute) und als Ereignis im
   Strom der Oberfläche; Stellen einer Aufnahme bei der Aufnahme; Spots und "werbend" je Sender lesend.
6. **Wiedergabe (Oberfläche):** der Werbesprung aus RAD-32 wird allgemein (Folge, Zeitversatz, Aufnahme) über eine
   Schnittstelle "Werbestellen der Quelle". Im Zeitversatz springt er an das Ende, wenn der Puffer so weit reicht,
   sonst schaltet er stumm und zeigt die Restzeit. Der Spot beim Verbinden wird gar nicht erst gespielt: die
   Wiedergabe beginnt nach ihm.
7. **Aufnahmen und Schnitt:** die Stellen kommen mit der Aufnahme mit und erscheinen im Schnitt als Stücke der Art
   Werbung (wie RAD-32 für Folgen), entfernbar mit einem Griff.

Datenmodell: `werbestellen` bekommt statt nur `folge_id` einen Bezug auf die Quelle (Folge oder Aufnahme), als neue
Stufe des Schemas; die Podcast-Stellen bleiben, wie sie sind.

## 3. Oberfläche (erst Entwurf, dann bauen)

- Hinweis in der Kanzel: "Werbung übersprungen" oder "Werbung, stumm noch 12 s", mit "Zurück und anhören" wie bei
  Folgen.
- Marken der Werbestellen in der Spulzeile des Zeitversatzes.
- "werbend" am Sender in der Liste und im Detail, mit der Zahl der bekannten Spots.
- Schalter: Werbung überspringen (an, aus) für alle und je Sender, in den Einstellungen und am Sender.
- Werbeblocker-Taste (nur Symbol) aus HELF-256 gehört dazu, sobald der Filter prüft; in Stufe 0 genügt der Schalter.

## 4. Prüfen

- Regeln: Tests mit den echten Angaben aus dem Versuch (drei Formate, Wechsel, fehlende Länge).
- Stromleser: Test mit einem nachgestellten Sender (ICY mit Werbeangaben und Ton), Stellen gegen den Ton.
- Probebetrieb: ein Probesender mit Spot beim Verbinden und einem im Programm.
- Live: an FFH, Antenne Bayern, Oldie Antenne, Mangoradio prüfen, dass der Spot nicht zu hören ist; Gegenprobe an
  einem Sender ohne Werbung.

## 5. Reihenfolge

1. Stromleser mit einer Verbindung (eigene Arbeit, ohne sichtbare Änderung; Titel auch für https).
2. Regeln der Werbeangaben und Werbestellen der Sitzung (Backend, Tests).
3. Entwurf der Oberfläche zur Abnahme.
4. Werbesprung allgemein, Zeitversatz, Hinweis, Schalter.
5. Aufnahmen und Schnitt.
6. Spots sammeln, "werbend" je Sender.
7. Texte Deutsch und Englisch, Handbuch, Probe und live.

## 6. Entscheidungen (Nutzer 21.11.2026)

1. Genaue Grenze über die Stille: `silencedetect` läuft im ohnehin laufenden ffmpeg des Zeitversatzes und der
   Aufnahme mit; die Werbestelle endet an der Stille, die der Angabe am nächsten liegt (Fenster aus der Regeldatei).
   Ausnahme von "der Pi rechnet nicht", weil kein eigener Rechenschritt dazukommt.
2. Live am Rand des Puffers: stumm mit Restzeit, der Ton läuft weiter, man bleibt live.
3. Überspringen angekündigter Werbung gilt von Anfang an für alle Sender, abschaltbar für alle und je Sender.
4. Favoriten verbunden halten: später entscheiden, nach Stufe 0 messen, wie störend die Wartezeit beim Verbinden ist.
