// Maße der Kanzel für Meldungen (RAD-74): wie hoch die Kanzel vom unteren Fensterrand reicht (--rh-kanzel-oben), wo das
// Gehäuse der Lautstärke steht (--rh-laut-links, --rh-laut-rechts, vom linken Fensterrand) und wie weit es über die
// Kanzel ragt (--rh-laut-ueberstand, 0 in allen Formen außer der einen Reihe). Meldungen fahren als Lasche über der Lautstärke hinter
// der Kanzel hervor; data-kanzel am Wurzelelement sagt, dass es die Kanzel gibt. Eine Quelle, am Wurzelelement.
// Dazu, wie weit der Schriftzug des Urhebers vom rechten Rand der Kanzel steht: links neben dem Drehregler (RAD-86).
// Die Lasche selbst (--rh-band-links, --rh-band-rechts) steht über der Lautstärke, aber nie starr: fehlt rechts Platz
// (schmales Fenster, die Lautstärke ganz rechts), rückt sie nach links ins Fenster, statt abgeschnitten zu werden (RAD-113).
import type { Action } from "svelte/action";

/** so weit reicht die Lasche links und rechts über das Gehäuse der Lautstärke hinaus, und so viel Rand bleibt zum Fenster */
const UEBERSTAND = 150;
const RAND = 12;

/** Lage der Lasche im Fenster: mittig über der Lautstärke, so breit wie vorgesehen, aber ganz im Fenster */
export function laschenLage(lautLinks: number, lautRechts: number, fenster: number): { links: number; rechts: number } {
  let links = lautLinks - UEBERSTAND;
  let rechts = lautRechts + UEBERSTAND;
  if (rechts > fenster - RAND) { links -= rechts - (fenster - RAND); rechts = fenster - RAND; }
  if (links < RAND) { rechts = Math.min(fenster - RAND, rechts + RAND - links); links = RAND; }
  return { links: Math.round(links), rechts: Math.round(fenster - rechts) };
}

export const kanzelmasse: Action<HTMLElement> = (kanzel) => {
  const wurzel = document.documentElement.style;
  function messen() {
    const k = kanzel.getBoundingClientRect();
    wurzel.setProperty("--rh-kanzel-oben", `${Math.round(window.innerHeight - k.top)}px`);
    const laut = kanzel.querySelector<HTMLElement>(".rh-laut");
    const l = laut?.getBoundingClientRect();
    const dreh = kanzel.querySelector<HTMLElement>(".rh-bitrate-wahl")?.getBoundingClientRect();
    if (dreh && dreh.width) kanzel.style.setProperty("--rh-urheber-rechts", `${Math.round(k.right - dreh.left + 12)}px`);
    else kanzel.style.removeProperty("--rh-urheber-rechts");
    if (l && l.width) {
      wurzel.setProperty("--rh-laut-links", `${Math.round(l.left)}px`);
      wurzel.setProperty("--rh-laut-rechts", `${Math.round(l.right)}px`);
      wurzel.setProperty("--rh-laut-ueberstand", `${Math.max(0, Math.round(k.top - l.top))}px`);
      const lasche = laschenLage(l.left, l.right, window.innerWidth);
      wurzel.setProperty("--rh-band-links", `${lasche.links}px`);
      wurzel.setProperty("--rh-band-rechts", `${lasche.rechts}px`);
    }
  }
  const beobachter = new ResizeObserver(messen);
  beobachter.observe(kanzel);
  window.addEventListener("resize", messen);
  document.documentElement.dataset.kanzel = "";
  messen();
  return {
    destroy() {
      beobachter.disconnect();
      window.removeEventListener("resize", messen);
      for (const name of ["--rh-kanzel-oben", "--rh-laut-links", "--rh-laut-rechts", "--rh-laut-ueberstand", "--rh-band-links", "--rh-band-rechts"]) wurzel.removeProperty(name);
      delete document.documentElement.dataset.kanzel;
    },
  };
};
