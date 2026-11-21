// Werbung im Radio (RAD-33): wo die Wiedergabe nach einem Spot beim Verbinden beginnt, was an einer Stelle des Tons zu
// tun ist (springen, wenn das Ende im Puffer liegt, sonst stumm), Marken auf dem Balken des Zeitversatzes, die Kanzel
// in Bernstein und die Umrechnung zwischen Puffer und Tonelement über die Fragmente der Wiedergabeliste.
import { describe, expect, it, vi } from "vitest";

// die Engine braucht für die Umrechnung weder Netz noch hls.js
vi.mock("hls.js", () => ({ default: class {} }));
vi.mock("../src/lib/api.js", () => ({ api: {} }));
import { t as uebersetzen } from "../src/lib/i18n.js";
import { pufferZuTon, tonZuPuffer } from "../src/lib/playerEngine.js";
import { haeufigste, nachWerbenden, startwahl, stellenSchluessel, werbetat, type Pufferstand, type Werbestelle } from "../src/lib/radio/sendewerbung";
import { kanzelAnzeige, pufferMarken, type Stand } from "../src/spieler/kanzel";

const t = (k: string, w?: Record<string, string | number>) => uebersetzen(k, w) as string;

const stelle = (teil: Partial<Werbestelle> = {}): Werbestelle => ({
  von: 0, bis: 15.05, von_aus: "verbinden", bis_aus: "stille", format: "adswizz", kennung: "198927", werbender: "",
  titel: "", angekuendigt_ms: 15046, beim_verbinden: true, ...teil,
});
const puffer = (teil: Partial<Pufferstand> = {}): Pufferstand => ({
  segment_count: 10, segment_duration: 1, last_segment: 9, werbestellen: [], werbung_ueberspringen: true, ...teil,
});

describe("Start nach dem Spot beim Verbinden", () => {
  it("wartet auf genug Stücke", () => {
    expect(startwahl(puffer({ segment_count: 2 }))).toEqual({ art: "warten" });
  });
  it("ohne Spot an der Live-Kante", () => {
    expect(startwahl(puffer())).toEqual({ art: "start", sekunde: null });
  });
  it("mit Spot: wartet mit Restzeit, bis sein Ende samt Vorlauf im Puffer liegt, dann ab seinem Ende", () => {
    const spot = stelle();
    expect(startwahl(puffer({ werbestellen: [spot], last_segment: 9 }))).toEqual({ art: "werbung", stelle: spot, rest: 5.05 });
    expect(startwahl(puffer({ werbestellen: [spot], last_segment: 16 }))).toEqual({ art: "start", sekunde: 15.05 });
  });
  it("Ende noch offen: Restzeit unbekannt", () => {
    const spot = stelle({ bis: null, format: "titel", angekuendigt_ms: null });
    expect(startwahl(puffer({ werbestellen: [spot], last_segment: 40 }))).toEqual({ art: "werbung", stelle: spot, rest: null });
  });
  it("gilt nicht, wenn das Überspringen für den Sender aus ist", () => {
    expect(startwahl(puffer({ werbestellen: [stelle()], werbung_ueberspringen: false }))).toEqual({ art: "start", sekunde: null });
  });
});

describe("An einer Stelle des Tons", () => {
  const im = stelle({ von: 82.4, bis: 102.45, beim_verbinden: false, format: "creative", kennung: "196022", werbender: "adac.de" });
  const nie = () => false;
  it("springt, wenn das Ende schon im Puffer liegt", () => {
    expect(werbetat(85, puffer({ werbestellen: [im], last_segment: 300 }), nie)).toEqual({ art: "springen", stelle: im, nach: 102.45 });
  });
  it("stumm mit Restzeit, wenn das Ende noch nicht im Puffer liegt (live)", () => {
    expect(werbetat(90, puffer({ werbestellen: [im], last_segment: 95 }), nie)).toEqual({ art: "stumm", stelle: im, rest: 12.45 });
    const offen = { ...im, bis: null };
    expect(werbetat(90, puffer({ werbestellen: [offen], last_segment: 95 }), nie)).toEqual({ art: "stumm", stelle: offen, rest: null });
  });
  it("nichts außerhalb, kurz vor dem Ende, bei angehörten Stellen und wenn es aus ist", () => {
    const p = puffer({ werbestellen: [im], last_segment: 300 });
    expect(werbetat(80, p, nie).art).toBe("nichts");
    expect(werbetat(102.2, p, nie).art).toBe("nichts");
    expect(werbetat(85, p, (s) => stellenSchluessel(s) === "creative:196022@82").art).toBe("nichts");
    expect(werbetat(85, { ...p, werbung_ueberspringen: false }, nie).art).toBe("nichts");
  });
});

describe("Puffer und Tonelement", () => {
  // Fragmente wie hls.js sie führt: Nummer des Stücks und Zeit im Tonelement (die Wiedergabe begann bei Stück 100)
  const fragmente = [100, 101, 102, 103].map((sn, i) => ({ sn, start: 4 + i * 1.0, duration: 1.0 }));
  it("rechnet über das passende Fragment hin und zurück", () => {
    expect(pufferZuTon(102.25, fragmente)).toBeCloseTo(6.25);
    expect(tonZuPuffer(6.25, fragmente)).toBeCloseTo(102.25);
    expect(pufferZuTon(5, [])).toBeNull();
  });
});

