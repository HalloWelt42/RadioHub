// Entwurf RAD-11: Beschreibung aller Bereiche der Einstellungen. Einfache Werte stehen als Zeilen mit denselben Angaben
// wie das Modell des Servers (Titel, Beschreibung, Grenzen, Schritt, Einheit) und ihrer Geltung: "alle" (für alle
// Geräte, gespeichert über die Leiste Speichern) oder "geraet" (gilt sofort und nur hier). Sonderteile ("teil") zeichnet
// einstellungen.js. Jede Zeile des Bestands (docs/umbau/RAD-11-bestand.md) steht hier oder ist im Plan als entfallen
// genannt.

window.RHEinstellungen = {
  BEREICHE: [
    { id: "allgemein", titel: "Allgemein", symbol: "fa-gear", reiter: [
      { id: "bedienung", titel: "Bedienung", symbol: "fa-hand-pointer", karten: [
        { titel: "Sprache und Töne", symbol: "fa-language", zeilen: [
          { name: "Sprache", erklaerung: "Sprache der Oberfläche.", geltung: "alle", art: "sprache", wert: "de" },
          { name: "Klicktöne", erklaerung: "Leise Töne beim Drücken von Tasten und Schaltern.", geltung: "alle", art: "schalter", wert: true },
        ] },
        { titel: "Fehlersuche", symbol: "fa-stethoscope", zeilen: [
          { name: "Entwickleransicht", erklaerung: "Zeigt an Aufnahmen Güte und Lücken des Mitschnitts.", geltung: "geraet", art: "schalter", wert: false },
        ] },
      ] },
      { id: "tastatur", titel: "Tastatur", symbol: "fa-keyboard", teil: "tastatur" },
      { id: "ueber", titel: "Über", symbol: "fa-circle-info", teil: "ueber" },
      { id: "bedanken", titel: "Bedanken", symbol: "fa-heart", teil: "bedanken" },
    ] },
    { id: "darstellung", titel: "Darstellung", symbol: "fa-circle-half-stroke", reiter: [
      { id: "darstellung", titel: "Darstellung", karten: [
        { titel: "Aussehen", symbol: "fa-palette", hinweis: "Dieselben Einstellungen wie die Tafel Darstellung im Kopf.", zeilen: [
          { name: "Vorlage", erklaerung: "Grundform aller Bedienteile.", geltung: "geraet", art: "wahl", wert: "hifi",
            optionen: [["hifi", "HiFi", "fa-compact-disc"], ["ruhig", "Ruhig", "fa-feather"]] },
          { name: "Thema", erklaerung: "Hell, dunkel oder wie das Gerät eingestellt ist.", geltung: "geraet", art: "wahl", wert: "system",
            optionen: [["hell", "Hell", "fa-sun"], ["dunkel", "Dunkel", "fa-moon"], ["system", "System", "fa-display"]] },
          { name: "Schrift", erklaerung: "Größe aller Texte; Bedienteile wachsen mit.", geltung: "geraet", art: "schrift", wert: 0 },
        ] },
        { titel: "Bildschirm", symbol: "fa-mobile-screen", zeilen: [
          { name: "Bildschirm wach halten", erklaerung: "Das Gerät schaltet den Bildschirm nicht ab, solange RadioHub offen ist. Nicht jeder Browser kann das.", geltung: "geraet", art: "schalter", wert: false },
        ] },
      ] },
    ] },
    { id: "radio", titel: "Radio", symbol: "fa-radio", reiter: [
      { id: "regeln", titel: "Ausschlussregeln", symbol: "fa-filter-circle-xmark", verweis: "regeln.html?reiter=regeln" },
      { id: "ausgeblendet", titel: "Ausgeblendete Sender", symbol: "fa-eye-slash", verweis: "regeln.html?reiter=ausgeblendet" },
      { id: "laender", titel: "Länder der Seitenleiste", symbol: "fa-earth-europe", verweis: "regeln.html?reiter=laender" },
      { id: "werbung", titel: "Werbeerkennung", symbol: "fa-rectangle-ad", karten: [
        { titel: "Erkennung", symbol: "fa-magnifying-glass-chart", hinweis: "Stand, Prüfung aller Sender und Entscheidung über Verdächtige bleiben wie gebaut; neu ist nur, dass diese Werte im Modell des Servers liegen.", zeilen: [
          { name: "Werbeerkennung", erklaerung: "Prüft Sender auf reine Werbe- und Verkaufskanäle.", geltung: "alle", art: "schalter", wert: true },
          { name: "Verfahren", erklaerung: "Woran ein Sender erkannt wird; mehrere zugleich.", geltung: "alle", art: "mehrfach", wert: ["name", "adresse", "titel"],
            optionen: [["name", "Name", "fa-signature"], ["adresse", "Adresse", "fa-link"], ["titel", "Titel im Strom", "fa-music"]] },
          { name: "Schwelle", erklaerung: "Ab dieser Sicherheit gilt ein Sender als verdächtig.", geltung: "alle", art: "zahl", min: 40, max: 100, schritt: 5, einheit: "%", wert: 70 },
        ] },
      ] },
      { id: "abgleich", titel: "Senderverzeichnis", symbol: "fa-arrows-rotate", karten: [
        { titel: "Nächtlicher Abgleich", symbol: "fa-moon", hinweis: "Letzter Abgleich und Jetzt abgleichen bleiben wie gebaut; die Uhrzeit ist jetzt einstellbar.", zeilen: [
          { name: "Uhrzeit des Abgleichs", erklaerung: "Jede Nacht gleicht das Radio seinen Bestand mit dem Senderverzeichnis ab: neue Sender, geänderte Angaben, verschwundene markiert. Leer: nur auf Anstoß.", geltung: "alle", art: "uhrzeit", wert: "04:30", leerErlaubt: true },
        ] },
      ] },
      { id: "kategorien", titel: "Kategorien", symbol: "fa-folder", teil: "kategorien" },
    ] },
    { id: "wiedergabe", titel: "Wiedergabe", symbol: "fa-clock-rotate-left", reiter: [
      { id: "zeitversatz", titel: "Zeitversatz", karten: [
        { titel: "Zeitversatz", symbol: "fa-clock-rotate-left",
          hinweis: "Der Zeitversatz puffert den laufenden Sender, damit man zurückspulen und anhalten kann. Die Grenzen gelten für alle Geräte; die Drehwahl Bitrate in der Kanzel wählt je Gerät einen Wert innerhalb dieser Grenzen.", zeilen: [
          { name: "Kleinste Bitrate", erklaerung: "Untergrenze; schwächere Sender werden auf diesen Wert gehoben.", geltung: "alle", art: "zahl", min: 8, max: 512, schritt: 8, einheit: "kbit/s", wert: 32 },
          { name: "Größte Bitrate", erklaerung: "Obergrenze; stärkere Sender werden nicht aufgebläht.", geltung: "alle", art: "zahl", min: 8, max: 512, schritt: 8, einheit: "kbit/s", wert: 320, pruefung: "Muss mindestens so groß sein wie die kleinste Bitrate." },
          { name: "Abtastrate", erklaerung: "Abtastrate des Puffers.", geltung: "alle", art: "wahl", wert: "44100",
            optionen: [["22050", "22.050 Hz"], ["32000", "32.000 Hz"], ["44100", "44.100 Hz"], ["48000", "48.000 Hz"]] },
          { name: "Länge des Puffers", erklaerung: "So weit lässt sich zurückspulen. Bisher fest 120 Minuten.", geltung: "alle", art: "zahl", min: 10, max: 240, schritt: 10, einheit: "min", wert: 120 },
          { name: "Rückblick der Puffer-Aufnahme", erklaerung: "Eine Aufnahme aus dem Puffer beginnt so weit vor dem Moment des Drückens.", geltung: "alle", art: "zahl", min: 1, max: 120, schritt: 1, einheit: "min", wert: 5, pruefung: "Höchstens so lang wie der Puffer." },
        ] },
      ] },
    ] },
    { id: "aufnahmen", titel: "Aufnahmen", symbol: "fa-circle-dot", reiter: [
      { id: "ordner", titel: "Ordner", symbol: "fa-folder-tree", teil: "aufnahmeordner" },
      { id: "titel", titel: "Titel ignorieren", symbol: "fa-ban", teil: "muster" },
      { id: "technik", titel: "Technik", symbol: "fa-sliders", karten: [
        { titel: "Aufnahme", symbol: "fa-circle-dot", zeilen: [
          { name: "Bitrate der Aufnahme", erklaerung: "Mit dieser Bitrate wird gespeichert, wenn der Sender sie nicht selbst vorgibt.", geltung: "alle", art: "zahl", min: 8, max: 512, schritt: 8, einheit: "kbit/s", wert: 192 },
          { name: "Aufnahme protokollieren", erklaerung: "Schreibt zu jeder Aufnahme ein Protokoll der Ereignisse (Start, Stocken, Größe, Ende) neben die Aufnahme, für die Fehlersuche.", geltung: "alle", art: "schalter", wert: false },
        ] },
      ] },
    ] },
    { id: "podcasts", titel: "Podcasts", symbol: "fa-podcast", reiter: [
      { id: "abruf", titel: "Abruf", karten: [
        { titel: "Abruf der Abos", symbol: "fa-rotate", zeilen: [
          { name: "Abos von selbst abrufen", erklaerung: "Ruft die Feeds aller Abos regelmäßig ab und zeigt neue Folgen.", geltung: "alle", art: "schalter", wert: true },
          { name: "Abstand des Abrufs", erklaerung: "Zeit zwischen zwei Abrufen. Neue Folgen speichern stellt man je Abo in seinem Kopf ein.", geltung: "alle", art: "zahl", min: 1, max: 168, schritt: 1, einheit: "h", wert: 6 },
        ] },
      ] },
    ] },
    { id: "wecker", titel: "Wecker und Zeitansage", symbol: "fa-bell", reiter: [
      { id: "zeitansage", titel: "Zeitansage", symbol: "fa-comment-dots", karten: [
        { titel: "Zeitansage", symbol: "fa-comment-dots", hinweis: "Die Zeitansage gilt je Gerät, wie bisher am Telefon; jetzt auch am Rechner einstellbar.", zeilen: [
          { name: "Zeitansage", erklaerung: "Sagt die Uhrzeit an, auch in der Weckansicht.", geltung: "geraet", art: "schalter", wert: true },
          { name: "Abstand", erklaerung: "Alle so viele Minuten.", geltung: "geraet", art: "wahl", wert: "5", optionen: [["5", "5 min"], ["10", "10 min"], ["15", "15 min"], ["30", "30 min"], ["60", "60 min"]] },
          { name: "Zeitraum", erklaerung: "Nur zwischen diesen Uhrzeiten; leer: rund um die Uhr.", geltung: "geraet", art: "zeitraum", wert: ["", ""] },
          { name: "Wann", erklaerung: "Nur während ein Wecker klingelt oder immer.", geltung: "geraet", art: "wahl", wert: "wecker", optionen: [["wecker", "Nur mit Wecker"], ["immer", "Immer"]] },
          { name: "Bei Nachtrot", erklaerung: "Lautstärke der Ansage, wenn die Weckansicht nachts rot leuchtet.", geltung: "geraet", art: "wahl", wert: "leise", optionen: [["normal", "Normal"], ["leise", "Leise"], ["aus", "Aus"]] },
        ] },
        { titel: "Stimme", symbol: "fa-microphone-lines", teil: "stimme", zeilen: [
          { name: "Tempo der Zeit-Stimme", erklaerung: "1,0 ist das Tempo der Stimme; kleiner spricht langsamer.", geltung: "alle", art: "zahl", min: 0.5, max: 2, schritt: 0.05, einheit: "", wert: 1 },
        ] },
      ] },
      { id: "ort", titel: "Ort", symbol: "fa-location-dot", teil: "ort" },
      { id: "wecken", titel: "Wecken", symbol: "fa-bell", karten: [
        { titel: "Wecken", symbol: "fa-bell", hinweis: "Die Wecker selbst (Uhrzeit, Tage, Sender, Weckton) stellt man in der Weckerliste ein.", verweis: ["Wecker verwalten", "fa-list"], zeilen: [
          { name: "Schlummerdauer", erklaerung: "So lange schweigt der Wecker nach Schlummern. Bisher fest 9 Minuten.", geltung: "alle", art: "zahl", min: 1, max: 60, schritt: 1, einheit: "min", wert: 9 },
        ] },
      ] },
    ] },
    { id: "ablage", titel: "Ablage", symbol: "fa-hard-drive", reiter: [
      { id: "ablage", titel: "Ablage", teil: "ablage", karten: [
        { titel: "Kellerwolke", symbol: "fa-cloud", zeilen: [
          { name: "Ordner in der Kellerwolke", erklaerung: "Wurzelordner der Aufnahmen, Podcast-Folgen und Bausteine der Zeitansage.", geltung: "alle", art: "text", wert: "Apps/RadioHub" },
          { name: "Geduld beim Ablegen", erklaerung: "So lange wartet das Ablegen, wenn die Kellerwolke gerade nicht erreichbar ist, damit ein Neustart dort nichts kostet.", geltung: "alle", art: "zahl", min: 0, max: 3600, schritt: 60, einheit: "s", wert: 900 },
        ] },
      ] },
    ] },
    { id: "dienste", titel: "Dienste", symbol: "fa-plug", reiter: [
      { id: "dienste", titel: "Dienste", karten: [
        { titel: "Verzeichnisse", symbol: "fa-book-atlas", zeilen: [
          { name: "Senderverzeichnis", erklaerung: "Server des Senderverzeichnisses, in dieser Reihenfolge gefragt.", geltung: "alle", art: "liste", vorgabeKnopf: true,
            wert: ["https://de1.api.radio-browser.info", "https://at1.api.radio-browser.info", "https://nl1.api.radio-browser.info"] },
          { name: "Podcast-Verzeichnis, weltweit", erklaerung: "Suche nach Podcasts beim Abonnieren.", geltung: "alle", art: "text", vorgabeKnopf: true, wert: "https://itunes.apple.com/search" },
          { name: "Podcast-Verzeichnis, deutsch", erklaerung: "Zweite Suche, vor allem deutschsprachige Podcasts.", geltung: "alle", art: "text", vorgabeKnopf: true, wert: "https://api.fyyd.de/0.2/search/podcast" },
        ] },
        { titel: "Helfer im Haus", symbol: "fa-house-signal", zeilen: [
          { name: "Ortssuche", erklaerung: "Kartensuche für den Ort der Sonnenzeiten. Leer: keine Suche, der Standort des Geräts geht trotzdem.", geltung: "alle", art: "text", wert: "https://karte.pi5b.lan" },
          { name: "Vertonung", erklaerung: "Spricht die Bausteine der Zeitansage. Nimmt den App-Schlüssel der Kellerwolke als Zugang.", geltung: "alle", art: "text", wert: "https://vertonung.mac.lan", fest: true },
        ] },
        { titel: "Zugang", symbol: "fa-shield-halved", zeilen: [
          { name: "Fremde Ursprünge", erklaerung: "Nur nötig, wenn eine fremde Seite die Schnittstelle im Browser nutzen soll; nie *. Leer: die Oberfläche spricht über denselben Ursprung. Gilt nach einem Neustart.", geltung: "alle", art: "liste", wert: [] },
        ] },
      ] },
    ] },
  ],

  SPRACHEN: [["de", "Deutsch"], ["en", "English"], ["fr", "Français"], ["es", "Español"], ["it", "Italiano"], ["pt", "Português"], ["nl", "Nederlands"],
    ["pl", "Polski"], ["cs", "Čeština"], ["sk", "Slovenčina"], ["da", "Dansk"], ["sv", "Svenska"], ["no", "Norsk"], ["fi", "Suomi"], ["hu", "Magyar"],
    ["ro", "Română"], ["tr", "Türkçe"], ["ru", "Русский"], ["ja", "日本語"], ["zh", "中文"]],

  TASTEN: [
    { gruppe: "Wiedergabe", tasten: [["Leertaste", "Hören oder anhalten"], ["S", "Stopp (gesperrt während einer Aufnahme)"], ["M", "Stumm und wieder laut"], ["Pfeil hoch|Pfeil runter", "Lauter, leiser"], ["Pfeil links|Pfeil rechts", "Vorheriger, nächster Sender (gesperrt während einer Aufnahme)"]] },
    { gruppe: "Liste", tasten: [["Pfeil hoch|Pfeil runter", "In der Senderliste wandern, wenn sie den Fokus hat"], ["Eingabe", "Gewählten Sender hören"]] },
    { gruppe: "Bereiche", tasten: [["1", "Radio"], ["2", "Aufnahmen"], ["3", "Podcasts"], ["4", "Einstellungen"]] },
  ],

  AUFNAHMEORDNER: [
    { id: 1, name: "Jazz", aufnahmen: 42, aktiv: true },
    { id: 2, name: "Nachrichten", aufnahmen: 7, aktiv: false },
    { id: 3, name: "Hörspiele", aufnahmen: 0, aktiv: false },
  ],
  STAMM_AUFNAHMEN: 118,

  MUSTER: [
    { id: 1, muster: "Werbung", art: "enthaelt", eingebaut: true, treffer: 312 },
    { id: 2, muster: "Nachrichten", art: "exakt", eingebaut: true, treffer: 96 },
    { id: 3, muster: "Jingle", art: "enthaelt", eingebaut: false, treffer: 41 },
    { id: 4, muster: "Verkehr", art: "exakt", eingebaut: false, treffer: 12 },
  ],

  KATEGORIEN: [
    { id: 1, name: "Morgens", sender: 6 },
    { id: 2, name: "Zum Arbeiten", sender: 14 },
    { id: 3, name: "Kinder", sender: 0 },
  ],

  STIMMEN: [["katalog:sohee", "Sohee"], ["katalog:aiden", "Aiden"], ["katalog:eric", "Eric"]],
  BAUSTEINE: { vorhanden: 1440, gesamt: 1440 },

  ABLAGE: { datenordner: "/mnt/data/radiohub", belegt: 3.8, frei: 412, datenbank: 0.42, puffer: 2.9, dateien: 1832 },
};
