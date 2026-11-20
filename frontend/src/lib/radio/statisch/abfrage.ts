// Abfrage der Senderliste im Speicher (wie backend/app/services/senderquelle/abfrage.py): Schnellfilter über die
// sichtbaren Sender, Seiten per Zeiger (Sortierwert und uuid), Gesamtzahl, Einträge und Facetten je Gruppe ohne ihren
// eigenen Filter. Ein Durchgang über die vorsortierte Reihe; das Ergebnis bleibt für die weiteren Seiten gemerkt.
//
// Varianten: gebündelt zeigt die Liste je Gruppe nur den Vertreter. Sobald nach Codec, Qualität oder Bitrate gefiltert
// wird, zeigt sie jede passende Variante einzeln. "Nur erreichbare" ist immer erfüllt: die Liste führt nur erreichbare.
import type {
  Abfrageergebnis, Bewertung, Facette, Facetten, Qualitaet, SenderEintrag, SenderKurz, Sortierung, StationQuery,
} from "../typen";
import { Quellfehler } from "./fehler";
import { QUALITAET_RANG, sprachname, type Senderbestand } from "./format";
import { BEWERTUNGEN, istBewertung } from "./regeln";
import type { Sicht } from "./sicht";
import { base64urlKodieren, base64urlLesen, faltung, suchform, vergleichen, zeichen, zusammengezogen } from "./text";
import { sucheZerlegen } from "../suche";

const SORTIERUNGEN: readonly Sortierung[] = ["stimmen", "name", "qualitaet", "bitrate"];
const QUALITAETEN = (Object.keys(QUALITAET_RANG) as Qualitaet[]).sort((x, y) => QUALITAET_RANG[y] - QUALITAET_RANG[x]);

/** Die Abfrage mit den Vorgaben des Backends, geprüft */
export type Abfrage = Required<Omit<StationQuery, "bitrate_min" | "bitrate_max" | "stimmen_min" | "stimmen_max" | "nach" | "mit_facetten">>
  & Pick<StationQuery, "bitrate_min" | "bitrate_max" | "stimmen_min" | "stimmen_max" | "nach" | "mit_facetten">;

export function abfragePruefen(q: StationQuery): Abfrage {
  const a: Abfrage = {
    suche: q.suche ?? "", laender: q.laender ?? [], genres: q.genres ?? [], qualitaet: q.qualitaet ?? [], codecs: q.codecs ?? [],
    bitrate_min: q.bitrate_min ?? null, bitrate_max: q.bitrate_max ?? null, stimmen_min: q.stimmen_min ?? null,
    stimmen_max: q.stimmen_max ?? null, bewertungen: q.bewertungen ?? [], kategorien: q.kategorien ?? [],
    nur_favoriten: q.nur_favoriten ?? false, nur_erreichbar: q.nur_erreichbar ?? true, sortierung: q.sortierung ?? "stimmen",
    varianten_buendeln: q.varianten_buendeln ?? true, nach: q.nach ?? null, anzahl: q.anzahl ?? 50, mit_facetten: q.mit_facetten ?? null,
  };
  if (zeichen(a.suche) > 100) throw new Quellfehler("Suche: höchstens 100 Zeichen", 422);
  if (!Number.isInteger(a.anzahl) || a.anzahl < 1 || a.anzahl > 200) throw new Quellfehler("anzahl: 1 bis 200", 422);
  if (!SORTIERUNGEN.includes(a.sortierung)) throw new Quellfehler(`Unbekannte Sortierung: ${String(a.sortierung)}`, 422);
  const unbekannt = a.bewertungen.filter((b) => !istBewertung(b));
  if (unbekannt.length) throw new Quellfehler(`Unbekannte Bewertung: ${unbekannt.join(", ")}`, 422);
  return a;
}

export const buendeln = (q: Abfrage): boolean => q.varianten_buendeln && !(q.codecs.length || q.qualitaet.length || q.bitrate_min || q.bitrate_max);

// ----- Suche ------------------------------------------------------------------------------------------------------

