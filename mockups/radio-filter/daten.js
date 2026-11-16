// Beispieldaten des Entwurfs RAD-3: eine Stelle für Sender, Facetten, Regeln und Geräte, gelesen von allen Seiten.
// Sendernamen sind Favoriten des Nutzers und bekannte öffentliche Sender; Logos sind neutrale Flächen mit Kürzel.
// Titel im Verlauf sind erfunden. Zahlen sind plausibel, aber keine Messung (Stand der Sicherung vom 16.11.2026).

(() => {
  "use strict";

  const BESTAND = { gesamt: 58364, sichtbar: 49081, ausgeblendet: 8249, verschwunden: 1034, favoriten: 69 };

  // Qualitätsstufen aus gemessener Bitrate und Codec: Zahl der leuchtenden Lichter und ihre Farbe
  const GUETE = {
    verlustfrei: { name: "verlustfrei", lichter: 4, farbe: "cyan", hilfe: "Verlustfrei (FLAC), wie die Quelle" },
    hoch: { name: "hoch", lichter: 3, farbe: "gruen", hilfe: "Hoch: AAC ab 128 oder MP3 ab 256 kbit/s" },
    mittel: { name: "mittel", lichter: 2, farbe: "gelb", hilfe: "Mittel: MP3 128 bis 192 oder AAC 64 bis 96 kbit/s" },
    niedrig: { name: "niedrig", lichter: 1, farbe: "bernstein", hilfe: "Niedrig: unter 96 kbit/s (MP3) oder 64 kbit/s (AAC)" },
    unbekannt: { name: "unbekannt", lichter: 0, farbe: "weiss", hilfe: "Noch nicht gemessen; die Messung läuft im Hintergrund, Favoriten zuerst" },
  };

  const LAENDER = { DE: "Deutschland", AT: "Österreich", CH: "Schweiz", NL: "Niederlande", GB: "Großbritannien", FR: "Frankreich", US: "USA" };

  // Facetten der Seitenleiste: Werte mit Zahl der Treffer im sichtbaren Bestand
  const FACETTEN = {
    land: { titel: "Länder", werte: [["DE", 5419], ["US", 7824], ["FR", 2447], ["GB", 2086], ["NL", 1256], ["CH", 1034], ["AT", 812]] },
    genre: { titel: "Genres", werte: [["Nachrichten", 1912], ["Kultur", 1347], ["Klassik", 2108], ["80er", 1655], ["90er", 1402], ["Rock", 4870],
      ["Elektronik", 3215], ["Techno", 1120], ["Dark Wave", 388], ["Pop", 7410], ["Jazz", 986], ["Chillout", 1204]],
      mehr: [["Hörspiel", 214], ["Schlager", 1830], ["Volksmusik", 642], ["Hip-Hop", 1544], ["Metal", 1290], ["Soul", 704], ["Reggae", 512], ["Ambient", 688], ["Weltmusik", 1102], ["Kinder", 233]] },
    guete: { titel: "Qualität", werte: [["verlustfrei", 412], ["hoch", 9870], ["mittel", 21304], ["niedrig", 6118], ["unbekannt", 11377]] },
    codec: { titel: "Codec", werte: [["MP3", 30112], ["AAC", 13540], ["OGG", 1204], ["OPUS", 611], ["FLAC", 398], ["unbekannt", 3216]] },
    bewertung: { titel: "Eigene Bewertung", werte: [["3", 41], ["2", 18], ["1", 7], ["werbung", 12]] },
    kategorie: { titel: "Eigene Kategorien", werte: [["Morgens", 6], ["Arbeit", 14], ["Unterwegs", 11], ["Klassik am Abend", 8], ["Zum Einschlafen", 9]] },
  };
  const BEWERTUNG_NAMEN = { 3: "Sehr gut", 2: "Gut", 1: "Geht so", werbung: "Werbung" };

  // Stufen der Regler: Anteil des Bestands, der übrig bleibt
  const BITRATE_STUFEN = [["alle", 0, 1], ["64", 64, 0.81], ["128", 128, 0.52], ["192", 192, 0.21], ["256", 256, 0.14], ["320", 320, 0.05]];
  const STIMMEN_STUFEN = [["alle", 0, 1], ["ab 10", 10, 0.46], ["ab 100", 100, 0.12], ["ab 1.000", 1000, 0.018], ["ab 10.000", 10000, 0.0011]];

  const s = (o) => Object.assign({ favorit: true, bewertung: 0, werbung: false, kategorien: [], varianten: [], sprache: "Deutsch" }, o);
  const SENDER = [
    s({ id: "dlf", name: "Deutschlandfunk", land: "DE", ort: "Köln", genres: ["Nachrichten", "Kultur"], guete: "hoch", codec: "AAC", kbps: 256, verz: 128, stimmen: 3214,
        bewertung: 3, kategorien: ["Morgens", "Arbeit"], titel: "Nachrichten und Presseschau",
        varianten: [{ codec: "AAC", kbps: 256, guete: "hoch", stimmen: 3214, art: "Strom" }, { codec: "MP3", kbps: 128, guete: "mittel", stimmen: 1980, art: "Strom" },
          { codec: "AAC", kbps: 192, guete: "hoch", stimmen: 402, art: "HLS adaptiv" }, { codec: "MP3", kbps: 64, guete: "niedrig", stimmen: 88, art: "Strom" }] }),
    s({ id: "dlfk", name: "Deutschlandfunk Kultur", land: "DE", ort: "Berlin", genres: ["Kultur", "Klassik"], guete: "hoch", codec: "AAC", kbps: 256, verz: 128, stimmen: 1872,
        bewertung: 3, kategorien: ["Klassik am Abend"], titel: "Gespräch: Bauen mit Holz in der Stadt",
        varianten: [{ codec: "AAC", kbps: 256, guete: "hoch", stimmen: 1872, art: "Strom" }, { codec: "MP3", kbps: 128, guete: "mittel", stimmen: 1104, art: "Strom" },
          { codec: "AAC", kbps: 192, guete: "hoch", stimmen: 233, art: "HLS adaptiv" }] }),
    s({ id: "nova", name: "Deutschlandfunk Nova", land: "DE", ort: "Köln", genres: ["Nachrichten", "Pop"], guete: "mittel", codec: "MP3", kbps: 128, verz: 128, stimmen: 942, bewertung: 2, kategorien: ["Unterwegs"], titel: "Gespräch: Schlaf und Bildschirm" }),
    s({ id: "wdr2", name: "WDR 2", land: "DE", ort: "Köln", genres: ["Pop", "Nachrichten"], guete: "hoch", codec: "MP3", kbps: 256, verz: 128, stimmen: 1488, bewertung: 2, kategorien: ["Unterwegs"], titel: "Silberwald: Langer Sommer" }),
    s({ id: "wdr3", name: "WDR 3", land: "DE", ort: "Köln", genres: ["Klassik", "Kultur"], guete: "hoch", codec: "AAC", kbps: 256, verz: 0, stimmen: 1106, bewertung: 3, kategorien: ["Klassik am Abend"], titel: "Sonate für Violine in drei Sätzen",
        varianten: [{ codec: "AAC", kbps: 256, guete: "hoch", stimmen: 1106, art: "Strom" }, { codec: "MP3", kbps: 128, guete: "mittel", stimmen: 512, art: "Strom" }] }),
    s({ id: "wdr5", name: "WDR 5", land: "DE", ort: "Köln", genres: ["Kultur", "Nachrichten"], guete: "mittel", codec: "MP3", kbps: 128, verz: 128, stimmen: 863, bewertung: 2, kategorien: ["Arbeit"], titel: "Feature: Wasser in der Stadt" }),
    s({ id: "ndri", name: "NDR Info", land: "DE", ort: "Hamburg", genres: ["Nachrichten"], guete: "hoch", codec: "AAC", kbps: 128, verz: 128, stimmen: 1320, bewertung: 3, kategorien: ["Morgens"], titel: "Nachrichten und Wetter" }),
    s({ id: "mdrk", name: "MDR Klassik", land: "DE", ort: "Leipzig", genres: ["Klassik"], guete: "verlustfrei", codec: "FLAC", kbps: 1411, verz: 256, stimmen: 644, bewertung: 3, kategorien: ["Klassik am Abend", "Zum Einschlafen"], titel: "Konzert für Klavier und Orchester, Finale" }),
    s({ id: "b2", name: "Bremen Zwei", land: "DE", ort: "Bremen", genres: ["Kultur", "Pop"], guete: "mittel", codec: "MP3", kbps: 128, verz: 128, stimmen: 214, bewertung: 2, titel: "Hafenlichter: Ohne Eile" }),
    s({ id: "dfm", name: "detektor.fm Wort", land: "DE", ort: "Leipzig", genres: ["Nachrichten", "Kultur"], guete: "mittel", codec: "MP3", kbps: 160, verz: 128, stimmen: 187, bewertung: 2, kategorien: ["Arbeit"], titel: "Gespräch über Bahnstrecken auf dem Land" }),
    s({ id: "rp", name: "Radio Paradise", land: "US", ort: "Paradise, Kalifornien", sprache: "Englisch", genres: ["Rock", "Pop"], guete: "verlustfrei", codec: "FLAC", kbps: 1411, verz: 320, stimmen: 9844, bewertung: 3, kategorien: ["Arbeit"], titel: "Kalte Küste: Weites Land",
        varianten: [{ codec: "FLAC", kbps: 1411, guete: "verlustfrei", stimmen: 9844, art: "Strom" }, { codec: "AAC", kbps: 320, guete: "hoch", stimmen: 4120, art: "Strom" },
          { codec: "MP3", kbps: 128, guete: "mittel", stimmen: 2876, art: "Strom" }, { codec: "AAC", kbps: 64, guete: "niedrig", stimmen: 610, art: "Strom" }] }),
    s({ id: "80s", name: "80s80s", land: "DE", ort: "Hamburg", genres: ["80er", "Pop"], guete: "mittel", codec: "MP3", kbps: 128, verz: 128, stimmen: 2540, bewertung: 2, werbung: true, kategorien: ["Unterwegs"], titel: "Neonwelle: Herz aus Glas",
        varianten: [{ codec: "MP3", kbps: 128, guete: "mittel", stimmen: 2540, art: "Strom" }, { codec: "AAC", kbps: 64, guete: "mittel", stimmen: 830, art: "Strom" }, { codec: "MP3", kbps: 64, guete: "niedrig", stimmen: 122, art: "Strom" }] }),
    s({ id: "80dw", name: "80s80s Dark Wave", land: "DE", ort: "Hamburg", genres: ["80er", "Dark Wave"], guete: "mittel", codec: "MP3", kbps: 128, verz: 128, stimmen: 312, bewertung: 3, titel: "Graue Stadt: Nachtzug" }),
    s({ id: "sl", name: "Sunshine Live", land: "DE", ort: "Mannheim", genres: ["Elektronik", "Techno"], guete: "mittel", codec: "MP3", kbps: 192, verz: 192, stimmen: 4402, bewertung: 2, werbung: true, kategorien: ["Arbeit"], titel: "Pulsar Sieben: Lichtfeld" }),
    s({ id: "chill", name: "Laut.FM Chillharmonie", land: "DE", ort: "Berlin", genres: ["Elektronik", "Chillout"], guete: "niedrig", codec: "MP3", kbps: 64, verz: 128, stimmen: 58, bewertung: 1, kategorien: ["Zum Einschlafen"], titel: "Wolkenlage: Stilles Wasser" }),
    s({ id: "udr", name: "Ultra Dark Radio", land: "DE", ort: "Berlin", genres: ["Dark Wave", "Rock"], guete: "unbekannt", codec: "MP3", kbps: 0, verz: 128, stimmen: 96, bewertung: 2, titel: "Schwarzlicht: Ferne Glocken" }),
    s({ id: "wdr4", name: "WDR 4", land: "DE", ort: "Köln", genres: ["Pop", "80er"], guete: "mittel", codec: "MP3", kbps: 128, verz: 128, stimmen: 702, favorit: false, titel: "Morgenrot: Alte Straße" }),
    s({ id: "ndrk", name: "NDR Kultur", land: "DE", ort: "Hannover", genres: ["Klassik", "Kultur"], guete: "hoch", codec: "AAC", kbps: 128, verz: 128, stimmen: 455, favorit: false, titel: "Serenade in G" }),
    s({ id: "swrk", name: "SWR Kultur", land: "DE", ort: "Stuttgart", genres: ["Kultur", "Klassik"], guete: "hoch", codec: "AAC", kbps: 128, verz: 128, stimmen: 391, favorit: false, titel: "Lesung: Die Brücke am Fluss" }),
    s({ id: "brk", name: "BR-Klassik", land: "DE", ort: "München", genres: ["Klassik"], guete: "hoch", codec: "AAC", kbps: 192, verz: 128, stimmen: 1210, favorit: false, titel: "Quartett in D, langsamer Satz" }),
    s({ id: "r1", name: "radioeins", land: "DE", ort: "Potsdam", genres: ["Pop", "Rock"], guete: "mittel", codec: "MP3", kbps: 128, verz: 128, stimmen: 1630, favorit: false, titel: "Kreidezeit: Sonne über Asphalt" }),
    s({ id: "hr2", name: "hr2-kultur", land: "DE", ort: "Frankfurt", genres: ["Kultur", "Klassik", "Jazz"], guete: "hoch", codec: "AAC", kbps: 128, verz: 96, stimmen: 274, favorit: false, titel: "Jazzfenster" }),
  ];

  // Titelverlauf (erfundene Titel), je Sender höchstens die letzten Einträge; Größe in der App begrenzt
  const VERLAUF = {
    dlfk: [["14:05", "Gespräch: Bauen mit Holz in der Stadt"], ["13:58", "Musik: Streichquartett Nr. 2, zweiter Satz"], ["13:30", "Buchkritik: Ein Sommer am Haff"],
      ["13:07", "Nachrichten"], ["12:40", "Reportage: Nachtzüge durch Europa"], ["12:05", "Musik: Lied ohne Worte, Klavier"]],
    _musik: [["14:06", "Silberwald: Langer Sommer"], ["14:02", "Nordlicht: Kalte Hände"], ["13:58", "Kreidezeit: Sonne über Asphalt"], ["13:54", "Hafenlichter: Ohne Eile"],
      ["13:49", "Neonwelle: Herz aus Glas"], ["13:45", "Graue Stadt: Nachtzug"]],
  };

  const AEHNLICH = { dlfk: [["wdr3", "Klassik und Kultur, hoch"], ["ndrk", "Kultur, gleicher Takt am Abend"], ["mdrk", "Klassik, verlustfrei"], ["b2", "Kultur, Bremen"]] };

  // Geräte im Hausempfang: genau eins spielt; der Wecker ist eigenständig und fehlt hier
  const GERAETE = [
    { id: "rechner", name: "Rechner im Arbeitszimmer", symbol: "fa-desktop", dieses: true },
    { id: "telefon", name: "Telefon", symbol: "fa-mobile-screen" },
    { id: "kueche", name: "Pi in der Küche", symbol: "fa-microchip" },
    { id: "wohnzimmer", name: "Wohnzimmer", symbol: "fa-tv" },
  ];

  // Lebende Ausschlussregeln; Überschneidungen zählen in der Summe einmal (8.249 Sender)
  const REGELN = [
    { id: "r1", art: "sprache", wert: "Russisch", code: "ru", betroffen: 1683, favoriten: 0, an: true },
    { id: "r2", art: "sprache", wert: "Arabisch", code: "ar", betroffen: 1212, favoriten: 0, an: true },
    { id: "r3", art: "sprache", wert: "Türkisch", code: "tr", betroffen: 1377, favoriten: 0, an: true },
    { id: "r4", art: "sprache", wert: "Spanisch", code: "es", betroffen: 3410, favoriten: 0, an: false },
    { id: "r5", art: "tag", wert: "Religion", code: "", betroffen: 1988, favoriten: 0, an: true },
    { id: "r6", art: "stimmen", wert: "weniger als 3 Stimmen", code: "", betroffen: 2640, favoriten: 0, an: true },
    { id: "r7", art: "werbung", wert: "Werbeverdacht hoch", code: "", betroffen: 214, favoriten: 0, an: true },
    { id: "r8", art: "bewertung", wert: "eigene Bewertung Schlecht", code: "", betroffen: 7, favoriten: 0, an: true },
    { id: "r9", art: "einzeln", wert: "Einzelsperren", code: "", betroffen: 23, favoriten: 0, an: true },
  ];
  const REGEL_ARTEN = {
    sprache: { name: "Sprache", symbol: "fa-language", erklaerung: "exakter Sprachcode, Sender ohne Angabe bleiben sichtbar" },
    tag: { name: "Genre", symbol: "fa-tag", erklaerung: "normalisiertes Genre, alle Schreibweisen" },
    stimmen: { name: "Mindeststimmen", symbol: "fa-thumbs-up", erklaerung: "gilt auch für neue Sender" },
    werbung: { name: "Werbung", symbol: "fa-rectangle-ad", erklaerung: "aus Messung und eigener Bewertung" },
    bewertung: { name: "Bewertung", symbol: "fa-star", erklaerung: "eigene Bewertungen" },
    einzeln: { name: "Einzelsender", symbol: "fa-eye-slash", erklaerung: "per Auge ausgeblendet" },
  };

  // Sprachen als exakte Einträge mit deutschem Namen und Code; Zahlen je Sprache, davon Favoriten
  const SPRACHEN = [
    ["Chinesisch (Mandarin)", "zh", 2159, 0], ["Chinesisch (Kantonesisch)", "yue", 212, 0], ["Deutsch", "de", 3583, 47], ["Schweizerdeutsch", "gsw", 164, 0],
    ["Niederdeutsch", "nds", 21, 0], ["Englisch", "en", 11206, 9], ["Französisch", "fr", 2310, 0], ["Griechisch", "el", 734, 0], ["Hindi", "hi", 802, 0],
    ["Italienisch", "it", 2116, 0], ["Japanisch", "ja", 488, 0], ["Koreanisch", "ko", 351, 0], ["Niederländisch", "nl", 1012, 0], ["Polnisch", "pl", 1290, 0],
    ["Portugiesisch", "pt", 2744, 0], ["Rumänisch", "ro", 690, 0], ["Russisch", "ru", 1683, 0], ["Spanisch", "es", 3410, 0], ["Tschechisch", "cs", 402, 0],
    ["Türkisch", "tr", 1377, 0], ["Ukrainisch", "uk", 377, 0], ["Ungarisch", "hu", 509, 0], ["Arabisch", "ar", 1212, 0], ["Persisch", "fa", 298, 0],
  ];
  const GENRE_REGELN = [["Religion", 1988, 0], ["Schlager", 1830, 0], ["Volksmusik", 642, 0], ["Hip-Hop", 1544, 0], ["Metal", 1290, 1], ["Kinder", 233, 0], ["Sport", 912, 0], ["Comedy", 401, 0]];

  // Ausgeblendete Sender (neutral erfundene Namen) mit Grund; seitenweise
  const silben = ["Volna", "Sever", "Dalga", "Aydin", "Nour", "Baraka", "Zvezda", "Liman", "Rüzgar", "Hayat", "Sahil", "Iman", "Svet", "Ufuk", "Salam"];
  const AUSGEBLENDET = Array.from({ length: 60 }, (_, i) => {
    const regel = REGELN.filter((r) => r.an)[i % 8];
    const name = `Radio ${silben[(i * 7) % silben.length]} ${80 + ((i * 13) % 28)},${(i * 3) % 10}`;
    const land = { sprache: ["RU", "EG", "TR"][i % 3], tag: "US", stimmen: ["BR", "IN", "MX"][i % 3], werbung: "DE", bewertung: "DE", einzeln: "DE" }[regel.art];
    return { name, land, regel: regel.id, stimmen: (i * 37) % 900 };
  });

  window.RHDaten = { BESTAND, GUETE, LAENDER, FACETTEN, BEWERTUNG_NAMEN, BITRATE_STUFEN, STIMMEN_STUFEN, SENDER, VERLAUF, AEHNLICH, GERAETE, REGELN, REGEL_ARTEN, SPRACHEN, GENRE_REGELN, AUSGEBLENDET };
})();
