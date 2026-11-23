// Aufnahmen im Spieler und bei der Übergabe (RAD-134): Beschreibung, Titelreihe, Sperrbildschirm.
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/lib/playerEngine.js", () => ({ folgenBild: () => null }));
vi.mock("$ziel/quelle", () => ({ senderquelle: { logoAdresse: () => null } }));
vi.mock("../src/lib/schnitt", () => ({ schnittquelle: { ton: () => "/ton" } }));
vi.stubGlobal("location", { href: "http://localhost/" });

import { aktualisieren, beschreibung } from "../src/lib/telefon/medien.js";
import { reiheAus, reiheVon } from "../src/lib/aufnahmen/spielreihe";
import type { Aufnahme, Titel } from "../src/lib/aufnahmen/typen";
import type { Aufnahmequelle } from "../src/lib/aufnahmen/quelle";

const A = { id: "rec_1", sender: "Probe", senderUuid: "u1", beginn: "2026-11-23T20:00:00", dauer: 60 } as Aufnahme;
const T: Titel[] = [{ id: 7, nr: 1, titel: "Eins", start: 0, dauer: 30, groesse: 1, pfad: "a/1.mp3" }, { id: 8, nr: 2, titel: "", start: 30, dauer: 30, groesse: 1, pfad: "a/2.mp3" }];
const Q = { titelTon: (i: number) => `/ton/${i}`, titelDatei: (i: number) => `/datei/${i}`, alsEineDatei: (i: string) => `/eine/${i}`, aufnahme: async () => A, titel: async () => T } as unknown as Aufnahmequelle;

describe("Titelreihe einer Aufnahme", () => {
  it("je Titel ein Eintrag mit Ton, Datei und Aufnahme, ohne Titel die ganze", async () => {
    const r = await reiheVon(Q, "rec_1");
    expect(r.map((x) => [x.path, x.name, x.playUrl, x.ladeUrl, x.session_id, x.station_uuid])).toEqual([
      ["a/1.mp3", "Eins", "/ton/7", "/datei/7", "rec_1", "u1"], ["a/2.mp3", "Probe", "/ton/8", "/datei/8", "rec_1", "u1"]]);
    expect(reiheAus(Q, A, []).map((x) => [x.path, x.ladeUrl])).toEqual([["sitzung:rec_1", "/eine/rec_1"]]);
  });
});

describe("Aufnahme im Spieler", () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.stubGlobal("location", { href: "http://localhost/" }); });
  const zustand = (recording: object | null) => ({ currentEpisode: null, currentStation: null, currentRecording: recording, isPlaying: true, isPaused: false });

  it("hat eine Beschreibung (Spielerleiste, Geräte)", () => {
    expect(beschreibung(zustand(null))).toBeNull();
    expect(beschreibung(zustand({ name: "Eins", station_name: "Probe" }))).toMatchObject({ title: "Eins", artist: "Probe", folge: false, spulbar: true, reihe: true });
  });

  it("lässt sich am Sperrbildschirm spulen und durch die Titel schalten", () => {
    const an: string[] = [];
    vi.stubGlobal("MediaMetadata", class {});
    vi.stubGlobal("navigator", { mediaSession: { setActionHandler: (n: string, f: unknown) => { if (f) an.push(n); } } });
    const tun = () => undefined;
    aktualisieren(zustand({ name: "Eins", station_name: "Probe" }), { abspielen: tun, pause: tun, zurueck: tun, vor: tun, springen: tun, voriger: tun, naechster: tun });
    expect(an).toEqual(["play", "pause", "seekto", "previoustrack", "nexttrack"]);
  });
});