/** Ein Wort: ab drei Zeichen ein Teilstück des Suchtexts (ohne Diakritika), sonst des Namens */
function enthaelt(b: Senderbestand, wort: string): (i: number) => boolean {
  if (zeichen(wort) >= 3) {
    const nadel = suchform(wort);
    return (i) => b.suchtext[i].includes(nadel);
  }
  const nadel = faltung(wort);
  return (i) => b.nameKlein[i].includes(nadel);
}

/** Prüfung der Suche: der Text wie ein Wort (siehe enthaelt), dazu keines der Wörter mit Minus (lib/radio/suche.ts) */
export function suchpruefung(b: Senderbestand, suche: string): ((i: number) => boolean) | null {
  const wunsch = sucheZerlegen(suche);
  const text = zusammengezogen(wunsch.text);
  const mit = text ? enthaelt(b, text) : null;
  const ohne = wunsch.ohne.map((w) => enthaelt(b, w));
  if (!mit && !ohne.length) return null;
  return (i) => (!mit || mit(i)) && !ohne.some((p) => p(i));
}

// ----- Seitenzeiger -----------------------------------------------------------------------------------------------

type Zeigerwert = number | string;

function sortwerte(b: Senderbestand, sortierung: Sortierung, i: number): Zeigerwert[] {
  switch (sortierung) {
    case "stimmen": return [b.stimmen[i]];
    case "name": return [b.nameKlein[i]];
    case "qualitaet": return [b.qualitaetRang[i], b.kbps[i]];
    case "bitrate": return [b.kbps[i]];
  }
}
const ABSTEIGEND: Record<Sortierung, boolean[]> = { stimmen: [true], name: [false], qualitaet: [true, true], bitrate: [true] };

export function zeigerBauen(b: Senderbestand, sortierung: Sortierung, i: number): string {
  return base64urlKodieren(JSON.stringify([sortierung, ...sortwerte(b, sortierung, i), b.uuid[i]]));
}

export function zeigerLesen(sortierung: Sortierung, zeiger: string): Zeigerwert[] {
  let daten: unknown;
  try {
    daten = JSON.parse(base64urlLesen(zeiger));
  } catch {
    throw new Quellfehler("Seitenzeiger unlesbar");
  }
  const laenge = ABSTEIGEND[sortierung].length + 2;
  if (!Array.isArray(daten) || daten[0] !== sortierung || daten.length !== laenge
      || daten.slice(1).some((w) => typeof w !== "number" && typeof w !== "string")) {
    throw new Quellfehler("Seitenzeiger passt nicht zur Sortierung");
  }
  return daten.slice(1) as Zeigerwert[];
}

const gleichArtig = (a: Zeigerwert, b: Zeigerwert): number =>
  typeof a === "number" && typeof b === "number" ? a - b : vergleichen(String(a), String(b));

/** < 0: Sender i steht vor dem Zeiger, > 0: danach */
function gegenZeiger(b: Senderbestand, sortierung: Sortierung, i: number, werte: Zeigerwert[]): number {
  const eigene = [...sortwerte(b, sortierung, i), b.uuid[i]];
  const richtung = [...ABSTEIGEND[sortierung], false];
  for (let k = 0; k < eigene.length; k++) {
    const d = gleichArtig(eigene[k], werte[k]);
    if (d) return richtung[k] ? -d : d;
  }
  return 0;
}

/** erste Stelle der (sortierten) Treffer nach dem Zeiger */
function nachDemZeiger(b: Senderbestand, q: Abfrage, liste: Int32Array, werte: Zeigerwert[]): number {
  let unten = 0;
  let oben = liste.length;
  while (unten < oben) {
    const mitte = (unten + oben) >> 1;
    if (gegenZeiger(b, q.sortierung, liste[mitte], werte) <= 0) unten = mitte + 1;
    else oben = mitte;
  }
  return unten;
}

// ----- Durchgang --------------------------------------------------------------------------------------------------

const BIT = { laender: 1, genres: 2, qualitaet: 4, codecs: 8, bewertungen: 16, kategorien: 32 } as const;
type Gruppe = keyof typeof BIT;

