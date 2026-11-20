// Wecktöne (RAD-15): jeder Ton lässt sich erzeugen, ist hörbar, übersteuert nicht und klingt bei jedem Erzeugen gleich
import { describe, expect, it } from "vitest";
import { VORGABE, WECKTOENE, wecktonDaten } from "../src/lib/telefon/wecktoene.js";

describe("wecktoene", () => {
  for (const id of WECKTOENE) {
    it(`${id}: hörbar, ohne Übersteuern, gleichbleibend`, () => {
      const d = wecktonDaten(id, 22050);
      expect(d.length).toBeGreaterThan(22050);
      let summe = 0, spitze = 0;
      for (const v of d) { expect(Number.isFinite(v)).toBe(true); summe += v * v; spitze = Math.max(spitze, Math.abs(v)); }
      expect(Math.sqrt(summe / d.length)).toBeGreaterThan(0.02);
      expect(spitze).toBeLessThanOrEqual(0.7001);
      expect(wecktonDaten(id, 22050)).toEqual(d);
    });
  }
  it("unbekannte Kennung: die Vorgabe", () => {
    expect(wecktonDaten("gibt-es-nicht", 22050)).toEqual(wecktonDaten(VORGABE, 22050));
  });
});
