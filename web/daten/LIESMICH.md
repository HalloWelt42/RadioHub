# Senderliste der Webversion

`sender.json` ist die statische Senderliste der Webversion (RAD-4). Sie enthält nur Sender, die direkt im Browser
über https spielen: Stream-Adresse (aufgelöst, sonst die eingetragene) über https, bei der letzten Prüfung des
Verzeichnisses erreichbar, ohne Fehler im Zertifikat. Logos stehen drin, wenn sie über https erreichbar sind (RAD-105); die Webversion lädt sie direkt vom Server des Senders und zeigt ohne Logo das Kürzel.

## Herkunft und Lizenz

Die Angaben stammen aus dem freien Senderverzeichnis radio-browser.info, das seine Daten als öffentliche Daten zur
freien Nutzung bereitstellt (Bedingungen: https://www.radio-browser.info). Aufbereitet sind sie mit dem
Senderdaten-Baustein des Backends (`backend/app/senderdaten`: genaue Sprachen, Genres, Qualität, Varianten); der Kopf
der Datei nennt die Fassung der Aufbereitung, den Zeitpunkt und die Herkunft (Verzeichnis oder Datenbank).

## Neu erzeugen

Aus dem Ordner `backend/`:

```
.venv/bin/python -m app.werkzeuge.statische_liste --aus ../web/daten
.venv/bin/python -m app.werkzeuge.statische_liste --aus ../web/daten --aus-datenbank <Pfad>/radiohub.db
```

Ohne `--aus-datenbank` lädt das Werkzeug das ganze Verzeichnis seitenweise über die eingestellten Server; mit der
Angabe liest es die Tabelle `stations` der Datenbank nur lesend (ohne verschwundene Sender). Das Format beschreibt der
Kopf des Werkzeugs (`backend/app/werkzeuge/statische_liste.py`), gelesen wird es in
`frontend/src/lib/radio/statisch/format.ts`.

# Zeitansage der Webversion

`zeitansage/` hält die 84 Bausteine der Zeitansage ("Es ist", "null Uhr" bis "dreiundzwanzig Uhr", "eins" bis
"neunundfünfzig") als MP3 mono, gesprochen von der hauseigenen Vertonung mit der Katalogstimme sohee des
Sprachmodells. Eigene oder geklonte Stimmen kommen nie hierher, denn die Webversion ist öffentlich. Das Telefon setzt
die Bausteine zusammen wie in der vollen App ("Es ist sechs Uhr zweiundvierzig").

Neu sprechen lassen (dort, wo die Einstellungen der App liegen, etwa im Container des Pi), danach den Ordner hierher
holen:

```
python -m app.werkzeuge.zeitansage_bausteine --stimme katalog:sohee --aus /tmp/zeitansage
```

Das Werkzeug misst die Länge je Silbe und spricht auffällige Bausteine bis zu viermal neu; anhören muss man sie danach
trotzdem (Sprache, Aussprache).
