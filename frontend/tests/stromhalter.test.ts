import { describe, expect, it } from "vitest";
import { mediaTyp, STROMHALTER } from "../src/lib/stromhalter.js";

describe("Stromhalter (RAD-84)", () => {
  it("bildet die Inhaltstypen der Sender auf Typen der MediaSource ab", () => {
    expect(mediaTyp("audio/mpeg")).toBe("audio/mpeg");
    expect(mediaTyp("audio/mpeg; charset=utf-8")).toBe("audio/mpeg");
    expect(mediaTyp("Audio/AACP")).toBe("audio/aac");
    expect(mediaTyp("audio/x-aac")).toBe("audio/aac");
    expect(mediaTyp("application/ogg")).toBeNull();
    expect(mediaTyp(null)).toBeNull();
  });
  it("hält mehr Vorrat als der Browser von sich aus (gemessen etwa 2 s) und gibt erst nach mehreren Versuchen auf", () => {
    expect(STROMHALTER.vorlaufS).toBeGreaterThan(2);
    expect(STROMHALTER.startHoechstensS).toBeLessThanOrEqual(STROMHALTER.vorlaufS);
    expect(STROMHALTER.pausenMs.length).toBeGreaterThanOrEqual(3);
  });
});
