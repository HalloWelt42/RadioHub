---
zweck: "Internetradio, Podcasts, Aufnahmen und Wecker im HiFi-Look: Senderverzeichnis mit Schnellfiltern, Ausschlussregeln und Favoriten, Zeitversatz, Aufnahmen mit Schnitt, Podcast-Abos, Weckeransicht mit Zeitansage am Telefon; Aufnahmen und Folgen liegen in der Kellerwolke."
geraet: [pi]
abhaengigkeiten: [kellerwolke]
daten:
  - "Pi: `{{wurzel}}/data/radiohub.db` (Sender mit Aufbereitung, Favoriten, Ausschlussregeln, Einzelsperren und Freigaben, Index der Aufnahmen, Abos und Folgen, Wecker, Stand der Oberfläche), `{{wurzel}}/data/appkern/radiohub.sqlite` (Einstellungen, Protokoll, Aufträge des Appkerns), `{{wurzel}}/data/cache` (Senderlogos, Zwischenstände, Arbeitsordner laufender Aufnahmen und Downloads), `{{wurzel}}/data/storage.json` (Speicherzonen)"
  - "Kellerwolke, Ordner `Apps/RadioHub`: Aufnahmen mit Titelliste und Wellenform, heruntergeladene Podcast-Folgen, Bausteine der Zeitansage"
sicherung:
  - "nach der Regel des Appkerns eine Kopie von `radiohub.db` nach `{{wurzel}}/sicherungen` und eine der Datenbank des Gerüsts nach `{{wurzel}}/sicherungen/appkern`: regelmäßig von der App (Vorgabe alle 7 Tage) und vor jedem Ausrollen (nur wenn die jüngste älter als 24 Stunden ist und sich etwas geändert hat, höchstens drei je Datenbank)"
  - "Aufnahmen, Folgen und Bausteine hängen an der Sicherung der Kellerwolke"
schluessel_orte:
  - "Pi: `{{wurzel}}/.env`, Modus 0600: App-Schlüssel und Adresse der Kellerwolke als feste Einstellungen (RADIOHUB_FEST_KELLERWOLKE_SCHLUESSEL und _ADRESSE, vom Ausrollen), dazu Adressen der Kellerwolke und der Vertonung, Zertifikatsstelle, Kennung der Zeit-Stimme"
  - "Pi: `{{wurzel}}/data/kellerwolke.schluessel`, Modus 0600: der App-Schlüssel von vor RAD-6; gilt nur noch, solange die .env keinen festen hat"
  - "Pi: `{{wurzel}}/zertifikate/`, Blattzertifikat mit Schlüssel aus der Hausstelle (vom Ausrollen)"
einrichten: einrichten.sh
stand: b3e5c62
---

# RadioHub

## Zweck

RadioHub ist das Radio des Hauses, Fassung {{fassung}}: tausende Sender aus dem Senderverzeichnis (jede Nacht
abgeglichen, Sprachen, Genres, Qualität und Varianten aufbereitet) mit Suche, Schnellfiltern,
Ausschlussregeln, die auch für neue Sender gelten (mit Grund je ausgeblendetem Sender) und Favoriten, Zeitversatz (zurückspulen im laufenden Sender), Aufnahmen von Hand oder nach Zeitplan mit
Schnitt in der Wellenform, Podcast-Abos zum Hören und Herunterladen. Am Telefon gibt es eine eigene Ansicht (der
große Spieler liegt auf einem Farbschein aus dem Logo, die Bedienung darauf aus Glas) und quer
gelegt die Weckeransicht für den Nachttisch mit Wecker, Sonnenband und Zeitansage. Aufnahmen und heruntergeladene
Folgen liegen in der [[Kellerwolke]]; RadioHub hält lokal nur die Datenbank und Zwischenstände.

Erreichbar über HTTPS am eigenen Vorschaltdienst auf Port {{port:ziel/vorne}} des Pi und im Heimnetz unter
`radio.<Rufname des Pi>.lan` über den [[Vorbau]]. Die frühere Adresse ohne TLS ({{adresse}}) leitet der Vorbau auf
HTTPS um. Die App (Backend auf dem Gerüst des [[Appkern]], liefert die Oberfläche selbst aus) ist nur im eigenen Netz
der Container erreichbar. Angemeldet wird mit dem Konto der [[Kellerwolke]], dem der App-Schlüssel gehört; Telefone
koppelt man einmal mit einem Code aus der Kellerwolke. Architektur und harte Regeln stehen in `docs/ARCHITEKTUR.md`,
der Plan der Überarbeitung liegt nur lokal in `docs/umbau/PLAN.md` (Pläne und Entwürfe gehören nicht ins Repo).

