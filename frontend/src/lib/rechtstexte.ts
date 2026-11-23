// Rechtstexte und Hinweise aus /legal/<sprache>/ (RAD-11, RAD-123): in der Sprache der Oberfläche, sonst Englisch, sonst
// Deutsch. Welche Texte eine Ausgabe zeigt, sagt ihr Bauziel ($ziel/einstellungen).
import { parseMarkdown } from "./markdown.js";

async function laden(datei: string, sprache: string): Promise<string> {
  for (const s of [...new Set([sprache, "en", "de"])]) {
    try {
      const r = await fetch(`${import.meta.env.BASE_URL}legal/${s}/${datei}`);
      if (r.ok) return await r.text();
    } catch { /* nächste Sprache */ }
  }
  return "";
}

/** die Texte in ihrer Reihenfolge als HTML, durch eine Linie getrennt; "", wenn keiner zu holen ist */
export async function rechtstexte(dateien: readonly string[], sprache: string): Promise<string> {
  const teile = await Promise.all(dateien.map((d) => laden(d, sprache)));
  return teile.filter(Boolean).map((md) => parseMarkdown(md)).join("<hr>");
}
