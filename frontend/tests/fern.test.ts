// Steuermodus (RAD-96): Tasten und Antippen gehen an das gewählte Gerät, nie aus Versehen hierher
import { beforeEach, describe, expect, it, vi } from "vitest";

const h = vi.hoisted(() => ({ umleitung: null as null | ((...a: unknown[]) => boolean), meldungen: [] as string[], gesendet: [] as unknown[][],
  andere: [] as { id: string; name: string; zustand: unknown }[] }));
vi.mock("../src/lib/store.svelte.js", () => ({ actions: { showToast: (x: string) => h.meldungen.push(x) }, umleitungSetzen: (w: never) => { h.umleitung = w; } }));
vi.mock("../src/lib/i18n.svelte.js", () => ({ t: (k: string) => k }));
vi.mock("../src/spieler/geraete.svelte", () => ({ geraete: {
  get andere() { return h.andere; },
  befehlen: (...a: unknown[]) => h.gesendet.push(["befehl", ...a]), geben: (...a: unknown[]) => h.gesendet.push(["geben", ...a]),
} }));
import { fern, fernsteuerung } from "../src/spieler/fern.svelte";

beforeEach(() => {
  h.andere = [{ id: "pc", name: "Rechner", zustand: null }];
  h.gesendet.length = 0; h.meldungen.length = 0;
  fern.waehlen(null);
});

describe("Steuermodus", () => {
  it("ohne Wahl bleibt alles hier", () => {
    fernsteuerung.umschalten();
    expect(h.umleitung!("sender", { uuid: "u1" })).toBe(false);
    expect(h.gesendet).toEqual([]);
  });
  it("Tasten und angetippte Quellen gehen an das gewählte Gerät", () => {
    fern.waehlen("pc");
    fernsteuerung.naechster();
    fernsteuerung.vor(30);
    expect(h.umleitung!("sender", { uuid: "u1", name: "M", tags: "x".repeat(600) })).toBe(true);
    expect(h.gesendet).toEqual([["befehl", "pc", "weiter", null], ["befehl", "pc", "vor", 30],
      ["geben", "pc", { art: "sender", sender: { uuid: "u1", name: "M" }, stelle: 0 }]]);
  });
  it("Folgen reisen mit Abo und Stelle", () => {
    fern.waehlen("pc");
    h.umleitung!("folge", { id: 7, resume_position: 61 }, { id: 3, title: "Abo" });
    expect(h.gesendet[0]).toEqual(["geben", "pc", { art: "folge", folge: { id: 7, resume_position: 61 }, podcast: { id: 3, title: "Abo" }, stelle: 61 }]);
  });
  it("ist das Gerät weg, ruht alles, und hier geht trotzdem nichts los", () => {
    fern.waehlen("pc");
    h.andere = [];
    expect([fern.aktiv, fern.erreichbar, fern.name]).toEqual([true, false, "Rechner"]);
    fernsteuerung.umschalten();
    expect(h.umleitung!("sender", { uuid: "u1" })).toBe(true);
    expect(h.gesendet).toEqual([]);
    expect(h.meldungen).toEqual(["telefon.fernWeg"]);
  });
  it("Lautstärke beim Ziehen gebündelt, der letzte Wert kommt an", () => {
    vi.useFakeTimers();
    fern.waehlen("pc");
    for (let i = 40; i <= 60; i++) fern.lautstaerke(i);
    vi.advanceTimersByTime(500);
    expect(h.gesendet).toEqual([["befehl", "pc", "lautstaerke", 40], ["befehl", "pc", "lautstaerke", 60]]);
    vi.useRealTimers();
  });
});
