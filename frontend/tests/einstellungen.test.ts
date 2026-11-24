// Einstellungen (RAD-11): ein Feld des Servermodells als Zeile (Art, Grenzen, Sekunden als Stunden oder Minuten,
// fest gesetzt, Typ der Wahl) und die Tastentabelle, aus der Verhalten und Seite Tastatur zugleich lesen.
import { describe, expect, it, vi } from "vitest";
import type { Feld } from "appkern-oberflaeche";
import { anzeigeeinheit, SEGMENT_HOECHSTENS, wahlArt, wahlwert, zeileAusFeld } from "../src/lib/einstellungen/aus-feld";

const feld = (teil: Partial<Feld>): Feld => ({
  name: "x", titel: "X", beschreibung: "", art: "text", optionen: [], beschriftungen: {}, schritt: null, kleinste: null, groesste: null,
  einheit: "", angebot: false, paar: null, wert: null, gesetzt: true, vorgabe: null, herkunft: "vorgabe", gruppe: null, qr: "", ...teil,
} as Feld);

describe("Feld als Zeile", () => {
  it("eine Wahl klappt ab einer Grenze auf, für Server und Gerät gleich (RAD-122)", () => {
    expect([wahlArt(SEGMENT_HOECHSTENS), wahlArt(SEGMENT_HOECHSTENS + 1), wahlArt(20)]).toEqual(["wahl", "auswahl", "auswahl"]);
  });
  it("Arten: Schalter, Zahl, wenige Werte als Segment, viele als Aufklappliste, Liste mit Namen als Mehrfachwahl, Uhrzeit", () => {
    expect(zeileAusFeld(feld({ art: "schalter" }), true, false).art).toBe("schalter");
    expect(zeileAusFeld(feld({ art: "zahl", kleinste: 8, groesste: 512, schritt: 8, einheit: "kbit/s" }), 32, false))
      .toMatchObject({ art: "zahl", kleinste: 8, groesste: 512, schritt: 8, einheit: "kbit/s", wert: 32 });
    const wenige = feld({ art: "auswahl", optionen: ["22050", "44100"], beschriftungen: { "44100": "44.100 Hz" } });
    expect(zeileAusFeld(wenige, 44100, false)).toMatchObject({ art: "wahl", optionen: [{ wert: "22050", titel: "22050" }, { wert: "44100", titel: "44.100 Hz" }] });
    const viele = feld({ art: "auswahl", optionen: Array.from({ length: SEGMENT_HOECHSTENS + 1 }, (_, i) => `s${i}`) });
    expect(zeileAusFeld(viele, "s0", false).art).toBe("auswahl");
    expect(zeileAusFeld(feld({ art: "text", angebot: true }), "katalog:sohee", false)).toMatchObject({ art: "auswahl", angebot: true });
    const verfahren = feld({ art: "liste", beschriftungen: { url_check: "Adresse prüfen", header_check: "Kopf des Stroms" } });
    expect(zeileAusFeld(verfahren, ["url_check"], false)).toMatchObject({ art: "mehrfach", optionen: [{ wert: "url_check", titel: "Adresse prüfen" }, { wert: "header_check", titel: "Kopf des Stroms" }] });
    expect(zeileAusFeld(feld({ art: "liste" }), ["https://a"], false).art).toBe("liste");
    expect(zeileAusFeld(feld({ art: "text", einheit: "Uhrzeit" }), "04:30", false)).toMatchObject({ art: "uhrzeit", einheit: "" });
  });

  it("Sekunden in großen Schritten als Stunden oder Minuten; kleine Untergrenzen bleiben (Tempo 0,5)", () => {
    expect(anzeigeeinheit({ einheit: "s", schritt: 3600 })).toEqual({ faktor: 3600, einheit: "h" });
    expect(anzeigeeinheit({ einheit: "s", schritt: 60 })).toEqual({ faktor: 60, einheit: "min" });
    expect(anzeigeeinheit({ einheit: "kbit/s", schritt: 8 })).toEqual({ faktor: 1, einheit: "kbit/s" });
    const abruf = zeileAusFeld(feld({ art: "zahl", einheit: "s", schritt: 3600, kleinste: 60, groesste: 604800 }), 21600, false);
    expect(abruf).toMatchObject({ wert: 6, einheit: "h", schritt: 1, kleinste: 1, groesste: 168, faktor: 3600 });
    const tempo = zeileAusFeld(feld({ art: "zahl", kleinste: 0.5, groesste: 2, schritt: 0.05 }), 1, false);
    expect(tempo).toMatchObject({ kleinste: 0.5, groesste: 2, schritt: 0.05, faktor: 1 });
  });

  it("fest gesetzt, geändert, Geltung und Typ der Wahl", () => {
    const z = zeileAusFeld(feld({ herkunft: "fest", vorgabe: 44100 }), 44100, true);
    expect(z).toMatchObject({ fest: true, geaendert: true, geltung: "alle" });
    expect(wahlwert({ vorgabe: 44100 }, "48000")).toBe(48000);
    expect(wahlwert({ vorgabe: "de" }, "en")).toBe("en");
  });
});

