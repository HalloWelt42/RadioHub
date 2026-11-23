// Einen Titel aus dem Puffer speichern (RAD-132): ein Weg für die Spur der Kanzel, die Großansicht und das Telefon, mit Meldung.
// Was gerade gespeichert wird, ist gesperrt; was gespeichert ist, sagt der Server am Abschnitt.
import { SvelteSet } from "svelte/reactivity";
import { actions } from "../lib/store.svelte.js";
import { t } from "../lib/i18n.svelte.js";
import type { Abschnitt } from "../lib/radio/abschnitte";
import { puffer } from "./puffer.svelte";

const laufend = new SvelteSet<number>();

export const titelsichern = {
  geht: (a: Abschnitt): boolean => a.komplett && !a.gesichert && !laufend.has(a.von),
  async tun(a: Abschnitt): Promise<void> {
    if (!this.geht(a)) return;
    laufend.add(a.von);
    try {
      await puffer.titelSichern(a);
      actions.showToast(t("puffer.titelGespeichert", { titel: puffer.benennen(a) }), "success");
    } catch (f) {
      actions.showToast(t("puffer.fehler", { text: (f as Error).message }), "error");
    } finally {
      laufend.delete(a.von);
    }
  },
  symbol: (a: Abschnitt): string => (a.gesichert ? "fa-solid fa-circle-check" : laufend.has(a.von) ? "fa-solid fa-spinner fa-spin" : "fa-regular fa-floppy-disk"),
  hilfe: (a: Abschnitt): string => (a.gesichert ? t("puffer.gespeichert") : t("puffer.titelSpeichern")),
};
