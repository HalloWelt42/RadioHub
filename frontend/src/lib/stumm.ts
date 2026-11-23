// Ein Ort fürs Stummschalten des Tonelements: mehrere dürfen es zugleich wollen (Werbung live, Übersetzerstimme, Zeitansage). Stumm ist es,
// solange einer will; wer aufhört, schaltet nur seinen eigenen Grund ab. Das Tonelement meldet sich selbst an (tonelement.ts).

export type Stummgrund = "werbung" | "uebersetzer" | "zeitansage";

const gruende = new Set<Stummgrund>();
let ziel: { muted: boolean } | null = null;

export function stummVerbinden(element: { muted: boolean }): void {
  ziel = element;
  if (gruende.size) ziel.muted = true;
}

export function stummSetzen(grund: Stummgrund, an: boolean): void {
  if (an) gruende.add(grund);
  else if (!gruende.delete(grund)) return;
  if (ziel) ziel.muted = gruende.size > 0;
}

export const stummWegen = (grund: Stummgrund): boolean => gruende.has(grund);
