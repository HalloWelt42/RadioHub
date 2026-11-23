// Transkript einer Folge (RAD-22): der Absatz an der Stelle, Transkribieren mit Fortschritt bis zum Text, Fehler bleiben sichtbar.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { absatzBei, Folgentext, type Transkriptstand } from "../src/lib/podcasts/transkript.svelte";

const A = [{ nr: 0, von: 2, bis: 9, text: "Eins", sprecher: "" }, { nr: 1, von: 12, bis: 20, text: "Zwei", sprecher: "" }];
const stand = (t: Partial<Transkriptstand> = {}): Transkriptstand => ({ transkript: null, lauf: null, fehler: "", kann_transkribieren: true, ...t });

describe("Absatz an der Stelle", () => {
  it("der laufende, in einer Pause der vorige, davor keiner", () => {
    expect([0, 1.9, 5, 10, 12, 99].map((s) => absatzBei(A, s))).toEqual([null, 0, 0, 0, 1, 1]);
    expect(absatzBei([], 3)).toBeNull();
  });
});

describe("Folgentext", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it("folgt dem Lauf, bis der Text da ist, und fragt danach nicht weiter", async () => {
    const wege: string[] = [];
    const antworten = [stand(), stand({ lauf: { id: "x", fortschritt: null, schritt: "wartet" } }), stand({ lauf: { id: "x", fortschritt: 0.5, schritt: "" } }),
      stand({ transkript: { herkunft: "gehoert", sprache: "de", absaetze: A } })];
    const a = (async (weg: string, o: { methode?: string } = {}) => { wege.push(`${o.methode ?? "GET"} ${weg}`); return antworten.shift()!; }) as never;
    const x = new Folgentext(7, a);
    await x.laden();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(wege).toEqual(["GET /api/podcasts/episodes/7/transkript"]);
    await x.transkribieren();
    await vi.advanceTimersByTimeAsync(3000);
    expect(x.stand?.lauf?.fortschritt).toBe(0.5);
    await vi.advanceTimersByTimeAsync(3000);
    expect(x.stand?.transkript?.absaetze.length).toBe(2);
    await vi.advanceTimersByTimeAsync(30_000);
    expect(wege.length).toBe(4);
  });

  it("zeigt Fehler, und nach dem Schließen kommt nichts mehr", async () => {
    const x = new Folgentext(7, (async () => { throw new Error("weg"); }) as never);
    await x.laden();
    expect(x.fehler).toBe("weg");
    let n = 0;
    const y = new Folgentext(7, (async () => { n++; return stand({ lauf: { id: "x", fortschritt: null, schritt: "" } }); }) as never);
    await y.laden();
    y.beenden();
    await vi.advanceTimersByTimeAsync(20_000);
    expect(n).toBe(1);
  });
});
