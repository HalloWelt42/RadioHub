// Warum die Liste der Folgen leer ist und wohin ein Klick führt (RAD-149): ohne Abos zur Suche im Verzeichnis, sonst zurück zu dem,
// was den Folgen im Weg steht (Suche, Ungehört, Gespeichert, Auswahl der Abos). Eine Regel für Rechner und Telefon, Basic und PRO.
import type { Podcastansicht } from "./ansicht.svelte";

export type Leergrund = "ohneAbos" | "suche" | "ungehoert" | "gespeichert" | "auswahl" | "ohneFolgen";

export interface Leerhinweis {
  grund: Leergrund;
  symbol: string;
  /** was der Klick aus der Ansicht macht */
  weiter: (a: Podcastansicht) => Podcastansicht;
}

const ALLE = (a: Podcastansicht): Podcastansicht => ({ ...a, wahl: "alle", offen: null });

export function leerhinweis(abos: number, a: Podcastansicht): Leerhinweis {
  if (!abos) return { grund: "ohneAbos", symbol: "fa-podcast", weiter: (x) => ({ ...x, verzeichnis: true, aboUebersicht: false, offen: null }) };
  if (a.suche.trim()) return { grund: "suche", symbol: "fa-magnifying-glass", weiter: (x) => ({ ...x, suche: "" }) };
  if (a.wahl === "ungehoert") return { grund: "ungehoert", symbol: "fa-circle-check", weiter: ALLE };
  if (a.wahl === "gespeichert") return { grund: "gespeichert", symbol: "fa-cloud", weiter: ALLE };
  if (a.abos.length) return { grund: "auswahl", symbol: "fa-filter-circle-xmark", weiter: (x) => ({ ...x, abos: [], offen: null }) };
  return { grund: "ohneFolgen", symbol: "fa-rotate", weiter: (x) => x };
}
