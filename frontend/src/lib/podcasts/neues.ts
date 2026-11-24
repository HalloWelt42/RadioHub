// Neues der letzten 1, 7 und 30 Tage je Abo (RAD-136): ungehörte Folgen, die in der Zeit erschienen sind. Am einzelnen Abo (und am
// Ordner) steht die jüngste Stufe, die etwas hat; insgesamt stehen alle drei.
import type { Abo } from "./typen";

export type Neustufe = "tag" | "woche" | "monat";

export interface Neues {
  tag: number;
  woche: number;
  monat: number;
  ungehoert: number;
}

export const STUFEN: readonly Neustufe[] = ["tag", "woche", "monat"];

export function neues(abos: Pick<Abo, "heuteUngehoert" | "wocheUngehoert" | "monatUngehoert" | "ungehoert">[]): Neues {
  const summe = (wert: (a: (typeof abos)[number]) => number) => abos.reduce((s, a) => s + wert(a), 0);
  return { tag: summe((a) => a.heuteUngehoert), woche: summe((a) => a.wocheUngehoert), monat: summe((a) => a.monatUngehoert), ungehoert: summe((a) => a.ungehoert) };
}

/** die jüngste Stufe mit Neuem, null: in 30 Tagen kam nichts */
export const juengste = (n: Neues): Neustufe | null => STUFEN.find((s) => n[s] > 0) ?? null;
