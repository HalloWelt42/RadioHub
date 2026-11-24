// Neues der Abos (RAD-136): Summen über mehrere Abos, am einzelnen nur die jüngste Stufe mit Neuem.
import { describe, expect, it } from "vitest";
import { juengste, neues } from "../src/lib/podcasts/neues";

const A = (heuteUngehoert: number, wocheUngehoert: number, monatUngehoert: number, ungehoert: number) => ({ heuteUngehoert, wocheUngehoert, monatUngehoert, ungehoert });

describe("Neues", () => {
  it("zählt über alle Abos zusammen", () => {
    expect(neues([A(1, 3, 9, 53), A(0, 2, 4, 10)])).toEqual({ tag: 1, woche: 5, monat: 13, ungehoert: 63 });
    expect(neues([])).toEqual({ tag: 0, woche: 0, monat: 0, ungehoert: 0 });
  });
  it("nennt die jüngste Stufe, ohne Neues keine", () => {
    expect([A(1, 3, 9, 53), A(0, 2, 4, 10), A(0, 0, 4, 10), A(0, 0, 0, 10)].map((a) => juengste(neues([a])))).toEqual(["tag", "woche", "monat", null]);
  });
});
