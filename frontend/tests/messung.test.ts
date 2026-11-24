// Messmodus (RAD-143): ein Zittern wird ein Ereignis je Sekunde, Stocken bekommt seine Dauer, nichts geht beim Senden verloren.
import { describe, expect, it } from "vitest";
import { HOECHSTENS, JE_SENDUNG, Messsammler, tonlage, type Tonlage } from "../src/lib/messung";

const lage = (zeit: number): Tonlage => ({ zeit, vorrat: 5, hinten: 8, stumm: false });

describe("Messsammler", () => {
  it("fasst je Sekunde zusammen: tausend Sprünge werden ein Ereignis", () => {
    const s = new Messsammler();
    for (let i = 0; i < 1000; i++) { s.ton("seeking", i * 0.9, lage(9)); s.ton("playing", i * 0.9, lage(9)); }
    s.ton("pause", 5000, lage(10));
    const [erstes, zweites] = s.nehmen();
    expect(erstes).toMatchObject({ art: "ton", werte: { anzahl: 2000, ereignisse: { seeking: 1000, playing: 1000 } } });
    expect(zweites.werte.ereignisse).toEqual({ pause: 1 });
  });
  it("misst, wie lange der Ton stockt", () => {
    const s = new Messsammler();
    s.ton("waiting", 1000, lage(20));
    s.ton("waiting", 1500, lage(20));
    s.ton("playing", 3250, lage(20));
    expect(s.nehmen().find((e) => e.art === "gestockt")?.werte).toMatchObject({ dauer_s: 2.25, ende: "playing", zeit: 20 });
  });
  it("sendet in Teilen, und Gescheitertes kommt wieder nach vorn", () => {
    const s = new Messsammler();
    for (let i = 0; i < HOECHSTENS + 10; i++) s.merken("zustand", { i });
    const teil = s.nehmen();
    expect(teil).toHaveLength(JE_SENDUNG);
    s.zurueck(teil);
    expect(s.nehmen()[0].werte.i).toBe(0);
  });
  it("gleiche Zustände nur einmal, mit der Zeit des Geschehens", () => {
    let uhr = 1000;
    const s = new Messsammler(() => uhr);
    s.geaendert("zustand", { live: true });
    uhr = 2000;
    s.geaendert("zustand", { live: true });
    s.geaendert("zustand", { live: false });
    expect(s.nehmen().map((e) => [e.um, e.werte.live])).toEqual([[1000, true], [2000, false]]);
  });
  it("Lage des Tonelements: Vorrat und Abstand zum Ende", () => {
    const bereich = (von: number, bis: number) => ({ length: 1, start: () => von, end: () => bis });
    expect(tonlage({ currentTime: 12, buffered: bereich(0, 20.5), seekable: bereich(0, 30), muted: true } as never)).toEqual({ zeit: 12, vorrat: 8.5, hinten: 18, stumm: true });
  });
});
