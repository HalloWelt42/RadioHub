// Vertonte Fassungen einer Folge (RAD-26): vertonen lassen, dem Lauf folgen, zwischen Original und Fassung wählen. Die Wahl führt der
// Server, sie gilt auf allen Geräten.
import { netz, type Anfrage } from "../radio/netz";

export interface Sprachfassung {
  sprache: string;
  name: string;
  stimme: string;
}

export interface Fassungsstand {
  fassungen: Sprachfassung[];
  /** welche man hört, leer: das Original */
  gewaehlt: string;
  ziel: string;
  zielname: string;
  lauf: { id: string; fortschritt: number | null; schritt: string } | null;
  fehler: string;
  kann_vertonen: boolean;
}

const TAKT_MS = 5000;

export class Folgenfassung {
  stand = $state.raw<Fassungsstand | null>(null);
  fehler = $state("");
  private uhr: ReturnType<typeof setTimeout> | undefined;
  private zu = false;

  constructor(readonly folgeId: number, private readonly a: Anfrage = netz()) {}

  private get weg(): string {
    return `/api/podcasts/episodes/${this.folgeId}`;
  }

  laden = (): Promise<void> => this.holen(() => this.a<Fassungsstand>(`${this.weg}/vertonung`));
  /** nach den Voreinstellungen; gibt es die Fassung schon, entsteht sie neu */
  vertonen = (): Promise<void> => this.holen(() => this.a<Fassungsstand>(`${this.weg}/vertonung`, { methode: "POST" }));
  /** ob es gelang */
  waehlen = async (sprache: string): Promise<boolean> => {
    await this.holen(() => this.a<Fassungsstand>(`${this.weg}/fassung`, { methode: "PUT", daten: { sprache } }));
    return this.stand?.gewaehlt === sprache;
  };

  beenden(): void {
    this.zu = true;
    clearTimeout(this.uhr);
  }

  private async holen(arbeit: () => Promise<Fassungsstand>): Promise<void> {
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
