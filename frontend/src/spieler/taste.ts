// Taster des Appkerns (ak-taster) nach dem Zustand der App führen: Kappe an oder aus, Tastenlicht (Lichtschlitz in der
// Kappe, Merkmal licht) mit Farbe und Zustand, gesperrt, Erklärung und Symbol. Der Taster baut sein Innenleben einmal
// beim Einhängen und liest Symbol und Licht nur dann; was sich zur Laufzeit ändert, setzt diese Aktion. Schaltet sich
// eine Taste bei Bedienung selbst (Modus rasten oder tasten), meldet sie "input"; führt die App ihre Kappe (an), gilt
// danach wieder der Zustand der App.
import type { Action } from "svelte/action";
import type { Leuchtfarbe, Taster } from "appkern-oberflaeche/instrumente";
import type { Leuchtzustand } from "./kanzel";

export interface TastenStand {
  /** Kappe an oder aus; ohne Angabe führt der Taster sie selbst (Modus tasten: leuchtet, solange gedrückt) */
  an?: boolean;
  licht?: Leuchtzustand;
  lichtFarbe?: Leuchtfarbe;
  gesperrt?: boolean;
  hilfe?: string;
  /** Font-Awesome-Klasse des Symbols */
  symbol?: string;
  /** Symbol gespiegelt (etwa Weiter bei rückwärts) */
  gespiegelt?: boolean;
  /** Bedienung der Taste (Klick oder Tastatur auf ihrem Knopf; gesperrt kommt nichts an) */
  beiDruck?: () => void;
  /** langes Drücken (Zeiger mindestens LANG_MS auf der Taste, RAD-60); dann kommt beiDruck nicht mehr */
  beiLang?: () => void;
}

/** so lange hält man eine Taste für "lang gedrückt" */
export const LANG_MS = 600;

export const taste: Action<Taster, TastenStand> = (el, anfang) => {
  let stand = anfang;

  function setzen() {
    if (stand.an !== undefined) el.an = stand.an;
    const knopf = el.querySelector<HTMLButtonElement>(".ak-taster-knopf");
    const licht = el.querySelector("ak-led[art='schlitz']");
    if (licht) {
      if (stand.lichtFarbe) licht.setAttribute("farbe", stand.lichtFarbe);
      if (stand.licht) licht.setAttribute("zustand", stand.licht);
    }
    el.toggleAttribute("gesperrt", !!stand.gesperrt);
    if (knopf) {
      knopf.disabled = !!stand.gesperrt;
      if (stand.hilfe !== undefined) knopf.setAttribute("aria-label", stand.hilfe);
      const symbol = knopf.querySelector("i");
      if (symbol && stand.symbol) symbol.className = `fa-solid ${stand.symbol}${stand.gespiegelt ? " rh-gespiegelt" : ""}`;
    }
    if (stand.hilfe !== undefined) el.title = stand.hilfe;
  }

  const zustandZurueck = () => { if (stand.an !== undefined) setzen(); };
  // langes Drücken: nach LANG_MS gilt beiLang, der Klick beim Loslassen zählt dann nicht mehr
  let uhr: ReturnType<typeof setTimeout> | undefined;
  let langErledigt = false;
  const halten = () => {
    langErledigt = false;
    clearTimeout(uhr);
    if (!stand.beiLang || stand.gesperrt) return;
    uhr = setTimeout(() => { langErledigt = true; stand.beiLang?.(); }, LANG_MS);
  };
  const loslassen = () => clearTimeout(uhr);
  const druck = () => {
    if (langErledigt) { langErledigt = false; return; }
    if (!stand.gesperrt) stand.beiDruck?.();
  };
  const knopf = el.querySelector<HTMLButtonElement>(".ak-taster-knopf");
  el.addEventListener("input", zustandZurueck);
  knopf?.addEventListener("pointerdown", halten);
  for (const art of ["pointerup", "pointerleave", "pointercancel"]) knopf?.addEventListener(art, loslassen);
  knopf?.addEventListener("click", druck);
  setzen();

  return {
    update(neu) {
      stand = neu;
      setzen();
    },
    destroy() {
      el.removeEventListener("input", zustandZurueck);
      clearTimeout(uhr);
      knopf?.removeEventListener("pointerdown", halten);
      for (const art of ["pointerup", "pointerleave", "pointercancel"]) knopf?.removeEventListener(art, loslassen);
      knopf?.removeEventListener("click", druck);
    },
  };
};
