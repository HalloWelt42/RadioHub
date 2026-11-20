// Typen der Senderquelle unter /api/radio (RAD-7). Vorlage sind die Pydantic-Modelle in
// backend/app/services/senderquelle/modelle.py; backend/tests/test_typen.py prüft, dass jede Schnittstelle hier
// genau die Felder ihres Modells führt. Länder kommen als Code (ISO 3166-1) mit dem englischen Namen des
// Verzeichnisses; den deutschen Namen bildet die Oberfläche mit Intl.DisplayNames("de", { type: "region" }).

export type Qualitaet = "verlustfrei" | "hoch" | "mittel" | "niedrig" | "unbekannt";
export type RegelArt = "sprache" | "genre" | "tag" | "stimmen" | "werbung" | "bewertung" | "einzeln" | "altsperren";
export type Herkunft = "nutzer" | "ueberfuehrt" | "bestand";
export type WerbeStufe = "eigene" | "hoch" | "mittel" | "verdacht";
export type Werbeverdacht = "keine" | "verdacht" | "mittel" | "hoch" | "eigene";
export type Sortierung = "stimmen" | "name" | "qualitaet" | "bitrate";
export type KandidatenArt = "sprache" | "genre" | "tag" | "bewertung" | "einzeln";

/** Eigene Bewertungen: Sterne als "sterne:1" bis "sterne:3", Markierungen mit ihrem Schlüssel. */
export type Bewertung =
  | "sterne:3" | "sterne:2" | "sterne:1" | "werbung" | "religioes" | "politisch_extrem" | "populistisch"
  | "nicht_jugendfrei" | "schlechte_qualitaet" | "schwankende_qualitaet" | "haeufig_offline" | "hoher_sprachanteil";

// ----- Regeln --------------------------------------------------------------------------------------------------------

/** Sprache: `schluessel` sind Codes ("ru") oder freie Einträge ("frei:asunción"), `eintraege` genaue Einträge des
 * Verzeichnisses. Sender ohne Sprachangabe bleiben sichtbar. */
export interface SpracheEntwurf {
  art: "sprache";
  schluessel: string[];
  eintraege: string[];
}

export interface GenreEntwurf {
  art: "genre";
  genres: string[];
}

export interface TagEntwurf {
  art: "tag";
  tags: string[];
}

export interface StimmenEntwurf {
  art: "stimmen";
  mindeststimmen: number;
}

export interface WerbungEntwurf {
  art: "werbung";
  stufe: WerbeStufe;
}

export interface BewertungEntwurf {
  art: "bewertung";
  bewertungen: Bewertung[];
}

export type RegelEntwurf =
  | SpracheEntwurf | GenreEntwurf | TagEntwurf | StimmenEntwurf | WerbungEntwurf | BewertungEntwurf;

/** Eine lebende Regel. `nur_diese`: so viele Sender werden sichtbar, wenn sie aus ist oder entfernt wird. */
export interface Regel {
  id: string;
  art: RegelArt;
  an: boolean;
  herkunft: Herkunft;
  titel: string;
  erklaerung: string;
  entwurf: RegelEntwurf | null;
  betroffen: number;
  favoriten: number;
  nur_diese: number;
  angelegt_am: string;
  geaendert_am: string;
}

export interface Bestand {
  gesamt: number;
  sichtbar: number;
  ausgeblendet: number;
  verschwunden: number;
  favoriten: number;
  ausnahmen: number;
}

export interface Regeluebersicht {
  bestand: Bestand;
  regeln: Regel[];
}

export interface SenderKurz {
  uuid: string;
  name: string;
  land: string;
  stimmen: number;
  logo: string;
}

/** Vorschau vor dem Anlegen; ändert nichts. */
export interface RegelVorschau {
  titel: string;
  betroffen: number;
  neu_ausgeblendet: number;
  favoriten: number;
  favoriten_namen: string[];
  beispiele: SenderKurz[];
  gleiche_regel: string | null;
}

/** Folgenvorschau vor dem Ausschalten oder Entfernen. */
export interface RegelFolgen {
  regel: Regel;
  wieder_sichtbar: number;
  beispiele: SenderKurz[];
}

/** Ergebnis einer Änderung, für Band und Rückgängig (Anlegen rückgängig: DELETE der neuen Regel). */
export interface RegelAenderung {
  regel: Regel | null;
  bestand: Bestand;
  ausgeblendet: number;
  wieder_sichtbar: number;
}

export interface RegelSchalten {
  an: boolean;
}

export interface Kandidat {
  schluessel: string;
  name: string;
  code: string | null;
  anzahl: number;
  favoriten: number;
}

// ----- Abfrage -------------------------------------------------------------------------------------------------------