/** Ein Durchgang: die Treffer in Reihenfolge und für die Facetten je Sender, welche Gruppenfilter er verfehlt */
export interface Durchgang {
  treffer: Int32Array;
  /** Sender, die alle Filter außer denen der Gruppen erfüllen, und ihre verfehlten Gruppen als Bits */
  kandidaten: Int32Array;
  verfehlt: Uint8Array;
}

export function durchgehen(b: Senderbestand, s: Sicht, q: Abfrage): Durchgang {
  const gebuendelt = buendeln(q);
  const suche = suchpruefung(b, q.suche);
  const laender = new Set(q.laender);
  const genres = new Set(q.genres);
  const qualitaet = new Set<string>(q.qualitaet);
  const codecs = new Set(q.codecs);
  const bewertungen = new Set<string>(q.bewertungen);
  const genreNamen = b.kopf.woerter.genre;
  const treffer: number[] = [];
  const kandidaten: number[] = [];
  const verfehlt: number[] = [];
  for (const i of b.reihen[q.sortierung]) {
    if (!s.sichtbar[i] || (gebuendelt && !s.vertreter[i]) || (suche && !suche(i))) continue;
    const kbps = b.kbps[i];
    if ((q.bitrate_min && kbps < q.bitrate_min) || (q.bitrate_max && kbps > q.bitrate_max)) continue;
    if ((q.stimmen_min && b.stimmen[i] < q.stimmen_min) || (q.stimmen_max != null && b.stimmen[i] > q.stimmen_max)) continue;
    if (q.nur_favoriten && !s.favorit[i]) continue;
    let bits = 0;
    if (laender.size && !laender.has(b.land[i])) bits |= BIT.laender;
    if (genres.size && !b.genres[i].some((g) => genres.has(genreNamen[g]))) bits |= BIT.genres;
    if (qualitaet.size && !qualitaet.has(b.qualitaet[i])) bits |= BIT.qualitaet;
    if (codecs.size && !codecs.has(b.codec[i])) bits |= BIT.codecs;
    if (bewertungen.size && !(s.bewertungen.get(i) ?? []).some((x) => bewertungen.has(x))) bits |= BIT.bewertungen;
    if (q.kategorien.length) bits |= BIT.kategorien;            // eigene Kategorien gibt es in der Webversion nicht
    if (!bits) treffer.push(i);
    kandidaten.push(i);
    verfehlt.push(bits);
  }
  return { treffer: Int32Array.from(treffer), kandidaten: Int32Array.from(kandidaten), verfehlt: Uint8Array.from(verfehlt) };
}

// ----- Facetten ---------------------------------------------------------------------------------------------------

function zaehlen(d: Durchgang, gruppe: Gruppe, werte: (i: number) => Iterable<string>): Map<string, number> {
  const zahlen = new Map<string, number>();
  const ohne = ~BIT[gruppe];
  d.kandidaten.forEach((i, k) => {
    if (d.verfehlt[k] & ohne) return;
    for (const w of werte(i)) zahlen.set(w, (zahlen.get(w) ?? 0) + 1);
  });
  return zahlen;
}

function sortiert(zahlen: Map<string, number>, namen: (w: string) => string = (w) => w, gewaehlt: string[] = []): Facette[] {
  const werte = new Set([...zahlen.keys(), ...gewaehlt]);
  return [...werte].map((w) => ({ wert: w, name: namen(w), anzahl: zahlen.get(w) ?? 0 }))
    .sort((x, y) => y.anzahl - x.anzahl || vergleichen(x.name, y.name));
}

export const landname = (b: Senderbestand, code: string): string => b.landnamen.get(code) || code;

