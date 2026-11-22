// Podcasts (RAD-17): die Quelle des Bauziels ($ziel/podcasts: Backend in der vollen App, Browser in der Webversion,
// RAD-102) und die eine Aboliste für alle Ansichten.
import { podcastquelle, werbequelle } from "$ziel/podcasts";
import { actions } from "../store.svelte.js";
import { appPfad } from "../router.js";
import { Aboliste } from "./abos.svelte";
import { Aboaustausch } from "./austausch.svelte";
import { Podcastzustand } from "./ansicht.svelte";

export { podcastquelle, werbequelle };
export const aboliste = new Aboliste(podcastquelle);
/** Abos als Datei sichern und übernehmen (RAD-102) */
export const aboaustausch = new Aboaustausch(aboliste);
export const podcastzustand = new Podcastzustand({
  pfad: () => appPfad(),
  abfrage: () => window.location.search.replace(/^\?/, ""),
  ersetzen: (pfad) => actions.navigateTo(pfad, { replace: true }),
  neu: (pfad) => actions.navigateTo(pfad),
});

export { Folgenliste } from "./folgenliste.svelte";
export { Speicherauftrag } from "./speicherauftrag.svelte";
export { Verzeichnissuche } from "./verzeichnissuche.svelte";
export * from "./ansicht.svelte";
export type { Podcastquelle } from "./quelle";
export { dateiWaehlen, uebernahmeText, type Uebernahme } from "./austausch.svelte";
export * from "./typen";
export type { Werbequelle, Werbestelle, Werbestellen, Werbeherkunft } from "./werbung";
