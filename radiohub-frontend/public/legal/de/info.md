# RadioHub - Technische Informationen

Dieses Handbuch erklärt die wichtigsten Konzepte, Fachbegriffe und technischen Grenzen von RadioHub. Es hilft beim Verständnis, warum bestimmte Funktionen so arbeiten wie sie es tun.

---

## Wiedergabe-Modi

### HLS-Modus (Standard)

HLS steht für "HTTP Live Streaming". RadioHub wandelt den Radio-Stream über das Backend in kleine Segmente um, die der Browser abspielen kann. Das ermöglicht:

- **Zeitversatz (Timeshift):** Zurückspulen im laufenden Programm
- **Pause und Fortsetzen:** Der Puffer läuft im Hintergrund weiter
- **Puffer-Aufnahme:** Bereits Gehörtes nachträglich aufnehmen (HLS-REC)
- **Bitrate-Kontrolle:** Automatische Anpassung an die Verbindung

Der HLS-Puffer wird im Backend gehalten. Die Größe lässt sich unter [Einstellungen > Allgemein](#/setup/allgemein/einstellungen) konfigurieren (Zeitversatz-Puffer).

### Direct-Modus

Im Direct-Modus verbindet sich der Browser direkt mit dem Original-Stream des Senders. Das ist ressourcenschonender, aber ohne Timeshift, ohne Pause und ohne Puffer-Aufnahme. Nützlich bei Servern, die HLS-Konvertierung nicht unterstützen.

---

## Badges in der Senderliste

### ICY (grün / grau)

**ICY** steht für "Icecast Metadata" - ein Protokoll, mit dem Radio-Sender den aktuellen Titel im Stream mitsenden. Wenn ein Sender ICY unterstützt, zeigt RadioHub den laufenden Titel an und kann Aufnahmen automatisch in einzelne Songs schneiden.

- **ICY (grün, "good"):** Der Sender liefert präzise Titelwechsel-Zeitpunkte. Schnitte werden sauber.
- **ICY (grün, "poor"):** Der Sender liefert ICY-Daten, aber die Zeitpunkte sind ungenau (z.B. verspätete Meldungen). Schnitte können Überlappungen oder Lücken haben.
- **ICY (grau):** ICY ist vorhanden, aber die Qualität wurde noch nicht bewertet. Per Klick kann zwischen "good" und "poor" gewechselt werden.

**Warum ist das wichtig?** Manche Sender melden den neuen Titel erst Sekunden nach dem tatsächlichen Wechsel. RadioHub nutzt Byte-Positionen im Audio-Stream für die Schnittberechnung, aber wenn der Sender zu spät meldet, liegt der Schnitt daneben.

### AD-Badges (Werbeerkennung)

RadioHub kann Sender auf Werbung prüfen. Die Prüfung lässt sich unter [Setup > Radio > Sender](#/setup/radio/sender) starten und analysiert Stream-URLs und Server-Antworten:

- **0% AD (grün):** Kein Werbeverdacht nach Prüfung
- **XX% AD (gelb):** Prozentualer Verdacht (z.B. "35% AD") - Schwellwert konfigurierbar
- **AD (rot):** Manuell als Werbung markiert (ausgeblendet)
- **OK (blau):** Manuell freigegeben trotz Verdacht

---

## Aufnahme-System

### Segmentierte Aufnahme

RadioHub nimmt in 30-Minuten-Segmenten auf. Fällt die Verbindung zum Sender aus, geht maximal das aktuelle Segment verloren - nicht die gesamte Aufnahme. Bei einer 8-Stunden-Aufnahme wären das höchstens 30 Minuten statt alles. Aufnahme-Einstellungen (Format, Bitrate, Ordner) unter [Setup > Aufnahmen](#/setup/aufnahmen).

### Stall-Erkennung

Während einer Aufnahme überwacht RadioHub die Dateigröße. Wächst die Datei über 30 Sekunden nicht, wird der Aufnahmeprozess als "hängend" erkannt und neu gestartet. Das verhindert stille Aufnahmen, bei denen FFmpeg zwar läuft aber keine Daten mehr empfängt.

### ICY-Titel-Split

Hat ein Sender ICY-Metadaten, werden die 30-Minuten-Segmente nach der Aufnahme automatisch anhand der erkannten Titelwechsel in einzelne Songs geschnitten. Ohne ICY bleiben die 30-Minuten-Blöcke als Segmente erhalten.

### HTTPS-Streams und Reconnect

Viele Sender nutzen HTTPS. FFmpegs eingebaute Reconnect-Funktion arbeitet nur mit HTTP-Streams zuverlässig. Deshalb übernimmt RadioHub selbst die Überwachung und den Neustart bei Verbindungsabbrüchen, unabhängig vom Protokoll.

---

## Timeshift und Puffer

### Wie funktioniert Timeshift?

Das Backend hält einen rollierenden Puffer aus Audio-Segmenten. Jedes Segment ist wenige Sekunden lang. Der Browser fragt diese Segmente per HLS-Playlist ab. Beim Zurückspulen werden ältere Segmente aus dem Puffer geladen.

### Puffer-Aufnahme (HLS-REC)

Die Puffer-Aufnahme nutzt den bereits vorhandenen HLS-Puffer. Startest du eine Aufnahme, kann RadioHub die letzten X Minuten aus dem Puffer mit aufnehmen. Der Rückblick-Zeitraum ist unter [Einstellungen > Allgemein](#/setup/allgemein/einstellungen) konfigurierbar (HLS-Aufnahme). So lässt sich ein Lied aufnehmen, das bereits läuft.

---

## Cutter (Schnitt-Werkzeug)

### Waveform

Die Wellenform-Anzeige wird aus den Audio-Daten berechnet (Peak-Werte). Sie zeigt die Lautstärke über die Zeit und hilft beim präzisen Setzen von Schnittpunkten.

### Marker

Marker sind Schnittpunkte in der Waveform. Sie können manuell gesetzt oder automatisch aus ICY-Titelwechseln übernommen werden. Beim Schneiden wird die Aufnahme an diesen Punkten in Segmente zerteilt.

### Übergangs-Analyse

Die Analyse untersucht die Audio-Bereiche um jeden Marker herum. Sie bewertet, ob der Übergang sauber ist (Stille zwischen Titeln) oder problematisch (z.B. Crossfade, wo zwei Titel überblenden). Farben: Grün = gut, Gelb = prüfen, Rot = problematisch.

### Normalisierung (EBU R128)

Normalisierung passt die Lautstärke an den EBU R128 Standard an - den europäischen Broadcast-Standard für einheitliche Lautstärke. So klingen alle Segmente gleich laut, unabhängig von der Originallautstärke des Senders.

---

## Podcast-System

### Auto-Download

Abonnierte Podcasts können automatisch neue Episoden herunterladen. Das Intervall ist unter [Setup > Podcast](#/setup/podcast) konfigurierbar. Downloads werden lokal gespeichert und sind auch offline verfügbar.

### Feed-Aktualisierung

Podcast-Feeds werden per RSS/Atom abgefragt. Das [Aktualisierungsintervall](#/setup/podcast) bestimmt, wie oft RadioHub auf neue Episoden prüft.

---

## Speicher und Daten

Unter [Setup > Speicher](#/setup/speicher) lassen sich die Speicherpfade für Aufnahmen, Podcasts und Cache konfigurieren. Die Anzeige zeigt den belegten und freien Speicherplatz pro Zone.

Externe Datenquellen (Radio-Browser API, Podcast-Index) sind unter [Setup > Dienste](#/setup/dienste) einsehbar und bei Bedarf auf eigene Instanzen umstellbar.

---

## Automatische Hintergrundprozesse

RadioHub führt mehrere Prozesse im Hintergrund aus, die ohne Nutzerinteraktion arbeiten:

### Podcast-Feed-Aktualisierung

Beim Start von RadioHub wird ein periodischer Hintergrundprozess gestartet, der alle abonnierten Podcast-Feeds automatisch auf neue Episoden prüft. Das Intervall (Standard: 6 Stunden) ist unter [Setup > Podcast](#/setup/podcast) einstellbar. Bei aktiviertem Auto-Download werden neue Episoden automatisch heruntergeladen.

### HLS-Puffer-Verwaltung

Sobald ein Sender im HLS-Modus abgespielt wird, startet das Backend einen FFmpeg-Prozess, der den Audio-Stream in kurze Segmente (je 1 Sekunde) zerlegt. Diese bilden einen rollierenden 10-Minuten-Puffer. Parallel dazu läuft ein ICY-Metadata-Logger, der Titelwechsel im Stream erkennt. Beide Prozesse enden automatisch, wenn die Wiedergabe gestoppt wird.

### Aufnahme-Überwachung

Während einer aktiven Aufnahme laufen zwei Überwachungsprozesse:

- **Stall-Erkennung:** Alle 30 Sekunden wird geprüft, ob die Aufnahmedatei wächst. Drei aufeinanderfolgende Prüfungen ohne Wachstum (90 Sekunden) führen zum Neustart des Aufnahmeprozesses.
- **Speicherplatz-Überwachung:** Der freie Speicherplatz wird regelmäßig geprüft. Fällt er unter 100 MB, wird die Aufnahme automatisch gestoppt, um Datenverlust zu vermeiden.

### HLS-Puffer-Aufnahme (HLS-REC)

Bei einer HLS-Puffer-Aufnahme kopiert ein Collector-Prozess alle 0,5 Sekunden neue Segmente aus dem HLS-Puffer in das Aufnahmeverzeichnis. Beim Start werden zusätzlich die konfigurierten Rückblick-Minuten aus dem bereits vorhandenen Puffer übernommen. Bei Beendigung wird automatisch zusammengefügt und bei vorhandenen ICY-Daten in Einzeltitel geschnitten.

### Favicon-Cache

Beim Laden der Senderliste werden fehlende Sender-Icons im Hintergrund heruntergeladen und lokal zwischengespeichert. Dieser Prozess arbeitet lautlos und beeinflusst die Bedienung nicht.

### Bitrate-Erkennung

Beim erstmaligen Abspielen eines Senders prüft RadioHub per FFprobe die tatsächliche Bitrate und den Codec. Das Ergebnis wird gespeichert und in der Senderliste angezeigt. Unter [Setup > Radio > Sender](#/setup/radio/sender) kann eine Massenprüfung für alle Sender gestartet werden.

---

## Bekannte Einschränkungen

- **Timeshift nur im HLS-Modus:** Direct-Streams werden 1:1 durchgereicht, ohne Pufferung.
- **ICY-Qualität variiert:** Manche Sender liefern ungenaue oder verspätete Metadaten. Das beeinflusst die Schnittgenauigkeit.
- **SSL-Zertifikate:** Einige Sender nutzen ungewöhnliche SSL-Konfigurationen. RadioHub umgeht dies bei Bedarf, aber es kann zu Warnungen kommen.
- **Lange Aufnahmen:** Bei Verbindungsabbrüchen während einer Aufnahme gehen maximal 30 Minuten verloren (ein Segment). Ältere Segmente bleiben erhalten.
- **Browser-Einschränkungen:** Die Web Audio API im Browser kann VU-Meter-Daten nur liefern, wenn der Audio-Kontext aktiv ist. Bei manchen Browsern erfordert das eine Nutzerinteraktion.

---

## Weiterführende Quellen

Für technisch Interessierte - die Technologien und Standards hinter RadioHub:

### Streaming-Protokolle

- [HTTP Live Streaming (HLS)](https://de.wikipedia.org/wiki/HTTP_Live_Streaming) - Apples adaptives Streaming-Protokoll, das RadioHub für Timeshift nutzt
- [Icecast](https://de.wikipedia.org/wiki/Icecast) - Open-Source Streaming-Server, der das ICY-Metadata-Protokoll verbreitet hat
- [SHOUTcast / ICY-Protokoll](https://en.wikipedia.org/wiki/SHOUTcast) - Ursprung des ICY-Metadata-Standards für Titelinformationen im Stream
- [Internetradio](https://de.wikipedia.org/wiki/Internetradio) - Allgemeiner Überblick über Radio-Streaming im Internet

### Audio-Formate und Codecs

- [MP3 (MPEG-1 Audio Layer 3)](https://de.wikipedia.org/wiki/MP3) - Das verbreitetste Audio-Format für Radio-Streams
- [AAC (Advanced Audio Coding)](https://de.wikipedia.org/wiki/Advanced_Audio_Coding) - Modernerer Codec mit besserer Qualität bei gleicher Bitrate
- [Ogg Vorbis](https://de.wikipedia.org/wiki/Vorbis) - Freier, offener Audio-Codec
- [FLAC (Free Lossless Audio Codec)](https://de.wikipedia.org/wiki/Free_Lossless_Audio_Codec) - Verlustfreie Kompression für höchste Qualität

### Audio-Verarbeitung

- [EBU R128](https://de.wikipedia.org/wiki/EBU-Empfehlung_R_128) - Europäischer Standard für Lautstärke-Normalisierung im Rundfunk
- [FFmpeg](https://de.wikipedia.org/wiki/FFmpeg) - Das zentrale Multimedia-Framework, das RadioHub für Konvertierung, Aufnahme und Schnitt verwendet
- [Web Audio API](https://developer.mozilla.org/de/docs/Web/API/Web_Audio_API) - Browser-Schnittstelle für Audio-Analyse (VU-Meter, Wellenform)

### Datenquellen

- [Radio-Browser API](https://www.radio-browser.info/) - Offene Community-Datenbank mit über 30.000 Radio-Sendern weltweit
- [Podcast Index](https://podcastindex.org/) - Offener Podcast-Katalog als Alternative zu proprietären Verzeichnissen
- [RSS (Really Simple Syndication)](https://de.wikipedia.org/wiki/RSS_(Web-Feed)) - Das Feed-Format, über das Podcasts neue Episoden bereitstellen

### Technische Grundlagen

- [Bitrate](https://de.wikipedia.org/wiki/Bitrate) - Datenrate eines Audio-Streams (z.B. 128 kbps, 320 kbps)
- [Streaming Media](https://de.wikipedia.org/wiki/Streaming_Media) - Grundlagen der Echtzeit-Datenübertragung
- [Digitale Audiodatenreduktion](https://de.wikipedia.org/wiki/Audiodatenkompression) - Wie verlustbehaftete Kompression funktioniert
- [SSL/TLS](https://de.wikipedia.org/wiki/Transport_Layer_Security) - Verschlüsselung, die bei HTTPS-Streams zum Einsatz kommt
