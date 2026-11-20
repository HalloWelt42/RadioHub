// Podcastquelle gegen das eigene Backend (/api/podcasts): bildet dessen Antworten auf das Datenmodell ab (typen.ts).
// Seiten zählt das Backend ab einer Stelle (offset); der Zeiger der nächsten Seite ist diese Stelle als Text.
// Bilder kommen über die eigene App, nie direkt von fremden Servern.
import type { Folgenwiedergabe, Podcastfaehigkeiten, Podcastquelle } from "./quelle";
import type { Abo, Aktualisierungsstand, Folge, Folgenabfrage, Folgenfilter, Folgenseite, Folgensortierung, Fundstueck,
  Merkbericht } from "./typen";

/** der Teil von lib/api.js, den die Quelle braucht */
export interface Anfrager {
  fetch(pfad: string, optionen?: RequestInit): Promise<any>;
  baseUrl: string;
}

type Roh = Record<string, any>;

const FILTER: Record<Folgenfilter, string> = {
  alle: "all", heute: "today", woche: "week", ungehoert: "unplayed", gemerkt: "downloaded", gehoert: "played",
};
const SORTIERUNG: Record<Folgensortierung, string> = { datum: "published_at", titel: "title", dauer: "duration" };
export const SEITE = 50;

const text = (w: unknown) => (typeof w === "string" ? w : "");
const zahl = (w: unknown) => (typeof w === "number" && Number.isFinite(w) ? w : 0);

export class BackendPodcastquelle implements Podcastquelle {
  readonly faehig: Podcastfaehigkeiten = { abonnieren: true, merken: true, automatisch: true };
  /** zuletzt gesehene Rohdaten je Kennung: der Spieler braucht sie in seinem Format */
  private rohFolgen = new Map<number, Roh>();
  private rohAbos = new Map<number, Roh>();

  constructor(private readonly api: Anfrager) {}

  aboBild(id: number): string {
    return `${this.api.baseUrl}/api/podcasts/${id}/image`;
  }

  folgenBild(id: number): string {
    return `${this.api.baseUrl}/api/podcasts/episodes/${id}/image`;
  }

  private abo(r: Roh): Abo {
    this.rohAbos.set(r.id, r);
    return {
      id: r.id, titel: text(r.title), autor: text(r.author), beschreibung: text(r.description), bild: this.aboBild(r.id),
      feed: text(r.feed_url), autoLaden: !!r.auto_download, aktualisiert: text(r.last_updated), folgen: zahl(r.episode_count),
      geladen: zahl(r.downloaded_count), ungehoert: zahl(r.unplayed_count), heuteUngehoert: zahl(r.today_unplayed),
      wocheUngehoert: zahl(r.week_unplayed), dauerGesamt: zahl(r.total_duration),
    };
  }

  private folge(r: Roh): Folge {
    this.rohFolgen.set(r.id, r);
    return {
      id: r.id, aboId: r.podcast_id, titel: text(r.title), beschreibung: text(r.description), dauer: zahl(r.duration),
      datum: text(r.published_at), stelle: zahl(r.resume_position), gehoert: !!r.is_played, gemerkt: !!r.is_downloaded,
      groesse: zahl(r.file_size), bild: r.image_url || r.local_image_path ? this.folgenBild(r.id) : this.aboBild(r.podcast_id),
      ...(r.podcast_title ? { aboTitel: text(r.podcast_title) } : {}),
    };
  }

  private seite(antwort: Roh, stelle: number): Folgenseite {
    const folgen = (antwort.episodes ?? []).map((r: Roh) => this.folge(r));
    const gesamt = zahl(antwort.total);
    const ende = stelle + folgen.length;
    return { folgen, gesamt, weiter: folgen.length && ende < gesamt ? String(ende) : null };
  }

  private static parameter(a: Folgenabfrage): { stelle: number; suche: URLSearchParams } {
    const stelle = Math.max(0, Number(a.nach ?? 0) || 0);
    const suche = new URLSearchParams({
      limit: String(a.anzahl ?? SEITE), offset: String(stelle), filter_status: FILTER[a.filter ?? "alle"],
      sort_by: SORTIERUNG[a.sortierung ?? "datum"], sort_order: a.absteigend === false ? "asc" : "desc",
    });
    return { stelle, suche };
  }

  // ----- Abos ------------------------------------------------------------------------------------------------------
  async abos(): Promise<Abo[]> {
    const r = await this.api.fetch("/api/podcasts/subscriptions");
    return (r.subscriptions ?? []).map((a: Roh) => this.abo(a));
  }

