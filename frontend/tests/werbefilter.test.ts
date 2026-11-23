// Werbefilter (RAD-128): Fächer und Reihenfolge der gefundenen Spots, Wege zum Backend.
import { describe, expect, it } from "vitest";
import { fach, geordnet, Werbefilter, type Spotfund } from "../src/lib/radio/werbefilter";

const spot = (id: string, teil: Partial<Spotfund> = {}, treffer = 1, stand: "wirkt" | "vorschlag" = "vorschlag"): Spotfund => ({
  id, quelle: "Sender", herkunft: "lernlauf", dauer_s: 20, angelegt: "2026-11-23T03:00:00", urteil: "offen", werbender: "", text: "", einschaetzung: "",
  quellen: [{ quelle: "u1", name: "Sender", stand, treffer, zuerst: "", zuletzt: "" }], ...teil });

describe("Werbefilter (RAD-128)", () => {
  it("legt Spots ins richtige Fach", () => {
    expect(fach(spot("a"))).toBe("pruefen");
    expect(fach(spot("b", { urteil: "bestaetigt" }, 1, "wirkt"))).toBe("wirkt");
    expect(fach(spot("c", { urteil: "verworfen" }))).toBe("verworfen");
    // angekündigte wirken an ihrem Sender sofort, an einem neuen fragt die Liste
    expect(fach(spot("d", { herkunft: "angabe" }, 1, "wirkt"))).toBe("wirkt");
    expect(fach(spot("e", { herkunft: "angabe" }))).toBe("pruefen");
  });

  it("zeigt zuerst, was am ehesten Werbung ist, dann was öfter lief", () => {
    const spots = [spot("ohne", { einschaetzung: "ohne_sprache" }, 50), spot("eigen", { einschaetzung: "sender" }, 9), spot("werbung1", { einschaetzung: "werbung" }, 2),
      spot("werbung5", { einschaetzung: "werbung" }, 5), spot("neu", {}, 3), spot("weg", { urteil: "verworfen" }, 99)];
    expect(geordnet(spots, "pruefen").map((s) => s.id)).toEqual(["werbung5", "werbung1", "neu", "eigen", "ohne"]);
    expect(geordnet(spots, "verworfen").map((s) => s.id)).toEqual(["weg"]);
  });

  it("spricht die Wege des Backends", async () => {
    const gesehen: string[] = [];
    const w = new Werbefilter((async (weg: string, o: { methode?: string; daten?: unknown } = {}) => {
      gesehen.push(`${o.methode ?? "GET"} ${weg} ${o.daten ? JSON.stringify(o.daten) : ""}`.trim());
      return {};
    }) as never);
    await w.stand();
    await w.stellen({ an: true });
    await w.jetzt(60);
    await w.ausnehmen("u/1", true);
    await w.beurteilen("s1", "verworfen");
    await w.quelle("s1", "u1", "wirkt");
    expect(gesehen).toEqual(["GET /api/werbefilter", 'PUT /api/werbefilter/lernlauf {"an":true}', 'POST /api/werbefilter/lernlauf/jetzt {"minuten":60}',
      'PUT /api/werbefilter/sender/u%2F1 {"aus":true}', 'PUT /api/werbefilter/signaturen/s1 {"urteil":"verworfen"}',
      'PUT /api/werbefilter/signaturen/s1/quellen/u1 {"stand":"wirkt"}']);
    expect(w.tonadresse("s1")).toBe("/api/werbefilter/signaturen/s1/ton");
  });
});
