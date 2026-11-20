// "Alle speichern" (RAD-17): die Folgen eines Abos nacheinander in der Kellerwolke speichern, mit Fortschritt, Anhalten,
// Weiter und Abbrechen. Eine Folge nach der anderen, damit die Ablage nicht überlastet und jede fertige sofort in der Liste steht.
import type { Podcastquelle } from "./quelle";

export class Speicherauftrag {
  gesamt = $state(0);
  fertig = $state(0);
  fehler = $state(0);
  laeuft = $state(false);
  angehalten = $state(false);
  aboId = $state<number | null>(null);

  private offen: number[] = [];
  private abbruch = false;
  private weiter: (() => void) | null = null;

  constructor(private readonly quelle: Podcastquelle, private readonly gespeichert: (id: number) => void) {}

  async starten(aboId: number, ids: number[]): Promise<void> {
    if (this.laeuft || !ids.length) return;
    this.aboId = aboId;
    this.offen = [...ids];
    this.gesamt = ids.length;
    this.fertig = this.fehler = 0;
    this.abbruch = this.angehalten = false;
    this.laeuft = true;
    try {
      while (this.offen.length && !this.abbruch) {
        if (this.angehalten) await new Promise<void>((weiter) => (this.weiter = weiter));
        if (this.abbruch) break;
        const id = this.offen.shift()!;
        try {
          await this.quelle.speichern(id, true);
          this.gespeichert(id);
        } catch {
          this.fehler += 1;
        }
        this.fertig += 1;
      }
    } finally {
      this.laeuft = false;
      this.angehalten = false;
    }
  }

  anhalten(): void {
    if (this.laeuft) this.angehalten = true;
  }

  fortsetzen(): void {
    this.angehalten = false;
    this.weiter?.();
    this.weiter = null;
  }

  abbrechen(): void {
    this.abbruch = true;
    this.fortsetzen();
  }
}