const zustand = vi.hoisted(() => ({ appState: { isRecording: false, volume: 50 }, aufrufe: [] as string[] }));
vi.mock("../src/lib/store.svelte.js", () => ({
  appState: zustand.appState,
  actions: {
    stop: () => zustand.aufrufe.push("stop"), setTab: (t: string) => zustand.aufrufe.push(`tab:${t}`),
    setVolume: (v: number) => { zustand.appState.volume = v; zustand.aufrufe.push(`laut:${v}`); },
    navigatePrev: () => zustand.aufrufe.push("zurueck"), navigateNext: () => zustand.aufrufe.push("weiter"),
  },
}));
// Pfeile laufen über Vor und Zurück der Kanzel (RAD-60: im Zeitversatz durch die Titel, sonst der Sender)
vi.mock("../src/spieler/aktionen", () => ({ spielenOderPause: () => zustand.aufrufe.push("spielen"),
  zurueck: () => zustand.aufrufe.push("zurueck"), vor: () => zustand.aufrufe.push("weiter") }));

describe("Tastatur aus einer Tabelle", () => {
  const taste = (key: string, extra: Partial<KeyboardEvent> = {}) =>
    ({ key, target: { tagName: "BODY", isContentEditable: false }, ctrlKey: false, metaKey: false, altKey: false, preventDefault: () => {}, ...extra }) as unknown as KeyboardEvent;

  it("wirkt wie beschrieben und sperrt während einer Aufnahme genau die markierten Tasten", async () => {
    const { TASTEN, tasteDerApp, LAUT_NACH_STUMM } = await import("../src/schale/tastatur");
    const bereiche = ["radio", "settings"];
    zustand.aufrufe.length = 0;
    for (const k of [" ", "s", "ArrowRight", "ArrowUp", "2", "m"]) tasteDerApp(taste(k), bereiche);
    expect(zustand.aufrufe).toEqual(["spielen", "stop", "weiter", "laut:55", "tab:settings", "laut:0"]);
    tasteDerApp(taste("m"), bereiche);
    expect(zustand.appState.volume).toBe(LAUT_NACH_STUMM);
    tasteDerApp(taste("s", { metaKey: true }), bereiche);           // Befehl+S gehört dem Browser
    expect(zustand.aufrufe.at(-1)).toBe(`laut:${LAUT_NACH_STUMM}`);

    zustand.appState.isRecording = true;
    zustand.aufrufe.length = 0;
    for (const t of TASTEN) tasteDerApp(taste(t.tasten[0]), bereiche);
    const gewirkt = TASTEN.filter((t) => !t.gesperrtBeiAufnahme).map((t) => t.name);
    expect(gewirkt).toEqual(["stumm", "lauter", "leiser", "zurueck", "weiter"]);
    expect(zustand.aufrufe.length).toBe(gewirkt.length);
    zustand.appState.isRecording = false;
  });
});
