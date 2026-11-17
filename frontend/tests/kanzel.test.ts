// Kanzel (RAD-8): Zuordnung Zustand -> Anzeige und Steuerung, Spulzeilen und Stellen der Punktmatrix aus der Breite
import { describe, expect, it } from "vitest";
import { t as uebersetzen } from "../src/lib/i18n.js";
import {
  kanzelAnzeige, kanzelTasten, naechsteReihenfolge, nachbar, positionStand, sekundenHinterLive, zeitversatzStand, zustandVon, type Stand,
} from "../src/spieler/kanzel";
import { stellenFuer } from "../src/spieler/rasterbreite";

const t = (k: string, w?: Record<string, string | number>) => uebersetzen(k, w) as string;
const SENDER = { uuid: "a", name: "Deutschlandfunk Kultur", codec: "mp3", bitrate: 128 };
const HLS = { first_segment: 100, last_segment: 1900, segment_duration: 1, buffered_seconds: 1800, max_segments: 1800 };

function stand(teil: Partial<Stand> = {}): Stand {
  return {
    isPlaying: false, isPaused: false, isRecording: false, playerMode: "none", isLive: true, currentStation: null, currentEpisode: null,
    currentRecording: null, streamTitle: null, streamQuality: null, hlsStatus: null, hlsActive: false, currentSegment: null, recordingElapsed: 0,
    recordingIcyCount: 0, canPlayDirect: true, canPlayHLS: null, playMode: "linear", stations: [], podcastPlaylist: [], currentEpisodeIndex: -1,
    recordingPlaylist: [], medium: "spielt", fehlerCode: null, zeit: 0, dauer: 0, lage: 0, hoerdauer: 0, ...teil,
  };
}
const spielt = (teil: Partial<Stand> = {}) => stand({ isPlaying: true, currentStation: SENDER, playerMode: "direct", ...teil });

describe("Zustand", () => {
  it("leer ohne Quelle oder ohne Wiedergabe", () => {
    expect(zustandVon(stand())).toBe("leer");
    expect(zustandVon(stand({ currentStation: SENDER }))).toBe("leer");
  });
  it("Aufnahme vor allem anderen, dann Fehler, Pause, Laden, Puffern", () => {
    expect(zustandVon(spielt({ isRecording: true, medium: "fehler" }))).toBe("aufnahme");
    expect(zustandVon(spielt({ medium: "fehler", isPaused: true }))).toBe("fehler");
    expect(zustandVon(spielt({ isPaused: true, medium: "laedt" }))).toBe("pause");
    expect(zustandVon(spielt({ medium: "laedt" }))).toBe("laedt");
    expect(zustandVon(spielt({ medium: "puffert" }))).toBe("puffert");
  });
  it("live, Zeitversatz, Podcast, Wiedergabe einer Aufnahme", () => {
    expect(zustandVon(spielt())).toBe("live");
    expect(zustandVon(spielt({ playerMode: "hls", isLive: true }))).toBe("live");
    expect(zustandVon(spielt({ playerMode: "hls", isLive: false }))).toBe("versatz");
    expect(zustandVon(stand({ isPlaying: true, playerMode: "podcast", currentEpisode: { title: "F" } }))).toBe("podcast");
    expect(zustandVon(stand({ isPlaying: true, playerMode: "hls", isLive: false, currentEpisode: { title: "F" } }))).toBe("podcast");
    expect(zustandVon(stand({ isPlaying: true, playerMode: "recording", currentRecording: { name: "R" } }))).toBe("wiedergabe");
  });
});

