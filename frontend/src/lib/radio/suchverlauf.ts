// Suchverlauf der Sendersuche: die zehn letzten Suchen ab zwei Zeichen, im Browser gemerkt (Schlüssel wie bisher,
// radiohub_search_history). Ohne Speicher (privates Fenster) gilt der Verlauf bis zum Neuladen.
const SCHLUESSEL = "radiohub_search_history";
const GROESSE = 10;

function lesen(): string[] {
  try {
    const roh = JSON.parse(localStorage.getItem(SCHLUESSEL) ?? "[]");
    return Array.isArray(roh) ? roh.filter((x): x is string => typeof x === "string").slice(0, GROESSE) : [];
  } catch {
    return [];
  }
}

function schreiben(liste: string[]): void {
  try {
    if (liste.length) localStorage.setItem(SCHLUESSEL, JSON.stringify(liste));
    else localStorage.removeItem(SCHLUESSEL);
  } catch {
    /* ohne Speicher nur bis zum Neuladen */
  }
}

let verlauf: string[] | null = null;

export function suchverlauf(): string[] {
  verlauf ??= lesen();
  return verlauf;
}

/** Suche merken (vorn, ohne Doppel); kürzere als zwei Zeichen nicht */
export function merken(suche: string): string[] {
  const s = suche.trim();
  if (s.length < 2) return suchverlauf();
  verlauf = [s, ...suchverlauf().filter((x) => x !== s)].slice(0, GROESSE);
  schreiben(verlauf);
  return verlauf;
}

export function vergessen(): string[] {
  verlauf = [];
  schreiben(verlauf);
  return verlauf;
}
