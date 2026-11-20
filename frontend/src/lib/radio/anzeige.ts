// Darstellung der Senderdaten, an einer Stelle für Rechner und Telefon: Zahlen, Ländernamen, Kürzel und Lackfarbe der
// Logos ohne Bild, Qualitätsstufen als Lichterleiste, Namen der Bewertungen. Ohne Bausteine der Oberfläche.
import { currentLanguage, t } from "../i18n.js";
import type { Bewertung, Qualitaet, RegelArt, SenderEintrag } from "./typen";

export const zahl = (n: number): string => n.toLocaleString(currentLanguage() === "de" ? "de-DE" : currentLanguage());

const namen = new Map<string, Intl.DisplayNames | null>();
/** Name eines Landes in der Sprache der Oberfläche; ohne Übersetzung der Name des Verzeichnisses */
export function landName(code: string, ersatz = ""): string {
  const sprache = currentLanguage();
  if (!namen.has(sprache)) {
    try { namen.set(sprache, new Intl.DisplayNames([sprache], { type: "region" })); } catch { namen.set(sprache, null); }
  }
  if (!/^[A-Z]{2}$/.test(code)) return ersatz || code;
  try { return namen.get(sprache)?.of(code) ?? ersatz ?? code; } catch { return ersatz || code; }
}

/** Kürzel aus dem Namen (für Logos ohne Bild): Zahl im Namen vorn, sonst die ersten Buchstaben zweier Wörter */
export function kuerzel(name: string): string {
  const teile = name.replace(/[.\-_|/]/g, " ").split(/\s+/).filter((t) => /[\p{L}\p{N}]/u.test(t));
  if (!teile.length) return "?";
  if (/^\d/.test(teile[0])) return teile[0].slice(0, 3);
  const zahlTeil = teile.find((t) => /^\d+$/.test(t));
  if (zahlTeil) return (teile[0][0] + zahlTeil).toUpperCase().slice(0, 3);
  return teile.slice(0, 2).map((t) => [...t][0]).join("").toUpperCase();
}

/** Lackfarbe aus dem Namen (gleicher Name, gleiche Farbe), Marken --rh-lack-1 bis --rh-lack-10 */
export function lack(name: string): string {
  let h = 0;
  for (const z of name) h = (h * 31 + (z.codePointAt(0) ?? 0)) >>> 0;
  return `var(--rh-lack-${(h % 10) + 1})`;
}


export const QUALITAET: Record<Qualitaet, { lichter: number; farbe: string }> = {
  verlustfrei: { lichter: 4, farbe: "cyan" },
  hoch: { lichter: 3, farbe: "gruen" },
  mittel: { lichter: 2, farbe: "gelb" },
  niedrig: { lichter: 1, farbe: "bernstein" },
  unbekannt: { lichter: 0, farbe: "weiss" },
};

export const qualitaetName = (q: Qualitaet): string => t(`radio.qualitaet.${q}`);

/** Codec und Bitrate kurz: "AAC 128", ohne Messung "MP3 ?" */
export function format(e: Pick<SenderEintrag, "codec" | "kbps">): string {
  const codec = e.codec && e.codec !== "unbekannt" ? e.codec : "?";
  return e.kbps ? `${codec} ${zahl(e.kbps)}` : `${codec} ?`;
}

export const MARKIERUNGEN = ["werbung", "religioes", "politisch_extrem", "populistisch", "nicht_jugendfrei", "schlechte_qualitaet",
  "schwankende_qualitaet", "haeufig_offline", "hoher_sprachanteil"] as const satisfies readonly Bewertung[];

/** Sterne einer Bewertung (sterne:1 bis sterne:3), sonst 0 */
export const sterneVon = (b: string): number => (b.startsWith("sterne:") ? Number(b.slice(7)) : 0);

export const bewertungName = (b: string): string => t(`radio.bewertung.${b.replace(":", "_")}`);

export const REGEL_SYMBOL: Record<RegelArt, string> = {
  sprache: "fa-language", genre: "fa-tag", tag: "fa-hashtag", stimmen: "fa-thumbs-up", werbung: "fa-rectangle-ad",
  bewertung: "fa-star", einzeln: "fa-eye-slash", altsperren: "fa-box-archive",
};

/** Ort eines Senders: Region oder Bundesland, sonst das Land */
export function ort(e: Pick<SenderEintrag, "bundesland" | "region" | "land" | "land_name">): string {
  return e.bundesland || landName(e.land, e.land_name);
}