describe("Anzeige", () => {
  it("leer: keine Matrix, Zeit gestrichelt, keine Zeile", () => {
    const a = kanzelAnzeige(stand(), t);
    expect(a).toMatchObject({ sender: "", titel: null, zeit: "--:--:--", zeile: null, art: "BEREIT", led: { zustand: "aus" } });
  });
  it("Originalstrom: DIREKT, Hördauer, Format aus dem Sender, Titelzeile nur mit Titel", () => {
    const a = kanzelAnzeige(spielt({ hoerdauer: 2537 }), t);
    expect(a).toMatchObject({ quelle: { text: "DIREKT", farbe: "blau" }, zeit: "00:42:17", format: "MP3 128 kbit/s", titel: null, zeile: null, sender: "Deutschlandfunk Kultur" });
    expect(kanzelAnzeige(spielt({ streamTitle: "Crosby, Stills, Nash & Young - Ohio" }), t).titel).toBe("Crosby, Stills, Nash & Young - Ohio");
  });
  it("Zeitversatz: Abstand zu live in Zeit und Statuszeile, Zeile Zeitversatz, gemessenes Format", () => {
    const a = kanzelAnzeige(spielt({ playerMode: "hls", isLive: false, hlsStatus: HLS, currentSegment: 1648,
      streamQuality: { inputCodec: "aac", inputBitrate: 192 } }), t);
    expect(a).toMatchObject({ zustand: "versatz", zeit: "-00:04:12", art: "4:12 HINTER LIVE", quelle: { text: "VERSATZ", farbe: "bernstein" },
      zeile: "zeitversatz", format: "AAC 192 kbit/s", led: { farbe: "bernstein", zustand: "an" } });
  });
  it("Aufnahme: rot blinkend, Dauer, Bitrate mit erkannten Titeln", () => {
    const a = kanzelAnzeige(spielt({ isRecording: true, recordingElapsed: 768, recordingIcyCount: 3, streamQuality: { outputBitrate: 192 } }), t);
    expect(a).toMatchObject({ zustand: "aufnahme", led: { farbe: "rot", zustand: "blinkt" }, zeit: "00:12:48", art: "AUFNAHME 00:12:48",
      quelle: { text: "REC", farbe: "rot" }, format: "192 kbit/s · 3 Titel" });
  });
  it("Podcast: Matrix Podcast, Titel Folge, Position", () => {
    const a = kanzelAnzeige(stand({ isPlaying: true, playerMode: "podcast", zeit: 754, dauer: 2700,
      currentEpisode: { title: "Folge 12", podcast: { title: "15 Minuten" } } }), t);
    expect(a).toMatchObject({ sender: "15 Minuten", titel: "Folge 12", zeit: "00:12:34", zeile: "position", quelle: { text: "PODCAST" } });
  });
  it("Aufnahme abspielen: Herkunft als Quelle", () => {
    const a = kanzelAnzeige(stand({ isPlaying: true, playerMode: "recording", currentRecording: { name: "Mitschnitt", station_name: "DLF", source: "cutter" } }), t);
    expect(a).toMatchObject({ zustand: "wiedergabe", sender: "DLF", titel: "Mitschnitt", quelle: { text: "SCHNITT" }, zeile: "position" });
  });
  it("Fehler je Art, rot getönt", () => {
    expect(kanzelAnzeige(spielt({ medium: "fehler", fehlerCode: 2 }), t)).toMatchObject({ art: "VERBINDUNG VERLOREN", ton: "fehler", zeit: "--:--:--" });
    expect(kanzelAnzeige(spielt({ medium: "fehler", fehlerCode: 3 }), t).art).toBe("NICHT ABSPIELBAR");
    expect(kanzelAnzeige(spielt({ medium: "fehler", fehlerCode: 4 }), t).art).toBe("WIEDERGABEFEHLER");
  });
  it("Quelle passt in 14 Segmente (höchstens 7 Zeichen)", () => {
    for (const s of [stand(), spielt(), spielt({ medium: "laedt" }), spielt({ medium: "puffert" }), spielt({ isPaused: true }),
      spielt({ playerMode: "hls", isLive: false }), spielt({ isRecording: true }), spielt({ medium: "fehler" }),
      stand({ isPlaying: true, playerMode: "recording", currentRecording: { name: "R" } })]) {
      expect(kanzelAnzeige(s, t).quelle.text.length).toBeLessThanOrEqual(7);
    }
  });
});

