// Verdrahtung der Senderquelle: welche Umsetzung gilt, sagt das Bauziel ($ziel/quelle: Backend in der vollen App,
// statische Liste in der Webversion, RAD-4); der Zustand der Schnellfilter steht an der Adresse des Browsers. Die
// Ansichten kennen nur diese Stelle.
import { actions } from "../store.svelte.js";
import { appPfad } from "../router.js";
import { Filterzustand } from "./filterzustand.svelte";
import { senderquelle } from "$ziel/quelle";
import { Werbeerkennung } from "./werbeerkennung";

export { senderquelle };

export const filterzustand = new Filterzustand({
  pfad: () => appPfad(),
  abfrage: () => window.location.search.replace(/^\?/, ""),
  ersetzen: (pfad) => actions.navigateTo(pfad, { replace: true }),
  neu: (pfad) => actions.navigateTo(pfad),
});

/** nur in der vollen App (Einstellungen > Radio) */
export const werbeerkennung = new Werbeerkennung();

export type * from "./quelle";
export type * from "./typen";
