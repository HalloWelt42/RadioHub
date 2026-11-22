// Was die Webversion über Podcasts im Browser behält (RAD-102): Abos mit den eigenen Angaben, Ordner und je Folge Stelle
// und gehört. Die Folgen selbst nicht: sie kommen bei jedem Start frisch aus dem Feed. Ein Schlüssel, ein JSON.
import type { Speicher } from "../../radio/statisch/speicher";
import type { Ordner, Podcastsortierung } from "../typen";

export const PODCAST_SCHLUESSEL = "radiohub.web.podcasts";

export interface AboDaten {
  id: number;
  feed: string;
  titel: string;
  autor: string;
  beschreibung: string;
  bild: string;
  angeheftet: boolean;
  sortierung: Podcastsortierung | "";
  ordnerId: string | null;
  /** zuletzt aus dem Feed gelesen (ISO) oder leer */
  aktualisiert: string;
}

/** Stand einer Folge; `a` ist das Abo (zum Aufräumen beim Abbestellen) */
export interface FolgenDaten {
  a: number;
  stelle: number;
  gehoert: boolean;
}

export interface Podcastablage {
  abos: AboDaten[];
  ordner: Ordner[];
  folgen: Record<string, FolgenDaten>;
}

const leer = (): Podcastablage => ({ abos: [], ordner: [], folgen: {} });

export function ablageLesen(speicher: Speicher): Podcastablage {
  try {
    const roh = JSON.parse(speicher.lesen(PODCAST_SCHLUESSEL) ?? "null") as Partial<Podcastablage> | null;
    if (!roh || typeof roh !== "object") return leer();
    return { abos: Array.isArray(roh.abos) ? roh.abos : [], ordner: Array.isArray(roh.ordner) ? roh.ordner : [],
             folgen: roh.folgen && typeof roh.folgen === "object" ? roh.folgen : {} };
  } catch {
    return leer();
  }
}

export function ablageSchreiben(speicher: Speicher, ablage: Podcastablage): void {
  speicher.schreiben(PODCAST_SCHLUESSEL, JSON.stringify(ablage));
}

/** feste Kennung aus Text (53 Bit, cyrb53): dieselbe Adresse gibt auf jedem Gerät dieselbe Zahl */
export function kennung(text: string): number {
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 2654435761);
    h2 = Math.imul(h2 ^ c, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return 4294967296 * (2097151 & h2) + (h1 >>> 0);
}
