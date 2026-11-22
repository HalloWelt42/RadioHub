// Die eine Liste der Abos (RAD-17): Rechner, Telefon und Wecker lesen dieselbe (früher je eine in der Ansicht und im
// Store). Änderungen gehen über die Quelle und danach in die Liste, ohne alles neu zu laden.
import type { Podcastquelle } from "./quelle";
import type { Abo, Ordner } from "./typen";

export class Aboliste {
  abos = $state<Abo[]>([]);
  /** eigene Ordner in ihrer Reihenfolge (RAD-23) */
  ordner = $state<Ordner[]>([]);
  laedt = $state(false);
  fehler = $state("");
  geladen = $state(false);

  constructor(private readonly quelle: Podcastquelle) {}

  async laden(): Promise<void> {
    this.laedt = true;
    this.fehler = "";
    try {
      [this.abos, this.ordner] = await Promise.all([this.quelle.abos(), this.quelle.ordner()]);
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

  /** das Abo eines Feeds, zum Öffnen aus dem Verzeichnis (RAD-104) */
  vonFeed(feed: string): Abo | undefined {
    return this.abos.find((a) => a.feed === feed);
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

  /** oben anheften oder lösen; danach die Reihenfolge des Backends (ein gelöstes kehrt an seine Stelle zurück) */
  async anheften(id: number, an: boolean): Promise<void> {
    await this.quelle.anheften(id, an);
    this.aendern(id, { angeheftet: an });
    await this.laden();
  }

  async sortierungSetzen(id: number, sortierung: Abo["sortierung"]): Promise<void> {
    if (this.abo(id)?.sortierung === sortierung) return;
    await this.quelle.sortierungSetzen(id, sortierung);
    this.aendern(id, { sortierung });
  }

  async autoLaden(id: number, an: boolean): Promise<void> {
    await this.quelle.autoLaden(id, an);
    this.aendern(id, { autoLaden: an });
  }

  /** nach neuen Folgen fragen (ein Abo oder alle), danach die Zahlen neu; liefert die Zahl neuer Folgen */
  async aktualisieren(id?: number): Promise<number> {
    const neu = await this.quelle.aktualisieren(id);
    await this.laden();
    return neu;
  }

  // ----- Ordner ----------------------------------------------------------------------------------------------------
  async ordnerAnlegen(name: string): Promise<Ordner> {
    const neu = await this.quelle.ordnerAnlegen(name);
    this.ordner = [...this.ordner, neu];
    return neu;
  }

  async ordnerAendern(id: string, teil: Partial<Pick<Ordner, "name" | "offen">>): Promise<void> {
    this.ordner = this.ordner.map((o) => (o.id === id ? { ...o, ...teil } : o));     // sofort sichtbar (etwa Einklappen)
    const neu = await this.quelle.ordnerAendern(id, teil);
    this.ordner = this.ordner.map((o) => (o.id === id ? neu : o));
  }

  /** nur die Gruppierung löschen: die Abos des Ordners stehen danach lose */
  async ordnerLoeschen(id: string): Promise<void> {
    await this.quelle.ordnerLoeschen(id);
    this.ordner = this.ordner.filter((o) => o.id !== id);
    this.abos = this.abos.map((a) => (a.ordnerId === id ? { ...a, ordnerId: null } : a));
  }

  async ordnerOrdnen(ids: string[]): Promise<void> {
    const nach = new Map(this.ordner.map((o) => [o.id, o]));
    this.ordner = ids.map((id) => nach.get(id)).filter((o): o is Ordner => !!o);
    await this.quelle.ordnerOrdnen(ids);
  }

  /** Abo in einen Ordner (oder lose) und an die Stelle `ids` (neue Reihenfolge aller Abos) */
  async zuordnen(aboId: number, ordnerId: string | null, ids?: number[]): Promise<void> {
    await this.quelle.zuordnen(aboId, ordnerId);
    this.aendern(aboId, { ordnerId });
    if (ids) await this.ordnen(ids);
  }

  /** die Abos eines Ordners (null: lose), ohne die angehefteten (die stehen oben) */
  imOrdner(ordnerId: string | null): Abo[] {
    return this.abos.filter((a) => !a.angeheftet && (a.ordnerId ?? null) === ordnerId);
  }

  aendern(id: number, teil: Partial<Abo>): void {
    this.abos = this.abos.map((a) => (a.id === id ? { ...a, ...teil } : a));
  }
}
