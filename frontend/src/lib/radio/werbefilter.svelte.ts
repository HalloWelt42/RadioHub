// Werbefilter (HELF-256, RAD-128): was der Propaganda-Filter kennt und was sein Lernlauf hört. RadioHub reicht nur durch.
// Die Listen kommen stückweise und laden beim Rollen nach (Stueckliste).
import { netz, type Anfrage } from "./netz";

export type Urteil = "offen" | "bestaetigt" | "verworfen";
/** Fach der Durchsicht; was wohin gehört, sagt der Filter */
export type Fach = "pruefen" | "wirkt" | "verworfen";
export type Grund = "gehoert" | "favorit" | "aehnlich" | "bekannt";

export interface Fundsender {
  quelle: string;
  name: string;
  stand: "wirkt" | "vorschlag";
  treffer: number;
  zuerst: string;
  zuletzt: string;
}

export interface Spotfund {
  id: string;
  /** Name der ersten Quelle */
  quelle: string;
  herkunft: "lernlauf" | "angabe" | "schnitt" | "vergleich";
  dauer_s: number;
  angelegt: string;
  urteil: Urteil;
  werbender: string;
  text: string;
  einschaetzung: "" | "werbung" | "sender" | "anderes" | "ohne_sprache" | "unklar";
  quellen: Fundsender[];
}

export interface Laufend {
  quelle: string;
  name: string;
  grund: Grund;
  schritt: string;
  sekunden: number;
  titel: string;
}

export interface Lauf {
  id: string;
  begonnen: string;
  beendet: string | null;
  sender: number;
  fehler: number;
  stunden: number;
  neu: number;
  bekannte: number;
}

export interface Lernstand {
  an: boolean;
  von: string;
  bis: string;
  gleichzeitig: number;
  laeuft: boolean;
  sofort_bis: string | null;
  laufend: Laufend[];
  sender: number;
  stunden: number;
  archiv_stunden: number;
  naechste: string[];
  laeufe: Lauf[];
}

export interface Lernsender {
  quelle: string;
  name: string;
  grund: Grund;
  dabei: boolean;
  aus: boolean;
  zuletzt: string | null;
  stunden: number;
  kandidaten: number;
  bekannte: number;
  fehler: string;
}

export interface Filterstand {
  eingerichtet: boolean;
  erreichbar: boolean;
  grund: string;
  filter: { signaturen: Record<Urteil, number>; stroeme: number; abschrift: boolean; abschrift_fehler: string } | null;
  lernlauf: Lernstand | null;
}

export class Werbefilter {
  constructor(private readonly a: Anfrage = netz()) {}

  stand(): Promise<Filterstand> {
    return this.a("/api/werbefilter");
  }
  stellen(teil: Partial<Pick<Lernstand, "an" | "von" | "bis" | "gleichzeitig">>): Promise<Lernstand> {
    return this.a("/api/werbefilter/lernlauf", { methode: "PUT", daten: teil });
  }
  jetzt(minuten: number): Promise<Lernstand> {
    return this.a("/api/werbefilter/lernlauf/jetzt", { methode: "POST", daten: { minuten } });
  }
  sender(ab: number, anzahl: number): Promise<{ gesamt: number; sender: Lernsender[] }> {
    return this.a(`/api/werbefilter/sender?ab=${ab}&anzahl=${anzahl}`);
  }
  ausnehmen(uuid: string, aus: boolean): Promise<Lernsender> {
    return this.a(`/api/werbefilter/sender/${encodeURIComponent(uuid)}`, { methode: "PUT", daten: { aus } });
  }
  spots(fach: Fach, ab: number, anzahl: number): Promise<{ faecher: Record<Fach, number>; signaturen: Spotfund[] }> {
    return this.a(`/api/werbefilter/spots/${fach}?ab=${ab}&anzahl=${anzahl}`);
  }
  beurteilen(id: string, urteil: Urteil): Promise<Spotfund> {
    return this.a(`/api/werbefilter/signaturen/${encodeURIComponent(id)}`, { methode: "PUT", daten: { urteil } });
  }
  quelle(id: string, uuid: string, stand: "wirkt" | "vorschlag"): Promise<Spotfund> {
    return this.a(`/api/werbefilter/signaturen/${encodeURIComponent(id)}/quellen/${encodeURIComponent(uuid)}`, { methode: "PUT", daten: { stand } });
  }
  tonadresse = (id: string): string => `/api/werbefilter/signaturen/${encodeURIComponent(id)}/ton`;
}

/** wie oft ein Spot insgesamt lief */
export const gehoert = (s: Spotfund): number => s.quellen.reduce((n, q) => n + q.treffer, 0);

export const JE_STUECK = 25;

/** Eine Liste, die stückweise lädt. `holen` liefert ab einer Stelle das nächste Stück und wie viele es insgesamt sind. */
export class Stueckliste<T> {
  eintraege = $state.raw<T[]>([]);
  gesamt = $state<number | null>(null);
  laedt = $state(false);
  fehler = $state("");
  private lauf = 0;

  constructor(private readonly holen: (ab: number, anzahl: number) => Promise<{ eintraege: T[]; gesamt: number }>, private readonly kennung: (e: T) => string) {}

  /** das nächste Stück; was inzwischen gerutscht ist, steht nie doppelt da */
  async mehr(): Promise<void> {
    if (this.laedt || (this.gesamt !== null && this.eintraege.length >= this.gesamt)) return;
    await this.stueck(this.eintraege.length, JE_STUECK, true);
  }

  /** von vorn, so viele wie gerade gezeigt */
  async neu(): Promise<void> {
    await this.stueck(0, Math.min(200, Math.max(JE_STUECK, this.eintraege.length)), false);
  }

  /** leer und von vorn (anderes Fach) */
  async wechsel(): Promise<void> {
    this.eintraege = [];
    this.gesamt = null;
    await this.neu();
  }

  ersetzen(e: T): void {
    this.eintraege = this.eintraege.map((x) => (this.kennung(x) === this.kennung(e) ? e : x));
  }

  private async stueck(ab: number, anzahl: number, anhaengen: boolean): Promise<void> {
    const lauf = ++this.lauf;
    this.laedt = true;
    this.fehler = "";
    try {
      const r = await this.holen(ab, anzahl);
      if (lauf !== this.lauf) return;                         // inzwischen gilt eine andere Anfrage
      const da = new Set(anhaengen ? this.eintraege.map(this.kennung) : []);
      const neue = r.eintraege.filter((e) => !da.has(this.kennung(e)));
      this.eintraege = anhaengen ? [...this.eintraege, ...neue] : neue;
      this.gesamt = anhaengen && !neue.length ? this.eintraege.length : r.gesamt;   // nichts Neues mehr: Ende
    } catch (f) {
      if (lauf === this.lauf) this.fehler = (f as Error).message;
    } finally {
      if (lauf === this.lauf) this.laedt = false;
    }
  }
}

export const werbefilter = new Werbefilter();
