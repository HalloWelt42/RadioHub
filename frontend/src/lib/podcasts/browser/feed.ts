// Podcast-Feed (RSS 2.0 mit den iTunes-Feldern) im Browser lesen (RAD-102): dieselben Felder wie das Backend
// (backend/app/services/podcast.py, _parse_feed), nur was die Webversion braucht. Kennt kein Netz: der Text kommt von
// außen, das Lesen übernimmt ein DOMParser (im Browser der eigene, in Tests einer aus der Testumgebung).

export interface FeedFolge {
  /** guid, sonst die Adresse der Datei: bleibt über Abrufe gleich */
  guid: string;
  titel: string;
  beschreibung: string;
  /** veröffentlicht (ISO) oder leer */
  datum: string;
  /** Sekunden, 0 unbekannt */
  dauer: number;
  /** Adresse der Audiodatei (enclosure) */
  adresse: string;
  /** Bytes laut Feed, 0 unbekannt */
  groesse: number;
  bild: string;
}

export interface Feedinhalt {
  titel: string;
  autor: string;
  beschreibung: string;
  bild: string;
  folgen: FeedFolge[];
}

export class Feedfehler extends Error {
  constructor(text: string) {
    super(text);
    this.name = "Feedfehler";
  }
}

/** direkte Kinder mit diesem Namen (mit Vorsilbe wie "itunes:image" oder ohne) */
function kinder(el: Element, name: string): Element[] {
  return Array.from(el.children).filter((k) => k.tagName === name || (!name.includes(":") && k.localName === name && !k.prefix));
}

function text(el: Element, ...namen: string[]): string {
  for (const name of namen) {
    const t = kinder(el, name)[0]?.textContent?.trim();
    if (t) return t;
  }
  return "";
}

/** "1:02:03", "62:03" oder "3723" in Sekunden */
export function dauerAus(t: string): number {
  const teile = t.trim().split(":").map((x) => Number(x));
  if (!teile.length || teile.some((x) => !Number.isFinite(x) || x < 0)) return 0;
  return Math.round(teile.reduce((s, x) => s * 60 + x, 0));
}

function datumAus(t: string): string {
  if (!t) return "";
  const d = new Date(t);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString();
}

function bildVon(el: Element): string {
  return kinder(el, "itunes:image")[0]?.getAttribute("href")?.trim() || (kinder(el, "image")[0] && text(kinder(el, "image")[0], "url")) || "";
}

export function feedLesen(xml: string, parser: DOMParser): Feedinhalt {
  const dok = parser.parseFromString(xml, "application/xml");
  if (dok.getElementsByTagName("parsererror").length) throw new Feedfehler("Der Feed ist kein gültiges XML");
  const kanal = dok.documentElement?.localName === "rss" ? kinder(dok.documentElement, "channel")[0] : undefined;
  if (!kanal) throw new Feedfehler("Der Feed ist kein Podcast-Feed (RSS)");
  const folgen: FeedFolge[] = [];
  for (const item of kinder(kanal, "item")) {
    const anhang = kinder(item, "enclosure")[0];
    const adresse = anhang?.getAttribute("url")?.trim() ?? "";
    if (!adresse) continue;
    folgen.push({
      guid: text(item, "guid") || adresse,
      titel: text(item, "title"),
      beschreibung: text(item, "description", "itunes:summary", "content:encoded"),
      datum: datumAus(text(item, "pubDate")),
      dauer: dauerAus(text(item, "itunes:duration")),
      adresse,
      groesse: Math.max(0, Number(anhang?.getAttribute("length")) || 0),
      bild: kinder(item, "itunes:image")[0]?.getAttribute("href")?.trim() ?? "",
    });
  }
  return {
    titel: text(kanal, "title"),
    autor: text(kanal, "itunes:author", "author"),
    beschreibung: text(kanal, "description", "itunes:summary"),
    bild: bildVon(kanal),
    folgen,
  };
}
