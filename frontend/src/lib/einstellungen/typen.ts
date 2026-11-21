// Einstellungen (RAD-11): eine Zeile der Einstellungsseite, gleich ob der Wert auf dem Server liegt (für alle Geräte,
// aus dem Modell AppEinstellungen über die Einstellungsschicht des Appkerns) oder nur auf diesem Gerät (eigene Module
// wie Darstellung, Zeitansage, Wachhalten). Die Zeile kennt nur, was sie zum Zeichnen braucht; woher der Wert kommt
// und wohin er geht, regelt die Quelle der Zeile.

/** für alle Geräte (Server, Speichern über die Leiste) oder nur dieses Gerät (gilt sofort) */
export type Geltung = "alle" | "geraet";

/**
 * schalter: an oder aus · zahl: Schieber mit Grenzen · wahl: wenige Werte als Segment · auswahl: viele Werte als
 * Aufklappliste (auch aus dem System) · mehrfach: mehrere Werte zugleich · text: Adresse oder Name · liste: mehrere
 * Texte · uhrzeit: HH:MM oder leer · zeitraum: von und bis (je HH:MM oder leer) · stufe: geordnete Werte mit kleiner
 * und größer (etwa die Schrift)
 */
export type ZeilenArt = "schalter" | "zahl" | "wahl" | "auswahl" | "mehrfach" | "text" | "liste" | "uhrzeit" | "zeitraum" | "stufe";

export interface Wahlwert {
  wert: string;
  titel: string;
  symbol?: string;
  hinweis?: string;
}

export interface Zeile {
  /** Name des Felds (Server) oder Schlüssel der Geräteeinstellung */
  schluessel: string;
  titel: string;
  beschreibung: string;
  art: ZeilenArt;
  geltung: Geltung;
  wert: unknown;
  optionen: Wahlwert[];
  kleinste?: number;
  groesste?: number;
  schritt?: number;
  einheit: string;
  /** vom Ausrollen gesetzt, hier nicht änderbar */
  fest: boolean;
  /** geändert, noch nicht gespeichert (nur Geltung "alle") */
  geaendert: boolean;
  /** die Optionen kommen aus dem System und werden beim Öffnen geholt */
  angebot: boolean;
  /** Vorgabe, für den Knopf "Vorgabe" bei Adressen */
  vorgabe?: unknown;
  /** Zahl: gezeigt wird Wert / faktor in `einheit` (Sekunden als Stunden oder Minuten); gespeichert der volle Wert */
  faktor?: number;
  /** warum sich der Wert auf diesem Gerät nicht stellen lässt (etwa: der Browser kann es nicht); leer: frei */
  sperrgrund?: string;
}

/** Ein Teil, das wie Server-Werte über die Leiste Speichern geht (etwa der Ort), aber eigene Wege hat */
export interface Teilentwurf {
  titel: string;
  speichern(): Promise<void>;
  verwerfen(): void;
}
