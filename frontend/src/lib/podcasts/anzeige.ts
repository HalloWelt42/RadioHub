// Anzeigeformen der Podcasts (RAD-17), eine Stelle für Rechner und Telefon: Minuten, Datum, Stand, Megabyte, Text aus HTML.
import type { Folge } from "./typen";

export const minuten = (sekunden: number) => Math.max(0, Math.round(sekunden / 60));

/** "1 h 40 min" oder "48 min" */
export function dauerText(sekunden: number): string {
  const m = minuten(sekunden);
  return m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`;
}

/** "12:03" (Minuten:Sekunden) oder "1:02:03" */
export function stelleText(sekunden: number): string {
  const s = Math.max(0, Math.floor(sekunden)), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
  const zwei = (n: number) => String(n).padStart(2, "0");
  return h ? `${h}:${zwei(m)}:${zwei(r)}` : `${m}:${zwei(r)}`;
}

/** Tage seit dem Datum, bezogen auf `heute` (0 heute, 1 gestern), null ohne Datum */
export function tageHer(datum: string, heute = new Date()): number | null {
  const d = new Date(datum.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return null;
  const tag = (x: Date) => Date.UTC(x.getFullYear(), x.getMonth(), x.getDate());
  return Math.round((tag(heute) - tag(d)) / 86_400_000);
}

export type Standart = "gehoert" | "neu" | "laeuft";
export function standVon(f: Folge): { art: Standart; anteil: number; rest: number } {
  if (f.gehoert || (f.dauer > 0 && f.stelle >= f.dauer - 5)) return { art: "gehoert", anteil: 1, rest: 0 };
  if (!f.stelle) return { art: "neu", anteil: 0, rest: f.dauer };
  return { art: "laeuft", anteil: f.dauer ? Math.min(1, f.stelle / f.dauer) : 0, rest: Math.max(0, f.dauer - f.stelle) };
}

export const megabyte = (bytes: number) => Math.max(1, Math.round(bytes / 1_000_000));

/** sichtbarer Text einer Beschreibung in HTML (DOMParser lädt nichts und führt nichts aus) */
export function textAus(html: string): string {
  if (!html) return "";
  if (typeof DOMParser === "undefined") return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  return (new DOMParser().parseFromString(html, "text/html").body.textContent || "").replace(/\s+/g, " ").trim();
}

/** Datum kurz: "9. Apr."; aus einem anderen Jahr mit Jahr ("9. Sept. 2025") */
export function datumKurz(datum: string, heute = new Date()): string {
  const d = new Date(datum.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", ...(d.getFullYear() !== heute.getFullYear() ? { year: "numeric" } : {}) });
}
