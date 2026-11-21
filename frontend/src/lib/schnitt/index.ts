// Schnitt (RAD-17): Quelle gegen das Backend und der Zustand des Arbeitsplatzes.
import { api } from "../api.js";
import { BackendSchnittquelle } from "./quelle";

export const schnittquelle = new BackendSchnittquelle(api.baseUrl);
export { Arbeitsplatz, KLEINSTER_AUSSCHNITT, type Stueck } from "./arbeitsplatz.svelte";
export * from "./quelle";
