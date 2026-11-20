// Speicher der eigenen Angaben: eine kleine Schnittstelle über Schlüssel und Text, im Browser über localStorage, in
// Tests im Speicher. Kann der Browser nicht speichern (privates Fenster, Sperre), gilt das als Fehler beim Schreiben;
// gelesen wird dann nichts.

export interface Speicher {
  lesen(schluessel: string): string | null;
  /** wirft, wenn der Speicher voll oder gesperrt ist */
  schreiben(schluessel: string, wert: string): void;
}

/** über einen Storage des Browsers (localStorage) */
export function browserSpeicher(ablage: Pick<Storage, "getItem" | "setItem">): Speicher {
  return {
    lesen(schluessel) {
      try {
        return ablage.getItem(schluessel);
      } catch {
        return null;
      }
    },
    schreiben(schluessel, wert) {
      ablage.setItem(schluessel, wert);
    },
  };
}

/** nur im Speicher (Tests) */
export function fluechtigerSpeicher(anfang: Record<string, string> = {}): Speicher & { inhalt: Map<string, string> } {
  const inhalt = new Map(Object.entries(anfang));
  return { inhalt, lesen: (s) => inhalt.get(s) ?? null, schreiben: (s, w) => void inhalt.set(s, w) };
}
