// Schnitt (RAD-17): ein Weg für Aufnahmen und Dateien der Kellerwolke (Backend /api/schnitt). Lange Arbeiten
// (Schneiden, Normalisieren, Umwandeln) melden ihren Fortschritt als Ereignisstrom.
import { antwortPruefen, kopf } from "../sitzung";
import { ereignisse, fehlerText, type Fortschritt } from "../ereignisstrom";

export type { Fortschritt };

export interface Schnittgegenstand {
  art: "sitzung" | "datei";
  /** Kennung der Aufnahme oder Pfad der Datei in der Kellerwolke */
  kennung: string;
}

export interface Schnittinfo {
  art: Schnittgegenstand["art"];
  kennung: string;
  titel: string;
  zeit: string | null;
  format: string;
  bitrate: number | null;
  dauer: number;
  /** die bisherigen Stücke (Aufnahme) oder die ganze Datei */
  stuecke: { von: number; bis: number; name: string }[];
  /** beim Aufnehmen erkannte Titelwechsel */
  titelwechsel: { start: number; titel: string }[];
  /** in Worten, wohin Ergebnisse gehen */
  ziel: string;
  neben?: boolean;
  schritte: { id: number; was: string; zeit: string }[];
}

export interface StueckWahl {
  von: number;
  bis: number;
  name: string;
  behalten: boolean;
}


export type Umwandlung = { format: "mp3" | "ogg" | "aac"; bitrate: number; mono: boolean };

export interface Schnittquelle {
  info(g: Schnittgegenstand): Promise<Schnittinfo>;
  /** Abschnitt der Wellenform: 100 Werte je Sekunde, 0 bis 1 */
  wellenform(g: Schnittgegenstand, start: number, dauer: number): Promise<Float32Array>;
  ton(g: Schnittgegenstand): string;
  schneiden(g: Schnittgegenstand, stuecke: StueckWahl[], melden: (f: Fortschritt) => void): Promise<number>;
  normalisieren(g: Schnittgegenstand, melden: (f: Fortschritt) => void): Promise<number>;
  umwandeln(g: Schnittgegenstand, u: Umwandlung, melden: (f: Fortschritt) => void): Promise<number>;
  rueckgaengig(g: Schnittgegenstand): Promise<string>;
}

const parameter = (g: Schnittgegenstand) => new URLSearchParams({ art: g.art, kennung: g.kennung }).toString();

/** Ereignisstrom lesen: done liefert die Zahl der Ergebnisse (gemeinsamer Leser in lib/ereignisstrom) */
export async function strom(antwort: Response, melden: (f: Fortschritt) => void): Promise<number> {
  return Number(await ereignisse<number>(antwort, melden, "count")) || 0;
}

export class BackendSchnittquelle implements Schnittquelle {
  constructor(private readonly basis = "", private readonly abruf: typeof fetch = (w, i) => fetch(w, i)) {}

  private async json<T>(pfad: string, init: RequestInit = {}): Promise<T> {
    const antwort = await this.abruf(`${this.basis}${pfad}`, { ...init, headers: kopf({ "Content-Type": "application/json" }) });
    antwortPruefen(antwort);
    if (!antwort.ok) throw new Error(await fehlerText(antwort));
    return antwort.json();
  }

  private async arbeit(pfad: string, koerper: unknown, melden: (f: Fortschritt) => void): Promise<number> {
    const antwort = await this.abruf(`${this.basis}${pfad}`, { method: "POST", body: JSON.stringify(koerper), headers: kopf({ "Content-Type": "application/json" }) });
    return strom(antwort, melden);
  }

  info(g: Schnittgegenstand): Promise<Schnittinfo> {
    return this.json(`/api/schnitt/info?${parameter(g)}`);
  }

  async wellenform(g: Schnittgegenstand, start: number, dauer: number): Promise<Float32Array> {
    const antwort = await this.abruf(`${this.basis}/api/schnitt/wellenform?${parameter(g)}&start=${start}&dauer=${dauer}`, { headers: kopf() });
    antwortPruefen(antwort);
    if (!antwort.ok) throw new Error(await fehlerText(antwort));
    return new Float32Array(await antwort.arrayBuffer());
  }

  ton(g: Schnittgegenstand): string {
    return `${this.basis}/api/schnitt/ton?${parameter(g)}`;
  }

  schneiden(g: Schnittgegenstand, stuecke: StueckWahl[], melden: (f: Fortschritt) => void): Promise<number> {
    return this.arbeit("/api/schnitt/schneiden", { ...g, stuecke }, melden);
  }

  normalisieren(g: Schnittgegenstand, melden: (f: Fortschritt) => void): Promise<number> {
    return this.arbeit("/api/schnitt/normalisieren", g, melden);
  }

  umwandeln(g: Schnittgegenstand, u: Umwandlung, melden: (f: Fortschritt) => void): Promise<number> {
    return this.arbeit("/api/schnitt/umwandeln", { ...g, ...u }, melden);
  }

  async rueckgaengig(g: Schnittgegenstand): Promise<string> {
    return (await this.json<{ zurueckgenommen: string }>("/api/schnitt/rueckgaengig", { method: "POST", body: JSON.stringify(g) })).zurueckgenommen;
  }
}