Radio bedienen: am Rechner stehen links die Schnellfilter (oben fest das Gerät mit Nur Favoriten, Erreichbare und
Beliebtheit, darunter Länder, Genres, Qualität, Codec und Bitrate mit der Mindestbitrate, eigene Bewertung und Kategorien
mit Zahlen; lange Gruppen zeigen die häufigsten sechs und "Alle zeigen"); unter 1100 Pixeln
fährt die Leiste über den Knopf Filter ein. Alle Schnellfilter, Suche und Sortierung stehen in der Adresse
(`/radio?land=DE&genre=Rock&sort=name`, ein aufgeklappter Sender als `/radio/<Kennung>?...`), Neuladen und Lesezeichen
behalten sie; frühere Adressen `/radio/search/<Suche>` gelten weiter. Der Knopf mit dem durchgestrichenen Auge blendet einen einzelnen Sender aus
und bietet Rückgängig, nichts anderes startet. Am Telefon dieselben Filter als Blatt von unten. Dauerhafte Ausschlüsse
nur unter Einstellungen > Radio: Ausschlussregeln (erst Vorschau, dann anlegen, danach Rückgängig; Entfernen nennt
vorher die Folgen), Ausgeblendete Sender (Grund je Sender, Freigeben), Länder der Seitenleiste (blendet nichts aus),
Werbeerkennung, Senderverzeichnis (letzter Abgleich, Uhrzeit, Jetzt abgleichen) und Kategorien.
Die Fokus-Taste der Spielerleiste (Fadenkreuz, blaues Licht heißt ein, gemerkt im Gerät): ein springt zum laufenden
Sender, klappt ihn auf und folgt ihm bei jedem Wechsel (Weiter, Zurück, neuer Sender), dazwischen rollt man frei; aus
rollt nur frei. Wird der aufgeklappte Sender ausgeblendet, rückt der nächste der Reihe nach. Ein ausgeblendeter Favorit bleibt
gedämpft mit dem Hinweis "ausgeblendet, Favorit" stehen; das Auge blendet ihn wieder ein, ohne Stern verschwindet er.
Basic merkt sich die Sprache (Deutsch oder Englisch) je Gerät unter Einstellungen > Allgemein; ohne Wahl gilt die des
Browsers.

Werbung im Radio (RAD-33): viele Sender kündigen Werbung in ihren Sendedaten an, oft mit der Länge auf die Millisekunde;
das Ende sitzt an der Stille danach. Ist "Angekündigte Werbung überspringen" an (Einstellungen > Radio >
Werbeerkennung, für alle Sender, je Sender abschaltbar im Steckbrief), spielt RadioHub einen Sender von Anfang an aus
dem Zeitversatz (eine Verbindung zum Sender, sonst gehörte die erkannte Werbung zu einem anderen Ton): einen Spot beim
Verbinden spielt es nicht, die Wiedergabe beginnt danach (Hinweis mit Restzeit und "Trotzdem hören"); im Zeitversatz
springt es über Werbung ("Zurück und anhören"), live schaltet es stumm, bis sie vorbei ist ("Ton an"). Solange
Werbung nicht zu hören ist, steht die Kanzel in Bernstein auf WERBUNG; die Stellen stehen bernsteinfarben auf dem
Balken des Zeitversatzes. Ein Sender mit einem einzigen gefundenen Spot trägt in der Liste die Marke "Werbung". Woran
Werbung in den Sendedaten zu erkennen ist, steht als Regeln in `backend/app/sendewerbung/angaben.toml`. Manche Sender
spielen beim Verbinden je Hörer einen Vorlauf ein und nennen dabei als Titel nur ihren Namen (RAD-47); er zählt als
Werbung beim Verbinden, wenn an seinem Ende eine Stille liegt, sonst war es nur ein später gemeldeter Titel.

Ein aufgeklappter Sender (RAD-35) zeigt drei schmale Spalten: den Steckbrief (Läuft, Stream mit Kopieren und eigener
Adresse, Codec, Homepage, Sprache, Ort, Prüfung, Titel pünktlich oder ungenau; Erklärungen als Tooltip am Info-Zeichen),
die Werbung (Werbende nach Häufigkeit, aufklappbar bis zu den einzelnen Spots, Schalter Überspringen und das Ergebnis
der Prüfung) und die eigene Einschätzung. Dort steht nur, was gewählt ist; ein Klick auf das x wählt ab, das Plus
öffnet die Tafel mit Bewertung, Markierungen und Kategorien. Werbelisten ab sechs Einträgen rollen in sich und zeigen
höchstens die 40 häufigsten.

