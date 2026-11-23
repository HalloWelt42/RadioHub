// Aufnahmen der vollen App (RAD-17): eine Quelle gegen das Backend, Liste, Ordner und Ansicht für alle Teile.
import { api } from "../api.js";
import { actions } from "../store.svelte.js";
import { appPfad } from "../router.js";
import { BackendAufnahmequelle } from "./backend";
import { Aufnahmeliste, Aufnahmezustand, Ordnerliste } from "./zustand.svelte";

export const aufnahmequelle = new BackendAufnahmequelle(api);
export const aufnahmeliste = new Aufnahmeliste(aufnahmequelle);
export const ordnerliste = new Ordnerliste(aufnahmequelle);
export const aufnahmezustand = new Aufnahmezustand({
  pfad: () => appPfad(),
  abfrage: () => window.location.search.replace(/^\?/, ""),
  ersetzen: (pfad) => actions.navigateTo(pfad, { replace: true }),
  neu: (pfad) => actions.navigateTo(pfad),
});

export * from "./zustand.svelte";
export type { Aufnahmequelle, Aufnahmefaehigkeiten } from "./quelle";
export * from "./typen";
export * from "./spielreihe";
