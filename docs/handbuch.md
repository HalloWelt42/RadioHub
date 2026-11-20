---
zweck: "Internetradio, Podcasts, Aufnahmen und Wecker im HiFi-Look: Senderverzeichnis mit Schnellfiltern, lebenden Ausschlussregeln und Favoriten, Zeitversatz, Aufnahmen mit Schnitt, Podcast-Abos, Weckeransicht mit Zeitansage am Telefon; Aufnahmen und Folgen liegen in der Kellerwolke."
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
stand: 9ff31bd
---

# RadioHub

## Zweck

RadioHub ist das Radio des Hauses, Fassung {{fassung}}: tausende Sender aus dem Senderverzeichnis (jede Nacht
abgeglichen, Sprachen, Genres, Qualität und Varianten aufbereitet) mit Suche, Schnellfiltern, lebenden
Ausschlussregeln (mit Grund je ausgeblendetem Sender) und Favoriten, Zeitversatz (zurückspulen im laufenden Sender), Aufnahmen von Hand oder nach Zeitplan mit
Schnitt in der Wellenform, Podcast-Abos zum Hören und Herunterladen. Am Telefon gibt es eine eigene Ansicht und quer
gelegt die Weckeransicht für den Nachttisch mit Wecker, Sonnenband und Zeitansage. Aufnahmen und heruntergeladene
Folgen liegen in der [[Kellerwolke]]; RadioHub hält lokal nur die Datenbank und Zwischenstände.

Erreichbar über HTTPS am eigenen Vorschaltdienst auf Port {{port:ziel/vorne}} des Pi und im Heimnetz unter
`radio.<Rufname des Pi>.lan` über den [[Vorbau]]. Die frühere Adresse ohne TLS ({{adresse}}) leitet der Vorbau auf
HTTPS um. Die App (Backend auf dem Gerüst des [[Appkern]], liefert die Oberfläche selbst aus) ist nur im eigenen Netz
der Container erreichbar. Angemeldet wird mit dem Konto der [[Kellerwolke]], dem der App-Schlüssel gehört; Telefone
koppelt man einmal mit einem Code aus der Kellerwolke. Architektur und harte Regeln stehen in `docs/ARCHITEKTUR.md`,
der Plan der Überarbeitung in `docs/umbau/PLAN.md`.

Radio bedienen: am Rechner stehen links die Schnellfilter (oben fest das Gerät mit Nur Favoriten, Erreichbare, Mindeststimmen und
Mindestbitrate, darunter Länder, Genres, Qualität, Codec, eigene Bewertung und Kategorien mit Zahlen); unter 1100 Pixeln
fährt die Leiste über den Knopf Filter ein. Alle Schnellfilter, Suche und Sortierung stehen in der Adresse
(`/radio?land=DE&genre=Rock&sort=name`, ein aufgeklappter Sender als `/radio/<Kennung>?...`), Neuladen und Lesezeichen
behalten sie; frühere Adressen `/radio/search/<Suche>` gelten weiter. Das Auge blendet einen Sender als Einzelsperre aus
und bietet Rückgängig, nichts anderes startet. Am Telefon dieselben Filter als Blatt von unten. Dauerhafte Ausschlüsse
nur unter Einstellungen > Radio: Ausschlussregeln (erst Vorschau, dann anlegen, danach Rückgängig; Entfernen nennt
vorher die Folgen), Ausgeblendete Sender (Grund je Sender, Freigeben), Länder der Seitenleiste (blendet nichts aus),
Werbeerkennung, Senderverzeichnis (letzter Abgleich, Uhrzeit, Jetzt abgleichen) und Kategorien.
Die Fokus-Taste der Spielerleiste (Fadenkreuz, blaues Licht heißt ein, gemerkt im Gerät): ein springt zum laufenden
Sender, klappt ihn auf und folgt ihm bei jedem Wechsel (Weiter, Zurück, neuer Sender), dazwischen rollt man frei; aus
rollt nur frei. Wird der aufgeklappte Sender ausgeblendet, rückt der nächste der Reihe nach.

Podcasts am Rechner (wie die Radioseite): links oben die Wahl Alle, Ungehört oder Gemerkt, darunter die Abos mit der
Zahl ungehörter Folgen (mehrere wählbar, Reihenfolge per Ziehen, Abonnieren über die Suche im Verzeichnis); oben
Zählwerk, Suche in Titeln und Beschreibungen, Sortierung und Aktualisieren. Ein gewähltes Abo zeigt seinen Kopf mit
"Neue merken" (neue Folgen von selbst im Gerät), Aktualisieren, "Alle merken" mit Fortschritt und Abbestellen (mit
Rückgängig). Je Folge: hören, merken oder freigeben, als gehört setzen, Details. Spielt eine Folge, hat die
Abspielleiste statt der Bitrate eine Drehwahl für das Tempo.

Wecker am Telefon (Wecker-Taste oben): je Wecker Uhrzeit, Tage, Sender oder neueste Folge eines Abos, Weckton,
Lautstärke und wie langsam es lauter wird. Den Weckton (neun zur Wahl, Vorgabe Doppelpiep, alle im Gerät erzeugt und
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
Bitraten, Adressen der Verzeichnisse), übernimmt der erste Start einmal. Der Abgleich mit dem Senderverzeichnis läuft
jede Nacht zur Uhrzeit "Abgleich mit dem Senderverzeichnis" (`abgleich_uhrzeit`, Vorgabe 04:30, leer: nur auf Anstoß)
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
