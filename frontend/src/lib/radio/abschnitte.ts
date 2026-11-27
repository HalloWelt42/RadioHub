// Abschnitte des Zeitversatzes (RAD-46): Titel, Werbung und Einschübe im Puffer, wie der Server sie nach der Regel des
// Feinschnitts schneidet (GET /api/hls/abschnitte, Sekunden des Puffers wie die Segmente). Hier nur reine Regeln ohne
// Zustand, prüfbar mit vitest (tests/abschnitte.test.ts): welcher Abschnitt an einer Stelle läuft, wohin Vorheriger und
// Nächster Titel springen, und wie Sekunden auf eine Zeitleiste fallen.

export type Art = "titel" | "werbung" | "einschub";

export interface Abschnitt {
  von: number;
  bis: number;
  titel: string;
  art: Art;
  /** der Titel steht für mindestens zwei Drittel des Abschnitts (Feinschnitt) */
  sicher: boolean;
  /** der letzte Abschnitt läuft noch (sein Ende ist die Live-Kante) */
  laufend: boolean;
  /** beide Grenzen liegen im Puffer: der Titel lässt sich sichern (RAD-132) */
  komplett: boolean;
  /** Kennung seiner Aufnahme, leer: noch nicht gesichert */
  gesichert: string;
  /** gehört zur laufenden Aufnahme (RAD-150) */
  in_aufnahme?: boolean;
  /** dort abgewählt: fehlt nach dem Stopp in der Aufnahme */
  abgewaehlt?: boolean;
}

/** lässt sich gerade aus der laufenden Aufnahme ab- oder wieder anwählen (RAD-150) */
export const abwaehlbar = (a: Abschnitt): boolean => !!a.in_aufnahme && a.art === "titel";

/** so weit hinter dem Anfang eines Titels springt "Vorheriger Titel" an den Anfang des vorigen statt dieses */
export const ZURUECK_SCHWELLE_S = 3;

/** Der Abschnitt an der Stelle `t` (am Ende der letzte) */
export function bei(liste: Abschnitt[], t: number): Abschnitt | null {
  if (!liste.length) return null;
  return liste.find((a) => t >= a.von && t < a.bis) ?? (t >= liste[liste.length - 1].bis ? liste[liste.length - 1] : null);
}

/** so weit hinter dem Beginn wird nachgesehen: der Beginn liegt genau auf einer Grenze, Uhr und Puffer gehen einige Sekunden auseinander */
const HINTER_DEM_BEGINN_S = 4;

/** Titel, mit dem eine Aufnahme beginnt, die seit `seit` Sekunden läuft (Ende des Puffers `ende`); leer, solange er nicht feststeht */
export function anfangstitel(liste: Abschnitt[], ende: number, seit: number): string {
  const a = bei(liste, ende - seit + Math.min(HINTER_DEM_BEGINN_S, seit / 2));
  return a && a.art !== "werbung" ? a.titel : "";
}

const hoerbar = (a: Abschnitt): boolean => a.art !== "werbung";

/** Vorheriger Titel: an den Anfang des laufenden, steht man schon nahe daran, an den des vorigen (wie ein Abspieler);
 *  Werbung wird übersprungen. null, wenn es davor nichts gibt. */
export function vorheriger(liste: Abschnitt[], t: number): number | null {
  const i = liste.findIndex((a) => t >= a.von && t < a.bis);
  const jetzt = i >= 0 ? i : liste.length - 1;
  if (jetzt < 0) return null;
  if (t - liste[jetzt].von > ZURUECK_SCHWELLE_S && hoerbar(liste[jetzt])) return liste[jetzt].von;
  for (let k = jetzt - 1; k >= 0; k--) if (hoerbar(liste[k])) return liste[k].von;
  return null;
}

/** Nächster Titel: Anfang des nächsten hörbaren Abschnitts (über Werbung hinweg); null am laufenden Ende */
export function naechster(liste: Abschnitt[], t: number): number | null {
  const n = liste.find((a) => a.von > t + 0.5 && hoerbar(a));
  return n ? n.von : null;
}

/** Abschnitte, die ganz in einem Bereich liegen (Titel A bis Titel B, beide eingeschlossen) */
export function imBereich(liste: Abschnitt[], von: number, bis: number): Abschnitt[] {
  return liste.filter((a) => a.von >= von - 0.01 && a.bis <= bis + 0.01);
}

/** Bereich aus zwei gewählten Abschnitten (Reihenfolge egal): von Anfang des früheren bis Ende des späteren */
export function bereichAus(a: Abschnitt, b: Abschnitt): { von: number; bis: number } {
  return { von: Math.min(a.von, b.von), bis: Math.max(a.bis, b.bis) };
}

/** Prozent einer Sekunde auf einer Zeitleiste von `anfang` bis `ende` (gekappt) */
export function prozent(t: number, anfang: number, ende: number): number {
  return ende > anfang ? Math.min(100, Math.max(0, ((t - anfang) / (ende - anfang)) * 100)) : 0;
}

/** Ausschnitt einer Zeitleiste: `breite` Sekunden, die Stelle `mitte` möglichst mittig, innerhalb von anfang bis ende */
export function fenster(mitte: number, breite: number, anfang: number, ende: number): [number, number] {
  if (breite >= ende - anfang) return [anfang, ende];
  const von = Math.min(Math.max(anfang, mitte - breite / 2), ende - breite);
  return [von, von + breite];
}
