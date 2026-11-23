// Live mitlesen (RAD-129): ein Mitlesen zugleich, am laufenden Sender. Es läuft, bis man es ausschaltet, der Sender wechselt
// oder das Radio endet; ein zugeklappter Steckbrief beendet es nicht. Jede Abfrage sagt dem Server, dass noch jemand liest.
import { currentLanguage } from "../i18n.js";
import { Netzfehler, netz, type Anfrage } from "./netz";
import type { SpracheKurz } from "./typen";

export interface Absatz {
  nr: number;
  von: number;
  bis: number;
  /** Uhrzeit, zu der es gesendet wurde (ISO) */
  zeit: string;
  text: string;
  uebersetzung: string;
  /** Länge des gesprochenen Tons in Sekunden; 0: nicht gesprochen */
  ton_s: number;
}

export type Zustand = "aus" | "sammelt" | "hoert" | "uebersetzt" | "gestoert";

export interface Mitlesestand {
  laeuft: boolean;
  zustand: Zustand;
  grund: string;
  uuid: string;
  name: string;
  sprache: string;
  ziel: string;
  uebersetzen: boolean;
  /** die Übersetzerstimme spricht mit; kann_sprechen: Vertonung und Stimme sind eingerichtet */
  sprechen: boolean;
  kann_sprechen: boolean;
  /** es wird in der Kellerwolke abgelegt */
  ablegen: boolean;
  absaetze: Absatz[];
  fassung: number;
}

const TAKT_MS = 2000;
/** so lange darf der Sender brauchen, bis er über den Puffer läuft (409, bis dahin) */
const ANLAUF_MS = 1000, ANLAUF_HOECHSTENS = 25;

/** Sprache des Senders laut Label: genau eine mit Kürzel; bei keiner oder mehreren erkennt sie der Hördienst */
export function spracheVon(sprachen: Pick<SpracheKurz, "schluessel">[]): string {
  return sprachen.length === 1 && /^[a-z]{2,3}$/.test(sprachen[0].schluessel) ? sprachen[0].schluessel : "";
}

/** Neue und geänderte Absätze einsortieren, in der Reihenfolge der Sendung */
export function zusammen(alt: Absatz[], neu: Absatz[]): Absatz[] {
  if (!neu.length) return alt;
  const nach = new Map(alt.map((a) => [a.nr, a]));
  for (const a of neu) nach.set(a.nr, a);
  return [...nach.values()].sort((a, b) => a.nr - b.nr);
}

export const uhrzeit = (iso: string): string => iso.slice(11, 19);

/** Der Text zum Kopieren: je Absatz Uhrzeit und Text, mit Übersetzung darunter */
export const alsText = (absaetze: Absatz[], uebersetzt: boolean): string =>
  absaetze.map((a) => `${uhrzeit(a.zeit)}  ${a.text}${uebersetzt && a.uebersetzung ? `\n${a.uebersetzung}` : ""}`).join("\n\n");

export class Mitlesen {
  /** null: noch nicht gefragt */
  eingerichtet = $state<boolean | null>(null);
  /** der Sender, dessen Text gezeigt wird; bleibt stehen, wenn das Radio endet, bis man es ausschaltet */
  uuid = $state("");
  stand = $state.raw<Omit<Mitlesestand, "absaetze"> | null>(null);
  absaetze = $state.raw<Absatz[]>([]);
  fehler = $state("");
  beginnt = $state(false);
  private takt: ReturnType<typeof setInterval> | undefined;
  private fragt = false;

  constructor(private readonly a: Anfrage = netz()) {}

  /** fremde Sprache: nur dann ist Übersetzen eine Wahl */
  get fremd(): boolean {
    return !!this.stand?.sprache && this.stand.sprache !== this.stand.ziel;
  }

  laeuftFuer(uuid: string): boolean {
    return this.uuid === uuid;
  }

  async pruefen(): Promise<void> {
    if (this.eingerichtet !== null) return;
    this.eingerichtet = false;
    this.eingerichtet = (await this.a<{ eingerichtet: boolean }>("/api/mitlesen/kann").catch(() => ({ eingerichtet: false }))).eingerichtet;
  }

  /** Das Feld steht sofort da; läuft der Sender noch nicht, wird gewartet, bis er über den Puffer spielt. `weiter`: nach einem Ende
   *  fortsetzen, der gelesene Text bleibt */
  async starten(uuid: string, sprachen: SpracheKurz[], weiter = false): Promise<void> {
    const ziel = currentLanguage() || "de", sprache = spracheVon(sprachen);
    const daten = { uuid, sprache, ziel, uebersetzen: !!sprache && sprache !== ziel };
    clearInterval(this.takt);
    if (!weiter) {
      this.absaetze = [];
      this.stand = null;
    }
    this.fehler = "";
    this.uuid = uuid;
    this.beginnt = true;
    try {
      const s = await this.anlaufen(daten);
      if (this.uuid !== uuid || !s) return;            // inzwischen ausgeschaltet
      this.uebernehmen(s);
      this.takt = setInterval(() => void this.lesen(), TAKT_MS);
    } catch (f) {
      if (this.uuid === uuid && !weiter) this.uuid = "";
      throw f;
    } finally {
      this.beginnt = false;
    }
  }

  private async anlaufen(daten: { uuid: string }): Promise<Mitlesestand | null> {
    for (let i = 0; this.uuid === daten.uuid; i++) {
      try {
        return await this.a<Mitlesestand>("/api/mitlesen", { methode: "POST", daten });
      } catch (f) {
        if (!(f instanceof Netzfehler) || f.status !== 409 || i >= ANLAUF_HOECHSTENS) throw f;
        await new Promise((r) => setTimeout(r, ANLAUF_MS));
      }
    }
    return null;
  }

  /** Aus beendet auch die Arbeit am Server */
  async beenden(): Promise<void> {
    clearInterval(this.takt);
    this.uuid = "";
    await this.a("/api/mitlesen", { methode: "DELETE" }).catch(() => undefined);
  }

  async uebersetzen(an: boolean): Promise<void> {
    this.uebernehmen(await this.a("/api/mitlesen", { methode: "PUT", daten: { uebersetzen: an } }));
  }

  /** Übersetzerstimme an oder aus (an schließt Übersetzen ein) */
  async sprechen(an: boolean): Promise<void> {
    this.uebernehmen(await this.a("/api/mitlesen", { methode: "PUT", daten: { sprechen: an } }));
  }

  async lesen(): Promise<void> {
    if (this.fragt || !this.uuid) return;
    this.fragt = true;
    try {
      const s = await this.a<Mitlesestand>(`/api/mitlesen?ab=${this.stand?.fassung ?? 0}`);
      if (!this.uuid) return;                        // inzwischen ausgeschaltet
      this.uebernehmen(s);
      this.fehler = s.zustand === "gestoert" ? s.grund : "";
      if (!s.laeuft) clearInterval(this.takt);
    } catch (f) {
      this.fehler = (f as Error).message;
    } finally {
      this.fragt = false;
    }
  }

  private uebernehmen(s: Mitlesestand): void {
    const { absaetze, ...rest } = s;
    this.stand = rest;
    this.absaetze = zusammen(this.absaetze, absaetze);
  }
}

export const mitlesen = new Mitlesen();
