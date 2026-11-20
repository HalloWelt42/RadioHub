// Fokus auf den laufenden Sender (RAD-19), ein Schalter der Kanzel, gemerkt im Gerät. Ein: die Senderliste springt zum
// laufenden Sender und klappt ihn auf, und wieder bei jedem Senderwechsel (Weiter, Zurück, ein neuer Sender); dazwischen
// rollt man frei. Wird der fokussierte Sender ausgeblendet, rückt der nächste der Reihe in den Fokus. Aus: frei
// rollen, nichts springt von selbst. Die Radio-Ansicht führt das aus, hier liegt nur der Zustand.
import { zurQuelle } from "./aktionen";

const SCHLUESSEL = "radiohub_fokus";

function gemerkt(): boolean {
  try {
    return localStorage.getItem(SCHLUESSEL) === "1";
  } catch {
    return false;
  }
}

export const fokus = $state({ an: gemerkt() });

/** Ein oder aus; beim Einschalten gleich zum laufenden Sender */
export function fokusSchalten(): void {
  fokus.an = !fokus.an;
  try {
    localStorage.setItem(SCHLUESSEL, fokus.an ? "1" : "0");
  } catch { /* privates Fenster: gilt bis zum Neuladen */ }
  if (fokus.an) zurQuelle();
}
