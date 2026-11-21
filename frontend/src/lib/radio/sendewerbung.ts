// Werbung aus den Sendedaten (RAD-33): was der Server über die Werbung eines Senders weiß (bekannte Spots, Schalter
// je Sender) und die Werbestellen der laufenden Sitzung im Zeitversatz (Status des Puffers, Sekunden des Tons wie die
// Segmente). Dazu reine Regeln ohne Ton und ohne Zustand, damit sie mit vitest prüfbar sind (tests/sendewerbung.test.ts):
// wo die Wiedergabe beginnt, wenn der Sender beim Verbinden einen Spot spielt, und was an einer Stelle des Tons zu tun ist.
import { netz, type Anfrage } from "./netz";

export interface Werbestelle {
  von: number;
  /** null: läuft noch, das Ende kommt mit dem nächsten Wechsel der Sendedaten */
  bis: number | null;
  von_aus: string;
  bis_aus: string | null;
  format: string;
  kennung: string;
  werbender: string;
  titel: string;
  angekuendigt_ms: number | null;
  beim_verbinden: boolean;
}

export interface Spot {
  format: string;
  kennung: string;
  werbender: string;
  titel: string;
  dauer_ms: number | null;
  beim_verbinden: boolean;
  anzahl: number;
  zuerst: string;
  zuletzt: string;
}

export interface SenderWerbung {
  uuid: string;
  name: string;
  spots: number;
  zuletzt: string | null;
  ueberspringen: boolean;
  ausgenommen: boolean;
}

export interface Steckbrief extends SenderWerbung {
  liste: Spot[];
}

export class Sendewerbung {
  constructor(private readonly a: Anfrage = netz()) {}

  werbende(): Promise<SenderWerbung[]> {
    return this.a("/api/sendewerbung");
  }

  steckbrief(uuid: string): Promise<Steckbrief> {
    return this.a(`/api/sendewerbung/${encodeURIComponent(uuid)}`);
  }

  setzen(uuid: string, ueberspringen: boolean): Promise<Steckbrief> {
    return this.a(`/api/sendewerbung/${encodeURIComponent(uuid)}`, { methode: "PUT", daten: { ueberspringen } });
  }

  /** Einstellung für alle Sender (werbung_ueberspringen, Vorgabe an) */
  async alle(): Promise<boolean> {
    const c = await this.a<Record<string, unknown>>("/api/config");
    return c.werbung_ueberspringen !== false && c.werbung_ueberspringen !== "false";
  }

  async alleSetzen(an: boolean): Promise<void> {
    await this.a("/api/config", { methode: "PUT", daten: { updates: { werbung_ueberspringen: an } } });
  }
}

/** Werbelisten (Werbende, Spots, Sender mit Werbung; Nutzer 21.11.2026): ab so vielen Einträgen rollt die Liste in
 *  sich, und mehr als HOECHSTENS zeigt sie nicht, sondern nur die häufigsten */
export const LISTE_ROLLT_AB = 6;
export const LISTE_HOECHSTENS = 40;

/** Die häufigsten Einträge einer schon nach Häufigkeit sortierten Liste und wie viele weggelassen sind */
export function haeufigste<T>(liste: T[]): { zeigen: T[]; weggelassen: number; rollt: boolean } {
  const zeigen = liste.slice(0, LISTE_HOECHSTENS);
  return { zeigen, weggelassen: liste.length - zeigen.length, rollt: zeigen.length >= LISTE_ROLLT_AB };
}

/** Spots eines Werbenden (Steckbrief, RAD-35): wie oft zusammen, ob einer beim Verbinden kam, zuletzt */
export interface Werbender {
  /** Name aus den Sendedaten; leer, wenn der Sender keinen nennt (dann steht jede Kennung für sich) */
  name: string;
  kennung: string;
  spots: Spot[];
  mal: number;
  beimVerbinden: boolean;
  zuletzt: string;
}

