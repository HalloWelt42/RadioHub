// Aufnahmen (RAD-17): das Datenmodell, unabhängig von der Herkunft. Eine Aufnahme ist eine Sitzung mit ihren Titeln
// (Stücken) in der Ablage; ein Ordner sammelt Aufnahmen, höchstens einer ist das Ziel neuer Aufnahmen. Dazu die ganze
// Kellerwolke Ebene für Ebene, aus der der Schnitt beliebige Audiodateien öffnet.

/** schneidet: beendet, die Stücke werden noch genau geschnitten (hören geht, ändern nicht); voll: endete, weil der Platz bis
 *  auf die Reserve belegt war */
export type Aufnahmestatus = "fertig" | "laeuft" | "schneidet" | "voll" | "abgebrochen" | "unterbrochen" | "angehaengt";
export const zumHoeren = (a: Aufnahme): boolean => a.status !== "laeuft";
export const zumAendern = (a: Aufnahme): boolean => a.status !== "laeuft" && a.status !== "schneidet";
/** eine Aufnahme, die sich noch ändert: ihre Ansicht holt nach */
export const imGange = (a: Aufnahme): boolean => a.status === "laeuft" || a.status === "schneidet";
/** endete anders als gewollt */
export const vorzeitig = (a: Aufnahme): boolean => a.status === "voll" || a.status === "abgebrochen" || a.status === "unterbrochen";

export interface Aufnahme {
  id: string;
  sender: string;
  /** Kennung des Senders (für sein Logo), leer ohne */
  senderUuid: string;
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
  /** Titel: ohne Werbung, Einschübe und kurze Senderkennung (RAD-139) */
  titelzahl: number;
  /** alle Stücke */
  stueckzahl: number;
  status: Aufnahmestatus;
  /** an diese Aufnahme kommt sie, sobald sie fertig ist (RAD-145) */
  zielId: string | null;
  /** Stand des Feinschnitts, solange er arbeitet */
  arbeit: { fertig: number; gesamt: number } | null;
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
  titelzahl: number;
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
  /** Titel aller Aufnahmen der Abfrage */
  titelGesamt: number;
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
