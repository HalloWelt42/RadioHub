// Datenschutz und Herkunft der Basic (RAD-120, RAD-123): jede Sprache hat beide Texte mit demselben Aufbau wie Deutsch, denselben
// Verweisen und nur geraden Zeichen
import { readdirSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { availableLanguages } from "../src/lib/i18n.js";
import { EINSTELLUNGEN as BASIC } from "../src/ziel/web/einstellungen";
import { EINSTELLUNGEN as PRO } from "../src/ziel/voll/einstellungen";

const ORDNER = new URL("../public/legal/", import.meta.url);
const lies = (sprache: string, datei: string) => readFileSync(new URL(`${sprache}/${datei}`, ORDNER), "utf-8");
const aufbau = (md: string) => ({ titel: md.match(/^# /gm)?.length ?? 0, abschnitte: md.match(/^## /gm)?.length ?? 0,
  verweise: [...md.matchAll(/\]\((.+?)\)/g)].map((m) => m[1]).sort() });
const VERBOTEN = /[\u2012\u2013\u2014\u2015\u2018\u2019\u201A\u201C\u201D\u201E\u00AB\u00BB]/;

describe("Datenschutz und Herkunft", () => {
  it("nur die Basic zeigt den Knopf", () => {
    expect(BASIC.hinweise.length).toBe(2);
    expect(PRO.hinweise.length).toBe(0);
  });
  for (const { code } of availableLanguages) {
    it(`${code}: beide Texte wie Deutsch aufgebaut`, () => {
      expect(readdirSync(ORDNER)).toContain(code);
      for (const datei of BASIC.hinweise) {
        const md = lies(code, datei);
        expect(aufbau(md)).toEqual(aufbau(lies("de", datei)));
        expect(md).not.toMatch(VERBOTEN);
      }
      expect(lies(code, "basic-datenschutz.md")).toContain("HalloWelt42");
    });
  }
});