Podcasts am Rechner (wie die Radioseite): links oben die Wahl Alle, Ungehört oder Gespeichert, darunter die Abos mit
der Zahl ungehörter Folgen. Ein Klick wählt ein Abo, noch einmal alle; mit Befehls- oder Strg-Taste mehrere. Die Nadel
heftet ein Abo oben an; die Reihenfolge ändert Ziehen am Griff (ein gestrichelter Platzhalter zeigt, wo es landet).
Neue Podcasts über "Abonnieren" oben in der Werkzeugleiste (Suche im Verzeichnis oder die Adresse eines Feeds). Oben
Zählwerk, Suche in Titeln und Beschreibungen, Sortierung (jedes Abo merkt sich seine) und Aktualisieren. Ein
gewähltes Abo zeigt seinen Kopf mit "Neue speichern", Aktualisieren, "Alle speichern" mit Fortschritt, Oben anheften
und Abbestellen (mit Rückgängig). Je Folge: hören; Speichern legt sie in der Kellerwolke ab (Podcasts/<Abo>/),
Herunterladen lädt sie als Datei auf das Gerät, das gerade bedient; eine gespeicherte löschen fragt vorher und nennt
die Datei, die in den Papierkorb geht; als gehört setzen; Details. Spielt eine Folge, hat die Abspielleiste statt der
Bitrate eine Drehwahl für das Tempo; die Fokus-Taste folgt auch der laufenden Folge.

Werbung am Klang (HELF-256): ist der Propaganda-Filter eingerichtet, geht der laufende Ton eines Senders (MP3, AAC) in
Stücken an ihn; erkennt er einen bekannten Spot, der an diesem Sender gefiltert wird, entsteht eine Werbestelle wie aus
den Sendedaten. Angekündigte Spots bekommt der Filter als Ausschnitt, damit er sie auch ohne Ankündigung wiedererkennt.
Ist der Filter fort, ruht nur das Erkennen; Gefundenes wirkt weiter. Für den Lernlauf des Filters stellt RadioHub alle
sechs Stunden die Senderliste zusammen: was man hört (Tabelle hoerverlauf, 60 Tage), die Favoriten, ähnliche Sender nach
Genre, Sprache und Land und die bekanntesten der eigenen Länder; ausgeblendete Sender kommen nie hinein.

Werbung in Podcasts (RAD-32): die Details einer Folge zeigen ihre Werbestellen mit Herkunft. Sie kommen aus Kapiteln
des Feeds, deren Titel nach Werbung klingt, von Hand (beim Hören am Beginn und am Ende markieren) oder aus dem Vergleich
der Fassungen: viele Anbieter setzen Werbung erst beim Abruf ein, je Abruf andere. Für eine gespeicherte Folge
reicht RadioHub die Datei an den Propaganda-Filter (eigener Dienst am Mac, Einstellungen > Dienste > Propaganda-Filter),
der dieselbe Folge mehrmals neu holt (Vorgabe drei Fassungen), jede am Klang ausrichtet und auf 10 ms genau nennt, was
in der gespeicherten vorkommt, in einer anderen aber fehlt; aneinanderstoßende Spots werden ein Werbeplatz. Mehrere
Fassungen braucht es, weil an einem Platz oft mehrere Spots laufen und einer davon in einer Fassung zufällig gleich
sein kann. Die Zeiten gelten genau für diese Datei. "Werbung suchen" fragt alle Quellen, die für die Folge gehen, mit
Fortschritt; "Neue Folgen prüfen" im Kopf des Abos tut das von selbst nach dem Aktualisieren (nach dem Speichern neuer
Folgen, damit der Vergleich sie schon vorfindet). Beim Hören springt die Wiedergabe über die Stellen ("Überspringen" je
Abo), "Keine Werbung" verwirft eine Stelle (mit Rückgängig, eine neue Suche bringt sie nicht wieder), "Ohne Werbung
speichern" legt eine neue Datei ohne die Stellen neben das Original.

