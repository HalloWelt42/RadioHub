// Schnittstelle Podcastquelle (RAD-17): alles, was die Podcast-Ansichten am Rechner und am Telefon über Abos und
// Folgen wissen und ändern. Die volle App setzt sie gegen das Backend um (backend.ts). Was eine Umsetzung nicht kann,
// meldet sie in `faehig`; die Ansichten zeigen den Teil dann nicht (keine toten Knöpfe), wie bei der Senderquelle.
import type { Abo, Aktualisierungsstand, Folge, Folgenabfrage, Folgenseite, Fundstueck } from "./typen";

export interface Podcastfaehigkeiten {
  /** im Verzeichnis suchen und abonnieren */
  abonnieren: boolean;
  /** Folgen im Gerät merken (herunterladen) */
  merken: boolean;
  /** automatische Aktualisierung mit Abstand */
  automatisch: boolean;
}

/** Was der Spieler zum Abspielen einer Folge braucht (in seinem Format) */
export interface Folgenwiedergabe {
  folge: Record<string, unknown>;
  abo: Record<string, unknown>;
  /** die Liste für Vor und Zurück, im selben Format */
  liste: Record<string, unknown>[];
}

export interface Podcastquelle {
  readonly faehig: Podcastfaehigkeiten;

  // ----- Abos ------------------------------------------------------------------------------------------------------
  abos(): Promise<Abo[]>;
  abonnieren(feed: string): Promise<Abo>;
  abbestellen(id: number): Promise<void>;
  /** neue Reihenfolge der Abos (alle Kennungen) */
  ordnen(ids: number[]): Promise<void>;
  /** ein Abo oder ohne Kennung alle nach neuen Folgen fragen */
  aktualisieren(id?: number): Promise<void>;
  aktualisierungsstand(): Promise<Aktualisierungsstand>;
  autoLaden(id: number, an: boolean): Promise<void>;
  /** im Verzeichnis suchen (zum Abonnieren) */
  suchen(text: string, signal?: AbortSignal): Promise<Fundstueck[]>;

  // ----- Folgen ----------------------------------------------------------------------------------------------------
  folgen(abfrage: Folgenabfrage, signal?: AbortSignal): Promise<Folgenseite>;
  /** Volltextsuche in Titeln und Beschreibungen aller Folgen */
  folgenSuchen(text: string, abfrage: Folgenabfrage, signal?: AbortSignal): Promise<Folgenseite>;
  gehoert(id: number, an: boolean): Promise<void>;
  /** gehörte Stelle merken (Sekunden) */
  stelleMerken(id: number, sekunden: number): Promise<void>;
  /** im Gerät merken (herunterladen) oder wieder freigeben */
  merken(id: number, an: boolean): Promise<void>;
  /** was der Spieler für eine Folge braucht; `liste` wird die Wiedergabeliste (Vor und Zurück) */
  wiedergabe(folge: Folge, liste?: Folge[]): Promise<Folgenwiedergabe>;
}
