// Statische Senderliste der Webversion (RAD-4): Lesen von sender.json (Spaltenformat aus
// backend/app/werkzeuge/statische_liste.py) in einen Bestand aus Spalten mit den Indizes, die Regeln, Suche und
// Sortierungen brauchen. Einmal gebaut, danach nur gelesen; alles Veränderliche (Favoriten, Regeln, ...) liegt in
// den eigenen Angaben und der Sicht daraus.
import type { Qualitaet, Sortierung } from "../typen";
import { faltung, suchform, vergleichen } from "./text";

export const FORMAT = 3;   // 3: wieder mit Spalte logo (nur https, RAD-105); 2 war ohne

/** Spalten einer Zeile in dieser Reihenfolge (wie SPALTEN im Werkzeug) */
export const SPALTEN = [
  "uuid", "name", "adresse", "adresse_aufgeloest", "logo", "homepage", "land", "land_name", "region", "bundesland",
  "sprachen", "spracheintraege", "genres", "tags", "codec", "kbps", "qualitaet", "stimmen", "hls", "gruppe",
] as const;

const WOERTERBUECHER = ["land", "land_name", "region", "bundesland", "sprache", "spracheintrag", "genre", "tag", "codec", "qualitaet"] as const;
type Woerterbuch = (typeof WOERTERBUECHER)[number];

export const QUALITAET_RANG: Record<Qualitaet, number> = { verlustfrei: 4, hoch: 3, mittel: 2, niedrig: 1, unbekannt: 0 };
export const FREI = "frei:";

export interface Kopf {
  format: number;
  aufbereitung: number;
  erzeugt: string;
  quelle: "verzeichnis" | "datenbank";
  anzahl: number;
  spalten: string[];
  woerter: Record<Woerterbuch, string[]>;
  /** Code der Sprachtabelle -> deutscher Name */
  sprachnamen: Record<string, string>;
  /** genauer Spracheintrag -> Code, wenn die Sprachtabelle ihn kennt */
  eintragscodes: Record<string, string>;
}

/** Der Bestand der Liste, je Feld eine Spalte (Stelle i ist der Sender i). Wortlisten sind Nummern ins Wörterbuch. */
export interface Senderbestand {
  readonly kopf: Kopf;
  readonly anzahl: number;
  readonly uuid: string[];
  readonly name: string[];
  /** name in Vergleichsform (klein, gefaltet): Suche unter drei Zeichen und Sortierung nach Namen */
  readonly nameKlein: string[];
  readonly adresse: string[];
  readonly adresseAufgeloest: string[];
  readonly logo: string[];
  readonly homepage: string[];
  readonly land: string[];
  readonly landName: string[];
  readonly region: string[];
  readonly bundesland: string[];
  readonly sprachen: number[][];
  readonly eintraege: number[][];
  readonly genres: number[][];
  readonly tags: number[][];
  readonly codec: string[];
  /** kbit/s, 0 ohne Angabe */
  readonly kbps: Int32Array;
  readonly qualitaet: Qualitaet[];
  readonly qualitaetRang: Int8Array;
  readonly stimmen: Int32Array;
  readonly hls: Uint8Array;
  /** Zeilennummer des Senders, dessen uuid die Gruppe kennzeichnet */
  readonly gruppe: Int32Array;
  /** Suchtext ohne Diakritika, klein (wie die Volltextsuche des Backends) */
  readonly suchtext: string[];
  readonly nachUuid: Map<string, number>;
  /** Wert -> Sender (aufsteigend) */
  readonly mitSprache: Map<string, number[]>;
  readonly mitEintrag: Map<string, number[]>;
  readonly mitGenre: Map<string, number[]>;
  readonly mitTag: Map<string, number[]>;
  /** Gruppe (Zeilennummer) -> Glieder */
  readonly glieder: Map<number, number[]>;
  /** Sender je Sortierung in ihrer Reihenfolge, uuid als Nebenschlüssel */
  readonly reihen: Record<Sortierung, Int32Array>;
  /** Land -> Name, wie das Backend ihn nimmt (größter Name je Code) */
  readonly landnamen: Map<string, string>;
}

export class Formatfehler extends Error {
  constructor(text: string) {
    super(`Senderliste unlesbar: ${text}`);
    this.name = "Formatfehler";
  }
}

const istObjekt = (w: unknown): w is Record<string, unknown> => typeof w === "object" && w !== null && !Array.isArray(w);