Aufnahmen am Rechner (RAD-17, wie die Podcasts): links oben die Quelle, eigene Aufnahmen oder die ganze Kellerwolke.
Bei den Aufnahmen die Ordner mit Zahl; das rote Licht und der Kreis zeigen, wohin neue Aufnahmen gehen (ein Klick auf
den Kreis macht einen Ordner zum Ziel), umbenennen an Ort und Stelle, löschen nur leer. Oben Zählwerk, Suche nach
Sender und Titel, Sortierung über den Tabellenkopf; alles steht in der Adresse (`/aufnahmen?ordner=3&sort=dauer`, eine
Aufnahme `/aufnahmen/<Kennung>`, ihr Schnitt `/aufnahmen/<Kennung>/schnitt`). Läuft eine Aufnahme, steht oben ihr Kopf
mit erkannten Titeln, Uhr und "Aufnahme beenden". Eine gewählte Aufnahme zeigt ihren Kopf (Hören, Schneiden, Nach
Titeln teilen, Titel als ZIP, als eine Datei, Ordner, Löschen mit Rückfrage) und ihre Titel (ab hier hören, laden,
schneiden, für künftige Aufnahmen sperren, löschen). Die Kellerwolke zeigt Ordner für Ordner nur Audiodateien zum
Hören, Schneiden und Laden; dafür braucht RadioHub dort die Freigabe "Alles lesen" (Kellerwolke > Einstellungen >
Zugänge), sonst sagt die Seite das.
Der Schnitt nimmt die ganze Breite: Wellenform mit Übersicht, Marker per Knopf, Doppelklick, Taste M oder aus den
Titeln, ziehen zum Verschieben, Entf entfernt den nächsten; zwischen den Markern die Stücke mit Namen und Behalten oder
Weg. Schneiden fragt vorher und nennt, wohin es geht: bei einer Aufnahme ersetzt es ihre Stücke (die verworfenen fehlen
danach, die übrigen rücken zusammen), bei einer Datei der Kellerwolke entsteht eine neue Datei daneben und das Original
bleibt (darf RadioHub dort nicht schreiben, im eigenen Ordner `Schnitt/<Ordner>`). Normalisieren auf -16 LUFS und
Umwandeln (MP3, OGG, AAC, Bitrate, Mono) gehen genauso. Jeder Schritt lässt sich zurücknehmen: eine Aufnahme hält die
vorige Fassung im Unterordner `Schritte/<Nr>` ihres Ordners, eine Datei legt das Ergebnis beim Rückgängig in den
Papierkorb; die letzten zehn Schritte bleiben. Am Telefon gibt es den Reiter Aufnahmen nur zum Hören (Suche, Ordner,
Titel, Alles hören).
Nach dem Stopp schneidet RadioHub jede Aufnahme fein (RAD-45, Status "feinschnitt", solange bleibt die Wiedergabe
gesperrt): Grenzen an den Pausen zwischen den Titeln, bei Sendern mit Überblendung am tiefsten Pegeltal, Werbung als
eigenes Stück, Einstreuungen wie der Sendungsname mitten im Lied fallen weg, der Titel eines Stücks ist der mit dem
größten Anteil. Die Messwerte (Wechsel der Sendedaten, Stillen, Pegel, Werbestellen) liegen als `Analyse.json` im Ordner
der Aufnahme; `POST /api/recording/sessions/<Kennung>/feinschnitt` rechnet daraus neu und ersetzt den vorigen
Feinschnitt (als Schritt des Schnitts, also auch von Hand zurückzunehmen).
Geräte (RAD-18, nur PRO): Jedes Fenster von RadioHub meldet sich beim Vermittler des Appkerns
(`WS /api/v1/geraete/ws`, angemeldet mit der ersten Nachricht) und sieht die anderen Fenster desselben Kontos. Der
Knopf Geräte oben rechts nennt ihre Zahl und blinkt ruhig, solange auf einem davon etwas spielt; am Telefon steht er im
großen Spieler und öffnet ein Blatt von unten. Holen übernimmt die Wiedergabe von dort (Folgen und Aufnahmen an
derselben Stelle, ein Sender live), Dorthin gibt die eigene ab, hier hält sie an; eine laufende Aufnahme läuft weiter.
Den eigenen Namen in der Liste antippen benennt das Gerät um (gilt für alle Fenster dieses Browsers). Was gemeldet und
übergeben wird, steht in `backend/app/geraete.py` und `frontend/src/spieler/geraete.svelte.ts`.
Ton des Zeitversatzes (RAD-92): Der Drehregler Bitrate (am Telefon die Auswahl im Kasten Zeitversatz) hat als erste
Stufe Original: der Ton des Senders geht unverändert in den Puffer, ohne Neukodieren und ohne Angleichen der Lautheit
(MP3 und AAC; andere Formate wandelt der Puffer um und zeigt UMGEWANDELT). Voll wandelt in der Bitrate des Senders um,
mit Angleichen der Lautheit, danach folgen feste Stufen. Spielt ein Gerät das Original nicht ab, stellt es selbst auf
Voll. Die Wahl gilt je Browser (radiohub_bitrate_override). Am Pi liegen die Stücke im Arbeitsspeicher (tmpfs /puffer,
Größe über RADIOHUB_PUFFER_RAM, Vorgabe 1200m; Ort als Einstellung hls_puffer_ordner). Die Länge des Puffers
stellt man in den Einstellungen unter Wiedergabe ein, von 15 Minuten bis 8 Stunden in Schritten von 15 Minuten.
Ruhig hören (RAD-84): Ein direkter Strom (Original in PRO, jeder Sender in Basic) läuft über einen eigenen Vorrat im
Browser (`lib/stromhalter.js`): gespielt wird nach etwa 6 Sekunden Vorlauf, läuft er leer, füllt er still auf, statt zu
stottern, und reißt die Verbindung ab, verbindet er neu und hängt an, während der Vorrat weiterspielt (nach sechs
Versuchen gibt er auf). Sender ohne CORS spielt das Tonelement wie bisher direkt, mit demselben Neuverbinden. Live im
Zeitversatz heißt 8 Sekunden hinter der Kante des Puffers (`LIVE_ABSTAND_S` in `lib/playerEngine.js`).
Puffer und Aufnahme hängen am selben Empfang des Senders (RAD-46): eine Verbindung, Titel, Werbestellen, Stille und
Pegel, dazu ein Mitschnitt des Stroms über die Länge des Puffers im Arbeitsordner (`{{wurzel}}/data/cache`, bei
192 kbit/s und 2 h etwa 190 MB; beim Start geräumt). Läuft der Zeitversatz, beginnt eine Aufnahme am Anfang des
laufenden Titels (läuft Werbung, nach ihr) und bekommt den Ton bis jetzt aus dem Mitschnitt; Radio aus oder ein
anderer Sender beenden sie nicht. `GET /api/hls/abschnitte` nennt Titel, Werbung und Einschübe des Puffers (Grenzen
nach der Regel des Feinschnitts), `POST /api/hls/aufnahme` mit `von_s` und `bis_s` (Sekunden des Puffers) nimmt ab
einer Stelle auf oder sichert einen Bereich als fertige Aufnahme. Stille und Pegel kosten auf dem Pi unter 1 % eines
Kerns (gemessen 22.11.2026).
Bedienung (lokaler Entwurf `puffer.html`): der Balken des Zeitversatzes zeigt Titelgrenzen als Striche,
Werbung violett und eine laufende Aufnahme rot; beim Überfahren steht der Titel darüber, Loslassen nahe einer Grenze
rastet ein. Darunter steht "Länge von höchstens · Titel". Den Titel zeigt die Matrixanzeige; Vor und Zurück der Steuerung
(und die Pfeiltasten) springen hinter live durch die Titel (Werbung wird übersprungen, nach dem letzten an live), lang
gedrückt wechseln sie den Sender (RAD-60). Neben der Segmentanzeige stehen links Puffer und rechts Live; die Anzeige der
Kanzel ist das einzige Element, das mitwächst, und mindestens so breit, dass sie bündig mit der linken Spalte der Seite
endet; rechts endet die Kanzel mit demselben Rand wie links. Puffer öffnet die Großansicht `/radio/puffer`: Zeitleiste mit Übersicht und Ausschnitt (Alles, 30 oder 10 Minuten; Rad oder
Ziehen verschiebt, Doppelklick springt hin), darunter die Titel, neuester oben, je Titel hier hören, Aufnahme ab hier und
in den Bereich nehmen; ein Bereich wird als fertige Aufnahme gesichert. Am Telefon im Spieler derselbe Balken mit den
Knöpfen und die Puffer-Liste (antippen klappt Hören, Aufnehmen und Bereich auf). Eine Aufnahme beendet die Taste
Aufnahme (sie leuchtet, solange sie läuft) oder Stopp, das zugleich das Hören beendet. Während der Aufnahme bleibt der
Sender: Zurück und Vor springen nur im Zeitversatz durch die Titel des Puffers (an der Live-Kante kein Vor), sonst sind
sie gesperrt (RAD-83).

