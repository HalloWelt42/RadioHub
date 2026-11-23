// Was die Übersetzerstimme als Nächstes spricht (RAD-130). Reine Regeln ohne Ton: Vorlauf vor dem ersten Satz, schneller, wenn
// sich gesprochene Absätze stauen, und notfalls die ältesten auslassen, damit die Stimme nie immer weiter zurückfällt.

export interface Gesprochenes {
  nr: number;
  /** Länge in Sekunden; 0: noch nicht gesprochen */
  ton_s: number;
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

export const tempoBei = (wartend_s: number): number => (wartend_s > 60 ? 1.25 : wartend_s > 40 ? 1.15 : wartend_s > 25 ? 1.07 : 1);

/** Der nächste Absatz, oder null: es ist (noch) nichts zu sprechen. `zuletzt`: der letzte gesprochene oder ausgelassene;
 *  `laeuft`: die Stimme ist schon im Gang, dann braucht es keinen Vorlauf mehr */
export function naechster(absaetze: Gesprochenes[], zuletzt: number, laeuft: boolean): Schritt | null {
  let bereit = absaetze.filter((a) => a.nr > zuletzt && a.ton_s > 0);
  if (!bereit.length) return null;
  const summe = () => bereit.reduce((s, a) => s + a.ton_s, 0);
  if (!laeuft && bereit.length < VORLAUF_ABSAETZE && summe() < VORLAUF_S) return null;
  if (summe() > STAU_S) while (bereit.length > 1 && summe() > STAU_BIS_S) bereit = bereit.slice(1);
  return { nr: bereit[0].nr, tempo: tempoBei(summe()) };
}
