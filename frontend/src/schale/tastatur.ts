// Tastatur am Rechner, gemeinsam für beide Bauziele (volle App und Webversion, RAD-4): Leertaste wie die Taste Spielen
// (spielen, Pause, weiter), S beendet, Pfeile für Lautstärke und Sender, M stumm, die Ziffern 1 bis n wählen die
// angebotenen Bereiche in der Reihenfolge der Navigation. Bei laufender Aufnahme sind Anhalten, Beenden und
// Senderwechsel gesperrt. In Eingabefeldern und am Telefon gilt nichts davon.
// Die Belegung steht als Tabelle (TASTEN); dieselbe Tabelle zeigt die Seite Einstellungen > Allgemein > Tastatur
// (RAD-11), damit Beschreibung und Verhalten nie auseinanderlaufen.
import { actions, appState } from "../lib/store.svelte.js";
import { spielenOderPause } from "../spieler/aktionen";

/** Lautstärke nach Stumm wieder an */
export const LAUT_NACH_STUMM = 70;
const SCHRITT_LAUTSTAERKE = 5;

export interface Taste {
  /** Werte von KeyboardEvent.key */
  tasten: readonly string[];
  /** Schlüssel der Beschriftung (einstellungen.tastatur.<name>) */
  name: string;
  gruppe: "wiedergabe" | "bereiche";
  /** während einer Aufnahme ohne Wirkung */
  gesperrtBeiAufnahme: boolean;
  /** mit Strg oder Befehl gehört die Taste dem Browser */
  nurOhneStrg: boolean;
  tun(): void;
}

export const TASTEN: readonly Taste[] = [
  { tasten: [" "], name: "spielen", gruppe: "wiedergabe", gesperrtBeiAufnahme: true, nurOhneStrg: false, tun: () => spielenOderPause() },
  { tasten: ["s"], name: "stopp", gruppe: "wiedergabe", gesperrtBeiAufnahme: true, nurOhneStrg: true, tun: () => actions.stop() },
  { tasten: ["m"], name: "stumm", gruppe: "wiedergabe", gesperrtBeiAufnahme: false, nurOhneStrg: true,
    tun: () => actions.setVolume(appState.volume > 0 ? 0 : LAUT_NACH_STUMM) },
  { tasten: ["ArrowUp"], name: "lauter", gruppe: "wiedergabe", gesperrtBeiAufnahme: false, nurOhneStrg: false,
    tun: () => actions.setVolume(Math.min(100, appState.volume + SCHRITT_LAUTSTAERKE)) },
  { tasten: ["ArrowDown"], name: "leiser", gruppe: "wiedergabe", gesperrtBeiAufnahme: false, nurOhneStrg: false,
    tun: () => actions.setVolume(Math.max(0, appState.volume - SCHRITT_LAUTSTAERKE)) },
  { tasten: ["ArrowLeft"], name: "zurueck", gruppe: "wiedergabe", gesperrtBeiAufnahme: true, nurOhneStrg: false, tun: () => actions.navigatePrev() },
  { tasten: ["ArrowRight"], name: "weiter", gruppe: "wiedergabe", gesperrtBeiAufnahme: true, nurOhneStrg: false, tun: () => actions.navigateNext() },
];

export function tasteDerApp(e: KeyboardEvent, bereiche: readonly string[]): void {
  const ziel = e.target as HTMLElement;
  if (ziel.tagName === "INPUT" || ziel.tagName === "TEXTAREA" || ziel.tagName === "SELECT" || ziel.isContentEditable) return;
  const strg = e.ctrlKey || e.metaKey;
  const ziffer = Number(e.key);
  if (Number.isInteger(ziffer) && ziffer >= 1 && ziffer <= bereiche.length && !strg && !e.altKey) {
    actions.setTab(bereiche[ziffer - 1]);
    return;
  }
  const taste = TASTEN.find((t) => t.tasten.includes(e.key));
  if (!taste || (taste.nurOhneStrg && strg)) return;
  if (!taste.nurOhneStrg) e.preventDefault();          // Leertaste und Pfeile sollen die Seite nicht rollen
  if (!(taste.gesperrtBeiAufnahme && appState.isRecording)) taste.tun();
}
