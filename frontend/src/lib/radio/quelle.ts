// Schnittstelle Senderquelle (RAD-7, Entscheidung 28): alles, was die Radio-Ansichten über Sender wissen und ändern.
// Die Ansichten kennen nur diese Schnittstelle; die volle App setzt sie gegen das Backend um (backend.ts), die
// Webversion (RAD-4) später mit einer statischen Liste und dem Speicher des Browsers. Was eine Umsetzung nicht kann,
// meldet sie in `faehig`; die Ansichten zeigen dann den Teil nicht (keine toten Knöpfe).
import type {
  Abfrageergebnis, Abgleichstand, AusgeblendetAnfrage, AusgeblendetSeite, Bewertung, Kandidat, KandidatenArt,
  RegelAenderung, RegelEntwurf, RegelFolgen, Regeluebersicht, RegelVorschau, SenderEintrag, Sichtbarkeit, StationQuery,
} from "./typen";

/** Was eine Umsetzung kann; fehlt etwas, entfällt der Teil der Oberfläche. */
export interface Faehigkeiten {
  /** Abgleich mit dem Senderverzeichnis als Auftrag */
  abgleich: boolean;
  /** eigene Stream-Adresse je Sender */
  eigeneAdresse: boolean;
  /** Messung von Bitrate und Werbung beim Abspielen */
  messen: boolean;
  /** eigene Kategorien (verwalten in den Einstellungen) */
  kategorien: boolean;
  /** Titelangaben im Strom bewerten (genaue oder ungenaue Schnitte für Aufnahmen) */
  titelBewerten: boolean;
}

/** Ein Sender, wie ihn die Wiedergabe braucht (Felder der bisherigen Wiedergabe: Adresse für Zeitversatz und Aufnahme). */
export interface Wiedergabesender {
  uuid: string;
  name: string;
  url: string;
  url_resolved: string;
  favicon: string;
  country: string;
  countrycode: string;
  tags: string;
  codec: string;
  bitrate: number;
  homepage: string;
}

/** Titelangaben im Strom (ICY): gemessen, und wie genau sie Aufnahmen schneiden (eigene Bewertung). */
export type TitelGuete = "genau" | "ungenau" | null;

/** Was die Details eines Senders über die Zeile hinaus zeigen. */
export interface Steckbrief {
  /** Stream-Adresse aus dem Verzeichnis (aufgelöst) */
  adresse: string;
  /** eigene Stream-Adresse, wenn gesetzt */
  eigeneAdresse: string | null;
  /** Titelangaben im Strom erkannt (null: noch nicht gemessen) */
  titel: boolean | null;
  titelGuete: TitelGuete;
  /** eigener Widerspruch zur Werbeerkennung ("kein Werbeverdacht") */
  widerspruch: boolean;
}

/** Messwert nach dem Abspielen, für die Zeile des Senders. */
export interface Messwert {
  kbps: number | null;
  codec: string | null;
}

export interface Kategorie {
  id: number;
  name: string;
}

export interface LandZahl {
  code: string;
  name: string;
  anzahl: number;
}

export interface Senderquelle {
  readonly faehig: Faehigkeiten;

  // ----- Liste -----------------------------------------------------------------------------------------------------
  /** Erste Seite mit Gesamtzahl und Facetten, weitere über `nach`. */
  abfragen(q: StationQuery, signal?: AbortSignal): Promise<Abfrageergebnis>;
  /** Alle sichtbaren Varianten der Gruppe eines Senders, die beste vorn. */
  varianten(uuid: string): Promise<SenderEintrag[]>;
  /** Ein sichtbarer Sender (für Direktlinks), sonst null. */
  sender(uuid: string): Promise<SenderEintrag | null>;
  /** Warum ein Sender sichtbar ist oder nicht. */
  sichtbarkeit(uuid: string): Promise<Sichtbarkeit>;
  steckbrief(eintrag: SenderEintrag): Promise<Steckbrief>;
  /** Was die Wiedergabe zum Abspielen braucht. */
  wiedergabe(eintrag: SenderEintrag): Promise<Wiedergabesender>;
  /** Nach dem Start: messen (Bitrate, Werbung); liefert den Messwert, sobald er da ist, sonst null. */
  gespielt(eintrag: SenderEintrag, signal?: AbortSignal): Promise<Messwert | null>;

  // ----- Eigene Angaben --------------------------------------------------------------------------------------------
  favorit(eintrag: SenderEintrag, an: boolean): Promise<void>;
  bewerten(uuid: string, bewertung: Bewertung, an: boolean): Promise<void>;
  /** Kein Werbeverdacht (Widerspruch zur Erkennung) */
  werbungWidersprechen(uuid: string, an: boolean): Promise<void>;
  kategorien(): Promise<Kategorie[]>;
  kategorieZuordnen(uuid: string, kategorie: number, an: boolean): Promise<void>;
  /** eigene Stream-Adresse setzen; null nimmt wieder die des Verzeichnisses */
  eigeneAdresse(uuid: string, adresse: string | null): Promise<void>;
  titelBewerten(uuid: string, guete: TitelGuete): Promise<void>;

  // ----- Regeln ----------------------------------------------------------------------------------------------------
  regeln(): Promise<Regeluebersicht>;
  vorschau(entwurf: RegelEntwurf, signal?: AbortSignal): Promise<RegelVorschau>;
  anlegen(entwurf: RegelEntwurf): Promise<RegelAenderung>;
  schalten(id: string, an: boolean): Promise<RegelAenderung>;
  folgen(id: string): Promise<RegelFolgen>;
  /** Entfernen erst nach der Folgenvorschau (Vorgabe 9) */
  entfernen(id: string): Promise<RegelAenderung>;
  kandidaten(art: KandidatenArt, suche: string, grenze?: number, signal?: AbortSignal): Promise<Kandidat[]>;

  // ----- Ausgeblendete, Sperren, Freigaben ---------------------------------------------------------------------------
  ausgeblendet(anfrage: AusgeblendetAnfrage, signal?: AbortSignal): Promise<AusgeblendetSeite>;
  /** Einzelsperre (Auge); startet nichts, Rückgängig mit `entsperren` */
  sperren(uuid: string): Promise<Sichtbarkeit>;
  entsperren(uuid: string): Promise<Sichtbarkeit>;
  freigeben(uuid: string): Promise<Sichtbarkeit>;
  freigabeZuruecknehmen(uuid: string): Promise<Sichtbarkeit>;

  // ----- Länder der Seitenleiste (nur Anzeige, Entscheidung 6) -------------------------------------------------------
  laender(): Promise<LandZahl[]>;
  laenderLeiste(): Promise<string[]>;
  laenderLeisteSetzen(codes: string[]): Promise<void>;

  // ----- Abgleich mit dem Senderverzeichnis --------------------------------------------------------------------------
  abgleich(): Promise<Abgleichstand>;
  /** startet den Abgleich als Auftrag; Kennung des Auftrags */
  abgleichStarten(): Promise<string>;
}