Podcasts am Telefon (RAD-14): oben Suche, Zählwerk und das Plus zum Abonnieren, darunter die Wahl Neu (Folgen aller
Abos, neueste zuerst), Ungehört, Gespeichert und Abos (Übersicht nach Ordnern mit ungehört und gespeichert). Ein Abo
zeigt seinen Kopf mit Aktualisieren, Neue speichern und Abbestellen (fragt vorher) und seine Folgen mit Sortierung. Der
Knopf rechts an einer Folge hört sofort, weiter ab der gemerkten Stelle; ein Tipp auf die Folge öffnet ihr Blatt mit
Weiter ab, Von vorn, Speichern (eine gespeicherte löschen fragt mit Datei und Größe), Herunterladen und Gehört.

Einstellungen (RAD-11): links die Bereiche Allgemein, Darstellung, Radio, Wiedergabe, Aufnahmen, Podcasts, Wecker und
Zeitansage, Ablage, Dienste (Basic: Allgemein, Darstellung, Radio, Wecker und Zeitansage), oben Pfad und Reiter. Jede
Zeile nennt ihre Geltung: "Alle Geräte" (liegt auf dem Server, wartet mit einem Punkt in der Leiste unten, bis
Speichern oder Verwerfen), "Dieses Gerät" (gilt sofort) oder "Fest gesetzt" (vom Ausrollen, gesperrt). Speichern prüft
zusammen, etwa dass die kleinste Bitrate nicht über der größten liegt, und nennt sonst den Grund. Löschen fragt immer
vorher mit den Folgen (Kategorie mit Zahl der Zuordnungen, Aufnahmeordner nur leer, eingebaute Titelmuster bleiben).
Die Ablage zeigt Datenordner und Belegung nur an; Pfade setzt das Ausrollen. Die Tastatur steht unter Allgemein,
abgeleitet aus der wirksamen Belegung.

Wecker am Telefon (Wecker-Taste oben): je Wecker Uhrzeit, Tage, Sender oder neueste Folge eines Abos, Weckton,
Lautstärke, wie langsam es lauter wird und wie lange Schlummern dauert. Den Weckton (neun zur Wahl, Vorgabe Doppelpiep, alle im Gerät erzeugt und
ohne Netz) hört man in der Bearbeitung über den Knopf daneben an. Er klingelt, wenn beim Wecken auf Ton geschaltet wird
oder das Radio nicht zu hören ist; das Radio versucht es dabei weiter. Beim Klingeln lässt sich jederzeit zwischen Radio
und Ton wechseln. Geweckt wird nur bei offener Weckeransicht (Telefon quer, Seite offen).

