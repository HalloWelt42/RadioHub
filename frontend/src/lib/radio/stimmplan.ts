// Was die Übersetzerstimme als Nächstes spricht (RAD-130). Reine Regeln ohne Ton: Vorlauf vor dem ersten Satz, schneller, wenn
// sie länger braucht als das Original oder sich gesprochene Absätze stauen, und notfalls die ältesten auslassen, damit die Stimme nie immer weiter zurückfällt.

export interface Gesprochenes {
  nr: number;
  /** Länge in Sekunden; 0: noch nicht gesprochen */
  ton_s: number;
  /** der Absatz im Original, Sekunden der Sendung */
  von: number;
  bis: number;
}

/** so viel liegt bereit, bevor es losgeht */
export const VORLAUF_ABSAETZE = 2;
export const VORLAUF_S = 20;
/** ab so viel Wartendem wird ausgelassen, bis nur noch so viel wartet */
export const STAU_S = 90;
export const STAU_BIS_S = 45;

export interface Schritt {
  nr: number;
  tempo: number;
}

/** schneller wird sie nie */
export const TEMPO_HOECHSTENS = 1.4;

/** Ein Absatz soll etwa so lange dauern wie im Original; staut sich etwas, kommt noch etwas dazu */
export function tempoFuer(a: Gesprochenes, wartend_s: number): number {
  const passend = Math.min(1.25, Math.max(1, a.ton_s / Math.max(1, a.bis - a.von)));
  const stau = wartend_s > 60 ? 0.15 : wartend_s > 40 ? 0.08 : 0;
  return Math.round(Math.min(TEMPO_HOECHSTENS, passend + stau) * 100) / 100;
}

/** Der nächste Absatz, oder null: es ist (noch) nichts zu sprechen. `zuletzt`: der letzte gesprochene oder ausgelassene;
 *  `laeuft`: die Stimme ist schon im Gang, dann braucht es keinen Vorlauf mehr */
export function naechster(absaetze: Gesprochenes[], zuletzt: number, laeuft: boolean): Schritt | null {
  let bereit = absaetze.filter((a) => a.nr > zuletzt && a.ton_s > 0);
  if (!bereit.length) return null;
  const summe = () => bereit.reduce((s, a) => s + a.ton_s, 0);
  if (!laeuft && bereit.length < VORLAUF_ABSAETZE && summe() < VORLAUF_S) return null;
  if (summe() > STAU_S) while (bereit.length > 1 && summe() > STAU_BIS_S) bereit = bereit.slice(1);
  return { nr: bereit[0].nr, tempo: tempoFuer(bereit[0], summe() - bereit[0].ton_s) };
}
