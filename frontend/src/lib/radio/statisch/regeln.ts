// Lebende Regeln im Browser (wie backend/app/services/senderquelle/regeln.py und die Prüfung der Entwürfe in
// modelle.py): Entwurf prüfen und in die Form des Backends bringen, Inhalt für "gibt es schon", Titel in Worten und
// die getroffenen Sender. Regeln gelten für die ganze Liste, auch nach einer neuen Liste (Treffer entstehen neu).
// Ohne Werbung (keine Werbeerkennung in der Webversion) und ohne Altbestand.
import type {
  Bewertung, BewertungEntwurf, GenreEntwurf, RegelArt, RegelEntwurf, SpracheEntwurf, StimmenEntwurf, TagEntwurf, WerbungEntwurf,
} from "../typen";
import type { EigeneAngaben } from "./angaben";
import { Quellfehler } from "./fehler";
import { FREI, sprachname, type Senderbestand } from "./format";
import { vergleichen } from "./text";

export const EINZELSPERREN = "einzelsperren";

/** Arten, die die Webversion kennt */
export type StatischeArt = Exclude<RegelArt, "werbung" | "altsperren">;
export const ARTEN: readonly StatischeArt[] = ["sprache", "genre", "tag", "stimmen", "bewertung", "einzeln"];
/** Entwürfe, die die Webversion kennt */
export type StatischerEntwurf = Exclude<RegelEntwurf, WerbungEntwurf>;

/** Eigene Bewertungen mit Namen (wie BEWERTUNGEN im Backend, in dieser Reihenfolge) */
export const BEWERTUNGEN: Readonly<Record<Bewertung, string>> = {
  "sterne:3": "Sehr gut", "sterne:2": "Gut", "sterne:1": "Geht so", werbung: "Werbung", religioes: "Religiös",
  politisch_extrem: "Politisch extrem", populistisch: "Populistisch", nicht_jugendfrei: "Nicht jugendfrei",
  schlechte_qualitaet: "Schlechte Qualität", schwankende_qualitaet: "Schwankende Qualität",
  haeufig_offline: "Häufig nicht erreichbar", hoher_sprachanteil: "Hoher Sprachanteil",
};
export const istBewertung = (w: unknown): w is Bewertung => typeof w === "string" && Object.hasOwn(BEWERTUNGEN, w);

export const ERKLAERUNG: Readonly<Record<StatischeArt, string>> = {
  sprache: "exakter Sprachcode oder Eintrag, Sender ohne Angabe bleiben sichtbar",
  genre: "normalisiertes Genre, alle Schreibweisen",
  tag: "genauer Tag des Senderverzeichnisses",
  stimmen: "gilt auch für neue Sender",
  bewertung: "eigene Bewertungen",
  einzeln: "per Auge ausgeblendet",
};

// ----- Entwurf prüfen ---------------------------------------------------------------------------------------------

const ungueltig = (text: string): Quellfehler => new Quellfehler(text, 422);

function textliste(roh: unknown, feld: string, min: number, max: number): string[] {
  if (roh === undefined && min === 0) return [];
  if (!Array.isArray(roh)) throw ungueltig(`${feld}: Liste erwartet`);
  if (roh.length < min || roh.length > max) throw ungueltig(`${feld}: ${min} bis ${max} Einträge erwartet`);
  for (const w of roh) {
    if (typeof w !== "string" || [...w].length < 1 || [...w].length > 120) throw ungueltig(`${feld}: Texte mit 1 bis 120 Zeichen erwartet`);
  }
  return roh as string[];
}

/** sortiert und ohne Doppel, wie sorted(set(...)) */
const geordnet = (werte: string[]): string[] => [...new Set(werte)].sort(vergleichen);

