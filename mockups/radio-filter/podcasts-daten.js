// Musterdaten des Entwurfs Podcasts (RAD-17): erfundene Abos und Folgen, keine echten Sendungen und keine Marken.
// Längen in Minuten, Stand in Minuten (0: neu), gemerkt: im Gerät (heruntergeladen), Größe in MB.
(() => {
  "use strict";
  const ABOS = [
    { id: "morgen", name: "Morgenlage", autor: "Redaktion Frühdienst", auto: true, beschreibung: "Was der Tag bringt, in zwanzig Minuten." },
    { id: "werkstatt", name: "Werkstattfunk", autor: "Holz und Metall e. V.", auto: false, beschreibung: "Handwerk zum Zuhören: Werkzeuge, Kniffe, Fehler, die man nur einmal macht." },
    { id: "sterne", name: "Sternstunde Physik", autor: "Lehrstuhl am Fluss", auto: true, beschreibung: "Physik ohne Formeln, mit vielen Fragen von Hörern." },
    { id: "kueche", name: "Küchenkunde", autor: "Anna und Ben", auto: false, beschreibung: "Zwei kochen, einer erklärt, warum es klappt." },
    { id: "hoerspiel", name: "Hörspielzeit", autor: "Bühne im Ohr", auto: false, beschreibung: "Kurze Hörspiele, jede Woche ein neues." },
    { id: "zahlen", name: "Zahlenzauber", autor: "Mathe für alle", auto: false, beschreibung: "Rätsel, Tricks und Geschichten aus der Mathematik." },
  ];
  const tag = (vor) => { const d = new Date(2026, 10, 20); d.setDate(d.getDate() - vor); return d; };
  const F = (id, abo, titel, vorTagen, laenge, stand, gemerkt, mb, text) => ({ id, abo, titel, datum: tag(vorTagen), laenge, stand, gemerkt, mb, text });
  const FOLGEN = [
    F("m1", "morgen", "Der Tag: Brückenbau, Bahnstreik und ein Fund im Moor", 0, 21, 0, true, 19, "Die drei Themen des Morgens, dazu das Wetter und ein Blick in die Region."),
    F("m2", "morgen", "Der Tag: Wahlkampfauftakt und neue Mietregeln", 1, 22, 22, true, 20, "Was die neuen Regeln für Mieter heißen, erklärt in fünf Minuten."),
    F("s1", "sterne", "Warum der Himmel nachts dunkel ist", 2, 48, 12, false, 0, "Eine scheinbar einfache Frage, die Astronomen lange beschäftigt hat."),
    F("w1", "werkstatt", "Hobel einstellen, ohne zu fluchen", 3, 36, 0, false, 0, "Messer, Spanöffnung, Klappe: Schritt für Schritt zum feinen Span."),
    F("k1", "kueche", "Brot ohne Kneten", 4, 41, 41, false, 0, "Lange Gare statt Kraft: wie Teig von selbst Struktur bekommt."),
    F("h1", "hoerspiel", "Das Haus am Kanal, Teil 2", 5, 29, 0, true, 27, "Die Tür im Keller ist wieder offen. Wer war zuletzt unten?"),
    F("z1", "zahlen", "Das Geburtstagsrätsel", 6, 25, 9, false, 0, "Ab wie vielen Leuten im Raum teilen sich zwei wahrscheinlich einen Geburtstag?"),
    F("s2", "sterne", "Schwarze Löcher für Anfänger", 9, 52, 52, true, 48, "Was passiert am Ereignishorizont, und was nicht."),
    F("w2", "werkstatt", "Die richtige Säge für jeden Schnitt", 10, 33, 0, false, 0, "Japansäge, Fuchsschwanz, Gestellsäge: wann welche."),
    F("m3", "morgen", "Der Tag: Haushalt beschlossen", 2, 20, 20, false, 0, "Wofür das Geld im nächsten Jahr reicht und wofür nicht."),
    F("k2", "kueche", "Saucen retten", 11, 38, 0, false, 0, "Geronnen, zu dünn, zu salzig: was hilft wirklich."),
    F("h2", "hoerspiel", "Das Haus am Kanal, Teil 1", 12, 31, 31, false, 0, "Ein Erbe, ein altes Haus und ein Schlüssel, der zu keiner Tür passt."),
  ];
  // Treffer der Suche im Verzeichnis (zum Abonnieren); "abo" heißt schon abonniert
  const VERZEICHNIS = [
    { name: "Sternstunde Physik", autor: "Lehrstuhl am Fluss", herkunft: "Verzeichnis A", abo: "sterne" },
    { name: "Sternenstaub", autor: "Planetarium der Stadt", herkunft: "Verzeichnis A" },
    { name: "Sternküche", autor: "Kochschule am Markt", herkunft: "Verzeichnis B" },
    { name: "Unter Sternen", autor: "Nachtwanderer", herkunft: "Verzeichnis B" },
    { name: "Sternzeit Geschichte", autor: "Archiv im Ohr", herkunft: "Verzeichnis A" },
  ];
  window.RHPodcasts = { ABOS, FOLGEN, VERZEICHNIS };
})();
