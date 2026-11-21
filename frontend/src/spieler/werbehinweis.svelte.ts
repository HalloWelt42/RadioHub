// Hinweis zur Werbung als eigener kleiner Zustand: die Meldung der Schale zeigt ihn am Rechner und am Telefon, die
// Kanzel färbt sich bernstein, die Leiste der Wiedergabe zeigt die Stellen, ohne Podcasts oder Radio zu kennen (Basic
// lädt so nichts davon). Gesetzt wird er vom Überspringen in Folgen (werbesprung, RAD-32) und im Radio (radiowerbung,
// RAD-33).
//   uebersprungen  eine Stelle wurde übersprungen; Zurück und anhören
//   verbinden      der Sender spielt beim Verbinden einen Spot; die Wiedergabe beginnt danach, Trotzdem hören
//   stumm          live läuft Werbung, der Puffer reicht nicht zum Springen; stumm bis zum Ende, Ton an
export type Werbeart = "uebersprungen" | "verbinden" | "stumm";

export interface Werbehinweis {
  art: Werbeart;
  /** Länge der Stelle in Sekunden (falls bekannt) */
  dauer: number | null;
  /** Restzeit bis zum Ende in Sekunden (verbinden, stumm; null: Ende noch unbekannt) */
  rest?: number | null;
  /** woher die Stelle stammt (Schlüssel unter schale.werbeherkunft_*), wenn kein Werbender bekannt ist */
  herkunft: string;
  /** wer wirbt (aus den Sendedaten) */
  werbender?: string;
  /** Zurück und anhören, Trotzdem hören, Ton an */
  anhoeren: () => void;
  schliessen?: () => void;
}

/** jetzt: der stehende Hinweis; stellen: die Werbestellen der laufenden Folge in Sekunden (für die Leiste) */
export const werbehinweis = $state<{ jetzt: Werbehinweis | null; stellen: { von: number; bis: number }[] }>({ jetzt: null, stellen: [] });

/** Stellen in Prozent einer Dauer, für die Leiste der Wiedergabe */
export function werbemarken(dauer: number): { von: number; breite: number }[] {
  if (!dauer) return [];
  return werbehinweis.stellen.map((s) => ({ von: (s.von / dauer) * 100, breite: Math.max(0.6, ((s.bis - s.von) / dauer) * 100) }));
}

/** Für die Kanzel: läuft gerade Werbung, die nicht zu hören ist (verbinden oder stumm)? */
export function werbungLaeuft(): { art: "verbinden" | "stumm"; rest: number | null } | null {
  const w = werbehinweis.jetzt;
  return w && (w.art === "verbinden" || w.art === "stumm") ? { art: w.art, rest: w.rest ?? null } : null;
}
