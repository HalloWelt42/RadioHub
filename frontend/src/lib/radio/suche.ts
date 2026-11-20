// Suche mit Ausschlüssen (Nutzer 20.11.2026: "mit minus den sender wegfiltern"): ein Wort mit vorangestelltem Minus
// schließt jeden Sender aus, der es in Name, Genre, Tag, Ort oder Sprache hat; ein Minus allein zählt nicht. Dieselbe
// Regel wie im Backend (senderquelle/abfrage.py, suche_zerlegen).

export interface Suchwunsch {
  /** was gesucht wird, ohne die Ausschlüsse */
  text: string;
  /** Wörter, die keiner der Treffer enthalten darf */
  ohne: string[];
}

export function sucheZerlegen(suche: string): Suchwunsch {
  const woerter = suche.split(/\s+/).filter((w) => w && w !== "-");
  const aus = woerter.filter((w) => w.startsWith("-"));
  return { text: woerter.filter((w) => !w.startsWith("-")).join(" "), ohne: aus.map((w) => w.slice(1)) };
}
