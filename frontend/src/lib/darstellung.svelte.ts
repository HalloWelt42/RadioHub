// Darstellung dieses Geräts als Zustand für die Oberfläche: Vorlage (HiFi oder Klassisch, RAD-98, HiFi als Vorgabe),
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

/** die angebotenen Vorlagen (DARSTELLUNG.vorlagen, RAD-98) mit Name, Text und Symbol aus dem Appkern */
export const ANGEBOTENE_VORLAGEN = DARSTELLUNG.vorlagen
  .map((id) => VORLAGEN.find((v) => v.id === id))
  .filter((v): v is (typeof VORLAGEN)[number] => !!v);

// eine nicht angebotene Vorlage ersetzt schon darstellungVorab durch die Vorgabe (auch gemerkt)

// Thema System folgt dem Gerät, auch während die App offen ist
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => darstellungSetzen({}));
