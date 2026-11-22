// Folgen seitenweise (RAD-17), wie die Senderliste: die erste Seite mit Gesamtzahl, weitere über den Zeiger der vorigen
// Antwort. Eine neue Abfrage bricht die laufende ab; eine verspätete Antwort ändert nichts. Mit Suchtext sucht sie im
// Volltext der Folgen, sonst nach Abos, Filter und Sortierung. Wechselt die Wahl der Abos, steht bis zur Antwort nicht
// mehr die alte Liste da, sondern "lädt" (RAD-107: ein neues Abo schien sonst leer zu bleiben).
import type { Podcastquelle } from "./quelle";
import type { Folge, Folgenabfrage } from "./typen";

export const SEITE = 50;

export class Folgenliste {
  folgen = $state<Folge[]>([]);
  gesamt = $state<number | null>(null);
  weiter = $state<string | null>(null);
  laedt = $state(false);
  laedtMehr = $state(false);
  fehler = $state("");
  geladen = $state(false);

  private abfrage: Folgenabfrage = {};
  private suchtext = "";
  private lauf = 0;
  private abbruch: AbortController | null = null;

  constructor(private readonly quelle: Podcastquelle, private readonly seite = SEITE) {}

  /** die Wahl der Abos als Vergleichstext (leer: alle) */
  private static abos(a: Folgenabfrage): string {
    return [...(a.abos ?? [])].sort((x, y) => x - y).join(",");
  }

  private holen(nach: string | null, signal: AbortSignal) {
    const a = { ...this.abfrage, anzahl: this.seite, nach };
    return this.suchtext ? this.quelle.folgenSuchen(this.suchtext, a, signal) : this.quelle.folgen(a, signal);
  }

  async laden(abfrage: Folgenabfrage, suchtext = ""): Promise<void> {
    const meiner = ++this.lauf;
    this.abbruch?.abort();
    const abbruch = (this.abbruch = new AbortController());
    if (Folgenliste.abos(abfrage) !== Folgenliste.abos(this.abfrage)) {
      this.folgen = [];
      this.gesamt = null;
      this.weiter = null;
      this.geladen = false;
    }
    this.abfrage = abfrage;
    this.suchtext = suchtext.trim();
    this.laedt = true;
    this.laedtMehr = false;
    this.fehler = "";
    try {
      const r = await this.holen(null, abbruch.signal);
      if (meiner !== this.lauf) return;
      this.folgen = r.folgen;
      this.gesamt = r.gesamt;
      this.weiter = r.weiter;
    } catch (f) {
      if (meiner !== this.lauf || (f as Error).name === "AbortError") return;
      this.fehler = (f as Error).message;
    } finally {
      if (meiner === this.lauf) {
        this.laedt = false;
        this.geladen = true;
      }
    }
  }

  /** nächste Seite; doppelte Folgen (zwischen zwei Seiten neu eingetroffen) kommen nur einmal */
  async mehr(): Promise<void> {
    if (!this.weiter || this.laedt || this.laedtMehr || !this.abbruch) return;
    const meiner = this.lauf;
    this.laedtMehr = true;
    this.fehler = "";
    try {
      const r = await this.holen(this.weiter, this.abbruch.signal);
      if (meiner !== this.lauf) return;
      const da = new Set(this.folgen.map((f) => f.id));
      this.folgen = [...this.folgen, ...r.folgen.filter((f) => !da.has(f.id))];
      this.weiter = r.weiter;
    } catch (f) {
      if (meiner !== this.lauf || (f as Error).name === "AbortError") return;
      this.fehler = (f as Error).message;
    } finally {
      if (meiner === this.lauf) this.laedtMehr = false;
    }
  }

  /** eine Folge, die nicht auf den geladenen Seiten steht (Direktlink, laufende Folge), vorn einfügen wie in der
   *  Senderliste; liefert, ob sie jetzt da ist */
  async sicherstellen(id: number): Promise<boolean> {
    if (this.folgen.some((f) => f.id === id)) return true;
    const lauf = this.lauf;
    const f = await this.quelle.einzelfolge(id);
    if (!f || lauf !== this.lauf || this.folgen.some((x) => x.id === id)) return !!f && this.folgen.some((x) => x.id === id);
    this.folgen = [f, ...this.folgen];
    return true;
  }

  aendern(id: number, teil: Partial<Folge>): void {
    this.folgen = this.folgen.map((f) => (f.id === id ? { ...f, ...teil } : f));
  }
}
