// Musterdaten des Entwurfs Aufnahmen und Schnitt (RAD-17): erfundene Sender, Titel und Ordner, keine echten Sendungen.
// Zeiten in Sekunden, Größen in MB.
(() => {
  "use strict";
  const ORDNER = [
    { id: "jazz", name: "Jazz", ziel: true },
    { id: "hoerspiel", name: "Hörspiele", ziel: false },
    { id: "nachrichten", name: "Nachrichten", ziel: false },
  ];
  const T = (titel, dauer) => ({ titel, dauer });
  const S = (id, sender, ordner, datum, art, codec, kbit, titel, extra = {}) => {
    let t = 0;
    const liste = titel.map((x, i) => { const z = { nr: i + 1, titel: x.titel, start: t, dauer: x.dauer, mb: +(x.dauer * kbit / 8 / 1024).toFixed(1) }; t += x.dauer; return z; });
    return { id, sender, ordner, datum: new Date(datum), art, codec, kbit, titel: liste, dauer: t, mb: +liste.reduce((s, x) => s + x.mb, 0).toFixed(1), luecken: 0, ...extra };
  };
  const SITZUNGEN = [
    S("s1", "Jazzkeller FM", "jazz", "2026-11-21T20:14:03", "puffer", "AAC", 256, [
      T("Ansage: Abend im Keller", 42), T("Blaue Stunde am Hafen", 412), T("Drei Schritte zurück", 305), T("Werbung", 64),
      T("Nachtfalter", 388), T("Regen auf Blech", 271), T("Abmoderation", 55)], { luecken: 0, titelwechsel: 7 }),
    S("s2", "Hörspielbühne", "hoerspiel", "2026-11-20T21:00:00", "direkt", "MP3", 192, [T("Teil 1", 3122)], { titelwechsel: 4 }),
    S("s3", "Nachrichten Nord", "nachrichten", "2026-11-20T07:00:02", "direkt", "MP3", 128, [T("Nachrichten 7 Uhr", 312), T("Wetter und Verkehr", 96)]),
    S("s4", "Klassik am Morgen", null, "2026-11-19T08:30:00", "puffer", "AAC", 320, [T("Sonate in drei Sätzen", 1260), T("Kleine Nachtmusik für Bläser", 840)], { luecken: 2 }),
    S("s5", "Jazzkeller FM", "jazz", "2026-11-18T22:05:41", "direkt", "MP3", 256, [T("Kontrabass allein", 501), T("Zwischen den Takten", 433)], { abgebrochen: true }),
  ];
  // läuft gerade (Zustand "Aufnahme läuft")
  const LAEUFT = { sender: "Jazzkeller FM", start: "22:41:07", sekunden: 754, kbit: 256, codec: "AAC", art: "puffer", rueckblick: 5,
    titel: [["22:36:07", "Rückblick: Nachtfalter (Schluss)"], ["22:37:52", "Ansage"], ["22:38:30", "Ein Lied für Ida"], ["22:44:10", "Werbung", true], ["22:45:12", "Glas und Messing"]] };

  // Ausschnitt der Kellerwolke (Zustand "Kellerwolke"): Ordner und Audiodateien; nur Audio wird gezeigt
  const WOLKE = {
    "": { ordner: ["Apps", "Musik", "Interviews", "Sprachnotizen"], dateien: [] },
    "Interviews": { ordner: ["2025"], dateien: [
      ["Gespräch Werkstatt Teil 1.mp3", 2410, 33.1, "2026-10-02"], ["Gespräch Werkstatt Teil 2.mp3", 1980, 27.2, "2026-10-02"],
      ["Interview Bürgerhaus.m4a", 3540, 51.0, "2026-09-14"], ["Probe Mikrofon.wav", 64, 11.3, "2026-09-14"]] },
    "Interviews/2025": { ordner: [], dateien: [["Jahresrückblick.mp3", 1820, 25.0, "2025-12-28"]] },
    "Musik": { ordner: ["Eigene Aufnahmen"], dateien: [["Probe Klavier.flac", 245, 28.4, "2026-08-01"]] },
  };

  window.RHAufnahmen = { ORDNER, SITZUNGEN, LAEUFT, WOLKE, FREI_GB: 412, DATEIEN: 1832 };
})();
