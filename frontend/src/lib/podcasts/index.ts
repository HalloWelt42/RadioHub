// Podcasts der vollen App (RAD-17): eine Quelle gegen das Backend und die eine Aboliste für alle Ansichten.
import { api } from "../api.js";
import { actions } from "../store.svelte.js";
import { appPfad } from "../router.js";
import { Aboliste } from "./abos.svelte";
import { Podcastzustand } from "./ansicht.svelte";
import { BackendPodcastquelle } from "./backend";

export const podcastquelle = new BackendPodcastquelle(api);
export const aboliste = new Aboliste(podcastquelle);
export const podcastzustand = new Podcastzustand({
  pfad: () => appPfad(),
  abfrage: () => window.location.search.replace(/^\?/, ""),
  ersetzen: (pfad) => actions.navigateTo(pfad, { replace: true }),
  neu: (pfad) => actions.navigateTo(pfad),
});

export { Folgenliste } from "./folgenliste.svelte";
export { Merkauftrag } from "./merkauftrag.svelte";
export * from "./ansicht.svelte";
export type { Podcastquelle } from "./quelle";
export * from "./typen";
