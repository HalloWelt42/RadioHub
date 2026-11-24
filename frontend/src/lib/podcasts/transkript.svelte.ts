// Transkript einer Folge (RAD-22): lesen, transkribieren lassen und dem Lauf folgen. Die Quelle entscheidet, woher es kommt (gehört
// geht vor dem des Feeds); hier stehen Zustand und reine Regeln.
import { netz, type Anfrage } from "../radio/netz";

export interface Transkriptabsatz {
  nr: number;
  /** Sekunden der Folge */
  von: number;
  bis: number;
  text: string;
  sprecher: string;
}

export interface Transkript {
  herkunft: "feed" | "gehoert" | "vertont";
  sprache: string;
  absaetze: Transkriptabsatz[];
}

export interface Transkriptstand {
  transkript: Transkript | null;
  lauf: { id: string; fortschritt: number | null; schritt: string } | null;
  fehler: string;
  kann_transkribieren: boolean;
}

const TAKT_MS = 3000;

/** Der Absatz, der an der Stelle zu hören ist; zwischen zweien der vorige */
export function absatzBei(absaetze: Transkriptabsatz[], stelle: number): number | null {
  let nr: number | null = null;
  for (const a of absaetze) {
    if (a.von > stelle + 0.2) break;
    nr = a.nr;
  }
  return nr;
}

export class Folgentext {
  stand = $state.raw<Transkriptstand | null>(null);
  fehler = $state("");
  private uhr: ReturnType<typeof setTimeout> | undefined;
  private zu = false;

  /** welcher Text: der einer vertonten Fassung (Sprache) oder leer der des Originals */
  fassung = "";

  constructor(readonly folgeId: number, private readonly a: Anfrage = netz()) {}

  private get weg(): string {
    return `/api/podcasts/episodes/${this.folgeId}/transkript`;
  }

  laden = (): Promise<void> => this.holen(() => this.a<Transkriptstand>(this.fassung ? `${this.weg}?fassung=${encodeURIComponent(this.fassung)}` : this.weg));
  transkribieren = (): Promise<void> => this.holen(() => this.a<Transkriptstand>(this.weg, { methode: "POST" }));
  abbrechen = (): Promise<void> => this.holen(() => this.a<Transkriptstand>(`${this.weg}/lauf`, { methode: "DELETE" }));

  beenden(): void {
    this.zu = true;
    clearTimeout(this.uhr);
  }

  private async holen(arbeit: () => Promise<Transkriptstand>): Promise<void> {
    clearTimeout(this.uhr);
    try {
      const s = await arbeit();
      if (this.zu) return;
      this.stand = s;
      this.fehler = s.fehler;
    } catch (f) {
      this.fehler = (f as Error).message;
    }
    if (this.stand?.lauf && !this.zu) this.uhr = setTimeout(() => void this.laden(), TAKT_MS);
  }
}
