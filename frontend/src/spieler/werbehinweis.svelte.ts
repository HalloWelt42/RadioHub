// Hinweis "Werbung übersprungen" (RAD-32) als eigener kleiner Zustand: die Meldung der Schale zeigt ihn am Rechner und
// am Telefon, die Leiste der Wiedergabe die Stellen, ohne die Podcasts zu kennen (Basic lädt so nichts davon). Gesetzt
// wird beides vom Überspringen (werbesprung).
export interface Werbehinweis {
  /** Dauer der übersprungenen Stelle in Sekunden */
  dauer: number;
  /** woher die Stelle stammt (Schlüssel der Herkunft) */
  herkunft: string;
  zurueck: () => void;
  schliessen: () => void;
}

/** jetzt: der stehende Hinweis; stellen: die Werbestellen der laufenden Folge in Sekunden (für die Leiste) */
export const werbehinweis = $state<{ jetzt: Werbehinweis | null; stellen: { von: number; bis: number }[] }>({ jetzt: null, stellen: [] });

/** Stellen in Prozent einer Dauer, für die Leiste der Wiedergabe */
export function werbemarken(dauer: number): { von: number; breite: number }[] {
  if (!dauer) return [];
  return werbehinweis.stellen.map((s) => ({ von: (s.von / dauer) * 100, breite: Math.max(0.6, ((s.bis - s.von) / dauer) * 100) }));
}
