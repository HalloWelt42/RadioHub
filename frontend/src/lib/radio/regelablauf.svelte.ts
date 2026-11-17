// Ablauf einer neuen Ausschlussregel (Entscheidung 4): Entwurf ändern zeigt nach einer kurzen Pause die Vorschau (was
// ausgeblendet würde, davon Favoriten, Beispiele); erst "Anlegen" ändert etwas, danach steht Rückgängig bereit (das
// Entfernen der neuen Regel). Eine ältere Vorschau, die nach einer neueren ankommt, gilt nicht.
import type { Senderquelle } from "./quelle";
import type { RegelAenderung, RegelEntwurf, RegelVorschau } from "./typen";

export class Regelablauf {
  entwurf = $state<RegelEntwurf | null>(null);
  vorschau = $state<RegelVorschau | null>(null);
  laedt = $state(false);
  fehler = $state("");
  /** zuletzt angelegte Regel (für Rückgängig) */
  angelegt = $state<RegelAenderung | null>(null);

  private uhr: ReturnType<typeof setTimeout> | null = null;
  private abbruch: AbortController | null = null;
  private lauf = 0;

  constructor(private readonly quelle: Senderquelle, private readonly pauseMs = 250) {}

  /** Entwurf setzen (null: nichts gewählt); die Vorschau folgt nach der Pause */
  setzen(entwurf: RegelEntwurf | null): void {
    this.entwurf = entwurf;
    this.vorschau = null;
    this.fehler = "";
    if (this.uhr) clearTimeout(this.uhr);
    this.abbruch?.abort();
    const meiner = ++this.lauf;
    if (!entwurf) {
      this.laedt = false;
      return;
    }
    this.laedt = true;
    this.uhr = setTimeout(() => void this.vorschauHolen(entwurf, meiner), this.pauseMs);
  }

  private async vorschauHolen(entwurf: RegelEntwurf, meiner: number): Promise<void> {
    const abbruch = (this.abbruch = new AbortController());
    try {
      const v = await this.quelle.vorschau(entwurf, abbruch.signal);
      if (meiner === this.lauf) this.vorschau = v;
    } catch (f) {
      if (meiner === this.lauf && (f as Error).name !== "AbortError") this.fehler = (f as Error).message;
    } finally {
      if (meiner === this.lauf) this.laedt = false;
    }
  }

  /** anlegbar: Vorschau zum aktuellen Entwurf da, und es gibt die Regel noch nicht */
  get bereit(): boolean {
    return !!this.entwurf && !!this.vorschau && !this.laedt && !this.vorschau.gleiche_regel;
  }

  async anlegen(): Promise<RegelAenderung> {
    if (!this.entwurf || !this.bereit) throw new Error("Erst die Vorschau abwarten");
    const aenderung = await this.quelle.anlegen(this.entwurf);
    this.angelegt = aenderung;
    this.setzen(null);
    return aenderung;
  }

  /** die zuletzt angelegte Regel wieder entfernen */
  async rueckgaengig(): Promise<RegelAenderung | null> {
    const regel = this.angelegt?.regel;
    if (!regel) return null;
    const aenderung = await this.quelle.entfernen(regel.id);
    this.angelegt = null;
    return aenderung;
  }
}
