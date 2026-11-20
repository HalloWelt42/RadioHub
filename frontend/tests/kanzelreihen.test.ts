// Reihen der Kanzel aus dem Platzbedarf (RAD-10): eine Reihe, solange alles passt, sonst zwei, sonst drei
import { describe, expect, it } from "vitest";
import { reihenFuer, type Bedarf } from "../src/spieler/kanzelreihen";

const basic: Bedarf = { anzeige: 306, zeit: 267, laut: 196, steuerung: 272, luecke: 14 };
const pro: Bedarf = { ...basic, steuerung: 566 };

describe("reihenFuer", () => {
  it("Basic bleibt bei 1316 Pixeln in einer Reihe, PRO bricht um", () => {
    expect(reihenFuer(1316 - 56, basic)).toBe(1);
    expect(reihenFuer(1316 - 56, pro)).toBe(2);
  });
  it("die eine Reihe genau ab dem Bedarf", () => {
    const eine = 306 + 267 + 196 + 272 + 3 * 14;
    expect(reihenFuer(eine, basic)).toBe(1);
    expect(reihenFuer(eine - 1, basic)).toBe(2);
  });
  it("drei Reihen, wenn neben Quelle und Zeit die Tasten nicht passen", () => {
    expect(reihenFuer(267 + 272 + 196 + 2 * 14, basic)).toBe(2);
    expect(reihenFuer(267 + 272 + 196 + 2 * 14 - 1, basic)).toBe(3);
  });
});