describe("Kanzel und Balken", () => {
  const SENDER = { uuid: "a", name: "Hit Radio FFH", codec: "mp3", bitrate: 128 };
  const stand = (teil: Partial<Stand> = {}): Stand => ({
    isPlaying: true, isPaused: false, isRecording: false, playerMode: "hls", isLive: true, currentStation: SENDER, currentEpisode: null,
    currentRecording: null, streamTitle: "Lied", streamQuality: null, hlsStatus: { first_segment: 0, last_segment: 599, segment_duration: 1, buffered_seconds: 600, max_segments: 1200 },
    hlsActive: true, currentSegment: 599, recordingElapsed: 0, recordingIcyCount: 0, canPlayDirect: true, canPlayHLS: true, playMode: "linear",
    stations: [], podcastPlaylist: [], currentEpisodeIndex: -1, recordingPlaylist: [], medium: "spielt", fehlerCode: null, zeit: 0, dauer: 0,
    lage: 0, hoerdauer: 42, ...teil,
  });
  it("Spot beim Verbinden: bernstein, Restzeit statt Titel, Zeit rückwärts", () => {
    const a = kanzelAnzeige(stand({ medium: "laedt", werbung: { art: "verbinden", rest: 12 } }), t);
    expect([a.ton, a.art, a.quelle.text, a.quelle.farbe, a.zeit]).toEqual(["werbung", "WERBUNG BEIM VERBINDEN", "WERBUNG", "bernstein", "-00:00:12"]);
    expect(a.titel).toBe("Wiedergabe beginnt nach dem Spot, noch 0:12");
  });
  it("live stumm: bernstein, Restzeit, Zeit läuft weiter", () => {
    const a = kanzelAnzeige(stand({ werbung: { art: "stumm", rest: null } }), t);
    expect([a.ton, a.art, a.titel, a.zeit]).toEqual(["werbung", "WERBUNG, STUMM", "Werbung läuft, stumm noch --", "00:00:42"]);
  });
  it("ohne Werbung wie bisher", () => {
    expect(kanzelAnzeige(stand(), t).ton).toBe("");
  });
  it("Marken im Maßstab des größten Puffers; laufende Stelle bis zur Live-Kante", () => {
    const hls = { first_segment: 0, last_segment: 599, segment_duration: 1, buffered_seconds: 600, max_segments: 1200,
                  werbestellen: [{ von: 60, bis: 72 }, { von: 590, bis: null }] };
    expect(pufferMarken(stand({ hlsStatus: hls }))).toEqual([{ von: 5, breite: 1 }, { von: 590 / 12, breite: 10 / 12 }]);
  });
});

describe("Steckbrief: Spots nach Werbenden (RAD-35)", () => {
  const spot = (werbender: string, kennung: string, anzahl: number, zuletzt: string, beim_verbinden = false) =>
    ({ format: werbender ? "creative" : "adswizz", kennung, werbender, titel: "", dauer_ms: 15000, beim_verbinden, anzahl, zuerst: zuletzt, zuletzt });
  it("fasst zusammen, die häufigsten zuerst, mit beim Verbinden und zuletzt", () => {
    const g = nachWerbenden([
      spot("werkzeugladen.de", "1", 2, "2026-11-20 10:00:00"), spot("autoglas.de", "2", 5, "2026-11-21 09:00:00", true),
      spot("werkzeugladen.de", "3", 6, "2026-11-21 11:00:00"), spot("autoglas.de", "4", 1, "2026-11-19 08:00:00"),
    ]);
    expect(g.map((x) => [x.name, x.mal, x.spots.length, x.beimVerbinden, x.zuletzt])).toEqual([
      ["werkzeugladen.de", 8, 2, false, "2026-11-21 11:00:00"], ["autoglas.de", 6, 2, true, "2026-11-21 09:00:00"]]);
    expect(g[0].spots.map((s) => s.kennung)).toEqual(["3", "1"]);                     // der häufigste Spot zuerst
  });
  it("Spots ohne Werbenden bleiben je Kennung für sich", () => {
    expect(nachWerbenden([spot("", "198927", 1, "a"), spot("", "195341", 2, "b")]).map((x) => [x.name, x.kennung])).toEqual([["", "195341"], ["", "198927"]]);
  });
});

describe("Werbelisten: Bildlauf und Grenze (Nutzer 21.11.2026)", () => {
  it("bis fünf Einträge ohne Bildlauf, ab sechs mit, höchstens die 40 häufigsten", () => {
    const n = (k: number) => Array.from({ length: k }, (_, i) => i);
    expect(haeufigste(n(5))).toEqual({ zeigen: n(5), weggelassen: 0, rollt: false });
    expect(haeufigste(n(6)).rollt).toBe(true);
    const lang = haeufigste(n(57));
    expect([lang.zeigen.length, lang.zeigen[39], lang.weggelassen, lang.rollt]).toEqual([40, 39, 17, true]);
  });
});
