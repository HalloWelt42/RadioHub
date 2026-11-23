// Einstellungen nur dieses Geräts als Zeilen (RAD-11): Darstellung, Entwickleransicht, Bildschirm wach halten und die
// Zeitansage. Gespeichert wird weiter dort, wo die Werte schon leben (lib/darstellung, lib/telefon/zeitansage,
// lib/telefon/wachHalten, appState.devMode); hier steht nur, wie sie als Zeile aussehen und welcher Setter gilt.
import { DARSTELLUNG } from "../darstellung-vorab";
import { ANGEBOTENE_VORLAGEN, darstellung, darstellungSetzen } from "../darstellung.svelte";
import { t } from "../i18n.svelte.js";
import { geraetesprache, geraetespracheSetzen, SPRACHANGEBOT } from "../sprache";
import { actions, appState } from "../store.svelte.js";
import { wach, wachHaltenSetzen } from "../telefon/wachHalten.svelte.js";
import { nachtsSetzen, planSetzen, zeit, zeitansageSchalten } from "../telefon/zeitansage.svelte.js";
import { ABSTAENDE_MIN, BEDINGUNGEN, ZEITRAUM_SCHRITT_MIN } from "../telefon/zeitplan.js";
import { wahlArt } from "./aus-feld";
import type { Zeile, ZeilenArt } from "./typen";

interface Geraetewert {
  zeile(): Zeile;
  setzen(wert: unknown): void;
}

function geraetezeile(schluessel: string, art: ZeilenArt, wert: unknown, teil: Partial<Zeile> = {}): Zeile {
  return {
    schluessel, art, wert, geltung: "geraet", titel: t(`einstellungen.geraet.${schluessel}`),
    beschreibung: t(`einstellungen.geraet.${schluessel}Hilfe`), optionen: [], einheit: "", fest: false, geaendert: false,
    angebot: false, ...teil,
  };
}

const THEMEN = [["hell", "fa-sun"], ["dunkel", "fa-moon"], ["system", "fa-display"]] as const;
const NACHTS = ["normal", "leise", "aus"] as const;

export const GERAET: Record<string, Geraetewert> = {
  sprache: {
    zeile: () => geraetezeile("sprache", wahlArt(SPRACHANGEBOT.length), geraetesprache(), { optionen: SPRACHANGEBOT.map((l) => ({ wert: l.code, titel: l.label })) }),
    setzen: (w) => geraetespracheSetzen(String(w)),
  },
  vorlage: {
    zeile: () => geraetezeile("vorlage", "auswahl", darstellung.vorlage,
      { optionen: ANGEBOTENE_VORLAGEN.map((v) => ({ wert: v.id, titel: v.name, hinweis: v.text, symbol: v.symbol })) }),
    setzen: (w) => darstellungSetzen({ vorlage: String(w) }),
  },
  thema: {
    zeile: () => geraetezeile("thema", "wahl", darstellung.thema,
      { optionen: THEMEN.map(([w, s]) => ({ wert: w, titel: t(`schale.thema_${w}`), symbol: s })) }),
    setzen: (w) => darstellungSetzen({ thema: w as (typeof THEMEN)[number][0] }),
  },
  schrift: {
    zeile: () => geraetezeile("schrift", "stufe", darstellung.schrift,
      { optionen: DARSTELLUNG.stufen.map((s) => ({ wert: s, titel: t(`schale.schrift_${s}`) })) }),
    setzen: (w) => darstellungSetzen({ schrift: String(w) as typeof darstellung.schrift }),
  },
  wachHalten: {
    zeile: () => geraetezeile("wachHalten", "schalter", wach.gewuenscht,
      wach.unterstuetzt ? {} : { sperrgrund: t("einstellungen.geraet.wachHaltenFehlt") }),
    setzen: (w) => wachHaltenSetzen(!!w),
  },
  entwickleransicht: {
    zeile: () => geraetezeile("entwickleransicht", "schalter", appState.devMode),
    setzen: (w) => { if (!!w !== appState.devMode) actions.toggleDevMode(); },
  },
  zeitansage: {
    zeile: () => geraetezeile("zeitansage", "schalter", zeit.an),
    setzen: (w) => zeitansageSchalten(!!w),
  },
  zeitansageAbstand: {
    zeile: () => geraetezeile("zeitansageAbstand", "wahl", String(zeit.abstand),
      { optionen: ABSTAENDE_MIN.map((m) => ({ wert: String(m), titel: t("einstellungen.minuten", { n: m }) })) }),
    setzen: (w) => planSetzen({ abstand: Number(w) }),
  },
  zeitansageZeitraum: {
    zeile: () => geraetezeile("zeitansageZeitraum", "zeitraum", [zeit.von, zeit.bis], { schritt: ZEITRAUM_SCHRITT_MIN }),
    setzen: (w) => { const [von, bis] = w as [string, string]; planSetzen({ von, bis }); },
  },
  zeitansageWann: {
    zeile: () => geraetezeile("zeitansageWann", "wahl", zeit.bedingung,
      { optionen: BEDINGUNGEN.map((b: string) => ({ wert: b, titel: t(`einstellungen.geraet.wann_${b}`) })) }),
    setzen: (w) => planSetzen({ bedingung: String(w) }),
  },
  zeitansageNachts: {
    zeile: () => geraetezeile("zeitansageNachts", "wahl", zeit.nachts,
      { optionen: NACHTS.map((n) => ({ wert: n, titel: t(`einstellungen.geraet.nachts_${n}`) })) }),
    setzen: (w) => nachtsSetzen(String(w)),
  },
};

export function geraetZeile(schluessel: string): Zeile {
  return GERAET[schluessel].zeile();
}

export function geraetSetzen(schluessel: string, wert: unknown): void {
  GERAET[schluessel].setzen(wert);
}