function kopfLesen(roh: unknown): Kopf {
  if (!istObjekt(roh)) throw new Formatfehler("Kopf fehlt");
  if (roh.format !== FORMAT) throw new Formatfehler(`Fassung ${String(roh.format)} des Formats statt ${FORMAT}`);
  if (!Array.isArray(roh.spalten) || roh.spalten.join(",") !== SPALTEN.join(",")) throw new Formatfehler("Spalten passen nicht");
  if (typeof roh.anzahl !== "number" || !istObjekt(roh.woerter) || !istObjekt(roh.sprachnamen) || !istObjekt(roh.eintragscodes)) {
    throw new Formatfehler("Kopf unvollständig");
  }
  for (const w of WOERTERBUECHER) {
    const liste = roh.woerter[w];
    if (!Array.isArray(liste) || liste.some((x) => typeof x !== "string")) throw new Formatfehler(`Wörterbuch ${w} fehlt`);
  }
  return roh as unknown as Kopf;
}

function wort(kopf: Kopf, w: Woerterbuch, n: unknown): string {
  const wert = typeof n === "number" ? kopf.woerter[w][n] : undefined;
  if (wert === undefined) throw new Formatfehler(`Nummer ${String(n)} fehlt im Wörterbuch ${w}`);
  return wert;
}

function nummern(kopf: Kopf, w: Woerterbuch, roh: unknown): number[] {
  if (!Array.isArray(roh)) throw new Formatfehler(`Liste für ${w} erwartet`);
  for (const n of roh) wort(kopf, w, n);
  return roh as number[];
}

function text(roh: unknown, feld: string): string {
  if (typeof roh !== "string") throw new Formatfehler(`Text für ${feld} erwartet`);
  return roh;
}

function ganzzahl(roh: unknown, feld: string): number {
  if (typeof roh !== "number" || !Number.isInteger(roh)) throw new Formatfehler(`Zahl für ${feld} erwartet`);
  return roh;
}

/** Name einer Sprache aus ihrem Schlüssel (Code oder frei:<Eintrag>) */
export function sprachname(kopf: Kopf, schluessel: string): string {
  return schluessel.startsWith(FREI) ? schluessel.slice(FREI.length) : (kopf.sprachnamen[schluessel] ?? schluessel);
}

function indexBauen(spalte: number[][], woerter: string[]): Map<string, number[]> {
  const index = new Map<string, number[]>();
  spalte.forEach((liste, i) => {
    for (const n of liste) {
      const wert = woerter[n];
      const sender = index.get(wert);
      if (sender) sender.push(i);
      else index.set(wert, [i]);
    }
  });
  return index;
}

function reihenBauen(b: Pick<Senderbestand, "anzahl" | "uuid" | "nameKlein" | "stimmen" | "kbps" | "qualitaetRang">): Record<Sortierung, Int32Array> {
  const reihe = (vor: (x: number, y: number) => number): Int32Array => {
    const r = Int32Array.from({ length: b.anzahl }, (_, i) => i);
    return r.sort((x, y) => vor(x, y) || vergleichen(b.uuid[x], b.uuid[y]));
  };
  return {
    stimmen: reihe((x, y) => b.stimmen[y] - b.stimmen[x]),
    name: reihe((x, y) => vergleichen(b.nameKlein[x], b.nameKlein[y])),
    qualitaet: reihe((x, y) => b.qualitaetRang[y] - b.qualitaetRang[x] || b.kbps[y] - b.kbps[x]),
    bitrate: reihe((x, y) => b.kbps[y] - b.kbps[x]),
  };
}

