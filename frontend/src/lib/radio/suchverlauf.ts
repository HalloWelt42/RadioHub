// Suchverlauf eines Suchfelds: die zehn letzten Suchen ab zwei Zeichen, im Browser gemerkt, je Bereich ein Schlüssel
// (Sender wie bisher radiohub_search_history, Podcasts eigener). Ohne Speicher (privates Fenster) gilt der Verlauf bis
// zum Neuladen.
const GROESSE = 10;

export class Suchverlauf {
  private liste: string[] | null = null;

  constructor(private readonly schluessel: string) {}

  private lesen(): string[] {
    try {
      const roh = JSON.parse(localStorage.getItem(this.schluessel) ?? "[]");
      return Array.isArray(roh) ? roh.filter((x): x is string => typeof x === "string").slice(0, GROESSE) : [];
    } catch {
      return [];
    }
  }

  private schreiben(liste: string[]): void {
    try {
      if (liste.length) localStorage.setItem(this.schluessel, JSON.stringify(liste));
      else localStorage.removeItem(this.schluessel);
    } catch {
      /* ohne Speicher nur bis zum Neuladen */
    }
  }

  alle(): string[] {
    this.liste ??= this.lesen();
    return this.liste;
  }

  /** Suche merken (vorn, ohne Doppel); kürzere als zwei Zeichen nicht */
  merken(suche: string): string[] {
    const s = suche.trim();
    if (s.length < 2) return this.alle();
    this.liste = [s, ...this.alle().filter((x) => x !== s)].slice(0, GROESSE);
    this.schreiben(this.liste);
    return this.liste;
  }

  vergessen(): string[] {
    this.liste = [];
    this.schreiben(this.liste);
    return this.liste;
  }
}

export const senderSuchverlauf = new Suchverlauf("radiohub_search_history");
