// Suche in den Podcast-Verzeichnissen direkt aus dem Browser (RAD-102): weltweit und deutsch, beide erlauben den Abruf
// aus fremden Seiten (CORS, gemessen 22.11.2026). Dieselbe Auswertung wie das Backend (services/podcast.py); die
// Adressen kommen von außen (Bauziel), nichts ist hier fest verdrahtet.
import type { Fundstueck } from "../typen";

export interface Verzeichnisadressen {
  /** Suche weltweit (Felder term, media, limit) */
  weltweit: string;
  /** Suche deutsch (Felder title, count) */
  deutsch: string;
}

type Roh = Record<string, unknown>;
const text = (w: unknown) => (typeof w === "string" ? w : "");

async function json(adresse: string, abruf: typeof fetch, signal?: AbortSignal): Promise<Roh> {
  const antwort = await abruf(adresse, { signal });
  if (!antwort.ok) throw new Error(`Verzeichnis antwortet ${antwort.status}`);
  return (await antwort.json()) as Roh;
}

async function weltweit(basis: string, suche: string, anzahl: number, abruf: typeof fetch, signal?: AbortSignal): Promise<Fundstueck[]> {
  const r = await json(`${basis}?${new URLSearchParams({ term: suche, media: "podcast", limit: String(anzahl) })}`, abruf, signal);
  return ((r.results as Roh[] | undefined) ?? []).map((t) => ({
    titel: text(t.collectionName), autor: text(t.artistName), feed: text(t.feedUrl),
    bild: text(t.artworkUrl600) || text(t.artworkUrl100), beschreibung: "", herkunft: "itunes",
  }));
}

async function deutsch(basis: string, suche: string, anzahl: number, abruf: typeof fetch, signal?: AbortSignal): Promise<Fundstueck[]> {
  const r = await json(`${basis}?${new URLSearchParams({ title: suche, count: String(anzahl) })}`, abruf, signal);
  return ((r.data as Roh[] | undefined) ?? []).map((t) => ({
    titel: text(t.title), autor: text(t.author), feed: text(t.xmlURL), bild: text(t.imgURL),
    beschreibung: text(t.description).slice(0, 500), herkunft: "fyyd",
  }));
}

/** beide Verzeichnisse zugleich; fällt eines aus, zählt das andere. Ohne Doppel (gleicher Feed), höchstens `anzahl`. */
export async function verzeichnisSuchen(adressen: Verzeichnisadressen, suche: string, signal?: AbortSignal, anzahl = 20,
                                        abruf: typeof fetch = (a, i) => fetch(a, i)): Promise<Fundstueck[]> {
  const teile = await Promise.allSettled([weltweit(adressen.weltweit, suche, anzahl, abruf, signal),
                                          deutsch(adressen.deutsch, suche, anzahl, abruf, signal)]);
  if (signal?.aborted) throw new DOMException("abgebrochen", "AbortError");
  const ok = teile.filter((t): t is PromiseFulfilledResult<Fundstueck[]> => t.status === "fulfilled");
  if (!ok.length) throw (teile[0] as PromiseRejectedResult).reason;
  const gesehen = new Set<string>();
  return ok.flatMap((t) => t.value).filter((f) => f.feed && !gesehen.has(f.feed) && gesehen.add(f.feed)).slice(0, anzahl);
}
