// Großansicht des Puffers unter /radio/puffer (RAD-46). Offen folgt der Adresse; schließen übernimmt die Radioansicht,
// die weiß, wohin die Liste zurückkehrt (laufender Sender aufgeklappt und im Blick). Der Knopf Puffer der Kanzel schaltet
// um: ein zweiter Klick verlässt die Ansicht wie ihr Schließen (RAD-69).
import { actions, appState } from "../lib/store.svelte.js";

const PFAD = "puffer";
let schliesser: (() => void) | null = null;

export const pufferansicht = {
  get offen(): boolean {
    return appState.activeTab === "radio" && (appState.routeSegments as string[])[0] === PFAD;
  },
  oeffnen(): void {
    actions.navigateTo(`/radio/${PFAD}`);
  },
  schliessen(): void {
    schliesser?.();
  },
  umschalten(): void {
    if (this.offen) this.schliessen();
    else this.oeffnen();
  },
  /** die Radioansicht meldet ihr Schließen an; zurück kommt das Abmelden */
  anmelden(schliessen: () => void): () => void {
    schliesser = schliessen;
    return () => { if (schliesser === schliessen) schliesser = null; };
  },
};
