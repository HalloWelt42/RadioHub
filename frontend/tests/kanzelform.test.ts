// Form der Kanzel aus dem Platzbedarf (RAD-10, RAD-114): eine Reihe, solange alles passt, sonst zwei, sonst schmal
// (Tasten und Gehäuse in festen Spalten), sonst eng (drei Reihen)
import { describe, expect, it } from "vitest";
import { formFuer, type Bedarf } from "../src/spieler/kanzelform";

const basic: Bedarf = { anzeige: 306, zeit: 267, laut: 196, steuerung: 272, teile: [208, 44], luecke: 14 };
const pro: Bedarf = { ...basic, steuerung: 566, teile: [262, 154, 66] };

describe("formFuer", () => {
  it("Basic bleibt bei 1316 Pixeln in einer Reihe, PRO bricht um", () => {
    expect(formFuer(1316 - 56, basic)).toBe("eine");
    expect(formFuer(1316 - 56, pro)).toBe("zwei");
  });
  it("die eine Reihe genau ab dem Bedarf", () => {
    const eine = 306 + 267 + 196 + 272 + 3 * 14;
    expect(formFuer(eine, basic)).toBe("eine");
    expect(formFuer(eine - 1, basic)).toBe("zwei");
  });
  it("schmal, wenn neben Quelle und Zeit Tasten und Gehäuse nicht passen", () => {
    expect(formFuer(267 + 272 + 196 + 2 * 14, basic)).toBe("zwei");
    expect(formFuer(267 + 272 + 196 + 2 * 14 - 1, basic)).toBe("schmal");
  });
  it("eng, wenn auch Quelle und Zeit nicht neben die Tasten passen", () => {
    const schmal = 267 + 262 + 154 + 66 + 3 * 14;
    expect(formFuer(schmal, pro)).toBe("schmal");
    expect(formFuer(schmal - 1, pro)).toBe("eng");
  });
});
