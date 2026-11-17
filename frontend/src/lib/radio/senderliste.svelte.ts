// Senderliste seitenweise (Keyset): die erste Seite mit Gesamtzahl und Facetten, weitere über den Zeiger der vorigen
// Antwort. Eine neue Abfrage bricht die laufende ab; eine verspätete Antwort ändert nichts. Die Facetten bleiben stehen,
// bis neue da sind (kein Flackern beim Tippen).
import type { Senderquelle } from "./quelle";
import type { Facetten, SenderEintrag, StationQuery } from "./typen";

export const SEITE = 50;

export class Senderliste {
  eintraege = $state<SenderEintrag[]>([]);
  gesamt = $state<number | null>(null);
  facetten = $state<Facetten | null>(null);
  weiter = $state<string | null>(null);
  laedt = $state(false);
  laedtMehr = $state(false);
  fehler = $state("");
  /** schon einmal geladen (vorher zeigt die Ansicht den Ladezustand, nie "keine Treffer") */
  geladen = $state(false);

  private abfrage: StationQuery = {};
  private lauf = 0;
  private abbruch: AbortController | null = null;

  constructor(private readonly quelle: Senderquelle, private readonly seite = SEITE) {}

  async laden(abfrage: StationQuery): Promise<void> {
    const meiner = ++this.lauf;
    this.abbruch?.abort();
    const abbruch = (this.abbruch = new AbortController());
    this.abfrage = abfrage;
    this.laedt = true;
    this.laedtMehr = false;
    this.fehler = "";
    try {
      const r = await this.quelle.abfragen({ ...abfrage, anzahl: this.seite, nach: null }, abbruch.signal);
      if (meiner !== this.lauf) return;
      this.eintraege = r.eintraege;
      this.gesamt = r.gesamt;
      this.weiter = r.weiter;
      if (r.facetten) this.facetten = r.facetten;
      this.geladen = true;
    } catch (f) {
      if (meiner !== this.lauf || (f as Error).name === "AbortError") return;
      this.fehler = (f as Error).message;
      this.geladen = true;
    } finally {
      if (meiner === this.lauf) this.laedt = false;
    }
  }

  /** nächste Seite; doppelte Sender (zwischen zwei Seiten geändert) kommen nur einmal */
  async mehr(): Promise<void> {
    if (!this.weiter || this.laedt || this.laedtMehr) return;
    const meiner = this.lauf;
    this.laedtMehr = true;
    this.fehler = "";
    try {
      const r = await this.quelle.abfragen({ ...this.abfrage, anzahl: this.seite, nach: this.weiter, mit_facetten: false },
        this.abbruch?.signal);
      if (meiner !== this.lauf) return;
      const da = new Set(this.eintraege.map((e) => e.uuid));
      this.eintraege = [...this.eintraege, ...r.eintraege.filter((e) => !da.has(e.uuid))];
      this.weiter = r.weiter;
    } catch (f) {
      if (meiner !== this.lauf || (f as Error).name === "AbortError") return;
      this.fehler = (f as Error).message;
    } finally {
      if (meiner === this.lauf) this.laedtMehr = false;
    }
  }

  /** Felder eines Senders ändern (Favorit, Bewertung, Messwert ...) */
  aendern(uuid: string, teil: Partial<SenderEintrag>): void {
    this.eintraege = this.eintraege.map((e) => (e.uuid === uuid ? { ...e, ...teil } : e));
  }

  /** Sender aus der Liste nehmen (ausgeblendet); die Gesamtzahl sinkt mit */
  entfernen(uuid: string): number {
    const stelle = this.eintraege.findIndex((e) => e.uuid === uuid);
    if (stelle < 0) return -1;
    this.eintraege = this.eintraege.filter((e) => e.uuid !== uuid);
    if (this.gesamt !== null) this.gesamt = Math.max(0, this.gesamt - 1);
    return stelle;
  }

  /** Sender an seine Stelle zurück (Rückgängig) oder vorn einfügen (Direktlink) */
  einfuegen(eintrag: SenderEintrag, stelle = 0, zaehlen = true): void {
    if (this.eintraege.some((e) => e.uuid === eintrag.uuid)) return;
    const neu = [...this.eintraege];
    neu.splice(Math.max(0, Math.min(stelle, neu.length)), 0, eintrag);
    this.eintraege = neu;
    if (zaehlen && this.gesamt !== null) this.gesamt += 1;
  }
}
