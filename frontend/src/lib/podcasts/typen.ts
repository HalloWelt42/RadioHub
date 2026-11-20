// Datenmodell der Podcasts (RAD-17), unabhängig vom Backend: die Ansichten kennen nur diese Typen, die Quelle bildet die
// Antworten darauf ab (backend.ts). Zeiten in Sekunden, Daten als ISO-Text.

export interface Abo {
  id: number;
  titel: string;
  autor: string;
  beschreibung: string;
  /** Adresse des Bilds, über die eigene App (nie direkt fremde Server) */
  bild: string;
  feed: string;
  /** neue Folgen von selbst herunterladen */
  autoLaden: boolean;
  /** oben angeheftet (steht vor den übrigen) */
  angeheftet: boolean;
  /** gemerkte Sortierung der Folgen dieses Abos, leer: die der Ansicht */
  sortierung: Podcastsortierung | "";
  /** zuletzt aktualisiert (ISO) oder leer */
  aktualisiert: string;
  folgen: number;
  heruntergeladen: number;
  ungehoert: number;
  heuteUngehoert: number;
  wocheUngehoert: number;
  /** Länge aller Folgen in Sekunden */
  dauerGesamt: number;
}

export interface Folge {
  id: number;
  aboId: number;
  titel: string;
  beschreibung: string;
  /** Länge in Sekunden, 0 unbekannt */
  dauer: number;
  /** veröffentlicht (ISO) */
  datum: string;
  /** zuletzt gehörte Stelle in Sekunden */
  stelle: number;
  gehoert: boolean;
  /** heruntergeladen (in der Ablage), auch ohne Netz zu hören */
  heruntergeladen: boolean;
  /** Größe der heruntergeladenen Datei in Bytes */
  groesse: number;
  bild: string;
  /** nur in Listen über mehrere Abos */
  aboTitel?: string;
}

/** Welche Folgen: ein Filter für Rechner und Telefon (früher dort heute/Woche/alle, hier alle/ungehört/geladen) */
export type Folgenfilter = "alle" | "heute" | "woche" | "ungehoert" | "heruntergeladen" | "gehoert";
export const FOLGENFILTER: readonly Folgenfilter[] = ["alle", "heute", "woche", "ungehoert", "heruntergeladen", "gehoert"];

/** Sortierung der Folgen in der Ansicht (und je Abo gemerkt) */
export type Podcastsortierung = "neu" | "alt" | "titel" | "laenge";
export const PODCASTSORTIERUNG: readonly Podcastsortierung[] = ["neu", "alt", "titel", "laenge"];

export type Folgensortierung = "datum" | "titel" | "dauer";

export interface Folgenabfrage {
  /** nur diese Abos; leer oder fehlt: alle */
  abos?: number[];
  filter?: Folgenfilter;
  sortierung?: Folgensortierung;
  /** neueste zuerst (Vorgabe) bzw. absteigend */
  absteigend?: boolean;
  anzahl?: number;
  /** Zeiger der vorigen Seite */
  nach?: string | null;
}

export interface Folgenseite {
  folgen: Folge[];
  gesamt: number;
  /** Zeiger auf die nächste Seite, null am Ende */
  weiter: string | null;
}

/** Treffer der Suche im Verzeichnis (zum Abonnieren) */
export interface Fundstueck {
  titel: string;
  autor: string;
  bild: string;
  feed: string;
  beschreibung: string;
  /** woher (Verzeichnis); ob schon abonniert, sagt die Aboliste (gleicher Feed) */
  herkunft: string;
}

export interface Aktualisierungsstand {
  /** nächste automatische Aktualisierung (ISO) oder null */
  naechste: string | null;
  abstandStunden: number;
  automatisch: boolean;
}
