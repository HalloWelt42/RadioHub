// Alle Gestaltungen der Weckansicht an einer Stelle (RAD-15): Reihenfolge beim Blättern per Seitenwischen, Name, Klasse
// der Farben (stil/weckansicht.css) und Komponente. Eine neue Gestaltung kommt nur hier hinzu.
import type { Component } from "svelte";
import type { Gestaltungsprops } from "./typen";
import GUhr from "./GUhr.svelte";
import GMatrix from "./GMatrix.svelte";
import GHifi from "./GHifi.svelte";
import GSegment from "./GSegment.svelte";
import GRuhig from "./GRuhig.svelte";
import GSterne from "./GSterne.svelte";
import GAstro from "./GAstro.svelte";
import GAurora from "./GAurora.svelte";
import GRoehren from "./GRoehren.svelte";
import GPixel from "./GPixel.svelte";

export interface Gestaltung {
  id: string;
  /** Schlüssel des Namens unter telefon.gestaltung */
  name: string;
  /** Klasse der Farben an der Wurzel */
  klasse: string;
  komponente: Component<Gestaltungsprops>;
  /** zeigt die Tasten der ruhigen Ansicht erst nach Antippen */
  tastenNachTippen?: boolean;
  /** ein Leuchtfeld ist immer dunkel, auch im Hellmodus */
  immerDunkel?: boolean;
}

export const GESTALTUNGEN: Gestaltung[] = [
  { id: "ruhig", name: "ruhig", klasse: "g-ruhig", komponente: GRuhig },
  { id: "uhr", name: "uhr", klasse: "g-uhr", komponente: GUhr, tastenNachTippen: true },
  { id: "matrix", name: "matrix", klasse: "g-matrix", komponente: GMatrix, tastenNachTippen: true },
  { id: "hifi", name: "hifi", klasse: "g-hifi", komponente: GHifi },
  { id: "segment", name: "segment", klasse: "g-segment", komponente: GSegment },
  { id: "sterne", name: "sterne", klasse: "g-sterne", komponente: GSterne },
  { id: "astro", name: "astro", klasse: "g-astro", komponente: GAstro },
  { id: "aurora", name: "aurora", klasse: "g-aurora", komponente: GAurora, tastenNachTippen: true },
  { id: "roehren", name: "roehren", klasse: "g-roehren", komponente: GRoehren, tastenNachTippen: true },
  { id: "pixel", name: "pixel", klasse: "g-pixel", komponente: GPixel, tastenNachTippen: true, immerDunkel: true },
];

/** Gemerkte Wahl lesen; frühere Namen ("sonne" war die Ansicht vor D Ruhig) führen zur heutigen Gestaltung */
export function gestaltungVon(gemerkt: string | null): Gestaltung {
  const id = gemerkt === "sonne" ? "ruhig" : gemerkt;
  return GESTALTUNGEN.find((g) => g.id === id) ?? GESTALTUNGEN[0];
}

/** die nächste (schritt 1) oder vorige (-1) Gestaltung im Kreis */
export function naechste(aktuell: Gestaltung, schritt: number): Gestaltung {
  const i = GESTALTUNGEN.indexOf(aktuell);
  return GESTALTUNGEN[(i + schritt + GESTALTUNGEN.length) % GESTALTUNGEN.length];
}
