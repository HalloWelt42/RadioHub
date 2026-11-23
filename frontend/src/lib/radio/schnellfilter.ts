// Schnellfilter der Senderliste (Entscheidung 4, Vorgaben 1 und 2): eine Wahrheit für Auswahl, Suche und Sortierung,
// ihre Form in der Adresse (/radio?land=DE&genre=Rock ...), die Abfrage an die Senderquelle und die aktiven Filter als
// Chips. Nur reine Funktionen; den Zustand und den Abgleich mit der Adresse führt schnellfilter.svelte.ts.
import type { Bewertung, Qualitaet, Sortierung, StationQuery } from "./typen";

/** Stufen der Drehwahl Stimmen und des Schiebers Mindestbitrate (Wert 0: alle) */
export const STIMMEN_STUFEN = [0, 10, 100, 1000, 10000] as const;
export const BITRATE_STUFEN = [0, 64, 128, 192, 256, 320] as const;
export const QUALITAETEN: readonly Qualitaet[] = ["verlustfrei", "hoch", "mittel", "niedrig", "unbekannt"];
export const SORTIERUNGEN: readonly Sortierung[] = ["stimmen", "name", "qualitaet", "bitrate"];

export interface Schnellfilter {
  laender: string[];
  genres: string[];
  qualitaet: Qualitaet[];
  codecs: string[];
  bewertungen: Bewertung[];
  kategorien: number[];
  nurFavoriten: boolean;
  /** Vorgabe an: ohne Sender, die die letzte Prüfung nicht bestanden haben (Entscheidung 30) */
  nurErreichbar: boolean;
  /** Mindeststimmen als Wert einer Stufe aus STIMMEN_STUFEN */
  stimmen: number;
  /** Mindestbitrate in kbit/s als Wert einer Stufe aus BITRATE_STUFEN */
  bitrate: number;
  suche: string;
  sortierung: Sortierung;
  /** Reihenfolge von hinten (zweiter Klick auf den Spaltenkopf) */
  umgekehrt: boolean;
}

export const VORGABE: Readonly<Schnellfilter> = Object.freeze({
  laender: [], genres: [], qualitaet: [], codecs: [], bewertungen: [], kategorien: [],
  nurFavoriten: false, nurErreichbar: true, stimmen: 0, bitrate: 0, suche: "", sortierung: "stimmen", umgekehrt: false,
});

export function leer(): Schnellfilter {
  return { ...VORGABE, laender: [], genres: [], qualitaet: [], codecs: [], bewertungen: [], kategorien: [] };
}

// ----- Adresse ---------------------------------------------------------------------------------------------------------

const SCHLUESSEL = {
  land: "land", genre: "genre", qualitaet: "qualitaet", codec: "codec", bewertung: "bewertung", kategorie: "kategorie",
  favoriten: "favoriten", erreichbar: "erreichbar", stimmen: "stimmen", bitrate: "bitrate", suche: "suche", sortierung: "sort", umgekehrt: "um",
} as const;

/** Werte eines Schlüssels: wiederholt (land=DE&land=FR) oder mit Komma (land=DE,FR); Genres nur wiederholt */
function liste(p: URLSearchParams, schluessel: string, komma = true): string[] {
  const werte = p.getAll(schluessel).flatMap((w) => (komma ? w.split(",") : [w])).map((w) => w.trim()).filter(Boolean);
  return [...new Set(werte)];
}

/** nächstgelegene Stufe nach unten (ein Wert aus der Adresse, der keine Stufe ist) */
function stufe(stufen: readonly number[], wert: number): number {
  if (!Number.isFinite(wert) || wert <= 0) return 0;
  return [...stufen].reverse().find((s) => s <= wert) ?? 0;
}

