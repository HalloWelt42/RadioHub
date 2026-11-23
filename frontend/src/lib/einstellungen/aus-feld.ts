// Ein Feld des Servermodells (Feld des Appkerns: Titel, Beschreibung, Art, Grenzen, Einheit, Herkunft) als Zeile der
// Einstellungsseite (RAD-11). Rein rechnend; die Werte im Entwurf kommen von außen.
import type { Feld } from "appkern-oberflaeche";
import type { Wahlwert, Zeile, ZeilenArt } from "./typen";

/** Ab so vielen Werten klappt eine Wahl auf, statt als Segment nebeneinander zu stehen */
export const SEGMENT_HOECHSTENS = 6;

/** Art einer Wahl nach ihrer Zahl von Werten, für Felder des Servers und Einstellungen dieses Geräts gleich */
export function wahlArt(anzahl: number): "wahl" | "auswahl" {
  return anzahl > SEGMENT_HOECHSTENS ? "auswahl" : "wahl";
}

function art(feld: Feld): ZeilenArt {
  switch (feld.art) {
    case "schalter": return "schalter";
    case "zahl": return "zahl";
    case "auswahl": return feld.angebot ? "auswahl" : wahlArt(feld.optionen.length);
    case "liste": return Object.keys(feld.beschriftungen ?? {}).length ? "mehrfach" : "liste";
    case "text": return feld.einheit === "Uhrzeit" ? "uhrzeit" : feld.angebot ? "auswahl" : "text";
    default: return "text";
  }
}

function optionen(feld: Feld): Wahlwert[] {
  const namen = feld.beschriftungen ?? {};
  const werte = feld.optionen.length ? feld.optionen : Object.keys(namen);
  return werte.map((w) => ({ wert: String(w), titel: namen[String(w)] ?? String(w) }));
}

/** Sekunden in großen Schritten zeigt die Zeile als Stunden oder Minuten (Abstand des Abrufs, Geduld beim Ablegen) */
export function anzeigeeinheit(feld: Pick<Feld, "einheit" | "schritt">): { faktor: number; einheit: string } {
  const schritt = feld.schritt ?? 1;
  if (feld.einheit === "s" && schritt % 3600 === 0) return { faktor: 3600, einheit: "h" };
  if (feld.einheit === "s" && schritt % 60 === 0) return { faktor: 60, einheit: "min" };
  return { faktor: 1, einheit: feld.einheit ?? "" };
}

export function zeileAusFeld(feld: Feld, wert: unknown, geaendert: boolean): Zeile {
  const a = art(feld);
  const { faktor, einheit } = a === "zahl" ? anzeigeeinheit(feld) : { faktor: 1, einheit: feld.einheit ?? "" };
  const teilen = (x: number | null | undefined) => (x === null || x === undefined ? undefined : x / faktor);
  return {
    schluessel: feld.name, titel: feld.titel, beschreibung: feld.beschreibung, art: a, geltung: "alle",
    wert: a === "zahl" && typeof wert === "number" ? wert / faktor : wert,
    optionen: a === "wahl" || a === "auswahl" || a === "mehrfach" ? optionen(feld) : [],
    kleinste: faktor > 1 ? Math.ceil(teilen(feld.kleinste) ?? 0) : teilen(feld.kleinste), groesste: teilen(feld.groesste),
    schritt: teilen(feld.schritt), einheit: a === "uhrzeit" ? "" : einheit, faktor, fest: feld.herkunft === "fest", geaendert,
    angebot: !!feld.angebot, vorgabe: feld.vorgabe,
  };
}

/** Der Wert einer Wahl im Typ des Felds: Optionen sind immer Text, Zahlenwahlen (etwa die Abtastrate) bleiben Zahl */
export function wahlwert(feld: Pick<Feld, "vorgabe"> | undefined, text: string): string | number {
  return typeof feld?.vorgabe === "number" ? Number(text) : text;
}
