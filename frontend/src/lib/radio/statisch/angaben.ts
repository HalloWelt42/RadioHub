// Eigene Angaben der Webversion (RAD-4): Favoriten, Bewertungen, Regeln, Einzelsperren, Freigaben und die Länder der
// Seitenleiste. Eine Form für den Speicher des Browsers und für die Datei zum Sichern; das Prüfen ist streng, damit
// eine fremde oder beschädigte Datei nichts halb übernimmt.
import type { Einspielbericht } from "../quelle";
import type { Bewertung, Herkunft, RegelEntwurf } from "../typen";
import { Quellfehler } from "./fehler";
import { ARTEN, EINZELSPERREN, entwurfPruefen, inhalt, istBewertung, type StatischeArt } from "./regeln";

export const ANGABEN_ART = "radiohub-eigene-angaben";
export const ANGABEN_FASSUNG = 1;

export interface GespeicherteRegel {
  id: string;
  art: StatischeArt;
  an: boolean;
  herkunft: Herkunft;
  /** null nur bei den Einzelsperren */
  entwurf: RegelEntwurf | null;
  angelegt_am: string;
  geaendert_am: string;
}

export interface EigeneAngaben {
  art: typeof ANGABEN_ART;
  fassung: typeof ANGABEN_FASSUNG;
  gesichert_am: string;
  favoriten: string[];
  /** uuid -> Bewertungen (höchstens eine Sternstufe) */
  bewertungen: Record<string, Bewertung[]>;
  regeln: GespeicherteRegel[];
  sperren: string[];
  freigaben: string[];
  laender_leiste: string[];
}

const FELDER = ["art", "fassung", "gesichert_am", "favoriten", "bewertungen", "regeln", "sperren", "freigaben", "laender_leiste"];
const REGEL_FELDER = ["id", "art", "an", "herkunft", "entwurf", "angelegt_am", "geaendert_am"];
const HERKUNFT: readonly Herkunft[] = ["nutzer", "ueberfuehrt", "bestand"];
const KENNUNG = /^[\w-]{1,64}$/;
const LAND = /^[A-Z]{2}$/;

export function einzelsperrenRegel(zeit: string): GespeicherteRegel {
  return { id: EINZELSPERREN, art: "einzeln", an: true, herkunft: "bestand", entwurf: null, angelegt_am: zeit, geaendert_am: zeit };
}

export function leereAngaben(zeit: string): EigeneAngaben {
  return { art: ANGABEN_ART, fassung: ANGABEN_FASSUNG, gesichert_am: zeit, favoriten: [], bewertungen: {},
           regeln: [einzelsperrenRegel(zeit)], sperren: [], freigaben: [], laender_leiste: [] };
}

// ----- Nachziehen -------------------------------------------------------------------------------------------------

/** Dieselben Angaben unter den heutigen Kennungen der Sender (`heute` gibt unbekannte unverändert zurück). Ohne
 *  Änderung dieselben Angaben; nichts fällt weg, zwei frühere Kennungen desselben Senders werden eine. */
export function nachgezogen(a: EigeneAngaben, heute: (uuid: string) => string): EigeneAngaben {
  const betroffen = [...a.favoriten, ...a.sperren, ...a.freigaben, ...Object.keys(a.bewertungen)].some((u) => heute(u) !== u);
  if (!betroffen) return a;
  const einmal = (uuids: string[]) => [...new Set(uuids.map(heute))];
  const sperren = einmal(a.sperren);
  const bewertungen: Record<string, Bewertung[]> = {};
  for (const [uuid, werte] of Object.entries(a.bewertungen)) bewertungen[heute(uuid)] ??= werte;
  return { ...a, favoriten: einmal(a.favoriten), sperren, freigaben: einmal(a.freigaben).filter((u) => !sperren.includes(u)), bewertungen };
}

// ----- Prüfen -----------------------------------------------------------------------------------------------------

const falsch = (text: string): Quellfehler => new Quellfehler(`Die Datei passt nicht: ${text}`, 422);
const istObjekt = (w: unknown): w is Record<string, unknown> => typeof w === "object" && w !== null && !Array.isArray(w);

function genauDieFelder(o: Record<string, unknown>, felder: string[], wo: string): void {
  const fremd = Object.keys(o).filter((k) => !felder.includes(k));
  if (fremd.length) throw falsch(`unbekanntes Feld ${fremd.join(", ")} in ${wo}`);
  const fehlen = felder.filter((k) => !(k in o));
  if (fehlen.length) throw falsch(`es fehlt ${fehlen.join(", ")} in ${wo}`);
}

function zeitpunkt(roh: unknown, wo: string): string {
  if (typeof roh !== "string" || !roh || Number.isNaN(Date.parse(roh))) throw falsch(`kein Zeitpunkt in ${wo}`);
  return roh;
}

function liste(roh: unknown, wo: string, muster: RegExp): string[] {
  if (!Array.isArray(roh)) throw falsch(`${wo} ist keine Liste`);
  for (const w of roh) if (typeof w !== "string" || !muster.test(w)) throw falsch(`ungültiger Eintrag ${JSON.stringify(w)} in ${wo}`);
  if (new Set(roh).size !== roh.length) throw falsch(`doppelte Einträge in ${wo}`);
  return roh as string[];
}

