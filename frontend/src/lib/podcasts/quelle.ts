// Schnittstelle Podcastquelle (RAD-17): alles, was die Podcast-Ansichten am Rechner und am Telefon über Abos und
// Folgen wissen und ändern. Die volle App setzt sie gegen das Backend um (backend.ts). Was eine Umsetzung nicht kann,
// meldet sie in `faehig`; die Ansichten zeigen den Teil dann nicht (keine toten Knöpfe), wie bei der Senderquelle.
// Die Webversion liest alles im Browser (browser/browser-quelle.ts, RAD-102); welche gilt, sagt das Bauziel ($ziel/podcasts).
import type { Abo, Aktualisierungsstand, Folge, Folgenabfrage, Folgenseite, Fundstueck, Ordner, Podcastsortierung } from "./typen";

export interface Podcastfaehigkeiten {
  /** im Verzeichnis suchen und abonnieren */
  abonnieren: boolean;
  /** Folgen in der Kellerwolke speichern (Ablage der vollen App) */
  speichern: boolean;
  /** die laufende Folge als Datei auf das Gerät laden, das gerade bedient (großer Spieler) */
  herunterladen: boolean;
  /** dasselbe auch in den Listen der Folgen (volle App); die Webversion bleibt dort schlank (RAD-102) */
  herunterladenInListen: boolean;
  /** automatische Aktualisierung mit Abstand */
  automatisch: boolean;
  /** Werbestellen finden und überspringen (Werbequelle, RAD-32) */
  werbung: boolean;
  /** Transkripte der Folgen lesen und transkribieren lassen (RAD-22) */
  transkript: boolean;
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
  /** ein Abo oder ohne Kennung alle nach neuen Folgen fragen; liefert die Zahl wirklich neuer Folgen (RAD-107) */
  aktualisieren(id?: number): Promise<number>;
  aktualisierungsstand(): Promise<Aktualisierungsstand>;
  autoLaden(id: number, an: boolean): Promise<void>;
  /** oben anheften oder lösen */
  anheften(id: number, an: boolean): Promise<void>;
  /** Sortierung der Folgen dieses Abos merken; leer nimmt die der Ansicht */
  sortierungSetzen(id: number, sortierung: Podcastsortierung | ""): Promise<void>;
  // ----- Ordner (Gruppierung der Abos) ------------------------------------------------------------------------------
  ordner(): Promise<Ordner[]>;
  ordnerAnlegen(name: string): Promise<Ordner>;
  ordnerAendern(id: string, teil: Partial<Pick<Ordner, "name" | "offen">>): Promise<Ordner>;
  /** nur die Gruppierung: die Abos stehen danach lose; liefert ihre Zahl */
  ordnerLoeschen(id: string): Promise<number>;
  ordnerOrdnen(ids: string[]): Promise<void>;
  /** Abo in einen Ordner legen oder (null) wieder lose */
  zuordnen(aboId: number, ordnerId: string | null): Promise<void>;

  /** im Verzeichnis suchen (zum Abonnieren) */
  suchen(text: string, signal?: AbortSignal): Promise<Fundstueck[]>;

  // ----- Folgen ----------------------------------------------------------------------------------------------------
  folgen(abfrage: Folgenabfrage, signal?: AbortSignal): Promise<Folgenseite>;
  /** eine Folge allein (Direktlink oder laufende Folge, die nicht auf der geladenen Seite steht); null, wenn es sie nicht gibt */
  einzelfolge(id: number): Promise<Folge | null>;
  /** Volltextsuche in Titeln und Beschreibungen aller Folgen */
  folgenSuchen(text: string, abfrage: Folgenabfrage, signal?: AbortSignal): Promise<Folgenseite>;
  gehoert(id: number, an: boolean): Promise<void>;
  /** gehörte Stelle merken (Sekunden) */
  stelleMerken(id: number, sekunden: number): Promise<void>;
  /** in der Kellerwolke speichern oder dort löschen (in den Papierkorb) */
  speichern(id: number, an: boolean): Promise<void>;
  /** Adresse, unter der der Browser die Folge als Datei lädt (Herunterladen aufs Gerät) */
  dateiAdresse(id: number): string;
  /** was der Spieler für eine Folge braucht; `liste` wird die Wiedergabeliste (Vor und Zurück) */
  wiedergabe(folge: Folge, liste?: Folge[]): Promise<Folgenwiedergabe>;
}