## Was sie braucht

- Den Pi ({{rechner}}) nach [[Grundlage Pi]] mit Docker und dem gemeinsamen Netz `haus`; RadioHub läuft dort mit
  `compose.pi.yml` in zwei Containern: die App (FastAPI auf dem Gerüst des Appkerns mit der gebauten Oberfläche,
  FFmpeg, Nutzer 1000) und der Vorschaltdienst (Caddy); veröffentlicht ist nur der Vorschaltdienst.
- Die [[Kellerwolke]] für Anmeldung und Ablage (App RadioHub mit eigenem App-Schlüssel im Konto admin, besorgt vom
  Ausrollen); ohne sie wartet RadioHub auf die erste Einrichtung.
- Ohne die es auch geht: OSMLocal für die Ortssuche der Sonnenzeiten (über das Netz `haus`, Name `osmlocal`) und die
  [[Vertonung]] für die Bausteine der Zeitansage.
- Ein Zertifikat aus der Hausstelle für den Vorschaltdienst (stellt das Ausrollen aus, mit der Adresse des Pi, damit
  der Vorbau es prüfen kann).
- Am Mac für Entwicklung und Ausrollen: Python 3.12, Node.js, Docker, mkcert mit der Hausstelle, das
  Werkzeug `handbuch` und der [[Appkern]] mit seiner Umgebung (Prüfungen vor jedem Commit, Bausteine des Ausrollens).
  Die Oberfläche des Appkerns (Schale, Vorlagen, Instrumente) kommt wie das Backend über GitHub, beide am selben
  Commit.

## Neu einrichten

Wahl: aus der Sicherung (Datenbank mit Favoriten, Regeln, Abos und Weckern zurück, Schlüssel der Kellerwolke wie
vorher) oder frisch (leere Datenbank, der erste Start lädt das Senderverzeichnis als Auftrag, neuer App-Schlüssel).

### 1. Entwicklung am Mac

Im Ordner des Repos `./einrichten.sh` ausführen: Python-Umgebung des Backends mit den Testpaketen, Pakete der
Oberfläche und die Git-Haken (`tools/git-hooks`: Fassung zählen, Zeichen und Stil, harte Regeln aus
`architektur/regeln.toml`, Kennung RAD-n in jeder Commit-Nachricht).

Probe: `git config core.hooksPath` zeigt `tools/git-hooks`; `backend/.venv/bin/python -m pytest` (im Ordner
`backend`) und `npx vitest run` (im Ordner `frontend`) melden alle Tests grün.

### 2. Einmalig: Umzug in den Ordner des Betriebs

Lag RadioHub noch im alten Ordner (`umzug_von` in `deploy/ausrollen.toml`), bricht das Ausrollen ab, bis umgezogen ist.
Erst `tools/umzug-mnt-data.sh --probe` (zeigt Größe, Platz, Besitzer und Stand, ändert nichts), dann
`tools/umzug-mnt-data.sh`: zwei Abschriften mit rsync (die zweite nach dem Anhalten, die Datenbank ist danach
stimmig), Besitz 1000:1000, denn die Container laufen nicht mehr als root, `.env` mit Modus 0600, die frühere
`docker-compose.override.yml` heißt danach `.vor-umzug`. Der alte Ordner bleibt als Rückweg stehen (Kopfkommentar des
Skripts). Danach ist RadioHub aus, bis Schritt 3 läuft.

Probe: im Ordner `{{wurzel}}` liegt `.umzug-fertig`; ein zweiter Lauf meldet "schon umgezogen".

### 3. Betrieb auf dem Pi

`tools/ausrollen.sh` ausführen. Es prüft, dass Oberfläche und Backend den Appkern vom selben veröffentlichten Commit
nehmen (nicht aus `frontend/vendor`), dazu Stand, harte Regeln und Tests (Backend, Oberfläche, Typen, Bau) am Mac,
stellt das Zertifikat aus, holt den Stand nach `{{wurzel}}`, baut, wartet eine laufende Aufnahme ab, sichert beide
Datenbanken, besorgt die Zugänge (Abschnitt `[zugaenge]`: Adresse und App-Schlüssel der Kellerwolke als feste
Einstellungen in die `.env`, solange sie dort fehlen), startet neu und prüft über HTTPS Fassung, Datenbank, HTTP/2 und
Symbole. Vorher läuft die Freigabe des Handbuchs (Seite, Einrichtungsskript, Probelauf). Beim ersten Ausrollen nach
RAD-6 gehen die Container von davor (Backend, Oberfläche mit nginx) als verwaiste mit; die Datenbank wird ohne Umbau als
Stufe 1 übernommen. Stufe 2 (RAD-7) legt nur dazu (Felder des Verzeichnisses, Aufbereitung, Regeln) und bereitet den
Senderbestand beim ersten Start einmal auf (am Pi rund eine Minute); bis zur Überführung (Schritt 6) gilt die frühere
Sperrliste unverändert als Regel "Sperren von früher".

