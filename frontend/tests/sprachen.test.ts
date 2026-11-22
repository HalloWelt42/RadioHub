// Mehrsprachigkeit (RAD-99): jede angebotene Sprache hat genau die Texte des Deutschen (derselbe Schlüsselbaum, keiner
// fehlt, keiner zu viel), dieselben Platzhalter ({n}, {name}, ...) und nur gerade Zeichen (keine Gedankenstriche und
// typografischen Anführungszeichen, wie im ganzen Projekt). So heißt "vollständig" gemessen, nicht behauptet.
import { describe, expect, it } from "vitest";
import { availableLanguages } from "../src/lib/i18n.js";
import { SPRACHANGEBOT } from "../src/lib/sprache";
import de from "../src/lib/locales/de.js";

type Baum = { [k: string]: string | Baum };

/** alle Blätter als Pfad -> Text */
function blaetter(baum: Baum, vor = ""): Map<string, string> {
  const aus = new Map<string, string>();
  for (const [k, v] of Object.entries(baum)) {
    const pfad = vor ? `${vor}.${k}` : k;
    if (v && typeof v === "object") for (const [p, t] of blaetter(v, pfad)) aus.set(p, t);
    else aus.set(pfad, String(v));
  }
  return aus;
}

const platzhalter = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
const VERBOTEN = /[\u2012\u2013\u2014\u2015\u2018\u2019\u201A\u201C\u201D\u201E\u00AB\u00BB]/;
const DEUTSCH = blaetter(de as Baum);

describe("Sprachen (RAD-99)", () => {
  it("bietet alle 20 Sprachen an", () => {
    expect(availableLanguages.length).toBe(20);
    expect(SPRACHANGEBOT).toEqual(availableLanguages);
  });

  // was in den Anzeigen (Punktmatrix, 14 Segmente) landet, darf nur deren Zeichen haben, sonst bleibt die Stelle leer
  const ANZEIGE = /^(kanzel\.(art_\w+|quelle_\w+|kbit|pufferBitrate|pufferWechselt|bitrateOriginal|bitrateOriginalUmgewandelt|bitrateVoll|titel_werbung_verbinden|titel_werbung_stumm)|telefon\.live)$/;
  const DARSTELLBAR = /^[A-Z0-9\u00C4\u00D6\u00DC\u00DF .,:;\-%/+'*()!?{}\u00B7]*$/;
  for (const { code } of availableLanguages) {
    it(`${code}: Anzeigewörter nur mit Zeichen der Anzeige`, async () => {
      const sprache = blaetter((await import(`../src/lib/locales/${code}.js`)).default as Baum);
      const falsch = [...sprache].filter(([k, t]) => ANZEIGE.test(k) && !DARSTELLBAR.test(t.replace(/\{\w+\}/g, "").toUpperCase())).map(([k, t]) => `${k}: ${t}`);
      expect(falsch).toEqual([]);
    });
  }

  for (const { code } of availableLanguages) {
    it(`${code}: dieselben Texte wie Deutsch, dieselben Platzhalter, nur gerade Zeichen`, async () => {
      const sprache = blaetter((await import(`../src/lib/locales/${code}.js`)).default as Baum);
      const fehlen = [...DEUTSCH.keys()].filter((k) => !sprache.has(k));
      const zuViel = [...sprache.keys()].filter((k) => !DEUTSCH.has(k));
      const platz = [...DEUTSCH].filter(([k, t]) => sprache.has(k) && platzhalter(t) !== platzhalter(sprache.get(k)!)).map(([k]) => k);
      const leer = [...sprache].filter(([, t]) => !t.trim()).map(([k]) => k);
      const zeichen = [...sprache].filter(([, t]) => VERBOTEN.test(t)).map(([k]) => k);
      expect({ fehlen: fehlen.slice(0, 20), anzahlFehlen: fehlen.length, zuViel: zuViel.slice(0, 20), platz: platz.slice(0, 20), leer, zeichen: zeichen.slice(0, 20) })
        .toEqual({ fehlen: [], anzahlFehlen: 0, zuViel: [], platz: [], leer: [], zeichen: [] });
    });
  }
});
