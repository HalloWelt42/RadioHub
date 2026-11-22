// Reihen der Kanzel aus dem Platzbedarf (Nutzer 20.11.2026: "display bricht zu früh um ohne not onlineversion"): die
// Kanzel steht in einer Reihe, solange Anzeige (bündig zur linken Spalte der Seite), Quelle und Zeit, Lautstärke und Tastenreihe nebeneinander
// passen; sonst in zwei Reihen (Anzeige oben, darunter Quelle und Zeit und die Tastenreihe), erst wenn auch das nicht
// passt in drei. Gemessen wird der Inhalt, nicht eine feste Grenze: PRO mit Zeitversatz, Aufnahme und Drehwahl braucht
// mehr Platz als Basic, und jede Schriftstufe ändert den Bedarf. Die Gestalt jeder Reihenform steht in kanzel.css
// (data-reihen).
import type { Action } from "svelte/action";

export type Reihen = 1 | 2 | 3;

/** Breiten in Pixeln: was die Module mindestens brauchen, und die Spaltenlücke */
export interface Bedarf {
  anzeige: number;
  zeit: number;
  laut: number;
  steuerung: number;
  luecke: number;
}

/** Reihen für den Platz der Kanzel (ohne ihren Innenrand) */
export function reihenFuer(platz: number, b: Bedarf): Reihen {
  if (platz >= b.anzeige + b.zeit + b.laut + b.steuerung + 3 * b.luecke) return 1;
  if (platz >= b.zeit + b.steuerung + b.laut + 2 * b.luecke) return 2;
  return 3;
}

function breite(el: Element | null): number {
  return el ? el.getBoundingClientRect().width : 0;
}

/** Was die Module der Kanzel in der einen Reihe brauchen (auch für Prüfungen). In einer zu engen Reihe drückt das
 *  Raster die Module zusammen; darum misst es sie kurz in ihrer natürlichen Breite (data-messen in kanzel.css) und
 *  stellt die Reihenform danach wieder her, im selben Bildaufbau, ohne dass etwas sichtbar wechselt. */
export function bedarf(el: HTMLElement): Bedarf {
  const reihen = el.dataset.reihen;
  delete el.dataset.reihen;
  el.dataset.messen = "";
  try {
    const stil = getComputedStyle(el);
    return {
      anzeige: breite(el.querySelector(".rh-m-anzeige")),     // beim Messen so breit wie --rh-anzeige-breite (kanzel.css)
      zeit: breite(el.querySelector(".rh-m-zeit")),
      laut: breite(el.querySelector(".rh-m-laut")),
      steuerung: breite(el.querySelector(".rh-m-steuerung")),
      luecke: parseFloat(stil.columnGap) || 0,
    };
  } finally {
    delete el.dataset.messen;
    if (reihen) el.dataset.reihen = reihen;
  }
}

/** Setzt data-reihen an der Kanzel und hält es aktuell: bei neuer Breite, neuer Schriftstufe und wenn sich Module
 *  ändern (andere Tasten bei Folgen, Aufnahme) */
export const kanzelReihen: Action<HTMLElement> = (el) => {
  const rechnen = () => {
    const stil = getComputedStyle(el);
    const platz = el.clientWidth - (parseFloat(stil.paddingLeft) || 0) - (parseFloat(stil.paddingRight) || 0);
    const reihen = String(reihenFuer(platz, bedarf(el)));
    if (el.dataset.reihen !== reihen) el.dataset.reihen = reihen;
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
