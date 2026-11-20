// Weckton-Spieler (RAD-15): spielt den gewählten Ton mit der Lautstärke des Weckers, immer höchstens einen, ohne Lautsprecher
// geprüft gegen einen nachgebildeten Tonkontext.
import { beforeEach, describe, expect, it, vi } from "vitest";

interface Quelle { buffer: { id: number } | null; loop: boolean; gestartet: boolean; gestoppt: boolean; start(): void; stop(): void; connect(): void }

const kontext = vi.hoisted(() => {
  let puffer = 0;
  const c = {
    sampleRate: 8000,
    state: "running",
    currentTime: 0,
    quellen: [] as Quelle[],
    verstaerker: [] as { gain: { value: number; ziel: number | null; setTargetAtTime(w: number): void } }[],
    erzeugt: 0,
    createBuffer() { c.erzeugt += 1; return { id: ++puffer, copyToChannel() {} }; },
    createGain() {
      const g = { gain: { value: 1, ziel: null as number | null, setTargetAtTime(w: number) { g.gain.ziel = w; } }, connect() {}, disconnect() {} };
      c.verstaerker.push(g);
      return g;
    },
    createBufferSource() {
      const q: Quelle = { buffer: null, loop: false, gestartet: false, gestoppt: false,
        start() { q.gestartet = true; }, stop() { q.gestoppt = true; }, connect() {} };
      c.quellen.push(q);
      return q;
    },
    resume: async () => {},
    destination: {},
  };
  return c;
});
vi.mock("../src/lib/telefon/tonkontext.svelte.js", () => ({ kontext: () => kontext }));

const { wecktonAn, wecktonAus, wecktonVorbereiten, wecktonWaehlen } = await import("../src/lib/telefon/weckton.js");

describe("Weckton-Spieler", () => {
  beforeEach(() => { wecktonAus(); kontext.quellen.length = 0; kontext.verstaerker.length = 0; });

  it("bereitet die Vorgabe immer mit vor und jeden Ton nur einmal", () => {
    const vorher = kontext.erzeugt;
    wecktonVorbereiten(["glocke", "glocke"]);
    wecktonVorbereiten(["glocke"]);
    expect(kontext.erzeugt - vorher).toBeLessThanOrEqual(2);
  });

  it("spielt den gewählten Ton in Schleife mit der Lautstärke des Weckers", () => {
    wecktonWaehlen("harfe", 0.4);
    wecktonAn();
    expect(kontext.quellen).toHaveLength(1);
    expect(kontext.quellen[0].loop && kontext.quellen[0].gestartet).toBe(true);
    expect(kontext.verstaerker[0].gain.value).toBe(0.4);
  });

  it("wechselt beim Wählen eines anderen Tons sofort und lässt nie zwei laufen", () => {
    wecktonWaehlen("glocke", 1);
    wecktonAn();
    const erster = kontext.quellen[0];
    wecktonWaehlen("kuckuck", 1);
    expect(erster.gestoppt).toBe(true);
    expect(kontext.quellen).toHaveLength(2);
    expect(kontext.quellen[1].buffer).not.toBe(erster.buffer);
    expect(kontext.quellen.filter((q) => q.gestartet && !q.gestoppt)).toHaveLength(1);
  });

  it("ändert beim selben Ton nur die Lautstärke", () => {
    wecktonAn("sanft", 0.5);
    wecktonAn("sanft", 0.8);
    expect(kontext.quellen).toHaveLength(1);
    expect(kontext.verstaerker[0].gain.ziel).toBe(0.8);
  });

  it("nimmt für eine unbekannte Kennung die Vorgabe", () => {
    wecktonAn("doppelpiep", 1);
    const vorgabe = kontext.quellen[0].buffer;
    wecktonAus();
    wecktonWaehlen("gibtsnicht", 1);
    wecktonAn();
    expect(kontext.quellen[1].buffer).toBe(vorgabe);
  });

  it("schweigt nach Aus", () => {
    wecktonAn("digital", 1);
    wecktonAus();
    expect(kontext.quellen[0].gestoppt).toBe(true);
  });
});
