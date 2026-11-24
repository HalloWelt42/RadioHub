// Vertonte Fassungen einer Folge (RAD-26): vertonen mit Fortschritt, Wahl, Fehler; die Wiedergabe nimmt die gewählte Fassung.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Folgenfassung, type Fassungsstand } from "../src/lib/podcasts/fassung.svelte";

vi.stubGlobal("window", globalThis.window ?? {});
const { ueberBackend } = await import("../src/lib/wiedergabeweg.js");

const stand = (t: Partial<Fassungsstand> = {}): Fassungsstand =>
  ({ fassungen: [], gewaehlt: "", ziel: "de", zielname: "Deutsch", lauf: null, fehler: "", kann_vertonen: true, ...t });
const DE = { sprache: "de", name: "Deutsch", stimme: "katalog:sohee" };

describe("Folgenfassung", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it("folgt dem Lauf bis zur Fassung und wählt danach", async () => {
    const wege: string[] = [];
    const antworten = [stand(), stand({ lauf: { id: "x", fortschritt: 0.2, schritt: "Übersetzen" } }), stand({ fassungen: [DE], gewaehlt: "de" }),
      stand({ fassungen: [DE], gewaehlt: "" })];
    const a = (async (weg: string, o: { methode?: string; daten?: unknown } = {}) => {
      wege.push([o.methode ?? "GET", weg, o.daten ? JSON.stringify(o.daten) : ""].join(" ").trim());
      return antworten.shift()!;
    }) as never;
    const x = new Folgenfassung(7, a);
    await x.laden();
    expect(x.stand?.fassungen).toEqual([]);
    await x.vertonen();
    expect(x.stand?.lauf?.schritt).toBe("Übersetzen");
    await vi.advanceTimersByTimeAsync(5000);
    expect([x.stand?.fassungen.length, x.stand?.gewaehlt]).toEqual([1, "de"]);
    expect(await x.waehlen("")).toBe(true);
    await vi.advanceTimersByTimeAsync(30_000);
    expect(wege).toEqual(["GET /api/podcasts/episodes/7/vertonung", "POST /api/podcasts/episodes/7/vertonung",
      "GET /api/podcasts/episodes/7/vertonung", 'PUT /api/podcasts/episodes/7/fassung {"sprache":""}']);
  });

  it("eine gescheiterte Wahl gilt nicht", async () => {
    const x = new Folgenfassung(7, (async (_w: string, o: { methode?: string } = {}) => { if (o.methode) throw new Error("weg"); return stand(); }) as never);
    await x.laden();
    expect(await x.waehlen("de")).toBe(false);
    expect(x.fehler).toBe("weg");
  });
});

describe("Adresse der Folge", () => {
  const adresse = (folge: object) => new URL(ueberBackend.folge!.adresse(folge as never), "http://app.test").pathname + new URL(ueberBackend.folge!.adresse(folge as never), "http://app.test").search;
  it("die Fassung geht vor, sonst gespeichert oder durchgeleitet", () => {
    expect(adresse({ id: 7, is_downloaded: 0 })).toBe("/api/podcasts/episodes/7/stream");
    expect(adresse({ id: 7, is_downloaded: 1, fassung: "" })).toBe("/api/podcasts/episodes/7/play");
    expect(adresse({ id: 7, is_downloaded: 0, fassung: "de" })).toBe("/api/podcasts/episodes/7/play?fassung=de");
  });
});