describe("Steuerung", () => {
  const liste = [{ uuid: "x", name: "Erster" }, SENDER, { uuid: "z", name: "Letzter" }];
  it("Spielen: Symbol je Modus, gesperrt ohne Quelle und während der Aufnahme", () => {
    expect(kanzelTasten(stand(), t).spielen).toMatchObject({ gesperrt: true, symbol: "fa-play", an: false });
    expect(kanzelTasten(spielt(), t).spielen).toMatchObject({ symbol: "fa-stop", an: true });
    expect(kanzelTasten(spielt({ playerMode: "hls" }), t).spielen.symbol).toBe("fa-pause");
    expect(kanzelTasten(spielt({ isPaused: true }), t).spielen).toMatchObject({ symbol: "fa-play", licht: "atmet" });
    expect(kanzelTasten(spielt({ isRecording: true }), t).spielen.gesperrt).toBe(true);
  });
  it("Aufnahme: nur beim spielenden Sender, rot blinkend während sie läuft, Wechsel gesperrt", () => {
    expect(kanzelTasten(spielt(), t).aufnahme.gesperrt).toBe(false);
    expect(kanzelTasten(stand({ isPlaying: true, playerMode: "podcast", currentEpisode: { title: "F" } }), t).aufnahme.gesperrt).toBe(true);
    const rec = kanzelTasten(spielt({ isRecording: true, stations: liste }), t);
    expect(rec.aufnahme).toMatchObject({ an: true, licht: "blinkt" });
    expect(rec.zurueck).toMatchObject({ gesperrt: true, licht: "an" });
    expect(rec.vor.gesperrt).toBe(true);
    expect(rec.stopp.gesperrt).toBe(false);
  });
  it("Zurück und Weiter nennen den Nachbarn, rundum wie der Store", () => {
    const k = kanzelTasten(spielt({ stations: liste }), t);
    expect(k.zurueck.hilfe).toBe("Erster (←)");
    expect(k.vor.hilfe).toBe("Letzter (→)");
    expect(nachbar(spielt({ stations: liste, currentStation: liste[2] }), 1)).toBe("Erster");
    expect(kanzelTasten(spielt(), t).zurueck).toMatchObject({ gesperrt: true, hilfe: "Kein vorheriger Sender" });
  });
  it("Original oder Zeitversatz: immer da, nur wählbar, wenn der andere Modus geht", () => {
    expect(kanzelTasten(stand(), t).modus.gesperrt).toBe(true);
    expect(kanzelTasten(spielt({ canPlayHLS: true }), t).modus).toMatchObject({ gesperrt: false, farbe: "gelb", symbol: "fa-wave-square" });
    expect(kanzelTasten(spielt({ playerMode: "hls" }), t).modus).toMatchObject({ gesperrt: false, farbe: "gruen", symbol: "fa-arrows-rotate" });
    expect(kanzelTasten(spielt({ playerMode: "hls", isRecording: true }), t).modus.gesperrt).toBe(true);
    expect(kanzelTasten(spielt({ playerMode: "hls" }), t, true).modus).toMatchObject({ gesperrt: true, licht: "atmet" });
  });
  it("Reihenfolge: immer da, nur bei Folgen und Aufnahmen, rundum; Weiter gespiegelt bei rückwärts", () => {
    expect(kanzelTasten(spielt(), t).reihenfolge.gesperrt).toBe(true);
    const k = kanzelTasten(stand({ isPlaying: true, playerMode: "podcast", currentEpisode: { title: "F" }, playMode: "reverse" }), t);
    expect(k.reihenfolge).toMatchObject({ gesperrt: false, symbol: "fa-arrow-left", farbe: "bernstein" });
    expect(k.vor.gespiegelt).toBe(true);
    expect(["linear", "reverse", "loop", "shuffle"].map(naechsteReihenfolge)).toEqual(["reverse", "loop", "shuffle", "linear"]);
  });
});

describe("Spulzeilen", () => {
  it("Zeitversatz: Puffer von höchstens, Schritt je Segment im Versatz", () => {
    const z = zeitversatzStand(spielt({ playerMode: "hls", isLive: false, hlsStatus: { ...HLS, buffered_seconds: 900 } }), t);
    expect(z).toMatchObject({ fuellung: 50, bahn: 50, text: "15:00 von 30:00", gesperrt: false, live: false });
    expect(z.schritt).toBeCloseTo(100 / 1800);
    expect(zeitversatzStand(spielt({ playerMode: "hls", isRecording: true, hlsStatus: HLS }), t).gesperrt).toBe(true);
    expect(sekundenHinterLive(HLS, 1900)).toBe(0);
  });
  it("Position: Füllung nach der Lage, gesperrt ohne Dauer", () => {
    expect(positionStand(stand({ zeit: 754, dauer: 2700, lage: 27.9 }), t)).toMatchObject({ fuellung: 27.9, bahn: 100, text: "12:34 von 45:00", gesperrt: false });
    expect(positionStand(stand(), t).gesperrt).toBe(true);
  });
});

describe("Punktmatrix wächst mit der Breite", () => {
  it("mehr Stellen bei mehr Platz, nie unter 10, Zeichenhöhe bleibt", () => {
    expect(stellenFuer(274, 28)).toBe(11);
    expect(stellenFuer(933, 23.8)).toBe(50);
    expect(stellenFuer(120, 24)).toBe(10);
    expect(stellenFuer(0, 24)).toBe(10);
    // Probe: bei der gemeldeten Stellenzahl ist jede Zelle mindestens so hoch wie gewünscht
    for (const b of [300, 520, 777, 1200]) expect((b - 38) / stellenFuer(b, 24) / 0.75).toBeGreaterThanOrEqual(24);
  });
});