export function ausAdresse(p: URLSearchParams): Schnellfilter {
  const sortierung = p.get(SCHLUESSEL.sortierung) as Sortierung | null;
  return {
    laender: liste(p, SCHLUESSEL.land).map((l) => l.toUpperCase()).filter((l) => /^[A-Z]{2}$/.test(l)),
    genres: liste(p, SCHLUESSEL.genre, false).slice(0, 60),
    qualitaet: liste(p, SCHLUESSEL.qualitaet).filter((q): q is Qualitaet => (QUALITAETEN as string[]).includes(q)),
    codecs: liste(p, SCHLUESSEL.codec).slice(0, 12),
    bewertungen: liste(p, SCHLUESSEL.bewertung).filter((b) => /^(sterne:[123]|[a-z_]{3,40})$/.test(b)) as Bewertung[],
    kategorien: liste(p, SCHLUESSEL.kategorie).map(Number).filter((k) => Number.isInteger(k) && k > 0),
    nurFavoriten: p.get(SCHLUESSEL.favoriten) === "1",
    nurErreichbar: p.get(SCHLUESSEL.erreichbar) !== "0",
    stimmen: stufe(STIMMEN_STUFEN, Number(p.get(SCHLUESSEL.stimmen))),
    bitrate: stufe(BITRATE_STUFEN, Number(p.get(SCHLUESSEL.bitrate))),
    suche: (p.get(SCHLUESSEL.suche) ?? "").trim().slice(0, 100),
    sortierung: sortierung && SORTIERUNGEN.includes(sortierung) ? sortierung : "stimmen",
    umgekehrt: p.get(SCHLUESSEL.umgekehrt) === "1",
  };
}

/** Nur was von der Vorgabe abweicht; Listen als wiederholte Schlüssel */
export function inAdresse(f: Schnellfilter): URLSearchParams {
  const p = new URLSearchParams();
  for (const l of f.laender) p.append(SCHLUESSEL.land, l);
  for (const g of f.genres) p.append(SCHLUESSEL.genre, g);
  for (const q of f.qualitaet) p.append(SCHLUESSEL.qualitaet, q);
  for (const c of f.codecs) p.append(SCHLUESSEL.codec, c);
  for (const b of f.bewertungen) p.append(SCHLUESSEL.bewertung, b);
  for (const k of f.kategorien) p.append(SCHLUESSEL.kategorie, String(k));
  if (f.nurFavoriten) p.set(SCHLUESSEL.favoriten, "1");
  if (!f.nurErreichbar) p.set(SCHLUESSEL.erreichbar, "0");
  if (f.stimmen) p.set(SCHLUESSEL.stimmen, String(f.stimmen));
  if (f.bitrate) p.set(SCHLUESSEL.bitrate, String(f.bitrate));
  if (f.suche) p.set(SCHLUESSEL.suche, f.suche);
  if (f.sortierung !== "stimmen") p.set(SCHLUESSEL.sortierung, f.sortierung);
  if (f.umgekehrt) p.set(SCHLUESSEL.umgekehrt, "1");
  return p;
}