  async abonnieren(feed: string): Promise<Abo> {
    const r = await this.api.fetch("/api/podcasts/subscribe", { method: "POST", body: JSON.stringify({ feed_url: feed }) });
    return this.abo(r.podcast);
  }

  async abbestellen(id: number): Promise<void> {
    await this.api.fetch(`/api/podcasts/${id}`, { method: "DELETE" });
  }

  async ordnen(ids: number[]): Promise<void> {
    await this.api.fetch("/api/podcasts/order", { method: "PUT", body: JSON.stringify({ ordered_ids: ids }) });
  }

  async aktualisieren(id?: number): Promise<void> {
    await this.api.fetch(id == null ? "/api/podcasts/refresh-all" : `/api/podcasts/${id}/refresh`, { method: "POST" });
  }

  async aktualisierungsstand(): Promise<Aktualisierungsstand> {
    const r = await this.api.fetch("/api/podcasts/refresh-status");
    return { naechste: r.next_refresh_at ?? null, abstandStunden: zahl(r.interval_hours), automatisch: !!r.auto_refresh };
  }

  async autoLaden(id: number, an: boolean): Promise<void> {
    await this.api.fetch(`/api/podcasts/${id}/auto-download`, { method: "PUT", body: JSON.stringify({ enabled: an }) });
  }

  async suchen(suchtext: string, signal?: AbortSignal): Promise<Fundstueck[]> {
    const r = await this.api.fetch(`/api/podcasts/search?${new URLSearchParams({ q: suchtext, source: "all", limit: "20" })}`, { signal });
    return (r.results ?? []).map((t: Roh) => ({
      titel: text(t.title), autor: text(t.author), bild: text(t.image_url), feed: text(t.feed_url),
      beschreibung: text(t.description), herkunft: text(t.source),
    }));
  }

  // ----- Folgen ----------------------------------------------------------------------------------------------------
  async folgen(a: Folgenabfrage, signal?: AbortSignal): Promise<Folgenseite> {
    const { stelle, suche } = BackendPodcastquelle.parameter(a);
    const nurEins = a.abos?.length === 1;
    if (!nurEins && a.abos?.length) suche.set("podcast_ids", a.abos.join(","));
    const pfad = nurEins ? `/api/podcasts/${a.abos![0]}/episodes` : "/api/podcasts/episodes/all";
    return this.seite(await this.api.fetch(`${pfad}?${suche}`, { signal }), stelle);
  }

  async folgenSuchen(suchtext: string, a: Folgenabfrage, signal?: AbortSignal): Promise<Folgenseite> {
    const stelle = Math.max(0, Number(a.nach ?? 0) || 0);
    const suche = new URLSearchParams({ q: suchtext, limit: String(a.anzahl ?? SEITE), offset: String(stelle), search_in: "all" });
    return this.seite(await this.api.fetch(`/api/podcasts/episodes/search?${suche}`, { signal }), stelle);
  }

  async gehoert(id: number, an: boolean): Promise<void> {
    await this.api.fetch(`/api/podcasts/episodes/${id}/${an ? "played" : "unplayed"}`, { method: "PUT" });
  }

  async stelleMerken(id: number, sekunden: number): Promise<void> {
    await this.api.fetch(`/api/podcasts/episodes/${id}/position`, { method: "PUT",
      body: JSON.stringify({ position_seconds: Math.max(0, Math.round(sekunden)) }) });
  }

  async merken(id: number, an: boolean): Promise<void> {
    await this.api.fetch(`/api/podcasts/episodes/${id}/download`, { method: an ? "POST" : "DELETE" });
  }

  async mehrereMerken(aboId: number, ids: number[]): Promise<Merkbericht> {
    const r = await this.api.fetch(`/api/podcasts/${aboId}/download-batch`, { method: "POST", body: JSON.stringify({ episode_ids: ids }) });
    return { gesamt: zahl(r.total), neu: zahl(r.success), schonDa: zahl(r.skipped), fehler: zahl(r.failed) };
  }

  async wiedergabe(f: Folge): Promise<Folgenwiedergabe> {
    const folge = this.rohFolgen.get(f.id) ?? (await this.api.fetch(`/api/podcasts/episodes/${f.id}`));
    let abo = this.rohAbos.get(f.aboId);
    if (!abo) {
      await this.abos();
      abo = this.rohAbos.get(f.aboId) ?? { id: f.aboId };
    }
    return { folge, abo };
  }
}
