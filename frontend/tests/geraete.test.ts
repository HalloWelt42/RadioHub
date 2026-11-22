import { describe, expect, it } from "vitest";
import { kompakt, paketJetzt, zustandJetzt } from "../src/spieler/geraetepaket";
import type { AppZustand } from "../src/spieler/app";

const stand = (teil: Partial<AppZustand>): AppZustand => ({ isPlaying: true, isPaused: false, currentStation: null, currentEpisode: null,
  currentRecording: null, streamTitle: null, ...teil } as AppZustand);

describe("Übergabe im Radio (RAD-18)", () => {
  it("lange Texte und verschachtelte Teile reisen nicht mit", () => {
    expect(kompakt({ id: 7, title: "Folge", description: "x".repeat(600), podcast: { id: 1 } })).toEqual({ id: 7, title: "Folge" });
  });
  it("meldet, was spielt, und packt die Quelle mit Stelle", () => {
    const folge = stand({ currentEpisode: { id: 7, title: "Folge", podcast: { id: 3, title: "Abo" } } });
    expect(zustandJetzt(folge)).toEqual({ art: "folge", titel: "Folge", untertitel: "Abo", laeuft: true });
    expect(paketJetzt(folge, 61)).toEqual({ art: "folge", folge: { id: 7, title: "Folge" }, podcast: { id: 3, title: "Abo" }, stelle: 61 });
    const sender = stand({ currentStation: { uuid: "u1", name: "MANGORADIO" }, isPaused: true });
    expect(zustandJetzt(sender)).toEqual({ art: "sender", titel: "MANGORADIO", untertitel: "", laeuft: false });
    expect(paketJetzt(sender, 99)).toEqual({ art: "sender", sender: { uuid: "u1", name: "MANGORADIO" }, stelle: 0 });
    expect(zustandJetzt(stand({ isPlaying: false, currentStation: { uuid: "u1", name: "M" } }))).toBeNull();
    expect(paketJetzt(stand({ isPlaying: false }))).toBeNull();
  });
});
