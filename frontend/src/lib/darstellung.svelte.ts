// Darstellung dieses Geräts als Zustand für die Oberfläche: Vorlage (aus den Vorlagen des Appkerns, HiFi als Vorgabe),
// Thema (Hell, Dunkel, System) und Schriftstufe (Normal, Groß, Sehr groß), gemerkt im Browser. Angewendet wird schon
// vor dem Einhängen (Skript im Kopf der Startseite, lib/darstellung-vorab.ts); hier Wahl, Prüfung der Vorlage gegen die
// Liste des Appkerns und die Folge des Systemthemas.
import { VORLAGEN } from "appkern-oberflaeche";
import { DARSTELLUNG, darstellungVorab, type DarstellungsStand } from "./darstellung-vorab";

export const darstellung = $state<DarstellungsStand>(darstellungVorab(DARSTELLUNG));

export function darstellungSetzen(wahl: Partial<DarstellungsStand>): void {
  Object.assign(darstellung, darstellungVorab(DARSTELLUNG, wahl));
}

/** Stufe der Schrift um `schritt` verschieben; am Rand bleibt sie stehen */
export function schriftSchritt(schritt: number): void {
  const i = DARSTELLUNG.stufen.indexOf(darstellung.schrift) + schritt;
  if (i >= 0 && i < DARSTELLUNG.stufen.length) darstellungSetzen({ schrift: DARSTELLUNG.stufen[i] });
}

export function schriftAmRand(schritt: number): boolean {
  const i = DARSTELLUNG.stufen.indexOf(darstellung.schrift) + schritt;
  return i < 0 || i >= DARSTELLUNG.stufen.length;
}

// eine nicht mehr angebotene Vorlage gilt als die Vorgabe
if (!VORLAGEN.some((v) => v.id === darstellung.vorlage)) darstellungSetzen({ vorlage: DARSTELLUNG.vorgabe.vorlage });

// Thema System folgt dem Gerät, auch während die App offen ist
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => darstellungSetzen({}));
