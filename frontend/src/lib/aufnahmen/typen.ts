// Aufnahmen (RAD-17): das Datenmodell, unabhängig von der Herkunft. Eine Aufnahme ist eine Sitzung mit ihren Titeln
// (Stücken) in der Ablage; ein Ordner sammelt Aufnahmen, höchstens einer ist das Ziel neuer Aufnahmen. Dazu die ganze
// Kellerwolke Ebene für Ebene, aus der der Schnitt beliebige Audiodateien öffnet.

export type Aufnahmestatus = "fertig" | "laeuft" | "abgebrochen" | "unterbrochen";

export interface Aufnahme {
  id: string;
  sender: string;
  /** ISO-Zeit des Beginns */
  beginn: string;
  /** Sekunden */
  dauer: number;
  /** Bytes */
  groesse: number;
  codec: string;
  bitrate: number | null;
  /** direkt vom Sender oder aus dem Puffer des Zeitversatzes */
  art: "direkt" | "puffer";
  ordnerId: number | null;
  titelzahl: number;
  status: Aufnahmestatus;
  /** Lücken laut Messung beim Aufnehmen */
  luecken: number;
}

export interface Titel {
  id: number;
  nr: number;
  titel: string;
  /** Sekunden ab Beginn der Aufnahme */
  start: number;
  dauer: number;
  groesse: number;
  pfad: string;
}

export interface Aufnahmeordner {
  id: number;
  name: string;
  /** neue Aufnahmen landen hier */
  ziel: boolean;
  anzahl: number;
}

export type Aufnahmesortierung = "datum" | "sender" | "dauer" | "groesse";
export const AUFNAHMESORTIERUNG: readonly Aufnahmesortierung[] = ["datum", "sender", "dauer", "groesse"];

export interface Aufnahmeabfrage {
  suche: string;
  /** "" alle, "ohne" ohne Ordner, sonst die Kennung */
  ordner: string;
  sort: Aufnahmesortierung;
  absteigend: boolean;
}

export interface Aufnahmeseite {
  aufnahmen: Aufnahme[];
  gesamt: number;
}

export interface Wolkendatei {
  name: string;
  pfad: string;
  groesse: number;
  geaendert: string | null;
}

export interface Wolkenebene {
  pfad: string;
  kette: { name: string; pfad: string }[];
  ordner: { name: string; pfad: string }[];
  dateien: Wolkendatei[];
  gesamt: number;
  /** darf RadioHub hier Ergebnisse des Schnitts ablegen */
  schreibbar: boolean;
}
