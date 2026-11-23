// Werbefilter (HELF-256, RAD-128): was der Propaganda-Filter kennt und was sein Lernlauf hört. RadioHub reicht nur durch.
// Dazu reine Regeln für die Liste der Spots (Reihenfolge, Gruppen), mit vitest prüfbar.
import { netz, type Anfrage } from "./netz";

export type Urteil = "offen" | "bestaetigt" | "verworfen";
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
  sender(): Promise<Lernsender[]> {
    return this.a("/api/werbefilter/sender");
  }
  ausnehmen(uuid: string, aus: boolean): Promise<Lernsender[]> {
    return this.a(`/api/werbefilter/sender/${encodeURIComponent(uuid)}`, { methode: "PUT", daten: { aus } });
  }
  spots(): Promise<Spotfund[]> {
    return this.a("/api/werbefilter/signaturen");
  }
  beurteilen(id: string, urteil: Urteil): Promise<Spotfund> {
    return this.a(`/api/werbefilter/signaturen/${encodeURIComponent(id)}`, { methode: "PUT", daten: { urteil } });
  }
  quelle(id: string, uuid: string, stand: "wirkt" | "vorschlag"): Promise<Spotfund> {
    return this.a(`/api/werbefilter/signaturen/${encodeURIComponent(id)}/quellen/${encodeURIComponent(uuid)}`, { methode: "PUT", daten: { stand } });
  }
  tonadresse = (id: string): string => `/api/werbefilter/signaturen/${encodeURIComponent(id)}/ton`;
}

export type Fach = "pruefen" | "wirkt" | "verworfen";

/** Angekündigte und im Schnitt markierte Spots wirken an ihrem Sender sofort, die übrigen erst nach der Bestätigung */
export function fach(s: Spotfund): Fach {
  if (s.urteil === "verworfen") return "verworfen";
  if (s.urteil === "offen" && s.herkunft === "lernlauf") return "pruefen";
  return s.quellen.some((q) => q.stand === "vorschlag") ? "pruefen" : "wirkt";
}

const RANG: Record<Spotfund["einschaetzung"], number> = { werbung: 0, unklar: 1, "": 1, anderes: 2, sender: 3, ohne_sprache: 4 };
const mal = (s: Spotfund) => s.quellen.reduce((n, q) => n + q.treffer, 0);

/** Was am ehesten Werbung ist, zuerst; bei Gleichstand, was öfter lief */
export function geordnet(spots: Spotfund[], f: Fach): Spotfund[] {
  return spots.filter((s) => fach(s) === f)
    .sort((a, b) => (f === "pruefen" ? RANG[a.einschaetzung] - RANG[b.einschaetzung] : 0) || mal(b) - mal(a) || b.angelegt.localeCompare(a.angelegt));
}

export const gehoert = mal;

export const werbefilter = new Werbefilter();
