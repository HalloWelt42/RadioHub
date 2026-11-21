// Schnittstelle der Aufnahmen (RAD-17): was die Ansichten über Aufnahmen, Titel, Ordner, Sperrliste und die
// Kellerwolke wissen und ändern. Die volle App setzt sie gegen das Backend um (backend.ts); Basic hat keine Aufnahmen.
import type { Aufnahme, Aufnahmeabfrage, Aufnahmeordner, Aufnahmeseite, Titel, Wolkenebene } from "./typen";

export interface Aufnahmefaehigkeiten {
  /** Aufnahmen und Titel schneiden, normalisieren, umwandeln */
  schnitt: boolean;
  /** die ganze Kellerwolke durchgehen (Freigabe "Alles lesen") */
  wolke: boolean;
  /** Ordner, Verschieben, Löschen (am Telefon nicht) */
  verwalten: boolean;
}

export interface Aufnahmequelle {
  readonly faehig: Aufnahmefaehigkeiten;

  aufnahmen(abfrage: Aufnahmeabfrage, ab: number, anzahl: number): Promise<Aufnahmeseite>;
  aufnahme(id: string): Promise<Aufnahme>;
  titel(id: string): Promise<Titel[]>;
  /** beim Aufnehmen erkannte Titelwechsel (für "Nach Titeln teilen") */
  titelwechsel(id: string): Promise<number>;
  loeschen(id: string): Promise<void>;
  titelLoeschen(id: string, titelId: number): Promise<void>;
  nachTitelnTeilen(id: string): Promise<number>;
  verschieben(id: string, ordnerId: number | null): Promise<void>;

  ordner(): Promise<Aufnahmeordner[]>;
  ordnerAnlegen(name: string): Promise<void>;
  ordnerUmbenennen(id: number, name: string): Promise<void>;
  ordnerLoeschen(id: number): Promise<void>;
  /** null: neue Aufnahmen in den Stammordner */
  zielSetzen(id: number | null): Promise<void>;

  /** Titel, die eine Aufnahme nicht teilen (genaue Muster der Sperrliste) */
  gesperrt(): Promise<Set<string>>;
  sperren(titel: string, an: boolean): Promise<void>;

  /** Adressen zum Hören und Laden */
  titelTon(titelId: number): string;
  titelDatei(titelId: number): string;
  alsZip(id: string): string;
  alsEineDatei(id: string): string;

  wolke(pfad: string, ab?: number): Promise<Wolkenebene>;
  wolkeTon(pfad: string, herunterladen?: boolean): string;
}
