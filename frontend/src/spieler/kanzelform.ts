// Form der Kanzel aus dem Platzbedarf (Nutzer 20.11.2026: "display bricht zu früh um ohne not onlineversion").
// Gemessen wird der Inhalt, nicht eine feste Grenze: PRO mit Zeitversatz, Aufnahme und Drehwahl braucht mehr Platz als
// Basic, und jede Schriftstufe ändert den Bedarf. Vier Formen, von breit nach schmal:
//   eine    eine Reihe: Anzeige (bündig zur linken Spalte der Seite), Quelle und Zeit, Lautstärke, Tastenreihe
//   zwei    zwei Reihen neben dem Gehäuse: Anzeige oben, darunter Quelle und Zeit und die Tastenreihe
//   schmal  zwei Reihen, Tasten und Gehäuse in festen Spalten, das Gehäuse kleiner über dem Seltenen (RAD-114)
//   eng     drei Reihen in denselben Spalten, wenn auch Quelle und Zeit nicht mehr neben die Tasten passen
// Die Gestalt jeder Form steht in kanzel.css (data-form).
import type { Action } from "svelte/action";

export type Form = "eine" | "zwei" | "schmal" | "eng";

/** Breiten in Pixeln: was die Module mindestens brauchen, und die Spaltenlücke */
export interface Bedarf {
  anzeige: number;
  zeit: number;
  laut: number;
  steuerung: number;
  /** Breiten der Teile der Steuerung (Transport, Seltenes, Drehwahl), die in schmal und eng einzeln im Raster stehen */
  teile: number[];
  luecke: number;
}

/** Form für den Platz der Kanzel (ohne ihren Innenrand); in schmal stehen die Teile der Steuerung einzeln im Raster,
 *  mit dessen Lücke statt ihrer eigenen */
export function formFuer(platz: number, b: Bedarf): Form {
  if (platz >= b.anzeige + b.zeit + b.laut + b.steuerung + 3 * b.luecke) return "eine";
  if (platz >= b.zeit + b.steuerung + b.laut + 2 * b.luecke) return "zwei";
  if (platz >= b.zeit + b.teile.reduce((summe, t) => summe + t + b.luecke, 0)) return "schmal";
  return "eng";
}

function breite(el: Element | null): number {
  return el ? el.getBoundingClientRect().width : 0;
}

/** Was die Module der Kanzel in der einen Reihe brauchen (auch für Prüfungen). In einer zu engen Reihe drückt das
 *  Raster die Module zusammen; darum misst es sie kurz in ihrer natürlichen Breite (data-messen in kanzel.css) und
 *  stellt die Form danach wieder her, im selben Bildaufbau, ohne dass etwas sichtbar wechselt. */
export function bedarf(el: HTMLElement): Bedarf {
  const form = el.dataset.form;
  delete el.dataset.form;
  el.dataset.messen = "";
  try {
    const stil = getComputedStyle(el);
    return {
      anzeige: breite(el.querySelector(".rh-m-anzeige")),     // beim Messen in ihrer Mindestbreite --rh-anzeige-breite (kanzel.css)
      zeit: breite(el.querySelector(".rh-m-zeit")),
      laut: breite(el.querySelector(".rh-m-laut")),
      steuerung: breite(el.querySelector(".rh-m-steuerung")),
      teile: [...el.querySelectorAll(".rh-transport, .rh-betrieb, .rh-bitrate-wahl")].map(breite).filter((b) => b > 0),
      luecke: parseFloat(stil.columnGap) || 0,
    };
  } finally {
    delete el.dataset.messen;
    if (form) el.dataset.form = form;
  }
}

/** Setzt data-form an der Kanzel und hält es aktuell: bei neuer Breite, neuer Schriftstufe und wenn sich Module
 *  ändern (andere Tasten bei Folgen, Aufnahme) */
export const kanzelForm: Action<HTMLElement> = (el) => {
  const rechnen = () => {
    const stil = getComputedStyle(el);
    const platz = el.clientWidth - (parseFloat(stil.paddingLeft) || 0) - (parseFloat(stil.paddingRight) || 0);
    const form = formFuer(platz, bedarf(el));
    if (el.dataset.form !== form) el.dataset.form = form;
  };
  const groesse = new ResizeObserver(rechnen);
  const beobachten = () => {
    groesse.disconnect();
    groesse.observe(el);
    for (const m of el.querySelectorAll(".rh-m-zeit, .rh-m-laut, .rh-steuerung > *")) groesse.observe(m);
  };
  // Tastengruppen kommen und gehen (nur die Kinder der Tastenreihe, nicht jede Änderung der Anzeigen)
  const aufbau = new MutationObserver(() => { beobachten(); rechnen(); });
  const steuerung = el.querySelector(".rh-steuerung");
  if (steuerung) aufbau.observe(steuerung, { childList: true });
  beobachten();
  rechnen();
  return { destroy() { groesse.disconnect(); aufbau.disconnect(); } };
};
