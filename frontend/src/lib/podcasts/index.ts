// Podcasts der vollen App (RAD-17): eine Quelle gegen das Backend und die eine Aboliste für alle Ansichten.
import { api } from "../api.js";
import { Aboliste } from "./abos.svelte";
import { BackendPodcastquelle } from "./backend";

export const podcastquelle = new BackendPodcastquelle(api);
export const aboliste = new Aboliste(podcastquelle);

export { Folgenliste } from "./folgenliste.svelte";
export type { Podcastquelle } from "./quelle";
export * from "./typen";
