// Suche im Verzeichnis zum Abonnieren (RAD-14, aus der Ansicht am Rechner gelöst, damit Rechner und Telefon dieselbe
// haben): Text ab zwei Zeichen sucht, eine Adresse eines Feeds sucht nicht (sie wird direkt abonniert), eine neue Suche
// bricht die laufende ab, verspätete Antworten ändern nichts.
import type { Podcastquelle } from "./quelle";
import type { Fundstueck } from "./typen";

export class Verzeichnissuche {
  text = $state("");
  treffer = $state<Fundstueck[] | null>(null);
  sucht = $state(false);
  fehler = $state("");
  /** Feed, der gerade abonniert wird */
  arbeitet = $state<string | null>(null);
  private abbruch: AbortController | null = null;

  constructor(private readonly quelle: Podcastquelle) {}

  get istFeed(): boolean {
    return /^https?:\/\/\S+$/i.test(this.text.trim());
  }

  gesucht(s: string): void {
    this.text = s;
    if (s.length < 2 || this.istFeed) {
      this.abbruch?.abort();
      this.treffer = null;
      this.sucht = false;
      return;
    }
    void this.suchen(s);
  }

  private async suchen(s: string): Promise<void> {
    this.abbruch?.abort();
    const meiner = (this.abbruch = new AbortController());
    this.sucht = true;
    this.fehler = "";
    try {
      const r = await this.quelle.suchen(s, meiner.signal);
      if (meiner === this.abbruch) this.treffer = r;
    } catch (f) {
      if ((f as Error).name !== "AbortError") this.fehler = (f as Error).message;
    } finally {
      if (meiner === this.abbruch) this.sucht = false;
    }
  }

  async abonnieren(feed: string, arbeit: () => Promise<void>): Promise<void> {
    this.arbeitet = feed;
    try {
      await arbeit();
    } finally {
      this.arbeitet = null;
    }
  }
}