/** Liest sender.json streng und baut den Bestand mit allen Indizes (einmal je Liste). */
export function bestandLesen(roh: unknown): Senderbestand {
  if (!istObjekt(roh) || !Array.isArray(roh.zeilen)) throw new Formatfehler("Kopf und Zeilen erwartet");
  const kopf = kopfLesen(roh.kopf);
  const zeilen = roh.zeilen as unknown[];
  if (zeilen.length !== kopf.anzahl) throw new Formatfehler(`${zeilen.length} Zeilen statt ${kopf.anzahl}`);
  const n = zeilen.length;
  const b = {
    kopf, anzahl: n, uuid: [] as string[], name: [] as string[], nameKlein: [] as string[], adresse: [] as string[],
    adresseAufgeloest: [] as string[], logo: [] as string[], homepage: [] as string[], land: [] as string[],
    landName: [] as string[], region: [] as string[], bundesland: [] as string[], sprachen: [] as number[][],
    eintraege: [] as number[][], genres: [] as number[][], tags: [] as number[][], codec: [] as string[],
    kbps: new Int32Array(n), qualitaet: [] as Qualitaet[], qualitaetRang: new Int8Array(n), stimmen: new Int32Array(n),
    hls: new Uint8Array(n), gruppe: new Int32Array(n), suchtext: [] as string[], nachUuid: new Map<string, number>(),
  };
  zeilen.forEach((z, i) => {
    if (!Array.isArray(z) || z.length !== SPALTEN.length) throw new Formatfehler(`Zeile ${i} hat nicht ${SPALTEN.length} Spalten`);
    const [uuid, name, adresse, aufgeloest, logo, homepage, land, landName, region, bundesland, sprachen, eintraege, genres,
      tags, codec, kbps, qualitaet, stimmen, hls, gruppe] = z;
    const kennung = text(uuid, "uuid");
    if (!kennung || b.nachUuid.has(kennung)) throw new Formatfehler(`uuid in Zeile ${i} leer oder doppelt`);
    b.nachUuid.set(kennung, i);
    b.uuid.push(kennung);
    b.name.push(text(name, "name"));
    b.nameKlein.push(faltung(b.name[i].trim()));
    b.adresse.push(text(adresse, "adresse"));
    // leer heißt: wie adresse
    b.adresseAufgeloest.push(text(aufgeloest, "adresse_aufgeloest") || b.adresse[i]);
    b.logo.push(text(logo, "logo"));
    b.homepage.push(text(homepage, "homepage"));
    b.land.push(wort(kopf, "land", land));
    b.landName.push(wort(kopf, "land_name", landName));
    b.region.push(wort(kopf, "region", region));
    b.bundesland.push(wort(kopf, "bundesland", bundesland));
    b.sprachen.push(nummern(kopf, "sprache", sprachen));
    b.eintraege.push(nummern(kopf, "spracheintrag", eintraege));
    b.genres.push(nummern(kopf, "genre", genres));
    b.tags.push(nummern(kopf, "tag", tags));
    b.codec.push(wort(kopf, "codec", codec));
    b.kbps[i] = ganzzahl(kbps, "kbps");
    const stufe = wort(kopf, "qualitaet", qualitaet) as Qualitaet;
    if (!(stufe in QUALITAET_RANG)) throw new Formatfehler(`Qualität ${stufe} unbekannt`);
    b.qualitaet.push(stufe);
    b.qualitaetRang[i] = QUALITAET_RANG[stufe];
    b.stimmen[i] = ganzzahl(stimmen, "stimmen");
    b.hls[i] = ganzzahl(hls, "hls") ? 1 : 0;
    const g = ganzzahl(gruppe, "gruppe");
    if (g < 0 || g >= n) throw new Formatfehler(`Gruppe ${g} in Zeile ${i} außerhalb der Liste`);
    b.gruppe[i] = g;
  });
  const w = kopf.woerter;
  for (let i = 0; i < n; i++) {
    const teile = [b.name[i], ...b.genres[i].map((g) => w.genre[g]), ...b.tags[i].map((t) => w.tag[t]), b.bundesland[i], b.landName[i],
      ...b.sprachen[i].map((s) => sprachname(kopf, w.sprache[s]))];
    b.suchtext.push(suchform(teile.filter((t) => t).join(" ")));
  }
  const glieder = new Map<number, number[]>();
  for (let i = 0; i < n; i++) {
    const liste = glieder.get(b.gruppe[i]);
    if (liste) liste.push(i);
    else glieder.set(b.gruppe[i], [i]);
  }
  const landnamen = new Map<string, string>();
  for (let i = 0; i < n; i++) {
    const bisher = landnamen.get(b.land[i]);
    if (bisher === undefined || b.landName[i] > bisher) landnamen.set(b.land[i], b.landName[i]);
  }
  return {
    ...b, glieder, landnamen, reihen: reihenBauen(b),
    mitSprache: indexBauen(b.sprachen, w.sprache), mitEintrag: indexBauen(b.eintraege, w.spracheintrag),
    mitGenre: indexBauen(b.genres, w.genre), mitTag: indexBauen(b.tags, w.tag),
  };
}
