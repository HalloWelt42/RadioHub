// Wache über das Laden der Tonstücke (RAD-130): erst hinter das Stück, hilft das nicht, neu ansetzen; gewöhnliches Laden nie.
import { describe, expect, it } from "vitest";
import { RUHE_MS, Stueckwache, WIEDERHOLT } from "../src/lib/stueckwache.js";

const oft = (w: Stueckwache, nr: number, n: number, ab: number) => Array.from({ length: n }, (_, i) => w.geladen(nr, ab + i * 20)).filter((x) => x !== "weiter");

describe("Stückwache", () => {
  it("lässt gewöhnliches Laden in Ruhe, auch ein einzelnes Wiederholen", () => {
    const w = new Stueckwache();
    for (let nr = 0; nr < 200; nr++) expect(w.geladen(nr, nr * 10)).toBe("weiter");
    expect(oft(w, 500, WIEDERHOLT - 1, 5000)).toEqual([]);
    for (let i = 0; i < 20; i++) expect(w.geladen(501, 10_000 + i * 3000)).toBe("weiter");      // langsam: Netz, keine Schleife
  });
  it("geht bei einer Schleife weiter und setzt beim zweiten Mal neu an", () => {
    const w = new Stueckwache();
    expect(oft(w, 595, 5, 0)).toEqual(["vor"]);
    expect(oft(w, 596, 5, 500)).toEqual(["neu"]);
    expect(oft(w, 700, 5, 500 + RUHE_MS * 2)).toEqual(["vor"]);
  });
});
