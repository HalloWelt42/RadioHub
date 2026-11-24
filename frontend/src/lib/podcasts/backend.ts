// Podcastquelle gegen das eigene Backend (/api/podcasts): bildet dessen Antworten auf das Datenmodell ab (typen.ts).
// Seiten zählt das Backend ab einer Stelle (offset); der Zeiger der nächsten Seite ist diese Stelle als Text.
// Bilder kommen über die eigene App, nie direkt von fremden Servern.
import type { Folgenwiedergabe, Podcastfaehigkeiten, Podcastquelle } from "./quelle";
import { PODCASTSORTIERUNG, type Abo, type Aktualisierungsstand, type Folge, type Folgenabfrage, type Folgendatei, type Folgenfilter, type Folgenseite,
  type Folgensortierung, type Fundstueck, type Ordner, type Podcastsortierung } from "./typen";

/** der Teil von lib/api.js, den die Quelle braucht */
export interface Anfrager {
  fetch(pfad: string, optionen?: RequestInit): Promise<any>;
  baseUrl: string;
}

type Roh = Record<string, any>;

const FILTER: Record<Folgenfilter, string> = {
  alle: "all", heute: "today", woche: "week", ungehoert: "unplayed", gespeichert: "downloaded", gehoert: "played",
};
const SORTIERUNG: Record<Folgensortierung, string> = { datum: "published_at", titel: "title", dauer: "duration" };
export const SEITE = 50;

const text = (w: unknown) => (typeof w === "string" ? w : "");
const zahl = (w: unknown) => (typeof w === "number" && Number.isFinite(w) ? w : 0);

export class BackendPodcastquelle implements Podcastquelle {
  readonly faehig: Podcastfaehigkeiten = { abonnieren: true, speichern: true, herunterladen: true, herunterladenInListen: true,
                                           automatisch: true, werbung: true, transkript: true };
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

  /** Cover eines Abos für eine Folge ohne eigenes Bild; leer, wenn das Abo bekanntlich keins hat (RAD-85: dann fragt
   *  die Oberfläche nichts an und zeigt das Kürzel, statt einen Fehler in der Konsole zu erzeugen) */
  private coverVon(aboId: number): string {
    return this.rohAbos.get(aboId)?.hat_bild === false ? "" : this.aboBild(aboId);
  }

  private abo(r: Roh): Abo {
    this.rohAbos.set(r.id, r);
    return {
      id: r.id, titel: text(r.title), autor: text(r.author), beschreibung: text(r.description), bild: r.hat_bild === false ? "" : this.aboBild(r.id),
      feed: text(r.feed_url), autoLaden: !!r.auto_download, angeheftet: !!r.angeheftet,
      sortierung: PODCASTSORTIERUNG.includes(r.sortierung) ? r.sortierung : "", ordnerId: r.ordner_id || null, aktualisiert: text(r.last_updated),
      folgen: zahl(r.episode_count), gespeichert: zahl(r.downloaded_count), ungehoert: zahl(r.unplayed_count), heuteUngehoert: zahl(r.today_unplayed),
      wocheUngehoert: zahl(r.week_unplayed), monatUngehoert: zahl(r.month_unplayed), dauerGesamt: zahl(r.total_duration),
      werbungUeberspringen: r.werbung_ueberspringen === undefined ? true : !!r.werbung_ueberspringen, werbungPruefen: !!r.werbung_pruefen,
      werbungFolgen: zahl(r.werbung_folgen),
    };
  }