export function facetten(b: Senderbestand, s: Sicht, q: Abfrage, d: Durchgang, leiste: string[]): Facetten {
  const auswahl = leiste.length ? [...new Set([...leiste, ...q.laender])].sort(vergleichen) : [];
  const inLeiste = new Set(auswahl);
  const laender = zaehlen(d, "laender", (i) => (b.land[i] && (!inLeiste.size || inLeiste.has(b.land[i])) ? [b.land[i]] : []));
  const genreNamen = b.kopf.woerter.genre;
  const genres = zaehlen(d, "genres", (i) => b.genres[i].map((g) => genreNamen[g]));
  const stufen = zaehlen(d, "qualitaet", (i) => [b.qualitaet[i]]);
  const codecs = zaehlen(d, "codecs", (i) => [b.codec[i]]);
  const bewertungen = zaehlen(d, "bewertungen", (i) => new Set(s.bewertungen.get(i) ?? []));
  return {
    laender: sortiert(laender, (c) => landname(b, c), auswahl),
    genres: sortiert(genres, undefined, q.genres),
    qualitaet: QUALITAETEN.map((w) => ({ wert: w, name: w, anzahl: stufen.get(w) ?? 0 })),
    codecs: sortiert(codecs, undefined, q.codecs),
    bewertungen: (Object.keys(BEWERTUNGEN) as Bewertung[]).filter((k) => bewertungen.get(k) || q.bewertungen.includes(k))
      .map((k) => ({ wert: k, name: BEWERTUNGEN[k], anzahl: bewertungen.get(k) ?? 0 })),
    kategorien: [],
  };
}

// ----- Einträge ---------------------------------------------------------------------------------------------------

export function eintrag(b: Senderbestand, s: Sicht, i: number): SenderEintrag {
  const w = b.kopf.woerter;
  return {
    uuid: b.uuid[i], name: b.name[i], logo: "", homepage: b.homepage[i], land: b.land[i], land_name: b.landName[i],
    region: b.region[i], bundesland: b.bundesland[i],
    sprachen: b.sprachen[i].map((n) => ({ schluessel: w.sprache[n], name: sprachname(b.kopf, w.sprache[n]) })),
    genres: b.genres[i].map((n) => w.genre[n]), codec: b.codec[i], kbps: b.kbps[i] || null, kbps_gemessen: false,
    qualitaet: b.qualitaet[i], stimmen: b.stimmen[i], erreichbar: true, hls: !!b.hls[i], gruppe: b.uuid[b.gruppe[i]],
    varianten: s.varianten[i], favorit: !!s.favorit[i], ausnahme: s.sichtbar[i] ? s.gruende(i) : [], verschwunden: false,
    kategorien: [], bewertungen: [...(s.bewertungen.get(i) ?? [])], werbung: { stufe: "keine", entscheidung: null },
    eigene_adresse: null, adresse: b.adresse[i], adresse_aufgeloest: b.adresseAufgeloest[i],
  };
}

export function kurz(b: Senderbestand, i: number): SenderKurz {
  return { uuid: b.uuid[i], name: b.name[i], land: b.land[i], stimmen: b.stimmen[i], logo: "" };
}

/** die ersten `grenze` nach Stimmen (absteigend, dann uuid) */
export function nachStimmen(b: Senderbestand, sender: Iterable<number>, grenze = Infinity): number[] {
  return [...sender].sort((x, y) => b.stimmen[y] - b.stimmen[x] || vergleichen(b.uuid[x], b.uuid[y])).slice(0, grenze);
}

// ----- Abfrage ----------------------------------------------------------------------------------------------------

/** Schlüssel des Durchgangs: alles außer Seite und Facetten */
export function durchgangSchluessel(q: Abfrage): string {
  const { nach: _nach, anzahl: _anzahl, mit_facetten: _facetten, ...filter } = q;
  return JSON.stringify(filter);
}

export function seite(b: Senderbestand, s: Sicht, q: Abfrage, d: Durchgang, leiste: string[]): Abfrageergebnis {
  const anfang = q.nach ? nachDemZeiger(b, q, d.treffer, zeigerLesen(q.sortierung, q.nach)) : 0;
  const stellen = d.treffer.subarray(anfang, anfang + q.anzahl);
  const weiter = anfang + q.anzahl < d.treffer.length ? zeigerBauen(b, q.sortierung, stellen[stellen.length - 1]) : null;
  const mit = q.mit_facetten ?? !q.nach;
  return { gesamt: q.nach ? null : d.treffer.length, eintraege: [...stellen].map((i) => eintrag(b, s, i)), weiter,
           facetten: mit ? facetten(b, s, q, d, leiste) : null };
}