/** Ein Entwurf in der Form des Backends (geprüft, Sprachen und Tags klein und sortiert); wirft bei ungültigen Werten. */
export function entwurfPruefen(roh: unknown): StatischerEntwurf {
  if (typeof roh !== "object" || roh === null) throw ungueltig("Entwurf erwartet");
  const e = roh as Record<string, unknown>;
  switch (e.art) {
    case "sprache": {
      const klein = (liste: string[]) => geordnet(liste.filter((w) => w.trim()).map((w) => w.trim().toLowerCase()));
      return { art: "sprache", schluessel: klein(textliste(e.schluessel, "schluessel", 0, 100)),
               eintraege: klein(textliste(e.eintraege, "eintraege", 0, 2000)) } satisfies SpracheEntwurf;
    }
    case "genre":
      return { art: "genre", genres: textliste(e.genres, "genres", 1, 50) } satisfies GenreEntwurf;
    case "tag": {
      const tags = textliste(e.tags, "tags", 1, 500).filter((w) => w.trim())
        .map((w) => w.trim().toLowerCase().replace(/^#+/, "").split(/\s+/).filter((t) => t).join(" "));
      return { art: "tag", tags: geordnet(tags) } satisfies TagEntwurf;
    }
    case "stimmen": {
      const n = e.mindeststimmen;
      if (typeof n !== "number" || !Number.isInteger(n) || n < 1 || n > 1_000_000) throw ungueltig("mindeststimmen: ganze Zahl von 1 bis 1.000.000");
      return { art: "stimmen", mindeststimmen: n } satisfies StimmenEntwurf;
    }
    case "bewertung": {
      const liste = e.bewertungen;
      if (!Array.isArray(liste) || liste.length < 1 || liste.length > 20) throw ungueltig("bewertungen: 1 bis 20 Einträge erwartet");
      const unbekannt = liste.filter((b) => !istBewertung(b));
      if (unbekannt.length) throw ungueltig(`Unbekannte Bewertung: ${unbekannt.join(", ")}`);
      return { art: "bewertung", bewertungen: liste as Bewertung[] } satisfies BewertungEntwurf;
    }
    case "werbung":
      throw new Quellfehler("Regeln zur Werbung gibt es in der Webversion nicht");
    default:
      throw ungueltig(`Unbekannte Art: ${String(e.art)}`);
  }
}

/** Inhalt eines Entwurfs ohne die Art, mit sortierten Schlüsseln (wie entwurf_speichern): gleich heißt gleiche Regel */
export function inhalt(entwurf: RegelEntwurf): string {
  const { art: _art, ...rest } = entwurf;
  const felder = rest as Record<string, unknown>;
  return JSON.stringify(Object.fromEntries(Object.keys(felder).sort().map((k) => [k, felder[k]])));
}

// ----- Titel ------------------------------------------------------------------------------------------------------

function aufzaehlung(werte: string[], grenze = 4): string {
  if (werte.length <= grenze) return werte.join(", ");
  return `${werte.slice(0, grenze).join(", ")} und ${werte.length - grenze} weitere`;
}

/** Die Regel in Worten, wie die Oberfläche sie zeigt */
export function titel(b: Senderbestand, art: RegelArt, entwurf: RegelEntwurf | null): string {
  const name = (code: string) => sprachname(b.kopf, code);
  switch (entwurf?.art) {
    case "sprache": {
      const codes = new Set(entwurf.eintraege.map((e) => b.kopf.eintragscodes[e] ?? null));
      const [code] = [...codes];
      if (!entwurf.schluessel.length && entwurf.eintraege.length > 1 && codes.size === 1 && code !== null) {
        return `Sprache ist ${name(code)}, genau die Einträge ${aufzaehlung(entwurf.eintraege.map((e) => `"${e}"`))}`;
      }
      const namen = entwurf.schluessel.map((s) => (s.startsWith(FREI) ? s.slice(FREI.length) : `${name(s)} (${s})`));
      return `Sprache ist ${aufzaehlung([...namen, ...entwurf.eintraege.map((e) => `"${e}"`)])}`;
    }
    case "genre": return `Genre ist ${aufzaehlung(entwurf.genres)}`;
    case "tag": return `Tag ist ${aufzaehlung(entwurf.tags)}`;
    case "stimmen": return `weniger als ${entwurf.mindeststimmen} Stimmen`;
    case "bewertung": return `eigene Bewertung ${aufzaehlung(entwurf.bewertungen.map((x) => BEWERTUNGEN[x]))}`;
    default: return art === "einzeln" ? "Einzelsperren" : art;
  }
}

// ----- Treffer ----------------------------------------------------------------------------------------------------

function vereinigt(index: Map<string, number[]>, werte: string[]): Int32Array {
  const menge = new Set<number>();
  for (const w of werte) for (const i of index.get(w) ?? []) menge.add(i);
  return Int32Array.from(menge).sort();
}

function aus(b: Senderbestand, uuids: Iterable<string>): Int32Array {
  const menge = new Set<number>();
  for (const u of uuids) {
    const i = b.nachUuid.get(u);
    if (i !== undefined) menge.add(i);
  }
  return Int32Array.from(menge).sort();
}

/** Die Sender (Zeilennummern, aufsteigend), die eine Regel trifft, ob ein- oder ausgeschaltet */
export function treffer(b: Senderbestand, a: EigeneAngaben, art: StatischeArt, entwurf: RegelEntwurf | null): Int32Array {
  switch (entwurf?.art) {
    case "sprache": {
      const s = vereinigt(b.mitSprache, entwurf.schluessel);
      const e = vereinigt(b.mitEintrag, entwurf.eintraege);
      return Int32Array.from(new Set([...s, ...e])).sort();
    }
    case "genre": return vereinigt(b.mitGenre, entwurf.genres);
    case "tag": return vereinigt(b.mitTag, entwurf.tags);
    case "stimmen": {
      const liste: number[] = [];
      for (let i = 0; i < b.anzahl; i++) if (b.stimmen[i] < entwurf.mindeststimmen) liste.push(i);
      return Int32Array.from(liste);
    }
    case "bewertung": {
      const gesucht = new Set<string>(entwurf.bewertungen);
      return aus(b, Object.entries(a.bewertungen).filter(([, liste]) => liste.some((x) => gesucht.has(x))).map(([u]) => u));
    }
    default:
      if (art === "einzeln") return aus(b, a.sperren);
      throw new Quellfehler(`Unbekannte Art: ${art}`);
  }
}
