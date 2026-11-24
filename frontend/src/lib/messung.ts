// Messmodus (RAD-143), der rechnende Teil: fasst die Ereignisse des Tonelements je Sekunde zusammen (ein Zittern sind Tausende),
// misst, wie lange der Ton stockt, und sammelt, bis gesendet wird. Ohne Seite und ohne Netz, darum mit vitest prüfbar.

/** Wo das Tonelement steht */
export interface Tonlage {
  /** Sekunde im Ton, Vorrat davor in Sekunden, Abstand zum Ende des Spulbaren */
  zeit: number;
  vorrat: number;
  hinten: number | null;
  stumm: boolean;
}

export interface Messereignis {
  art: string;
  werte: Record<string, unknown>;
  /** wann es geschah (Millisekunden); gesendet wird, wie lange es her ist (die Uhren der Geräte gehen verschieden) */
  um: number;
}

export const FENSTER_MS = 1000;
/** so viele Ereignisse hält das Gerät, wenn der Server nicht antwortet */
export const HOECHSTENS = 2000;
/** so viele gehen auf einmal hinaus */
export const JE_SENDUNG = 400;

export class Messsammler {
  private warten: Messereignis[] = [];
  private fenster: { ab: number; um: number; namen: Record<string, number>; anfang: Tonlage; ende: Tonlage } | null = null;
  private stockt: { seit: number; lage: Tonlage } | null = null;

  private letzte = new Map<string, string>();

  constructor(private readonly jetzt: () => number = () => Date.now()) {}

  merken(art: string, werte: Record<string, unknown> = {}, um = this.jetzt()): void {
    if (this.warten.length < HOECHSTENS) this.warten.push({ art, werte, um });
  }

  /** nur, wenn sich gegenüber dem letzten Mal etwas geändert hat */
  geaendert(art: string, werte: Record<string, unknown>): void {
    const text = JSON.stringify(werte);
    if (this.letzte.get(art) === text) return;
    this.letzte.set(art, text);
    this.merken(art, werte);
  }

  /** ein Ereignis des Tonelements zur Zeit `jetzt` (Millisekunden) */
  ton(name: string, jetzt: number, lage: Tonlage): void {
    if (this.fenster && jetzt - this.fenster.ab >= FENSTER_MS) this.fensterZu();
    this.fenster ??= { ab: jetzt, um: this.jetzt(), namen: {}, anfang: lage, ende: lage };
    this.fenster.namen[name] = (this.fenster.namen[name] ?? 0) + 1;
    this.fenster.ende = lage;
    if (name === "waiting") this.stockt ??= { seit: jetzt, lage };
    else if (this.stockt && (name === "playing" || name === "pause" || name === "emptied")) {
      this.merken("gestockt", { dauer_s: rund((jetzt - this.stockt.seit) / 1000), ende: name, ...this.stockt.lage });
      this.stockt = null;
    }
  }

  fensterZu(): void {
    const f = this.fenster;
    if (!f) return;
    this.fenster = null;
    this.merken("ton", { anzahl: Object.values(f.namen).reduce((s, n) => s + n, 0), ereignisse: f.namen, anfang: f.anfang, ende: f.ende }, f.um);
  }

  /** die nächsten Ereignisse zum Senden; gelingt es nicht, kommen sie mit `zurueck` wieder nach vorn */
  nehmen(): Messereignis[] {
    this.fensterZu();
    return this.warten.splice(0, JE_SENDUNG);
  }

  zurueck(ereignisse: Messereignis[]): void {
    this.warten = [...ereignisse, ...this.warten].slice(0, HOECHSTENS);
  }

  leeren(): void {
    this.warten = [];
    this.letzte.clear();
    this.fenster = null;
    this.stockt = null;
  }
}

export const rund = (n: number): number => Math.round(n * 100) / 100;

export function tonlage(ton: Pick<HTMLMediaElement, "currentTime" | "buffered" | "seekable" | "muted">): Tonlage {
  const t = ton.currentTime;
  let vorrat = 0;
  for (let i = 0; i < ton.buffered.length; i++) if (ton.buffered.start(i) <= t + 0.5 && ton.buffered.end(i) > t) vorrat = ton.buffered.end(i) - t;
  const s = ton.seekable;
  const ende = s.length ? s.end(s.length - 1) : Infinity;
  return { zeit: rund(t), vorrat: rund(vorrat), hinten: Number.isFinite(ende) ? rund(ende - t) : null, stumm: ton.muted };
}
