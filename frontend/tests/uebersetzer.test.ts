// Übersetzerstimme (RAD-130): die Regeln (Vorlauf, Tempo, Auslassen) und das Spielen mit nachgestelltem Ton.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { naechster, STAU_BIS_S, TEMPO_HOECHSTENS, tempoFuer } from "../src/lib/radio/stimmplan";

const radio = { muted: false, paused: false, currentTime: 0, gespielt: 0, async play() { this.gespielt++; this.paused = false; } };
vi.mock("../src/spieler/tonelement", () => ({ tonelement: () => radio, anhaengen: () => undefined }));
const zustand = { volume: 50, isPlaying: true, isPaused: false };
const tonAuffrischen = vi.fn();
vi.mock("../src/lib/store.svelte.js", () => ({ appState: zustand, actions: {} }));
vi.mock("../src/lib/playerEngine.js", () => ({ tonAuffrischen }));

const absaetze = (...laengen: number[]) => laengen.map((ton_s, i) => ({ nr: i + 1, ton_s, von: i * 30, bis: i * 30 + 30 }));

describe("Plan der Übersetzerstimme", () => {
  it("wartet auf den Vorlauf und spricht danach ohne", () => {
    expect(naechster(absaetze(10), 0, false)).toBeNull();
    expect(naechster(absaetze(22), 0, false)).toEqual({ nr: 1, tempo: 1 });          // ein langer reicht
    expect(naechster(absaetze(10, 8), 0, false)).toEqual({ nr: 1, tempo: 1 });
    expect(naechster(absaetze(10, 8), 1, true)).toEqual({ nr: 2, tempo: 1 });
    expect(naechster(absaetze(10, 8), 2, true)).toBeNull();
    expect(naechster(absaetze(0, 8, 9), 0, false)?.nr).toBe(2);                       // nicht gesprochene bleiben stumm
  });
  it("dauert etwa so lange wie das Original, bei Stau etwas kürzer, nie schneller als die Grenze", () => {
    const a = (ton_s: number, original: number) => ({ nr: 1, ton_s, von: 0, bis: original });
    expect([tempoFuer(a(20, 30), 0), tempoFuer(a(22, 20), 0), tempoFuer(a(40, 20), 0)]).toEqual([1, 1.1, 1.25]);
    expect([tempoFuer(a(20, 20), 50), tempoFuer(a(20, 20), 70)]).toEqual([1.08, 1.15]);
    expect(tempoFuer(a(40, 10), 80)).toBe(TEMPO_HOECHSTENS);
  });
  it("lässt bei zu viel Rückstand die ältesten aus", () => {
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
  beforeEach(() => { vi.useFakeTimers(); vi.stubGlobal("Audio", Ton); Object.assign(radio, { muted: false, paused: false, currentTime: 0, gespielt: 0 }); Object.assign(zustand, { isPlaying: true, isPaused: false }); tonAuffrischen.mockClear(); Ton.alle = []; });
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.resetModules(); });

  async function bau() {
    const { mitlesen } = await import("../src/lib/radio/mitlesen.svelte");
    (await import("../src/lib/stumm")).stummVerbinden(radio);
    const { uebersetzer } = await import("../src/spieler/uebersetzer.svelte");
    mitlesen.uuid = "u";
    const stand = (sprechen: boolean, laeuft = true) => { mitlesen.stand = { laeuft, zustand: "sammelt", grund: "", uuid: "u", name: "", sprache: "en", ziel: "de", uebersetzen: true, sprechen, kann_sprechen: true, ablegen: true, fassung: 1 }; };
    mitlesen.sprechen = async (an: boolean) => stand(an);
    stand(false);
    const bereit = (...l: number[]) => { mitlesen.absaetze = l.map((ton_s, i) => ({ nr: i + 1, von: 0, bis: 1, zeit: "", text: "t", uebersetzung: "ü", ton_s })); };
    return { mitlesen, uebersetzer, stand, bereit };
  }

  it("macht das Radio sofort stumm und gibt es erst beim Ausschalten frei", async () => {
    const { uebersetzer, bereit } = await bau();
    const geschaltet = uebersetzer.schalten(true);
    expect(radio.muted).toBe(true);                              // noch vor der Antwort des Servers und vor dem ersten Absatz
    await geschaltet;
    bereit(12, 11);
    await vi.advanceTimersByTimeAsync(500);
    const ton = Ton.alle[0];
    expect([uebersetzer.spricht, radio.muted, ton.src, ton.volume]).toEqual([1, true, "/api/mitlesen/ton/1", 0.5]);
    ton.ende();
    expect([uebersetzer.spricht, ton.src]).toEqual([2, "/api/mitlesen/ton/2"]);
    await uebersetzer.schalten(false);
    expect([uebersetzer.an, uebersetzer.spricht, radio.muted, ton.paused]).toEqual([false, null, false, true]);
  });

  it("wartet sie auf den nächsten Absatz, bleibt der Sender still, und sie spricht ihn, sobald er da ist", async () => {
    const { uebersetzer, bereit } = await bau();
    await uebersetzer.schalten(true);
    bereit(22);
    await vi.advanceTimersByTimeAsync(500);
    Ton.alle[0].ende();
    await vi.advanceTimersByTimeAsync(90_000);
    expect([radio.muted, uebersetzer.an, uebersetzer.spricht]).toEqual([true, true, null]);
    bereit(22, 5);
    await vi.advanceTimersByTimeAsync(500);
    expect(uebersetzer.spricht).toBe(2);
    await uebersetzer.schalten(false);
    expect(radio.muted).toBe(false);
  });

  it("braucht der Server zum Einschalten länger, bleibt sie an", async () => {
    const { mitlesen, uebersetzer, stand } = await bau();
    mitlesen.sprechen = async (an: boolean) => { await new Promise((r) => setTimeout(r, 3000)); stand(an); };
    const geschaltet = uebersetzer.schalten(true);
    await vi.advanceTimersByTimeAsync(2500);
    expect([uebersetzer.an, radio.muted]).toEqual([true, true]);
    await vi.advanceTimersByTimeAsync(1000);
    await geschaltet;
    expect([uebersetzer.an, radio.muted]).toEqual([true, true]);
    uebersetzer.halt();
  });

  it("nach dem Ausschalten läuft das Original gleich weiter; steht es, setzt die Wiedergabe neu an", async () => {
    const { uebersetzer } = await bau();
    await uebersetzer.schalten(true);
    radio.paused = true;                                          // das Telefon hat es unter der Stimme angehalten
    await uebersetzer.schalten(false);
    expect([radio.muted, radio.paused, radio.gespielt]).toEqual([false, false, 1]);
    radio.currentTime = 2;
    await vi.advanceTimersByTimeAsync(3000);
    expect(tonAuffrischen).not.toHaveBeenCalled();
    await uebersetzer.schalten(true);
    await uebersetzer.schalten(false);
    await vi.advanceTimersByTimeAsync(3000);
    expect(tonAuffrischen).toHaveBeenCalledTimes(1);
    zustand.isPaused = true;                                      // angehalten heißt angehalten
    await uebersetzer.schalten(true);
    await uebersetzer.schalten(false);
    await vi.advanceTimersByTimeAsync(3000);
    expect([tonAuffrischen.mock.calls.length, radio.gespielt]).toEqual([1, 2]);
  });

  it("scheitert das Einschalten, ist der Sender wieder zu hören", async () => {
    const { mitlesen, uebersetzer } = await bau();
    mitlesen.sprechen = async () => { throw new Error("nein"); };
    await expect(uebersetzer.schalten(true)).rejects.toThrow("nein");
    expect([uebersetzer.an, radio.muted]).toEqual([false, false]);
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
