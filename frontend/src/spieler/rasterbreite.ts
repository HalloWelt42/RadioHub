// Rasteranzeigen wachsen mit der Breite (Nutzer 17.11.2026, RAD-8): eine Punktmatrix bekommt so viele Stellen, wie bei
// ihrer Zeichenhöhe in ihren Platz passen, statt fester 16 wie im Entwurf, und füllt ihr Glas ohne Lücke (Nutzer
// 20.11.2026: "dynamisches display hat lücken"): die Stellen werden abgerundet, die Zeichen danach so weit größer, dass
// die Zeile die ganze Breite einnimmt (kanzel.css rechnet die Zeichenhöhe ohne Rand und lässt sie bis zur Grenze
// MEHR_HOECHSTENS wachsen). Der Platz kommt vom Raster der Kanzel, nie vom Inhalt; darum wirkt eine neue Stellenzahl
// nicht auf die gemessene Breite zurück und nichts flackert. Die Zeichenhöhe folgt der Schriftstufe.
import type { Action } from "svelte/action";

/** Zeichenhöhe der Punktmatrix des Senders in Grundschriften (Normal 17 Pixel: knapp 24, wie im Entwurf) */
export const ZEICHEN_JE_SCHRIFT = 1.4;
/** Zeichenhöhe der kleinen Punktmatrix der Statuszeile in Grundschriften */
export const STATUS_JE_SCHRIFT = 0.7;
/** so viel größer als gewünscht darf ein Zeichen werden, damit die Zeile ihr Glas füllt (eine Stelle mehr wäre kleiner) */
export const MEHR_HOECHSTENS = 1.25;
/** Seitenverhältnis einer Zelle der Punktmatrix (fünf Punkte und eine Lücke breit, sieben und eine hoch) */
const VERHAELTNIS = 0.75;
const MINDESTENS = 10;
const HOECHSTENS = 120;

/** Stellen für eine Breite in Pixeln und eine Zeichenhöhe: so viele ganze Zellen, dass keine kleiner wird als gewünscht */
export function stellenFuer(breite: number, zeichenhoehe: number): number {
  if (!(breite > 0) || !(zeichenhoehe > 0)) return MINDESTENS;
  const stellen = Math.floor(breite / (zeichenhoehe * VERHAELTNIS));
  return Math.min(HOECHSTENS, Math.max(MINDESTENS, stellen));
}

export interface Rastermass {
  /** Zeichenhöhe in Grundschriften der Stelle, an der gemessen wird */
  jeSchrift: number;
  /** meldet die Stellenzahl (nur bei Änderung) */
  melden: (stellen: number) => void;
}

/** Misst den Platz der Anzeige und meldet die Stellenzahl; setzt die gewünschte Zeichenhöhe als --rh-matrix-zeichen */
export const rasterStellen: Action<HTMLElement, Rastermass> = (el, anfang) => {
  let mass = anfang;
  let zuletzt = 0;
  const messen = () => {
    const hoehe = parseFloat(getComputedStyle(el).fontSize) * mass.jeSchrift;
    el.style.setProperty("--rh-matrix-zeichen", `${hoehe.toFixed(2)}px`);
    const stellen = stellenFuer(el.clientWidth, hoehe);
    if (stellen !== zuletzt) {
      zuletzt = stellen;
      mass.melden(stellen);
    }
  };
  const beobachter = new ResizeObserver(messen);
  beobachter.observe(el);
  // die Schriftstufe ändert die Zeichenhöhe auch ohne neue Breite
  const stufe = new MutationObserver(messen);
  stufe.observe(document.documentElement, { attributes: true, attributeFilter: ["data-schrift"] });
  return {
    update(neu) { mass = neu; messen(); },
    destroy() { beobachter.disconnect(); stufe.disconnect(); },
  };
};

/** Statuszeile in einer Zeile fester Stellen: links, was geschieht, rechts der Hinweis bündig am Ende; passt beides
 *  nicht, kommt der Hinweis mit Abstand dahinter (die Matrix läuft dann) */
export function statuszeile(links: string, rechts: string | null, stellen: number): string {
  if (!rechts) return links;
  const luecke = stellen - links.length - rechts.length;
  return luecke >= 2 ? links + " ".repeat(luecke) + rechts : `${links}  ${rechts}`;
}
