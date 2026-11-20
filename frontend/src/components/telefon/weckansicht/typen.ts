// Was jede Gestaltung der Weckansicht zeigt und was sie auslösen kann (RAD-15). Die Weckansicht (TelefonWecker.svelte)
// rechnet den Zustand einmal; die Gestaltungen zeichnen ihn nur und rufen die Aktionen. So hat jede Gestaltung dieselben
// Ereignisse (Klingeln, Schlummern, Verbindung, Ansage) in ihrem eigenen Stil, und keine kennt die Logik.

export type Modus = "hell" | "dunkel" | "nacht";
export type Lage = "ruhe" | "klingelt" | "schlummert";
export type Weckquelle = "radio" | "weckton";
export type Verbindung = "aus" | "ok" | "verbindet" | "gestoert";

export interface Weckbild {
  /** "06:42" */
  zeit: string;
  jetzt: Date;
  /** "FR 20.11." */
  datum: string;
  modus: Modus;
  lage: Lage;
  /** beim Klingeln: was gerade weckt (der Weckton auch, wenn er für ein stummes Radio einspringt) */
  quelle: Weckquelle;
  /** "Radio" oder "Podcast": womit der Wecker weckt, wenn nicht der Weckton */
  quelleName: string;
  sender: string;
  /** kurz für grobe Anzeigen: erster Teil des Namens, in Großbuchstaben */
  senderKurz: string;
  /** nächster Wecker "Mo 06:30", sonst null */
  naechster: string | null;
  /** Uhrzeit des klingelnden Weckers "06:30" */
  klingelZeit: string | null;
  /** so lange schlummert der klingelnde Wecker (Minuten) */
  schlummerMinuten: number;
  /** Schlummern bis "06:39" */
  schlummerBis: string | null;
  sonne: { auf: string; unter: string } | null;
  spielt: boolean;
  /** Abspielknopf zeigt Stopp statt Pause (direkter Weg ohne Zeitversatz) */
  stoppStattPause: boolean;
  verbindung: Verbindung;
  ansage: { an: boolean; gesperrt: boolean; laeuft: boolean };
  nachtWahl: "auto" | "an" | "aus";
  /** Tasten der ruhigen Ansicht sichtbar (bei Gestaltungen, die sie erst nach Antippen zeigen) */
  tastenSichtbar: boolean;
  /** die Ziffern zucken kurz (Ansage noch nicht bereit) */
  zucken: boolean;
}

export interface Weckaktionen {
  umschalten(): void;
  ansage(): void;
  nacht(): void;
  schlummern(): void;
  aus(): void;
  quelle(q: Weckquelle): void;
}

export interface Gestaltungsprops {
  bild: Weckbild;
  tun: Weckaktionen;
  /** übersetzt einen Schlüssel aus "telefon" */
  t: (schluessel: string, werte?: Record<string, string | number>) => string;
}
