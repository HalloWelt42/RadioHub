// Ausgeblendete Sender seitenweise mit Grund, Kandidaten neuer Regeln mit Zahlen, Länder mit Zahl der sichtbaren
// Sender (wie backend/app/services/senderquelle/ausgeblendet.py und alte_wege.laender).
import type { LandZahl } from "../quelle";
import type { AusgeblendetAnfrage, AusgeblendetSeite, Bewertung, GrundZahl, Kandidat, KandidatenArt } from "../typen";
import { landname, suchpruefung } from "./abfrage";
import { Quellfehler } from "./fehler";
import { FREI, sprachname, type Senderbestand } from "./format";
import { BEWERTUNGEN } from "./regeln";
import type { Sicht } from "./sicht";
import { faltung, vergleichen } from "./text";

export function ausgeblendetSeite(b: Senderbestand, s: Sicht, a: AusgeblendetAnfrage): AusgeblendetSeite {
  const anzahl = a.anzahl ?? 25;
  if (!Number.isInteger(anzahl) || anzahl < 1 || anzahl > 100) throw new Quellfehler("anzahl: 1 bis 100", 422);
  const maske = a.regel ? (s.regeln.get(a.regel)?.maske ?? new Uint8Array(b.anzahl)) : null;
  const suche = suchpruefung(b, a.suche ?? "");
  const treffer: number[] = [];
  for (const i of b.reihen.stimmen) {
    if (!s.sichtbar[i] && (!maske || maske[i]) && (!suche || suche(i))) treffer.push(i);
  }
  const seiten = Math.max(1, Math.ceil(treffer.length / anzahl));
  const nummer = Math.min(a.seite ?? 0, seiten - 1);
  const zahlen = new Map<string, GrundZahl>();
  for (let i = 0; i < b.anzahl; i++) {
    if (s.sichtbar[i]) continue;
    for (const g of s.gruende(i)) {
      const z = zahlen.get(g.regel) ?? { regel: g.regel, titel: g.titel, anzahl: 0 };
      z.anzahl++;
      zahlen.set(g.regel, z);
    }
  }
  return {
    gesamt: treffer.length, seite: nummer, seiten,
    eintraege: treffer.slice(nummer * anzahl, (nummer + 1) * anzahl).map((i) => ({
      uuid: b.uuid[i], name: b.name[i], land: b.land[i], stimmen: b.stimmen[i], logo: b.logo[i], gruende: s.gruende(i) })),
    gruende: [...zahlen.values()].sort((x, y) => y.anzahl - x.anzahl || vergleichen(x.regel, y.regel)),
  };
}

// ----- Kandidaten -------------------------------------------------------------------------------------------------

interface Zahl { wert: string; anzahl: number; favoriten: number }

function gezaehlt(s: Sicht, werte: Iterable<[string, Iterable<number>]>, grenze: number): Zahl[] {
  const liste: Zahl[] = [];
  for (const [wert, sender] of werte) {
    let anzahl = 0;
    let favoriten = 0;
    for (const i of sender) {
      anzahl++;
      favoriten += s.favorit[i];
    }
    if (anzahl) liste.push({ wert, anzahl, favoriten });
  }
  return liste.sort((x, y) => y.anzahl - x.anzahl || vergleichen(x.wert, y.wert)).slice(0, grenze);
}

function sprachKandidaten(b: Senderbestand, s: Sicht, text: string, grenze: number): Kandidat[] {
  const namen = b.kopf.sprachnamen;
  const codes = new Set(text ? Object.keys(namen).filter((c) => faltung(namen[c]).includes(text) || c === text) : []);
  const passt = (k: string) => !text || (k.startsWith(FREI) && k.slice(FREI.length).includes(text)) || codes.has(k);
  return gezaehlt(s, [...b.mitSprache].filter(([k]) => passt(k)), grenze).map((z) => ({
    schluessel: z.wert, code: z.wert.startsWith(FREI) ? null : z.wert, name: sprachname(b.kopf, z.wert), anzahl: z.anzahl,
    favoriten: z.favoriten }));
}

function bewertungsKandidaten(b: Senderbestand, s: Sicht): Kandidat[] {
  const je = new Map<string, number[]>();
  for (const [i, liste] of s.bewertungen) for (const x of liste) je.set(x, [...(je.get(x) ?? []), i]);
  return gezaehlt(s, je, 50).filter((z) => z.wert in BEWERTUNGEN)
    .map((z) => ({ schluessel: z.wert, name: BEWERTUNGEN[z.wert as Bewertung], code: null, anzahl: z.anzahl, favoriten: z.favoriten }));
}

function einzelKandidaten(b: Senderbestand, s: Sicht, text: string, grenze: number): Kandidat[] {
  if ([...text].length < 2) return [];
  // die Reihe nach Stimmen ist schon in der Reihenfolge des Backends (Stimmen absteigend, dann uuid)
  const treffer = [...b.reihen.stimmen.filter((i) => b.nameKlein[i].includes(text))].slice(0, grenze);
  return treffer.map((i) => ({ schluessel: b.uuid[i], name: b.name[i], code: b.land[i], anzahl: 1, favoriten: s.favorit[i] }));
}

export function kandidaten(b: Senderbestand, s: Sicht, art: KandidatenArt, suche: string, grenze: number): Kandidat[] {
  if (!Number.isInteger(grenze) || grenze < 1 || grenze > 100) throw new Quellfehler("grenze: 1 bis 100", 422);
  const text = faltung(suche.trim());
  switch (art) {
    case "sprache": return sprachKandidaten(b, s, text, grenze);
    case "genre":
    case "tag": {
      const index = art === "genre" ? b.mitGenre : b.mitTag;
      return gezaehlt(s, [...index].filter(([w]) => w.toLowerCase().includes(text)), grenze)
        .map((z) => ({ schluessel: z.wert, name: z.wert, code: null, anzahl: z.anzahl, favoriten: z.favoriten }));
    }
    case "bewertung": return bewertungsKandidaten(b, s);
    case "einzeln": return einzelKandidaten(b, s, text, grenze);
    default: throw new Quellfehler(`Für die Art ${String(art)} gibt es keine Kandidaten`);
  }
}

// ----- Länder -----------------------------------------------------------------------------------------------------

export function laender(b: Senderbestand, s: Sicht): LandZahl[] {
  const zahlen = new Map<string, number>();
  for (let i = 0; i < b.anzahl; i++) if (s.sichtbar[i] && b.land[i]) zahlen.set(b.land[i], (zahlen.get(b.land[i]) ?? 0) + 1);
  return [...zahlen].sort((x, y) => y[1] - x[1] || vergleichen(x[0], y[0]))
    .map(([code, anzahl]) => ({ code, name: landname(b, code), anzahl }));
}
