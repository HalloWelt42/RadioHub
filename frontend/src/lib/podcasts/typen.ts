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
  /** neue Folgen von selbst in der Kellerwolke speichern */
  autoLaden: boolean;
  /** oben angeheftet (steht vor den übrigen) */
  angeheftet: boolean;
  /** gemerkte Sortierung der Folgen dieses Abos, leer: die der Ansicht */
  sortierung: Podcastsortierung | "";
  /** eigener Ordner (Gruppierung in der Seitenleiste), null: lose */
  ordnerId: string | null;
  /** zuletzt aktualisiert (ISO) oder leer */
  aktualisiert: string;
  folgen: number;
  /** Zahl der in der Kellerwolke gespeicherten Folgen */
  gespeichert: number;
  ungehoert: number;
  heuteUngehoert: number;
  wocheUngehoert: number;
  /** Länge aller Folgen in Sekunden */
  dauerGesamt: number;
  /** Werbestellen beim Hören überspringen (RAD-32) */
  werbungUeberspringen: boolean;
  /** neue Folgen von selbst auf Werbung durchsuchen */
  werbungPruefen: boolean;
  /** Zahl der Folgen mit Werbestellen */
  werbungFolgen: number;
}

/** eigener Ordner der Abos (RAD-23); löschen nimmt nur die Gruppierung */
export interface Ordner {
  id: string;
  name: string;
  /** aufgeklappt */
  offen: boolean;
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
  /** in der Kellerwolke gespeichert (Ablage), hörbar auch wenn der Feed sie nicht mehr hat */
  gespeichert: boolean;
  /** Pfad der gespeicherten Datei in der Ablage, leer ohne */
  ablagePfad: string;
  /** Größe der gespeicherten Datei in Bytes */
  groesse: number;
  bild: string;
  /** Werbestellen dieser Folge: Zahl und Dauer in Sekunden (RAD-32) */
  werbung: { anzahl: number; dauer: number };
  /** nur in Listen über mehrere Abos */
  aboTitel?: string;
}

/** Welche Folgen: ein Filter für Rechner und Telefon (früher dort heute/Woche/alle, hier alle/ungehört/geladen) */
export type Folgenfilter = "alle" | "heute" | "woche" | "ungehoert" | "gespeichert" | "gehoert";
export const FOLGENFILTER: readonly Folgenfilter[] = ["alle", "heute", "woche", "ungehoert", "gespeichert", "gehoert"];

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
