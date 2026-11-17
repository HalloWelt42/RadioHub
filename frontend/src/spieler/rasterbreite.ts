// Rasteranzeigen wachsen mit der Breite (Nutzer 17.11.2026, RAD-8): die Punktmatrix des Senders bekommt so viele
// Stellen, wie bei ihrer Zeichenhöhe in ihren Platz passen, statt fester 16 wie im Entwurf. Der Platz kommt vom Raster
// der Kanzel, nie vom Inhalt (die Anzeige ist so breit wie ihr Platz, die Zeichen passen sich an); darum wirkt eine
// neue Stellenzahl nicht auf die gemessene Breite zurück und nichts flackert. Die Zeichenhöhe folgt der Schriftstufe.
import type { Action } from "svelte/action";

/** Zeichenhöhe der Punktmatrix in Grundschriften (Normal 17 Pixel: knapp 24, wie im Entwurf) */
export const ZEICHEN_JE_SCHRIFT = 1.4;
/** Seitenverhältnis einer Zelle der Punktmatrix (fünf Punkte und eine Lücke breit, sieben und eine hoch) */
const VERHAELTNIS = 0.75;
/** Rand, den die Segmentanzeige des Appkerns von ihrer Breite abzieht (100cqi - 38px) */
const RAND = 38;
const MINDESTENS = 10;
const HOECHSTENS = 60;

/** Stellen für eine Breite in Pixeln und eine Zeichenhöhe: so viele ganze Zellen, dass keine kleiner wird als gewünscht */
export function stellenFuer(breite: number, zeichenhoehe: number): number {
  if (!(breite > 0) || !(zeichenhoehe > 0)) return MINDESTENS;
  const stellen = Math.floor((breite - RAND) / (zeichenhoehe * VERHAELTNIS));
  return Math.min(HOECHSTENS, Math.max(MINDESTENS, stellen));
}

/** Misst den Platz der Anzeige und meldet die Stellenzahl (nur bei Änderung); setzt die Zeichenhöhe als --rh-matrix-zeichen */
export const rasterStellen: Action<HTMLElement, (stellen: number) => void> = (el, anfang) => {
  let melden = anfang;
  let zuletzt = 0;
  const messen = () => {
    const hoehe = parseFloat(getComputedStyle(el).fontSize) * ZEICHEN_JE_SCHRIFT;
    el.style.setProperty("--rh-matrix-zeichen", `${hoehe.toFixed(2)}px`);
    const stellen = stellenFuer(el.clientWidth, hoehe);
    if (stellen !== zuletzt) {
      zuletzt = stellen;
      melden(stellen);
    }
  };
  const beobachter = new ResizeObserver(messen);
  beobachter.observe(el);
  // die Schriftstufe ändert die Zeichenhöhe auch ohne neue Breite
  const stufe = new MutationObserver(messen);
  stufe.observe(document.documentElement, { attributes: true, attributeFilter: ["data-schrift"] });
  return {
    update(neu) { melden = neu; },
    destroy() { beobachter.disconnect(); stufe.disconnect(); },
  };
};