  private folge(r: Roh): Folge {
    this.rohFolgen.set(r.id, r);
    return {
      id: r.id, aboId: r.podcast_id, titel: text(r.title), beschreibung: text(r.description), dauer: zahl(r.duration),
      datum: text(r.published_at), stelle: zahl(r.resume_position), gehoert: !!r.is_played, gespeichert: !!r.is_downloaded,
      ablagePfad: r.is_downloaded ? text(r.local_path) : "",
      groesse: zahl(r.file_size), werbung: { anzahl: zahl(r.werbung_anzahl), dauer: zahl(r.werbung_dauer) }, bild: r.image_url || r.local_image_path ? this.folgenBild(r.id) : this.coverVon(r.podcast_id),
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

  async aktualisieren(id?: number): Promise<number> {
    const r = await this.api.fetch(id == null ? "/api/podcasts/refresh-all" : `/api/podcasts/${id}/refresh`, { method: "POST" });
    return zahl(r?.new_episodes);
  }

  async aktualisierungsstand(): Promise<Aktualisierungsstand> {
    const r = await this.api.fetch("/api/podcasts/refresh-status");
    return { naechste: r.next_refresh_at ?? null, abstandStunden: zahl(r.interval_hours), automatisch: !!r.auto_refresh };
  }

  async anheften(id: number, an: boolean): Promise<void> {
    await this.api.fetch(`/api/podcasts/${id}/anheften`, { method: "PUT", body: JSON.stringify({ an }) });
  }

  async sortierungSetzen(id: number, sortierung: Podcastsortierung | ""): Promise<void> {
    await this.api.fetch(`/api/podcasts/${id}/sortierung`, { method: "PUT", body: JSON.stringify({ sortierung }) });
  }

  // ----- Ordner ----------------------------------------------------------------------------------------------------
  private static ordner(r: Roh): Ordner {
    return { id: String(r.id), name: text(r.name), offen: r.offen !== false };
  }

  async ordner(): Promise<Ordner[]> {
    return ((await this.api.fetch("/api/podcast-ordner")).ordner ?? []).map((r: Roh) => BackendPodcastquelle.ordner(r));
  }

  async ordnerAnlegen(name: string): Promise<Ordner> {
    return BackendPodcastquelle.ordner(await this.api.fetch("/api/podcast-ordner", { method: "POST", body: JSON.stringify({ name }) }));
  }

  async ordnerAendern(id: string, teil: Partial<Pick<Ordner, "name" | "offen">>): Promise<Ordner> {
    return BackendPodcastquelle.ordner(await this.api.fetch(`/api/podcast-ordner/${id}`, { method: "PUT", body: JSON.stringify(teil) }));
  }

  async ordnerLoeschen(id: string): Promise<number> {
    return zahl((await this.api.fetch(`/api/podcast-ordner/${id}`, { method: "DELETE" })).geloest);
  }

  async ordnerOrdnen(ids: string[]): Promise<void> {
    await this.api.fetch("/api/podcast-ordner/reihenfolge", { method: "PUT", body: JSON.stringify({ ids }) });
  }

  async zuordnen(aboId: number, ordnerId: string | null): Promise<void> {
    await this.api.fetch(`/api/podcast-ordner/abo/${aboId}`, { method: "PUT", body: JSON.stringify({ ordner_id: ordnerId }) });
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

  async einzelfolge(id: number): Promise<Folge | null> {
    try {
      return this.folge(await this.api.fetch(`/api/podcasts/episodes/${id}`));
    } catch {
      return null;
    }
  }

  /** Suche in Titel, Beschreibung und Transkript, mit derselben Abo-Wahl, demselben Filter und derselben Sortierung wie
   *  die Liste ohne Suchtext (RAD-44: vorher suchte sie über alle Abos) */
  async folgenSuchen(suchtext: string, a: Folgenabfrage, signal?: AbortSignal): Promise<Folgenseite> {
    const { stelle, suche } = BackendPodcastquelle.parameter(a);
    suche.set("q", suchtext);
    if (a.abos?.length) suche.set("podcast_ids", a.abos.join(","));
    return this.seite(await this.api.fetch(`/api/podcasts/episodes/all?${suche}`, { signal }), stelle);
  }

  async gehoert(id: number, an: boolean): Promise<void> {
    await this.api.fetch(`/api/podcasts/episodes/${id}/${an ? "played" : "unplayed"}`, { method: "PUT" });
  }

  async stelleMerken(id: number, sekunden: number): Promise<void> {
    await this.api.fetch(`/api/podcasts/episodes/${id}/position`, { method: "PUT",
      body: JSON.stringify({ position_seconds: Math.max(0, Math.round(sekunden)) }) });
  }

  dateiAdresse(id: number): string {
    return `${this.api.baseUrl}/api/podcasts/episodes/${id}/datei`;
  }

  async speichern(id: number, an: boolean): Promise<void> {
    await this.api.fetch(`/api/podcasts/episodes/${id}/download`, { method: an ? "POST" : "DELETE" });
  }

  async dateien(id: number): Promise<Folgendatei[]> {
    const r = await this.api.fetch(`/api/podcasts/episodes/${id}/dateien`);
    return (r.dateien ?? []).map((d: Roh) => ({ pfad: text(d.pfad), groesse: zahl(d.groesse) }));
  }

  fassungMerken(id: number, sprache: string): void {
    const roh = this.rohFolgen.get(id);
    if (roh) roh.fassung = sprache;
  }

  async wiedergabe(f: Folge, liste: Folge[] = [f]): Promise<Folgenwiedergabe> {
    const folge = this.rohFolgen.get(f.id) ?? (await this.api.fetch(`/api/podcasts/episodes/${f.id}`));
    let abo = this.rohAbos.get(f.aboId);
    if (!abo) {
      await this.abos();
      abo = this.rohAbos.get(f.aboId) ?? { id: f.aboId };
    }
    const roh = liste.map((x) => (x.id === f.id ? folge : this.rohFolgen.get(x.id))).filter((x): x is Roh => !!x);
    return { folge, abo, liste: roh.length ? roh : [folge] };
  }
}