function bewertungenPruefen(roh: unknown): Record<string, Bewertung[]> {
  if (!istObjekt(roh)) throw falsch("bewertungen ist keine Zuordnung");
  const ergebnis: Record<string, Bewertung[]> = {};
  for (const [uuid, werte] of Object.entries(roh)) {
    if (!KENNUNG.test(uuid)) throw falsch(`ungültige Senderkennung ${JSON.stringify(uuid)} in bewertungen`);
    if (!Array.isArray(werte) || !werte.length) throw falsch(`keine Bewertungen für ${uuid}`);
    const unbekannt = werte.filter((w) => !istBewertung(w));
    if (unbekannt.length) throw falsch(`unbekannte Bewertung ${unbekannt.join(", ")} für ${uuid}`);
    if (new Set(werte).size !== werte.length) throw falsch(`doppelte Bewertung für ${uuid}`);
    if (werte.filter((w) => String(w).startsWith("sterne:")).length > 1) throw falsch(`mehr als eine Sternstufe für ${uuid}`);
    ergebnis[uuid] = werte as Bewertung[];
  }
  return ergebnis;
}

function regelPruefen(roh: unknown, nummer: number): GespeicherteRegel {
  const wo = `Regel ${nummer + 1}`;
  if (!istObjekt(roh)) throw falsch(`${wo} ist kein Eintrag`);
  genauDieFelder(roh, REGEL_FELDER, wo);
  const { id, art, an, herkunft, entwurf } = roh;
  if (typeof id !== "string" || !KENNUNG.test(id)) throw falsch(`ungültige Kennung in ${wo}`);
  if (!ARTEN.includes(art as StatischeArt)) throw falsch(`unbekannte Art ${String(art)} in ${wo}`);
  if (typeof an !== "boolean") throw falsch(`an ist nicht wahr oder falsch in ${wo}`);
  if (!HERKUNFT.includes(herkunft as Herkunft)) throw falsch(`unbekannte Herkunft in ${wo}`);
  const einzeln = art === "einzeln";
  if (einzeln !== (id === EINZELSPERREN)) throw falsch(`nur die Regel ${EINZELSPERREN} sammelt Einzelsperren (${wo})`);
  if (einzeln && entwurf !== null) throw falsch(`die Einzelsperren haben keinen Entwurf (${wo})`);
  let geprueft: RegelEntwurf | null = null;
  if (!einzeln) {
    try {
      geprueft = entwurfPruefen(entwurf);
    } catch (f) {
      throw falsch(`${wo}: ${(f as Error).message}`);
    }
    if (geprueft.art !== art) throw falsch(`Art des Entwurfs passt nicht in ${wo}`);
  }
  return { id, art: art as StatischeArt, an, herkunft: herkunft as Herkunft, entwurf: geprueft,
           angelegt_am: zeitpunkt(roh.angelegt_am, wo), geaendert_am: zeitpunkt(roh.geaendert_am, wo) };
}

function regelnPruefen(roh: unknown): GespeicherteRegel[] {
  if (!Array.isArray(roh)) throw falsch("regeln ist keine Liste");
  const regeln = roh.map(regelPruefen);
  if (new Set(regeln.map((r) => r.id)).size !== regeln.length) throw falsch("doppelte Kennung einer Regel");
  const inhalte = regeln.filter((r) => r.entwurf).map((r) => `${r.art}|${inhalt(r.entwurf as RegelEntwurf)}`);
  if (new Set(inhalte).size !== inhalte.length) throw falsch("zwei Regeln mit demselben Inhalt");
  return regeln;
}

/** Eigene Angaben aus einem gelesenen JSON, streng geprüft; wirft Quellfehler mit lesbarer Meldung. Fehlt die Regel
 *  der Einzelsperren, kommt sie eingeschaltet dazu. */
export function angabenPruefen(roh: unknown, zeit: string): EigeneAngaben {
  if (!istObjekt(roh) || roh.art !== ANGABEN_ART) throw falsch("das ist keine Sicherung der eigenen Angaben des Radios");
  if (roh.fassung !== ANGABEN_FASSUNG) throw falsch(`Fassung ${String(roh.fassung)} wird nicht unterstützt (erwartet ${ANGABEN_FASSUNG})`);
  genauDieFelder(roh, FELDER, "der Datei");
  const sperren = liste(roh.sperren, "sperren", KENNUNG);
  const freigaben = liste(roh.freigaben, "freigaben", KENNUNG);
  const beide = sperren.filter((u) => freigaben.includes(u));
  if (beide.length) throw falsch(`gesperrt und freigegeben zugleich: ${beide.join(", ")}`);
  const regeln = regelnPruefen(roh.regeln);
  if (!regeln.some((r) => r.id === EINZELSPERREN)) regeln.push(einzelsperrenRegel(zeit));
  return { art: ANGABEN_ART, fassung: ANGABEN_FASSUNG, gesichert_am: zeitpunkt(roh.gesichert_am, "gesichert_am"),
           favoriten: liste(roh.favoriten, "favoriten", KENNUNG), bewertungen: bewertungenPruefen(roh.bewertungen), regeln,
           sperren, freigaben, laender_leiste: liste(roh.laender_leiste, "laender_leiste", LAND) };
}

/** Text einer Datei lesen und prüfen */
export function angabenAusText(text: string, zeit: string): EigeneAngaben {
  let roh: unknown;
  try {
    roh = JSON.parse(text);
  } catch {
    throw falsch("kein lesbares JSON");
  }
  return angabenPruefen(roh, zeit);
}

/** Was eine Sicherung enthält (ohne die Regel der Einzelsperren, die es immer gibt) */
export function bericht(a: EigeneAngaben): Einspielbericht {
  return { favoriten: a.favoriten.length, bewertungen: Object.values(a.bewertungen).reduce((n, l) => n + l.length, 0),
           regeln: a.regeln.filter((r) => r.id !== EINZELSPERREN).length, sperren: a.sperren.length, freigaben: a.freigaben.length };
}