Probe: die Ausgabe endet mit "Ausgerollt" und nennt den Besitzer; `/health` meldet Fassung {{fassung}} und die
Datenbank gesund; das Protokoll der App nennt "Stand Stufe 2" und "Senderbestand erstmals aufbereitet".

### 4. Einstellungen des Hauses

Alle Einstellungen stehen an einer Stelle, den Einstellungen des Appkerns: gespeichert in der App, sonst aus der `.env`
im Ordner `{{wurzel}}` (Modus 0600, Namen `RADIOHUB_<FELD>`), sonst die Vorgabe; fest (nicht änderbar) sind die Werte
`RADIOHUB_FEST_*`, die das Ausrollen setzt. Für die Vertonung `RADIOHUB_VERTONUNG_ADRESSE`, die Zeit-Stimme wählt man in den Einstellungen (Vorgabe Katalogstimme
sohee wie in Basic, austauschbar gegen jede für RadioHub freigegebene Stimme);
die Zertifikatsstelle (`RADIOHUB_CA_DATEI`) und die Ortssuche (OSMLocal im Netz `haus`) setzt `compose.pi.yml`. Die
Namen von vor RAD-6 gelten weiter (`RADIOHUB_KELLERWOLKE_CA`, `RADIOHUB_KELLERWOLKE_SCHLUESSEL` als Pfad einer Datei,
ohne Angabe `data/kellerwolke.schluessel`); Werte, die früher in der Tabelle `config` standen (Abruf der Podcasts,
Bitraten, Adressen der Verzeichnisse; seit RAD-11 auch Sprache, Klicktöne, Werbeerkennung und Ort), übernimmt
der erste Start einmal, je Übertrag. Der Abgleich mit dem Senderverzeichnis läuft
jede Nacht zur "Uhrzeit des Abgleichs" (Einstellungen > Radio > Senderverzeichnis, `abgleich_uhrzeit`, Vorgabe 04:30, leer: nur auf Anstoß)
als Auftrag mit Fortschritt; die Server stehen unter "Senderverzeichnis" (`service_radio_browser_servers`), der nächste
springt ein, wenn einer ausfällt. Aus der Sicherung: die alte `.env` zurücklegen.
Frisch: Werte aus den Seiten von [[Kellerwolke]] und [[Vertonung]], danach `tools/ausrollen.sh` erneut.

Probe: das Protokoll der App nennt "Verbunden als App RadioHub im Konto admin"; `GET /api/storage/ablage` meldet
verbunden, eine Aufnahme landet unter `Apps/RadioHub/Aufnahmen`.

### 5. Anmelden und Telefone koppeln

