// Verdrahtung der Senderquelle in der vollen App: die Umsetzung gegen das Backend, der Zustand der Schnellfilter an der
// Adresse des Browsers. Die Webversion (RAD-4) setzt hier ihre eigene Umsetzung ein; die Ansichten bleiben dieselben.
import { actions } from "../store.svelte.js";
import { BackendQuelle } from "./backend";
import { Filterzustand } from "./filterzustand.svelte";
import type { Senderquelle } from "./quelle";
import { Werbeerkennung } from "./werbeerkennung";

export const senderquelle: Senderquelle = new BackendQuelle({ beiFavoriten: () => void actions.loadFavorites() });

export const filterzustand = new Filterzustand({
  pfad: () => window.location.pathname,
  abfrage: () => window.location.search.replace(/^\?/, ""),
  ersetzen: (pfad) => actions.navigateTo(pfad, { replace: true }),
  neu: (pfad) => actions.navigateTo(pfad),
});

/** nur in der vollen App (Einstellungen > Radio) */
export const werbeerkennung = new Werbeerkennung();

export type * from "./quelle";
export type * from "./typen";