/** Pfad der Radio-Ansicht: mit aufgeklapptem Sender /radio/<uuid>, dazu die Schnellfilter als Abfrage */
export function radioPfad(f: Schnellfilter, offen: string | null = null): string {
  const abfrage = inAdresse(f).toString();
  return `/radio${offen ? `/${encodeURIComponent(offen)}` : ""}${abfrage ? `?${abfrage}` : ""}`;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Aus Pfad und Abfrage: Schnellfilter und aufgeklappter Sender. Frühere Adressen /radio/search/<suche> gelten weiter. */
export function ausOrt(pfad: string, abfrage: string): { filter: Schnellfilter; offen: string | null } {
  const filter = ausAdresse(new URLSearchParams(abfrage));
  const teile = pfad.split("/").filter(Boolean).map((t) => { try { return decodeURIComponent(t); } catch { return t; } });
  if (teile[0] !== "radio") return { filter, offen: null };
  if (teile[1] === "search" && teile[2]) return { filter: { ...filter, suche: teile[2].trim().slice(0, 100) }, offen: null };
  return { filter, offen: teile[1] && UUID.test(teile[1]) ? teile[1] : null };
}

// ----- Abfrage ---------------------------------------------------------------------------------------------------------

export function zuAbfrage(f: Schnellfilter): StationQuery {
  return {
    suche: f.suche, laender: f.laender, genres: f.genres, qualitaet: f.qualitaet, codecs: f.codecs,
    bewertungen: f.bewertungen, kategorien: f.kategorien, nur_favoriten: f.nurFavoriten, nur_erreichbar: f.nurErreichbar,
    stimmen_min: f.stimmen || null, bitrate_min: f.bitrate || null, sortierung: f.sortierung, umgekehrt: f.umgekehrt,
  };
}

// ----- Aktive Filter als Chips -----------------------------------------------------------------------------------------

export type ChipArt = "land" | "genre" | "qualitaet" | "codec" | "bewertung" | "kategorie" | "favoriten" | "erreichbar"
  | "stimmen" | "bitrate" | "suche";

export interface Chip {
  art: ChipArt;
  wert: string;
}

/** Alles, was von der Vorgabe abweicht (ohne Sortierung), in der Reihenfolge der Seitenleiste */
export function aktive(f: Schnellfilter): Chip[] {
  return [
    ...f.laender.map((wert) => ({ art: "land" as const, wert })),
    ...f.genres.map((wert) => ({ art: "genre" as const, wert })),
    ...f.qualitaet.map((wert) => ({ art: "qualitaet" as const, wert })),
    ...f.codecs.map((wert) => ({ art: "codec" as const, wert })),
    ...f.bewertungen.map((wert) => ({ art: "bewertung" as const, wert })),
    ...f.kategorien.map((k) => ({ art: "kategorie" as const, wert: String(k) })),
    ...(f.nurFavoriten ? [{ art: "favoriten" as const, wert: "1" }] : []),
    ...(f.nurErreichbar ? [] : [{ art: "erreichbar" as const, wert: "0" }]),
    ...(f.stimmen ? [{ art: "stimmen" as const, wert: String(f.stimmen) }] : []),
    ...(f.bitrate ? [{ art: "bitrate" as const, wert: String(f.bitrate) }] : []),
    ...(f.suche ? [{ art: "suche" as const, wert: f.suche }] : []),
  ];
}

/** Schnellfilter ohne diesen Chip (der Chip zurück auf die Vorgabe) */
export function ohne(f: Schnellfilter, c: Chip): Schnellfilter {
  const weg = <T>(werte: T[], w: T) => werte.filter((x) => x !== w);
  switch (c.art) {
    case "land": return { ...f, laender: weg(f.laender, c.wert) };
    case "genre": return { ...f, genres: weg(f.genres, c.wert) };
    case "qualitaet": return { ...f, qualitaet: weg(f.qualitaet, c.wert as Qualitaet) };
    case "codec": return { ...f, codecs: weg(f.codecs, c.wert) };
    case "bewertung": return { ...f, bewertungen: weg(f.bewertungen, c.wert as Bewertung) };
    case "kategorie": return { ...f, kategorien: weg(f.kategorien, Number(c.wert)) };
    case "favoriten": return { ...f, nurFavoriten: false };
    case "erreichbar": return { ...f, nurErreichbar: true };
    case "stimmen": return { ...f, stimmen: 0 };
    case "bitrate": return { ...f, bitrate: 0 };
    case "suche": return { ...f, suche: "" };
  }
}

/** Alle Filter zurück auf die Vorgabe; die Sortierung bleibt */
export function zurueckgesetzt(f: Schnellfilter): Schnellfilter {
  return { ...leer(), sortierung: f.sortierung, umgekehrt: f.umgekehrt };
}

/** Wert einer Liste an- oder abwählen */
export function umschalten<T>(werte: readonly T[], wert: T): T[] {
  return werte.includes(wert) ? werte.filter((w) => w !== wert) : [...werte, wert];
}

export function gleich(a: Schnellfilter, b: Schnellfilter): boolean {
  return inAdresse(a).toString() === inAdresse(b).toString();
}