/** Spots nach Werbenden zusammengefasst, die häufigsten zuerst; Spots ohne Namen bleiben je Kennung für sich */
export function nachWerbenden(liste: Spot[]): Werbender[] {
  const gruppen = new Map<string, Werbender>();
  for (const s of liste) {
    const schluessel = s.werbender || `${s.format}:${s.kennung}`;
    const g = gruppen.get(schluessel) ?? { name: s.werbender, kennung: s.kennung, spots: [], mal: 0, beimVerbinden: false, zuletzt: "" };
    g.spots.push(s);
    g.mal += s.anzahl;
    g.beimVerbinden ||= s.beim_verbinden;
    if (s.zuletzt > g.zuletzt) g.zuletzt = s.zuletzt;
    gruppen.set(schluessel, g);
  }
  for (const g of gruppen.values()) g.spots.sort((a, b) => b.anzahl - a.anzahl || b.zuletzt.localeCompare(a.zuletzt));
  return [...gruppen.values()].sort((a, b) => b.mal - a.mal || b.zuletzt.localeCompare(a.zuletzt));
}

/** Was der Puffer dem Start sagen muss (Ausschnitt aus /api/hls/status) */
export interface Pufferstand {
  segment_count?: number;
  segment_duration?: number;
  last_segment?: number | null;
  werbestellen?: Werbestelle[];
  werbung_ueberspringen?: boolean;
}

/** so viele Stücke braucht der Puffer, bevor die Wiedergabe beginnt (wie bisher beim Wechsel in den Zeitversatz) */
export const MINDESTENS_STUECKE = 3;
/** so viel Ton nach dem Ende des Spots soll schon im Puffer liegen, bevor die Wiedergabe dort beginnt */
export const VORLAUF_S = 1.5;

export type Startwahl =
  | { art: "warten" }
  | { art: "werbung"; stelle: Werbestelle; rest: number | null }
  | { art: "start"; sekunde: number | null };

/** Restzeit auf Millisekunden (gegen Rundungsreste wie 5,050000000000001) */
const restVon = (bis: number, jetzt: number): number => Math.max(0, Math.round((bis - jetzt) * 1000) / 1000);

/** Ende des Tons, der schon im Puffer liegt, in Sekunden */
export const pufferEnde = (p: Pufferstand): number => ((p.last_segment ?? -1) + 1) * (p.segment_duration || 1);

/** Wo beginnt die Wiedergabe? Spielt der Sender beim Verbinden einen Spot, beginnt sie nach ihm (null: an der
 *  Live-Kante); bis dahin wird gewartet und die Restzeit gemeldet. */
export function startwahl(p: Pufferstand): Startwahl {
  if ((p.segment_count ?? 0) < MINDESTENS_STUECKE) return { art: "warten" };
  const spot = p.werbung_ueberspringen ? p.werbestellen?.find((w) => w.beim_verbinden && w.von < 0.5) : undefined;
  if (!spot) return { art: "start", sekunde: null };
  const ende = pufferEnde(p);
  if (spot.bis !== null && ende >= spot.bis + VORLAUF_S) return { art: "start", sekunde: spot.bis };
  return { art: "werbung", stelle: spot, rest: spot.bis === null ? null : restVon(spot.bis, ende) };
}

/** so nah am Ende einer Stelle wird nicht mehr gesprungen (der Sprung wäre nur ein Ruckeln) */
export const RAND_S = 0.4;

export type Werbetat =
  | { art: "nichts" }
  | { art: "springen"; stelle: Werbestelle; nach: number }
  | { art: "stumm"; stelle: Werbestelle; rest: number | null };

/** Was an der Stelle `t` (Sekunden des Puffers) zu tun ist: liegt sie in einer nicht angehörten Werbestelle, springen,
 *  wenn ihr Ende schon im Puffer liegt, sonst stumm bis dahin. */
export function werbetat(t: number, p: Pufferstand, angehoert: (s: Werbestelle) => boolean): Werbetat {
  if (!p.werbung_ueberspringen) return { art: "nichts" };
  const s = (p.werbestellen ?? []).find((w) => t >= w.von && (w.bis === null || t < w.bis - RAND_S) && !angehoert(w));
  if (!s) return { art: "nichts" };
  if (s.bis !== null && s.bis + RAND_S <= pufferEnde(p)) return { art: "springen", stelle: s, nach: s.bis };
  return { art: "stumm", stelle: s, rest: s.bis === null ? null : restVon(s.bis, t) };
}

/** Kennung einer Stelle für "angehört" (dieselbe Stelle behält Kennung und Anfang) */
export const stellenSchluessel = (s: Werbestelle): string => `${s.format}:${s.kennung}@${Math.round(s.von)}`;

export const sendewerbung = new Sendewerbung();
