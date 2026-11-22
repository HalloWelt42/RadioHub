// Maße der Kanzel für Meldungen (RAD-74): wie hoch die Kanzel vom unteren Fensterrand reicht (--rh-kanzel-oben), wo das
// Gehäuse der Lautstärke steht (--rh-laut-links, --rh-laut-rechts, vom linken Fensterrand) und wie weit es über die
// Kanzel ragt (--rh-laut-ueberstand, 0 in zwei oder drei Reihen). Meldungen fahren als Lasche über der Lautstärke hinter
// der Kanzel hervor; data-kanzel am Wurzelelement sagt, dass es die Kanzel gibt. Eine Quelle, am Wurzelelement.
// Dazu, wie weit der Schriftzug des Urhebers vom rechten Rand der Kanzel steht: links neben dem Drehregler (RAD-86).
import type { Action } from "svelte/action";

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
      for (const name of ["--rh-kanzel-oben", "--rh-laut-links", "--rh-laut-rechts", "--rh-laut-ueberstand"]) wurzel.removeProperty(name);
      delete document.documentElement.dataset.kanzel;
    },
  };
};
