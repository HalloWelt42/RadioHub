// Werbefilter (RAD-128): Listen, die stückweise laden, und die Wege zum Backend.
import { describe, expect, it } from "vitest";
import { Stueckliste, Werbefilter } from "../src/lib/radio/werbefilter.svelte";

const bestand = (n: number) => Array.from({ length: n }, (_, i) => ({ id: `s${i}` }));

describe("Werbefilter (RAD-128)", () => {
  it("lädt stückweise bis zum Ende, ohne Doppel", async () => {
    let alle = bestand(60);
    const l = new Stueckliste(async (ab, anzahl) => ({ eintraege: alle.slice(ab, ab + anzahl), gesamt: alle.length }), (e) => e.id);
    await l.neu();
    expect([l.eintraege.length, l.gesamt]).toEqual([25, 60]);
    alle = [{ id: "neu" }, ...alle];                          // vorn kam eins dazu, alles rutscht um eins
    await l.mehr();
    expect(l.eintraege.length).toBe(49);
    await l.mehr();
    await l.mehr();
    expect(new Set(l.eintraege.map((e) => e.id)).size).toBe(l.eintraege.length);
    const vorher = l.eintraege.length;
    await l.mehr();                                           // zu Ende: nichts mehr holen, auch wenn eins fehlt
    expect(l.eintraege.length).toBe(vorher);
  });

  it("zeigt nach einer Änderung wieder so viele wie vorher und ab 'wechsel' von vorn", async () => {
    let alle = bestand(60);
    const l = new Stueckliste(async (ab, anzahl) => ({ eintraege: alle.slice(ab, ab + anzahl), gesamt: alle.length }), (e) => e.id);
    await l.neu();
    await l.mehr();
    alle = alle.slice(1);
    await l.neu();
    expect([l.eintraege.length, l.eintraege[0].id, l.gesamt]).toEqual([50, "s1", 59]);
    await l.wechsel();
    expect(l.eintraege.length).toBe(25);
    l.ersetzen({ id: "s3" });
    expect(l.eintraege.length).toBe(25);
  });

  it("eine überholte Antwort gilt nicht, ein Fehler steht da", async () => {
    const warten: ((r: { eintraege: { id: string }[]; gesamt: number }) => void)[] = [];
    const l = new Stueckliste<{ id: string }>(() => new Promise((fertig) => warten.push(fertig)), (e) => e.id);
    const erst = l.neu();
    const dann = l.wechsel();
    warten[1]({ eintraege: [{ id: "b" }], gesamt: 1 });
    await dann;
    warten[0]({ eintraege: [{ id: "a" }], gesamt: 1 });
    await erst;
    expect(l.eintraege.map((e) => e.id)).toEqual(["b"]);
    const k = new Stueckliste<{ id: string }>(() => Promise.reject(new Error("weg")), (e) => e.id);
    await k.neu();
    expect([k.fehler, k.laedt]).toEqual(["weg", false]);
  });

  it("spricht die Wege des Backends", async () => {
    const gesehen: string[] = [];
    const w = new Werbefilter((async (weg: string, o: { methode?: string; daten?: unknown } = {}) => {
      gesehen.push(`${o.methode ?? "GET"} ${weg} ${o.daten ? JSON.stringify(o.daten) : ""}`.trim());
      return {};
    }) as never);
    await w.stand();
    await w.stellen({ an: true });
    await w.spots("pruefen", 25, 25);
    await w.sender(0, 25);
    await w.jetzt(60);
    await w.ausnehmen("u/1", true);
    await w.beurteilen("s1", "verworfen");
    await w.quelle("s1", "u1", "wirkt");
    expect(gesehen).toEqual(["GET /api/werbefilter", 'PUT /api/werbefilter/lernlauf {"an":true}', "GET /api/werbefilter/spots/pruefen?ab=25&anzahl=25", "GET /api/werbefilter/sender?ab=0&anzahl=25", 'POST /api/werbefilter/lernlauf/jetzt {"minuten":60}',
      'PUT /api/werbefilter/sender/u%2F1 {"aus":true}', 'PUT /api/werbefilter/signaturen/s1 {"urteil":"verworfen"}',
      'PUT /api/werbefilter/signaturen/s1/quellen/u1 {"stand":"wirkt"}']);
    expect(w.tonadresse("s1")).toBe("/api/werbefilter/signaturen/s1/ton");
  });
});
