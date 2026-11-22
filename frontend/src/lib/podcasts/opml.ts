// Abos als OPML-Datei (RAD-102): das übliche Austauschformat der Podcast-Apps. Ausgabe aus den Abos, Einlesen liefert
// nur die Feeds (abonniert wird über die Podcastquelle, in beiden Fassungen gleich).
import type { Abo } from "./typen";

const maskiert = (t: string) =>
  t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function opmlAus(abos: Pick<Abo, "titel" | "feed">[], titel = "RadioHub Podcasts"): string {
  const zeilen = abos.filter((a) => a.feed).map((a) =>
    `    <outline type="rss" text="${maskiert(a.titel)}" title="${maskiert(a.titel)}" xmlUrl="${maskiert(a.feed)}" />`);
  return `<?xml version="1.0" encoding="UTF-8"?>\n<opml version="2.0">\n  <head><title>${maskiert(titel)}</title></head>\n  <body>\n${zeilen.join("\n")}\n  </body>\n</opml>\n`;
}

/** alle Feeds der Datei (auch in verschachtelten Gruppen), ohne Doppel */
export function feedsAus(xml: string, parser: DOMParser): string[] {
  const dok = parser.parseFromString(xml, "application/xml");
  if (dok.getElementsByTagName("parsererror").length || dok.documentElement?.localName !== "opml") return [];
  const feeds = Array.from(dok.getElementsByTagName("outline"))
    .map((o) => (o.getAttribute("xmlUrl") ?? o.getAttribute("xmlurl") ?? "").trim())
    .filter((f) => /^https?:\/\//i.test(f));
  return [...new Set(feeds)];
}
