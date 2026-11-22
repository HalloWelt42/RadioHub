// Werbestellen in Podcast-Folgen (RAD-32): Datenmodell und Quelle gegen das Backend (/api/podcasts/.../werbung).
// Die Wiedergabe springt darüber (spieler/werbesprung), die Datei bleibt vollständig.
import { ereignisse, fehlerText, type Fortschritt } from "../ereignisstrom";
import { antwortPruefen, kopf } from "../sitzung";

export type Werbeherkunft = "kapitel" | "hand" | "vergleich" | "transkript";

export interface Werbestelle {
  id: number;
  folgeId: number;
  /** Sekunden ab Beginn der Folge */
  von: number;
  bis: number;
  herkunft: Werbeherkunft;
  text: string;
}

export interface Werbestellen {
  stellen: Werbestelle[];
  /** womit eine Suche für diese Folge arbeiten kann (nur diese Quellen zeigt die Oberfläche) */
  quellen: Werbeherkunft[];
}

export interface Werbequelle {
  stellen(folgeId: number): Promise<Werbestellen>;
  setzen(folgeId: number, von: number, bis: number, text?: string): Promise<Werbestelle>;
  /** "keine Werbung" (an) oder doch Werbung (aus, Rückgängig) */
  verwerfen(stelleId: number, an: boolean): Promise<void>;
  /** alle möglichen Quellen; liefert je Quelle die Zahl gefundener Stellen */
  suchen(folgeId: number, melden: (f: Fortschritt) => void): Promise<Record<string, number>>;
  /** neue Datei ohne Werbung neben die gespeicherte Folge; liefert ihren Pfad */
  ohneWerbung(folgeId: number, melden: (f: Fortschritt) => void): Promise<string>;
  aboSetzen(aboId: number, teil: { ueberspringen?: boolean; pruefen?: boolean }): Promise<void>;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Rohdaten des Backends
const stelleAus = (r: Record<string, any>): Werbestelle =>
  ({ id: r.id, folgeId: r.folge_id, von: Number(r.von) || 0, bis: Number(r.bis) || 0, herkunft: r.herkunft, text: String(r.text ?? "") });

export class BackendWerbequelle implements Werbequelle {
  constructor(private readonly basis = "", private readonly abruf: typeof fetch = (w, i) => fetch(w, i)) {}

  private async json<T>(pfad: string, init: RequestInit = {}): Promise<T> {
    const antwort = await this.abruf(`${this.basis}${pfad}`, { ...init, headers: kopf({ "Content-Type": "application/json" }) });
    antwortPruefen(antwort);
    if (!antwort.ok) throw new Error(await fehlerText(antwort));
    return antwort.json();
  }

  private async strom<T>(pfad: string, feld: string, melden: (f: Fortschritt) => void): Promise<T> {
    const antwort = await this.abruf(`${this.basis}${pfad}`, { method: "POST", headers: kopf() });
    return ereignisse<T>(antwort, melden, feld);
  }

  async stellen(folgeId: number): Promise<Werbestellen> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const r = await this.json<{ stellen: any[]; quellen: Werbeherkunft[] }>(`/api/podcasts/episodes/${folgeId}/werbung`);
    return { stellen: r.stellen.map(stelleAus), quellen: r.quellen };
  }

  async setzen(folgeId: number, von: number, bis: number, text = ""): Promise<Werbestelle> {
    return stelleAus(await this.json(`/api/podcasts/episodes/${folgeId}/werbung`, { method: "POST", body: JSON.stringify({ von, bis, text }) }));
  }

  async verwerfen(stelleId: number, an: boolean): Promise<void> {
    await this.json(`/api/podcasts/werbung/${stelleId}`, { method: "PATCH", body: JSON.stringify({ verworfen: an }) });
  }

  suchen(folgeId: number, melden: (f: Fortschritt) => void): Promise<Record<string, number>> {
    return this.strom(`/api/podcasts/episodes/${folgeId}/werbung/suchen`, "gefunden", melden);
  }

  ohneWerbung(folgeId: number, melden: (f: Fortschritt) => void): Promise<string> {
    return this.strom(`/api/podcasts/episodes/${folgeId}/ohne-werbung`, "pfad", melden);
  }

  async aboSetzen(aboId: number, teil: { ueberspringen?: boolean; pruefen?: boolean }): Promise<void> {
    await this.json(`/api/podcasts/${aboId}/werbung`, { method: "PUT", body: JSON.stringify(teil) });
  }
}

/** ohne Werbeerkennung (Webversion, RAD-102): keine Stellen; ändern geht nicht, die Ansichten bieten es dort nicht an */
export class OhneWerbequelle implements Werbequelle {
  async stellen(): Promise<Werbestellen> {
    return { stellen: [], quellen: [] };
  }

  private nicht(): never {
    throw new Error("Werbeerkennung gibt es nur in der vollen App");
  }

  async setzen(): Promise<Werbestelle> { return this.nicht(); }
  async verwerfen(): Promise<void> { this.nicht(); }
  async suchen(): Promise<Record<string, number>> { return this.nicht(); }
  async ohneWerbung(): Promise<string> { return this.nicht(); }
  async aboSetzen(): Promise<void> { this.nicht(); }
}
