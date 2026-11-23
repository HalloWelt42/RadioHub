// Live mitlesen (RAD-129): Sprache aus dem Label, Absätze einsortieren, Text zum Kopieren, Ablauf mit nachgestelltem Server.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { alsText, Mitlesen, spracheVon, zusammen, type Absatz, type Mitlesestand } from "../src/lib/radio/mitlesen.svelte";

const absatz = (nr: number, text = `Text ${nr}.`, uebersetzung = ""): Absatz => ({ nr, von: nr, bis: nr + 1, zeit: `2026-11-23T18:00:0${nr}+01:00`, text, uebersetzung, ton_s: 0 });
const stand = (teil: Partial<Mitlesestand> = {}): Mitlesestand => ({ laeuft: true, zustand: "sammelt", grund: "", uuid: "u", name: "S", sprache: "en", ziel: "de", uebersetzen: true, sprechen: false, kann_sprechen: true, absaetze: [], fassung: 0, ...teil });

describe("Mitlesen (RAD-129)", () => {
  beforeEach(() => void vi.useFakeTimers());
  afterEach(() => void vi.useRealTimers());

  it("nimmt die Sprache nur von einem eindeutigen Label", () => {
    expect(spracheVon([{ schluessel: "fr" }])).toBe("fr");
    expect(spracheVon([])).toBe("");
    expect(spracheVon([{ schluessel: "de" }, { schluessel: "tr" }])).toBe("");
    expect(spracheVon([{ schluessel: "frei:klingonisch" }])).toBe("");
  });

  it("sortiert ein und ersetzt, wenn die Übersetzung nachkommt", () => {
    const l = zusammen([absatz(1), absatz(2)], [absatz(3), absatz(2, "Text 2.", "Satz 2.")]);
    expect(l.map((a) => [a.nr, a.uebersetzung])).toEqual([[1, ""], [2, "Satz 2."], [3, ""]]);
    expect(alsText(l.slice(1, 2), true)).toBe("18:00:02  Text 2.\nSatz 2.");
    expect(alsText(l.slice(1, 2), false)).toBe("18:00:02  Text 2.");
  });

  it("übersetzt fremde Sender von Anfang an, eigene nicht, und fragt nur, was neu ist", async () => {
    const wege: string[] = [];
    let antwort = stand();
    const m = new Mitlesen((async (weg: string, o: { methode?: string; daten?: unknown } = {}) => {
      wege.push(`${o.methode ?? "GET"} ${weg} ${o.daten ? JSON.stringify(o.daten) : ""}`.trim());
      return antwort;
    }) as never);
    await m.starten("u", [{ schluessel: "en", name: "Englisch" } as never]);
    expect(wege[0]).toBe('POST /api/mitlesen {"uuid":"u","sprache":"en","ziel":"de","uebersetzen":true}');
    antwort = stand({ absaetze: [absatz(1)], fassung: 4 });
    await vi.advanceTimersByTimeAsync(2100);
    await vi.advanceTimersByTimeAsync(2000);
    expect(wege.slice(1)).toEqual(["GET /api/mitlesen?ab=0", "GET /api/mitlesen?ab=4"]);
    expect(m.fremd && m.laeuftFuer("u") && m.absaetze.length === 1).toBe(true);
    await m.beenden();
    expect(wege.at(-1)).toBe("DELETE /api/mitlesen");
    const n = wege.length;
    await vi.advanceTimersByTimeAsync(10000);
    expect([wege.length, m.laeuftFuer("u")]).toEqual([n, false]);
    await m.starten("v", [{ schluessel: "de", name: "Deutsch" } as never]);
    expect(wege.at(-1)).toContain('"uebersetzen":false');
    await m.beenden();
  });

  it("endet das Radio, bleibt der Text stehen und es wird nicht weiter gefragt", async () => {
    let antwort = stand({ absaetze: [absatz(1)] });
    let anfragen = 0;
    const m = new Mitlesen((async () => { anfragen++; return antwort; }) as never);
    await m.starten("u", []);
    antwort = stand({ laeuft: false, zustand: "aus" });
    await vi.advanceTimersByTimeAsync(2100);
    const n = anfragen;
    await vi.advanceTimersByTimeAsync(9000);
    expect([anfragen, m.absaetze.length, m.laeuftFuer("u"), m.stand?.zustand]).toEqual([n, 1, true, "aus"]);
  });
});
