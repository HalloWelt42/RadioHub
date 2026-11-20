// Die eine Liste der Abos (RAD-17): Rechner, Telefon und Wecker lesen dieselbe (früher je eine in der Ansicht und im
// Store). Änderungen gehen über die Quelle und danach in die Liste, ohne alles neu zu laden.
import type { Podcastquelle } from "./quelle";
import type { Abo } from "./typen";

export class Aboliste {
  abos = $state<Abo[]>([]);
  laedt = $state(false);
  fehler = $state("");
  geladen = $state(false);

  constructor(private readonly quelle: Podcastquelle) {}

  async laden(): Promise<void> {
    this.laedt = true;
    this.fehler = "";
    try {
      this.abos = await this.quelle.abos();
    } catch (f) {
      this.fehler = (f as Error).message;
    } finally {
      this.laedt = false;
      this.geladen = true;
    }
  }

  abo(id: number): Abo | undefined {
    return this.abos.find((a) => a.id === id);
  }

  /** ob ein Feed schon abonniert ist (Treffer der Suche) */
  abonniert(feed: string): boolean {
    return this.abos.some((a) => a.feed === feed);
  }

  async abonnieren(feed: string): Promise<Abo> {
    const neu = await this.quelle.abonnieren(feed);
    this.abos = [...this.abos.filter((a) => a.id !== neu.id), neu];
    return neu;
  }

  async abbestellen(id: number): Promise<void> {
    await this.quelle.abbestellen(id);
    this.abos = this.abos.filter((a) => a.id !== id);
  }

  /** neue Reihenfolge: sofort sichtbar, bei einem Fehler zurück */
  async ordnen(ids: number[]): Promise<void> {
    const vorher = this.abos;
    const nach = new Map(vorher.map((a) => [a.id, a]));
    this.abos = ids.map((id) => nach.get(id)).filter((a): a is Abo => !!a);
    try {
      await this.quelle.ordnen(ids);
    } catch (f) {
      this.abos = vorher;
      throw f;
    }
  }

  async autoLaden(id: number, an: boolean): Promise<void> {
    await this.quelle.autoLaden(id, an);
    this.aendern(id, { autoLaden: an });
  }

  /** nach neuen Folgen fragen (ein Abo oder alle), danach die Zahlen neu */
  async aktualisieren(id?: number): Promise<void> {
    await this.quelle.aktualisieren(id);
    await this.laden();
  }

  aendern(id: number, teil: Partial<Abo>): void {
    this.abos = this.abos.map((a) => (a.id === id ? { ...a, ...teil } : a));
  }
}
