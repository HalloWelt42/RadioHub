// Darstellung dieses Geräts (Vorlage, Thema, Schriftstufe): Schlüssel, Stufen und das Anwenden auf das Wurzelelement.
// Die Vorlage liegt unter dem Schlüssel des Appkerns (appkern_vorlage, wie seine lib/vorlage.svelte.ts und seine
// Ansichtsprüfung ihn nutzen). Eine Wahrheit für zwei Wege: vite.config.ts setzt `darstellungVorab` mit `DARSTELLUNG`
// als kleines Skript in den Kopf der Startseite (vor jeder Gestaltung, damit nichts aufblitzt), lib/darstellung.svelte.ts
// nutzt dieselbe Funktion beim Umschalten. Die Funktion ist darum in sich geschlossen (keine Verweise nach außen, sie
// wird als Text eingesetzt).

export interface DarstellungsWerte {
  /** Schlüssel im Browser je Art */
  schluessel: { thema: string; schrift: string; vorlage: string };
  /** frühere Ablage des Themas (bis RAD-6: "dark" oder "light"), wird einmal übernommen */
  frueher: string;
  themen: readonly string[];
  stufen: readonly string[];
  /** angebotene Vorlagen des Appkerns (RAD-98: HiFi und Klassisch), in dieser Reihenfolge */
  vorlagen: readonly string[];
  vorgabe: { thema: string; schrift: string; vorlage: string };
}

export interface DarstellungsStand {
  thema: string;
  schrift: string;
  vorlage: string;
}

export const DARSTELLUNG: DarstellungsWerte = {
  schluessel: { thema: "radiohub_thema", schrift: "radiohub_schrift", vorlage: "appkern_vorlage" },
  frueher: "radiohub-theme",
  themen: ["hell", "dunkel", "system"],
  // ab mittel: Grundschrift 17, klein 15 Pixel (Hausregel große Schrift); sehr-gross aus den Marken des Appkerns
  stufen: ["mittel", "gross", "sehr-gross"],
  // nur diese Vorlagen bietet RadioHub an (Nutzer 22.11.2026, RAD-98); eine früher gewählte andere gilt als die Vorgabe
  vorlagen: ["hifi", "klassisch"],
  vorgabe: { thema: "system", schrift: "mittel", vorlage: "hifi" },
};

/** Liest die Wahl dieses Geräts (mit `wahl` statt dessen eine neue), merkt sie und setzt die Merkmale am Wurzelelement.
 *  Eine nicht angebotene Vorlage gilt als die Vorgabe (klassisch ist das Grunddesign des Appkerns, ohne Merkmal). */
export function darstellungVorab(w: DarstellungsWerte, wahl?: Partial<DarstellungsStand>): DarstellungsStand {
  const lesen = (k: string): string | null => {
    try {
      return localStorage.getItem(k);
    } catch {
      return null;
    }
  };
  const merken = (k: string, v: string): void => {
    try {
      localStorage.setItem(k, v);
    } catch {
      // ohne Speicher gilt die Wahl bis zum Neuladen
    }
  };
  const frueher = lesen(w.frueher);
  const stand: DarstellungsStand = {
    thema: lesen(w.schluessel.thema) ?? (frueher === "dark" ? "dunkel" : frueher === "light" ? "hell" : w.vorgabe.thema),
    schrift: lesen(w.schluessel.schrift) ?? w.vorgabe.schrift,
    vorlage: lesen(w.schluessel.vorlage) ?? w.vorgabe.vorlage,
  };
  if (wahl) {
    for (const art of ["thema", "schrift", "vorlage"] as const) {
      const neu = wahl[art];
      if (neu !== undefined) {
        stand[art] = neu;
        merken(w.schluessel[art], neu);
      }
    }
  }
  if (!w.themen.includes(stand.thema)) stand.thema = w.vorgabe.thema;
  if (!w.stufen.includes(stand.schrift)) stand.schrift = w.vorgabe.schrift;
  if (!w.vorlagen.includes(stand.vorlage)) {
    stand.vorlage = w.vorgabe.vorlage;
    merken(w.schluessel.vorlage, stand.vorlage);      // auch der Appkern liest diesen Schlüssel
  }
  const dunkel = stand.thema === "dunkel" || (stand.thema === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  const wurzel = document.documentElement;
  wurzel.dataset.theme = dunkel ? "dunkel" : "hell";
  wurzel.dataset.schrift = stand.schrift;
  if (stand.vorlage === "klassisch") delete wurzel.dataset.vorlage;
  else wurzel.dataset.vorlage = stand.vorlage;
  return stand;
}
