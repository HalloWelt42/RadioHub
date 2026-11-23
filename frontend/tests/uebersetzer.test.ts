// Übersetzerstimme (RAD-130): die Regeln (Vorlauf, Tempo, Auslassen) und das Spielen mit nachgestelltem Ton.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { naechster, STAU_BIS_S, tempoBei } from "../src/lib/radio/stimmplan";

const radio = { muted: false, paused: false };
vi.mock("../src/spieler/tonelement", () => ({ tonelement: () => radio, anhaengen: () => undefined }));
vi.mock("../src/lib/store.svelte.js", () => ({ appState: { volume: 50 }, actions: {} }));

const absaetze = (...laengen: number[]) => laengen.map((ton_s, i) => ({ nr: i + 1, ton_s }));

describe("Plan der Übersetzerstimme", () => {
  it("wartet auf den Vorlauf und spricht danach ohne", () => {
    expect(naechster(absaetze(10), 0, false)).toBeNull();
    expect(naechster(absaetze(22), 0, false)).toEqual({ nr: 1, tempo: 1 });          // ein langer reicht
    expect(naechster(absaetze(10, 8), 0, false)).toEqual({ nr: 1, tempo: 1 });
    expect(naechster(absaetze(10, 8), 1, true)).toEqual({ nr: 2, tempo: 1 });
    expect(naechster(absaetze(10, 8), 2, true)).toBeNull();
    expect(naechster(absaetze(0, 8, 9), 0, false)?.nr).toBe(2);                       // nicht gesprochene bleiben stumm
  });
  it("wird bei Stau schneller und lässt dann die ältesten aus", () => {
    expect([10, 30, 50, 80].map(tempoBei)).toEqual([1, 1.07, 1.15, 1.25]);
    const s = naechster(absaetze(20, 20, 20, 20, 20), 0, true)!;
    expect(s.nr).toBe(4);
    expect(20 * (5 - s.nr + 1)).toBeLessThanOrEqual(STAU_BIS_S);
  });
});

class Ton {
  static alle: Ton[] = [];
  src = ""; volume = 1; playbackRate = 1; paused = true; preservesPitch = false;
  onended: (() => void) | null = null; onerror: (() => void) | null = null;
  gespielt: string[] = [];
  constructor() { Ton.alle.push(this); }
  async play() { this.paused = false; if (this.gespielt.at(-1) !== this.src) this.gespielt.push(this.src); }
  pause() { this.paused = true; }
  ende() { this.paused = true; this.onended?.(); }
}

describe("Übersetzerstimme", () => {
  beforeEach(() => { vi.useFakeTimers(); vi.stubGlobal("Audio", Ton); Object.assign(radio, { muted: false, paused: false }); Ton.alle = []; });
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.resetModules(); });

  async function bau() {
    const { mitlesen } = await import("../src/lib/radio/mitlesen.svelte");
    (await import("../src/lib/stumm")).stummVerbinden(radio);
    const { uebersetzer } = await import("../src/spieler/uebersetzer.svelte");
    mitlesen.uuid = "u";
    const stand = (sprechen: boolean, laeuft = true) => { mitlesen.stand = { laeuft, zustand: "sammelt", grund: "", uuid: "u", name: "", sprache: "en", ziel: "de", uebersetzen: true, sprechen, kann_sprechen: true, fassung: 1 }; };
    mitlesen.sprechen = async (an: boolean) => stand(an);
    stand(false);
    const bereit = (...l: number[]) => { mitlesen.absaetze = l.map((ton_s, i) => ({ nr: i + 1, von: 0, bis: 1, zeit: "", text: "t", uebersetzung: "ü", ton_s })); };
    return { mitlesen, uebersetzer, stand, bereit };
  }

  it("macht das Radio stumm, solange sie spricht, und gibt es beim Ausschalten sofort frei", async () => {
    const { uebersetzer, bereit } = await bau();
    await uebersetzer.schalten(true);
    expect(radio.muted).toBe(false);                             // noch kein Vorlauf: man hört das Original
    bereit(12, 11);
    await vi.advanceTimersByTimeAsync(500);
    const ton = Ton.alle[0];
    expect([uebersetzer.spricht, radio.muted, ton.src, ton.volume]).toEqual([1, true, "/api/mitlesen/ton/1", 0.5]);
    ton.ende();
    expect([uebersetzer.spricht, ton.src]).toEqual([2, "/api/mitlesen/ton/2"]);
    await uebersetzer.schalten(false);
    expect([uebersetzer.an, uebersetzer.spricht, radio.muted, ton.paused]).toEqual([false, null, false, true]);
  });

  it("hat sie nichts mehr zu sagen, kommt nach kurzer Zeit das Original wieder", async () => {
    const { uebersetzer, bereit } = await bau();
    await uebersetzer.schalten(true);
    bereit(22);
    await vi.advanceTimersByTimeAsync(500);
    Ton.alle[0].ende();
    await vi.advanceTimersByTimeAsync(4000);
    expect(radio.muted).toBe(true);
    await vi.advanceTimersByTimeAsync(3500);
    expect([radio.muted, uebersetzer.an]).toEqual([false, true]);
    await uebersetzer.schalten(false);
  });

  it("Pause am Radio hält sie an, das Ende des Mitlesens schaltet sie aus", async () => {
    const { uebersetzer, bereit, stand } = await bau();
    await uebersetzer.schalten(true);
    bereit(12, 11);
    await vi.advanceTimersByTimeAsync(500);
    radio.paused = true;
    await vi.advanceTimersByTimeAsync(500);
    expect(Ton.alle[0].paused).toBe(true);
    radio.paused = false;
    await vi.advanceTimersByTimeAsync(500);
    expect(Ton.alle[0].paused).toBe(false);
    stand(true, false);
    await vi.advanceTimersByTimeAsync(500);
    expect([uebersetzer.an, radio.muted]).toEqual([false, false]);
  });

  it("stumm bleibt, solange einer es will (Werbung und Übersetzer)", async () => {
    const { stummSetzen, stummVerbinden } = await import("../src/lib/stumm");
    stummVerbinden(radio);
    stummSetzen("werbung", true);
    stummSetzen("uebersetzer", true);
    stummSetzen("uebersetzer", false);
    expect(radio.muted).toBe(true);
    stummSetzen("werbung", false);
    expect(radio.muted).toBe(false);
    radio.muted = true;                                          // von anderswo stumm: wer nichts wollte, schaltet nichts frei
    stummSetzen("werbung", false);
    expect(radio.muted).toBe(true);
  });
});