Am Rechner mit Name und Passwort des Kontos, dem der App-Schlüssel gehört (weitere Konten in der App unter
Einstellungen, Zugang). Jedes Telefon einmal koppeln: in der [[Kellerwolke]] unter Einstellungen, Geräte einen Code
erzeugen (gilt zehn Minuten), am iPhone RadioHub als Web-App vom Startbildschirm öffnen (sie hat einen eigenen Speicher,
also dort koppeln, nicht in Safari) und "Mit Code koppeln" wählen. Das Gerät bleibt angemeldet, bis man es in der
Kellerwolke trennt; der Lesezugang für Ton und Bilder erneuert sich von selbst, auch in der Weckeransicht, die tagelang
offen bleibt. Fällt die Kellerwolke aus, gelten bestätigte Anmeldungen 24 Stunden weiter (Einstellung "Anmeldung bei
Ausfall").

Probe: nach dem Koppeln zeigt die Weckeransicht ihre Wecker; ein Neustart von RadioHub verlangt keine neue Anmeldung.

### 6. Einmalig: heutige Sperren in Regeln überführen (RAD-7)

Nur nach Freigabe durch den Nutzer und erst, wenn Stufe 2 läuft. Vorschau (ändert nichts, rechnet alles in einer
Transaktion durch und nimmt sie zurück): `docker exec radiohub python -m app.werkzeuge.regeln_ueberfuehren`. Sie nennt
sichtbare Sender heute und danach, jede Änderung mit Grund und Beispielen, Favoriten und alle Regeln mit Zahlen. Aus
den Sprachen der Filter-Einstellungen werden Regeln auf genau diese Einträge (je Sprache eine), aus Tags und
Mindeststimmen (Einstellung und Gründe der Filtersperren) je eine Regel, aus Sperren von Hand Einzelsperren, aus
Werbesperren Werbeentscheidungen mit einer Werbe-Regel ab "eigene Entscheidung". Die Tabelle `blocklist` bleibt
unverändert stehen. Dann `... regeln_ueberfuehren --anwenden`; ein zweiter Lauf lehnt ab.

Probe: die Ausgabe nennt "Neu ausgeblendet: 0"; wieder sichtbar sind nur Favoriten, die heute gesperrt sind (sie
bleiben als Ausnahme sichtbar); `GET /api/radio/regeln` zeigt die Regeln und keine Regel "Sperren von früher" mehr.

## Sicherung und Rückspielen

Regelmäßig (Vorgabe alle 7 Tage, Einstellungen, Sicherung) und vor jedem Ausrollen entsteht nach der Regel des
Appkerns eine Kopie von `radiohub.db` in `{{wurzel}}/sicherungen` und eine der Datenbank des Gerüsts in
`{{wurzel}}/sicherungen/appkern` (je `radiohub-<Zeit>.sqlite`, höchstens drei). Aufnahmen, Folgen und die Bausteine der
Zeitansage sichert die [[Kellerwolke]]. Rückspielen: `docker compose -f compose.pi.yml stop radiohub`, die Kopie als
`{{wurzel}}/data/radiohub.db` (oder `data/appkern/radiohub.sqlite`) ablegen (alte `-wal` und `-shm` daneben entfernen,
Besitz 1000), `docker compose -f compose.pi.yml up -d`. Eine Kopie von vor RAD-6 übernimmt der Start ohne Umbau als
Stufe 1. Prüfen: Favoriten und Abos sind da, `/health` meldet die Datenbank gesund.

## Wenn etwas klemmt

- **Ausrollen bricht ab mit "liegt noch in ...":** Der Umzug fehlt; Schritt 2 ausführen.
- **RadioHub startet nicht, "Permission denied" unter /data oder /sicherungen:** Dateien gehören noch root (von den
  Containern vor dem Umzug); `sudo chown -R 1000:1000 {{wurzel}}/data {{wurzel}}/sicherungen` und neu starten.
- **Anmeldung schlägt fehl, "Diese App gehört dem Konto ...":** Nur das Konto des App-Schlüssels darf sich anmelden;
  weitere Konten unter Einstellungen, Zugang eintragen. Ein Koppelcode gilt nur in der Kellerwolke, an der RadioHub
  hängt (die Anmeldeseite nennt ihre Adresse).
- **Die App zeigt "einrichten":** Adresse oder App-Schlüssel der Kellerwolke fehlen; `tools/ausrollen.sh` erneut (es
  besorgt sie) oder auf der Seite eintragen, von anderswo als dem Pi mit dem Einrichtungscode aus
  `{{wurzel}}/data/appkern/einrichtungscode`.
- **Commit wird abgelehnt:** Der Haken nennt den Befund (Zeichen, Stil, harte Regel, Kennung RAD-n fehlt). Ursache
  beheben; eine Ausnahme von einer harten Regel gilt nur mit einem Kommentar des Nutzers am Ticket "Ausnahme
  freigegeben: <Regel>" und einem Eintrag in `architektur/ausnahmen.toml`.
- **Ein Sender spielt nicht, andere schon:** Der Durchleiter spielt nur bekannte Sender (Kennung, die Adresse kommt aus
  der Datenbank), prüft TLS und folgt Weiterleitungen nur auf http und https; ein Sender mit abgelaufenem Zertifikat
  bleibt stumm (502 im Log, `docker compose -f compose.pi.yml logs radiohub`). In den Senderdetails eine eigene Adresse eintragen, sie gilt vor der
  aus dem Senderverzeichnis.
- **Ein Sender fehlt in der Liste:** `GET /api/radio/sender/<Kennung>/sichtbarkeit` nennt die Regeln, die ihn
  ausblenden (oder dass er verschwunden ist); in den Einstellungen des Radios unter "Ausgeblendete Sender" freigeben oder
  die Regel ausschalten. Sender, die das Verzeichnis zuletzt nicht erreichte, zeigt die Liste nur, wenn der Taster
  "Erreichbare" in den Schnellfiltern aus ist (Chip "Auch nicht erreichbare").
- **Der Abgleich endet mit Fehler:** Die Liste der Aufträge nennt den Grund. "Kein Server erreichbar": Netz oder
  Einstellung "Senderverzeichnis" prüfen. "lieferte nur n von m Sendern": das Verzeichnis antwortete unvollständig; es
  wurde nichts als verschwunden markiert, der nächste Abgleich holt es nach (oder Einstellungen > Radio >
  Senderverzeichnis, "Jetzt abgleichen").
- **Die Datenbank soll ganz geprüft werden:** `/health` fragt nur, ob sie antwortet; die volle Prüfung über die ganze
  Datei ist `GET /api/datenbank/pruefung` (dauert bei der großen Datenbank eine Weile).
- **Ortssuche findet nichts:** OSMLocal läuft nicht oder hängt nicht im Netz `haus`; der Standort des Telefons geht
  trotzdem.