/** Schnellfilter der Senderliste; alle Felder wahlweise (Vorgaben des Servers wie im Modell). */
export interface StationQuery {
  suche?: string;
  laender?: string[];
  genres?: string[];
  qualitaet?: Qualitaet[];
  codecs?: string[];
  bitrate_min?: number | null;
  bitrate_max?: number | null;
  stimmen_min?: number | null;
  stimmen_max?: number | null;
  bewertungen?: Bewertung[];
  kategorien?: number[];
  nur_favoriten?: boolean;
  nur_erreichbar?: boolean;
  sortierung?: Sortierung;
  varianten_buendeln?: boolean;
  nach?: string | null;
  anzahl?: number;
  mit_facetten?: boolean | null;
}

export interface SpracheKurz {
  schluessel: string;
  name: string;
}

export interface Werbestatus {
  stufe: Werbeverdacht;
  entscheidung: "gesperrt" | "erlaubt" | null;
}

/** Warum ein Sender ausgeblendet ist (oder als Ausnahme sichtbar). */
export interface Grund {
  regel: string;
  art: RegelArt;
  titel: string;
}

export interface SenderEintrag {
  uuid: string;
  name: string;
  logo: string;
  homepage: string;
  land: string;
  land_name: string;
  region: string;
  bundesland: string;
  sprachen: SpracheKurz[];
  genres: string[];
  codec: string;
  kbps: number | null;
  kbps_gemessen: boolean;
  qualitaet: Qualitaet;
  stimmen: number;
  erreichbar: boolean;
  hls: boolean;
  gruppe: string;
  varianten: number;
  favorit: boolean;
  ausnahme: Grund[];
  verschwunden: boolean;
  kategorien: number[];
  bewertungen: string[];
  werbung: Werbestatus;
  eigene_adresse: string | null;
  /** Stream-Adressen aus dem Verzeichnis: die Zeile spielt ohne weitere Abfrage, auch Vor und Zurück über die Liste */
  adresse: string;
  adresse_aufgeloest: string;
}

export interface Facette {
  wert: string;
  name: string;
  anzahl: number;
}

export interface Facetten {
  laender: Facette[];
  genres: Facette[];
  qualitaet: Facette[];
  codecs: Facette[];
  bewertungen: Facette[];
  kategorien: Facette[];
}

export interface Abfrageergebnis {
  gesamt: number | null;
  eintraege: SenderEintrag[];
  weiter: string | null;
  facetten: Facetten | null;
}

// ----- Ausgeblendete Sender, Einzelsperren, Freigaben, Abgleich -------------------------------------------------------

export interface AusgeblendetAnfrage {
  suche?: string;
  regel?: string | null;
  seite?: number;
  anzahl?: number;
}

export interface AusgeblendeterSender {
  uuid: string;
  name: string;
  land: string;
  stimmen: number;
  logo: string;
  gruende: Grund[];
}

export interface GrundZahl {
  regel: string;
  titel: string;
  anzahl: number;
}

export interface AusgeblendetSeite {
  gesamt: number;
  seite: number;
  seiten: number;
  eintraege: AusgeblendeterSender[];
  gruende: GrundZahl[];
}

export interface Sichtbarkeit {
  uuid: string;
  sichtbar: boolean;
  verschwunden: boolean;
  favorit: boolean;
  freigegeben: boolean;
  gesperrt: boolean;
  gruende: Grund[];
}

export interface SenderAnfrage {
  uuid: string;
}

export interface Abgleichstand {
  zuletzt: string | null;
  uhrzeit: string;
  auftrag: string | null;
}

/** Wege der Senderquelle (alle unter der Anmeldung). */
export const WEGE = {
  abfrage: "/api/radio/abfrage",                                        // POST StationQuery -> Abfrageergebnis
  varianten: (uuid: string) => `/api/radio/sender/${encodeURIComponent(uuid)}/varianten`,       // GET -> SenderEintrag[]
  sichtbarkeit: (uuid: string) => `/api/radio/sender/${encodeURIComponent(uuid)}/sichtbarkeit`, // GET -> Sichtbarkeit
  regeln: "/api/radio/regeln",                                          // GET -> Regeluebersicht, POST RegelEntwurf -> RegelAenderung
  vorschau: "/api/radio/regeln/vorschau",                               // POST RegelEntwurf -> RegelVorschau
  regel: (id: string) => `/api/radio/regeln/${encodeURIComponent(id)}`, // PATCH RegelSchalten, DELETE ?bestaetigt=true
  folgen: (id: string) => `/api/radio/regeln/${encodeURIComponent(id)}/folgen`, // GET -> RegelFolgen
  kandidaten: "/api/radio/regeln/kandidaten",                           // GET ?art=&suche=&grenze= -> Kandidat[]
  ausgeblendet: "/api/radio/ausgeblendet",                              // POST AusgeblendetAnfrage -> AusgeblendetSeite
  sperren: "/api/radio/sperren",                                        // POST SenderAnfrage, DELETE /{uuid} -> Sichtbarkeit
  freigaben: "/api/radio/freigaben",                                    // POST SenderAnfrage, DELETE /{uuid} -> Sichtbarkeit
  abgleich: "/api/radio/abgleich",                                      // GET -> Abgleichstand, POST -> Auftrag (Appkern)
} as const;
