// Texte vergleichen wie das Backend: Faltung wie str.casefold (Namen, Suche unter drei Zeichen), Suchform wie die
// Volltextsuche mit Trigrammen ohne Diakritika (ab drei Zeichen ein Teilstück irgendwo im Suchtext), Seitenzeiger als
// base64url eines JSON-Felds.

/** klein und gefaltet (ß wird ss), wie str.casefold für die üblichen Schriften */
export function faltung(text: string): string {
  return text.toLowerCase().replace(/ß/g, "ss");
}

/** klein, ohne Diakritika (é wird e, ü wird u), wie die Volltextsuche mit remove_diacritics */
export function suchform(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

/** Leerraum zusammengezogen, wie " ".join(text.split()) */
export function zusammengezogen(text: string): string {
  return text.split(/\s+/).filter((t) => t).join(" ");
}

/** Länge in Zeichen (Codepunkte), wie len() in Python */
export const zeichen = (text: string): number => [...text].length;

export function base64urlKodieren(text: string): string {
  let binaer = "";
  for (const byte of new TextEncoder().encode(text)) binaer += String.fromCharCode(byte);
  return btoa(binaer).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** wirft bei unlesbarem Text */
export function base64urlLesen(text: string): string {
  const binaer = atob(text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4));
  return new TextDecoder("utf-8", { fatal: true }).decode(Uint8Array.from(binaer, (z) => z.charCodeAt(0)));
}

/** Vergleich in Codepunkt-Reihenfolge wie sorted() in Python (für die Texte der Liste ausreichend) */
export const vergleichen = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);
