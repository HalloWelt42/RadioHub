// Podcastquelle der Webversion (RAD-102): alles im Browser des Geräts, ohne Backend. Gesucht wird direkt in den
// Verzeichnissen, die Feeds liest der Browser selbst (nur, wenn ihr Server das erlaubt: CORS), Abos, Ordner, Stelle und
// gehört liegen im Speicher des Browsers (ablage.ts). Die Folgen eines Feeds bleiben für die Sitzung im Speicher und
// kommen beim nächsten Start frisch. Speichern in der Ablage, Werbeerkennung und automatisches Aktualisieren gibt es
// hier nicht; das meldet `faehig`, und die Aufrufe werfen einen klaren Fehler.
import { Quellfehler } from "../../radio/statisch/fehler";
import type { Speicher } from "../../radio/statisch/speicher";
import type { Folgenwiedergabe, Podcastfaehigkeiten, Podcastquelle } from "../quelle";
import type { Abo, Aktualisierungsstand, Folge, Folgenabfrage, Folgenfilter, Folgenseite, Folgensortierung, Fundstueck, Ordner,
  Podcastsortierung } from "../typen";
import { ablageLesen, ablageSchreiben, kennung, type AboDaten, type Podcastablage } from "./ablage";
import { Feedfehler, feedLesen, type FeedFolge, type Feedinhalt } from "./feed";
import { verzeichnisSuchen, type Verzeichnisadressen } from "./verzeichnis";

export interface BrowserPodcastOptionen {
  speicher: Speicher;
  verzeichnis: Verzeichnisadressen;
  /** Text des Hinweises, wenn ein Feed sich nicht lesen lässt (je nach Ursache) */
  hinweis: (problem: Feedproblem) => string;
  abruf?: typeof fetch;
  parser?: () => DOMParser;
  /** so viele Feeds zugleich abrufen */
  gleichzeitig?: number;
  /** so lange darf die Prüfung eines Treffers der Suche dauern (ms), danach gilt er als nicht lesbar */
  pruefzeit?: number;
}

const SEITE = 50;
const PRUEFZEIT_MS = 8000;
const TAG_MS = 86_400_000;

/** eine Folge im Speicher der Sitzung: aus dem Feed, mit ihrer festen Kennung */
interface Eintrag extends FeedFolge {
  id: number;
  aboId: number;
}

/** warum ein Feed sich nicht lesen ließ: der Browser bekam keine Antwort (Server erlaubt den Abruf nicht oder ist nicht
 *  erreichbar), der Server meldete einen Fehler, oder der Inhalt ist kein lesbarer Feed */
export interface Feedproblem {
  art: "abruf" | "antwort" | "inhalt";
  detail: string;
}

interface Feedstand {
  folgen: Eintrag[];
  /** gesetzt, wenn der letzte Abruf scheiterte und keine Folgen da sind */
  problem: Feedproblem | null;
}

class Antwortfehler extends Error {
  constructor(readonly status: number) {
    super(`HTTP ${status}`);
  }
}

/** eine Webseite statt eines Feeds: als HTML angekündigt oder so begonnen */
function istWebseite(text: string, art: string | null): boolean {
  return /text\/html/i.test(art ?? "") || /^\s*(<!doctype html|<html)/i.test(text.slice(0, 200));
}

function mitFormatXml(adresse: string): string {
  const u = new URL(adresse);
  u.searchParams.set("format", "xml");
  return u.toString();
}

/** in dieser Reihenfolge versuchen: je Adresse (http zuerst als https) erst so, dann mit format=xml */
function versuche(feed: string): string[][] {
  const sicher = feed.startsWith("http://") ? [feed.replace(/^http:/, "https:"), feed] : [feed];
  return sicher.map((a) => [a, mitFormatXml(a)]);
}

/** der Anfang des Inhalts (erster Block), ohne den Rest zu laden */
async function anfangLesen(antwort: Response): Promise<string> {
  const leser = antwort.body?.getReader();
  if (!leser) return (await antwort.text()).slice(0, 512);
  try {
    const { value } = await leser.read();
    return value ? new TextDecoder().decode(value.slice(0, 512)) : "";
  } finally {
    void leser.cancel().catch(() => {});
  }
}

function problemAus(f: unknown): Feedproblem {
  if (f instanceof Antwortfehler) return { art: "antwort", detail: String(f.status) };
  if (f instanceof Feedfehler) return { art: "inhalt", detail: f.message };
  return { art: "abruf", detail: f instanceof Error ? f.message : String(f) };
}

export class FeedGesperrt extends Quellfehler {
  constructor(text: string) {
    super(text, 403);
    this.name = "FeedGesperrt";
  }
}

const NICHT_HIER = "In der Webversion nicht verfügbar";

export class BrowserPodcastquelle implements Podcastquelle {
  readonly faehig: Podcastfaehigkeiten = { abonnieren: true, speichern: false, herunterladen: true, herunterladenInListen: false,
                                           automatisch: false, werbung: false };
  private readonly speicher: Speicher;
  private readonly abruf: typeof fetch;
  private readonly parser: () => DOMParser;
  private readonly gleichzeitig: number;
  private readonly pruefzeit: number;
  private ablage: Podcastablage;
  /** Folgen je Abo für diese Sitzung; laufende Abrufe teilen sich ein Versprechen */
  private feeds = new Map<number, Feedstand>();
  private laeuft = new Map<number, Promise<Feedstand>>();
  /** zuletzt gefundene Podcasts je Feed: Name und Bild, falls der Feed selbst nicht lesbar ist */
  private funde = new Map<string, Fundstueck>();

  constructor(private readonly o: BrowserPodcastOptionen) {
    this.speicher = o.speicher;
    this.abruf = o.abruf ?? ((a, i) => fetch(a, i));
    this.parser = o.parser ?? (() => new DOMParser());
    this.gleichzeitig = o.gleichzeitig ?? 4;
    this.pruefzeit = o.pruefzeit ?? PRUEFZEIT_MS;
    this.ablage = ablageLesen(this.speicher);
  }

  // ----- Speicher und Feeds -------------------------------------------------------------------------------------------
  private aendern(arbeit: (a: Podcastablage) => void): void {
    const neu = structuredClone(this.ablage);
    arbeit(neu);
    ablageSchreiben(this.speicher, neu);   // wirft bei vollem oder gesperrtem Speicher: dann bleibt der alte Stand
    this.ablage = neu;
  }

  private aboDaten(id: number): AboDaten {
    const a = this.ablage.abos.find((x) => x.id === id);
    if (!a) throw new Quellfehler("Abo nicht gefunden", 404);
    return a;
  }

  /** Text des Feeds; ein http-Feed zuerst über https (die Seite selbst ist https, http sperrt der Browser). Manche
   *  Feed-Dienste zeigen Telefonen statt des Feeds eine Webseite (RAD-107: Logbuch:Netzpolitik am iPhone); dann noch
   *  einmal mit format=xml, der üblichen Weiche dieser Dienste für den rohen Feed. */
  private async feedText(feed: string): Promise<string> {
    let fehler: unknown = null;
    for (const reihe of versuche(feed)) {
      for (const versuch of reihe) {
        try {
          // immer frisch: ein Feed soll aktuell sein, und eine ältere Antwort im Zwischenspeicher ohne Freigabe (CORS)
          // würde den Abruf sonst sperren (RAD-107)
          const antwort = await this.abruf(versuch, { cache: "no-store" });
          if (!antwort.ok) {
            fehler = new Antwortfehler(antwort.status);
            break;
          }
          const text = await antwort.text();
          if (!istWebseite(text, antwort.headers.get("content-type"))) return text;
          fehler = new Feedfehler("Der Server liefert eine Webseite statt des Feeds");
        } catch (f) {
          fehler = f;
          break;
        }
      }
    }
    throw fehler;
  }

  private async lesen(feed: string): Promise<Feedinhalt> {
    return feedLesen(await this.feedText(feed), this.parser());
  }

  /** ob ein Feed im Browser lesbar ist, ohne ihn ganz zu laden: Freigabe (CORS), Antwort und Anfang des Inhalts. So
   *  bietet die Suche nur an, was hier auch geht (RAD-109). */
  private async lesbar(feed: string, signal?: AbortSignal): Promise<boolean> {
    for (const reihe of versuche(feed)) {
      for (const versuch of reihe) {
        const ab = new AbortController();
        const stopp = () => ab.abort();
        signal?.addEventListener("abort", stopp);
        const uhr = setTimeout(stopp, this.pruefzeit);
        try {
          const antwort = await this.abruf(versuch, { cache: "no-store", signal: ab.signal });
          if (!antwort.ok) return false;
          const anfang = await anfangLesen(antwort);
          if (!istWebseite(anfang, antwort.headers.get("content-type"))) return /<(\?xml|rss)\b/i.test(anfang);
        } catch {
          break;   // keine Antwort (gesperrt, nicht erreichbar, zu langsam): die nächste Adresse oder nicht lesbar
        } finally {
          clearTimeout(uhr);
          signal?.removeEventListener("abort", stopp);
          ab.abort();
        }
      }
    }
    return false;
  }

  private eintraege(aboId: number, feed: string, inhalt: Feedinhalt): Eintrag[] {
    // die Seite ist https: eine http-Datei sperrt der Browser oder hebt sie nur unzuverlässig an, also gleich https
    // (Kennung bleibt die aus dem Feed)
    return inhalt.folgen.map((f) => ({ ...f, adresse: f.adresse.replace(/^http:\/\//i, "https://"), id: kennung(`${feed}\n${f.guid}`), aboId }));
  }

  private feedHolen(id: number, frisch = false): Promise<Feedstand> {
    const da = this.feeds.get(id);
    if (da && !frisch) return Promise.resolve(da);
    const laufend = this.laeuft.get(id);
    if (laufend) return laufend;
    const abo = this.aboDaten(id);
    const arbeit = (async (): Promise<Feedstand> => {
      let inhalt: Feedinhalt;
      try {
        inhalt = await this.lesen(abo.feed);
      } catch (f) {
        const alt = this.feeds.get(id)?.folgen ?? [];
        const stand = { folgen: alt, problem: alt.length ? null : problemAus(f) };
        this.feeds.set(id, stand);
        return stand;
      } finally {
        this.laeuft.delete(id);
      }
      return this.uebernehmen(id, abo.feed, inhalt);
    })();
    this.laeuft.set(id, arbeit);
    return arbeit;
  }

  /** einen gelesenen Feed übernehmen: Folgen für die Sitzung, Angaben des Abos (Name, Bild) im Speicher; scheitert der
   *  Speicher, bleiben die Folgen trotzdem da */
  private uebernehmen(id: number, feed: string, inhalt: Feedinhalt): Feedstand {
    const stand: Feedstand = { folgen: this.eintraege(id, feed, inhalt), problem: null };
    this.feeds.set(id, stand);
    try {
      this.aendern((a) => {
        const x = a.abos.find((y) => y.id === id);
        if (!x) return;
        x.aktualisiert = new Date().toISOString();
        if (inhalt.titel) x.titel = inhalt.titel;
        if (inhalt.autor) x.autor = inhalt.autor;
        if (inhalt.beschreibung) x.beschreibung = inhalt.beschreibung;
        if (inhalt.bild) x.bild = inhalt.bild;
      });
    } catch {
      /* nur die Angaben des Abos bleiben die alten */
    }
    return stand;
  }

  /** mehrere Feeds, höchstens `gleichzeitig` auf einmal */
  private async alleHolen(ids: number[], frisch = false): Promise<void> {
    const offen = [...ids];
    const arbeiter = Array.from({ length: Math.min(this.gleichzeitig, offen.length) }, async () => {
      for (let id = offen.shift(); id !== undefined; id = offen.shift()) await this.feedHolen(id, frisch);
    });
    await Promise.all(arbeiter);
  }

  private stand(id: number) {
    return this.ablage.folgen[String(id)];
  }

  // ----- Abbildung auf das Datenmodell ----------------------------------------------------------------------------------
  private abo(d: AboDaten): Abo {
    const folgen = this.feeds.get(d.id)?.folgen ?? [];
    const jetzt = Date.now();
    const ungehoert = folgen.filter((f) => !this.stand(f.id)?.gehoert);
    const juenger = (ms: number) => ungehoert.filter((f) => f.datum && jetzt - Date.parse(f.datum) < ms).length;
    return {
      id: d.id, titel: d.titel || d.feed, autor: d.autor, beschreibung: d.beschreibung, bild: d.bild, feed: d.feed,
      autoLaden: false, angeheftet: d.angeheftet, sortierung: d.sortierung, ordnerId: d.ordnerId, aktualisiert: d.aktualisiert,
      folgen: folgen.length, gespeichert: 0, ungehoert: ungehoert.length, heuteUngehoert: juenger(TAG_MS), wocheUngehoert: juenger(7 * TAG_MS),
      dauerGesamt: folgen.reduce((s, f) => s + f.dauer, 0), werbungUeberspringen: false, werbungPruefen: false, werbungFolgen: 0,
    };
  }

  private folge(e: Eintrag, mitAbo: boolean): Folge {
    const s = this.stand(e.id);
    const abo = this.ablage.abos.find((a) => a.id === e.aboId);
    return {
      id: e.id, aboId: e.aboId, titel: e.titel, beschreibung: e.beschreibung, dauer: e.dauer, datum: e.datum,
      stelle: s?.stelle ?? 0, gehoert: !!s?.gehoert, gespeichert: false, ablagePfad: "", groesse: e.groesse,
      bild: e.bild || abo?.bild || "", werbung: { anzahl: 0, dauer: 0 },
      ...(mitAbo && abo ? { aboTitel: abo.titel || abo.feed } : {}),
    };
  }

  private passt(e: Eintrag, filter: Folgenfilter): boolean {
    const gehoert = !!this.stand(e.id)?.gehoert;
    const alter = e.datum ? Date.now() - Date.parse(e.datum) : Infinity;
    switch (filter) {
      case "heute": return alter < TAG_MS;
      case "woche": return alter < 7 * TAG_MS;
      case "ungehoert": return !gehoert;
      case "gehoert": return gehoert;
      case "gespeichert": return false;
      default: return true;
    }
  }

  private static vergleich(sortierung: Folgensortierung): (a: Eintrag, b: Eintrag) => number {
    if (sortierung === "titel") return (a, b) => a.titel.localeCompare(b.titel);
    if (sortierung === "dauer") return (a, b) => a.dauer - b.dauer;
    return (a, b) => (a.datum < b.datum ? -1 : a.datum > b.datum ? 1 : 0);
  }

  private async auswahl(a: Folgenabfrage, suche = ""): Promise<Folgenseite> {
    const ids = a.abos?.length ? a.abos : this.ablage.abos.map((x) => x.id);
    await this.alleHolen(ids);
    // ein gewähltes Abo, dessen Feed nicht lesbar ist: Hinweis statt einer leeren Liste (über alle Abos fehlt es nur)
    const problem = a.abos?.length === 1 ? this.feeds.get(ids[0])?.problem : null;
    if (problem) throw new FeedGesperrt(this.o.hinweis(problem));
    const text = suche.trim().toLocaleLowerCase();
    const richtung = a.absteigend === false ? 1 : -1;
    const ordnung = BrowserPodcastquelle.vergleich(a.sortierung ?? "datum");
    const alle = ids.flatMap((id) => this.feeds.get(id)?.folgen ?? [])
      .filter((e) => this.passt(e, a.filter ?? "alle"))
      .filter((e) => !text || e.titel.toLocaleLowerCase().includes(text) || e.beschreibung.toLocaleLowerCase().includes(text))
      .sort((x, y) => richtung * ordnung(x, y));
    const stelle = Math.max(0, Number(a.nach ?? 0) || 0);
    const anzahl = a.anzahl ?? SEITE;
    const folgen = alle.slice(stelle, stelle + anzahl).map((e) => this.folge(e, ids.length > 1));
    const ende = stelle + folgen.length;
    return { folgen, gesamt: alle.length, weiter: folgen.length && ende < alle.length ? String(ende) : null };
  }

  private eintrag(id: number): Eintrag | null {
    for (const f of this.feeds.values()) {
      const e = f.folgen.find((x) => x.id === id);
      if (e) return e;
    }
    return null;
  }

  // ----- Abos ----------------------------------------------------------------------------------------------------------
  async abos(): Promise<Abo[]> {
    await this.alleHolen(this.ablage.abos.map((a) => a.id));
    return this.ablage.abos.map((a) => this.abo(a));
  }

  async abonnieren(feed: string): Promise<Abo> {
    const adresse = feed.trim();
    if (!/^https?:\/\//i.test(adresse)) throw new Quellfehler("Keine gültige Adresse eines Feeds", 422);
    const id = kennung(adresse);
    if (this.ablage.abos.some((a) => a.id === id)) {
      await this.feedHolen(id, true);
      return this.abo(this.aboDaten(id));
    }
    // ein Feed, den der Browser nicht lesen kann, wird gar nicht erst abonniert (RAD-109): sonst stünde ein Abo ohne
    // Folgen da; der Hinweis sagt warum
    let inhalt: Feedinhalt;
    try {
      inhalt = await this.lesen(adresse);
    } catch (f) {
      throw new FeedGesperrt(this.o.hinweis(problemAus(f)));
    }
    const fund = this.funde.get(adresse);
    this.aendern((a) => a.abos.push({ id, feed: adresse, titel: fund?.titel ?? "", autor: fund?.autor ?? "",
                                      beschreibung: fund?.beschreibung ?? "", bild: fund?.bild ?? "", angeheftet: false,
                                      sortierung: "", ordnerId: null, aktualisiert: "" }));
    this.uebernehmen(id, adresse, inhalt);
    return this.abo(this.aboDaten(id));
  }

  async abbestellen(id: number): Promise<void> {
    this.aendern((a) => {
      a.abos = a.abos.filter((x) => x.id !== id);
      for (const [k, v] of Object.entries(a.folgen)) if (v.a === id) delete a.folgen[k];
    });
    this.feeds.delete(id);
  }

  async ordnen(ids: number[]): Promise<void> {
    this.aendern((a) => {
      const rang = new Map(ids.map((id, i) => [id, i]));
      a.abos.sort((x, y) => (rang.get(x.id) ?? Infinity) - (rang.get(y.id) ?? Infinity));
    });
  }

  async aktualisieren(id?: number): Promise<number> {
    const ids = id == null ? this.ablage.abos.map((a) => a.id) : [id];
    const vorher = new Set(ids.flatMap((x) => this.feeds.get(x)?.folgen.map((f) => f.id) ?? []));
    // nur Abos, deren Folgen schon einmal da waren, zählen neue; ein bisher nicht lesbarer Feed bringt keine "neuen"
    const bekannt = new Set(ids.filter((x) => this.feeds.get(x)?.folgen.length));
    await this.alleHolen(ids, true);
    return ids.filter((x) => bekannt.has(x)).flatMap((x) => this.feeds.get(x)?.folgen ?? []).filter((f) => !vorher.has(f.id)).length;
  }

  async aktualisierungsstand(): Promise<Aktualisierungsstand> {
    return { naechste: null, abstandStunden: 0, automatisch: false };
  }

  async autoLaden(): Promise<void> {
    throw new Quellfehler(NICHT_HIER, 501);
  }

  async anheften(id: number, an: boolean): Promise<void> {
    this.aboDaten(id);
    this.aendern((a) => void (a.abos.find((x) => x.id === id)!.angeheftet = an));
  }

  async sortierungSetzen(id: number, sortierung: Podcastsortierung | ""): Promise<void> {
    this.aboDaten(id);
    this.aendern((a) => void (a.abos.find((x) => x.id === id)!.sortierung = sortierung));
  }

  // ----- Ordner --------------------------------------------------------------------------------------------------------
  async ordner(): Promise<Ordner[]> {
    return this.ablage.ordner.map((o) => ({ ...o }));
  }

  async ordnerAnlegen(name: string): Promise<Ordner> {
    const neu: Ordner = { id: crypto.randomUUID(), name: name.trim() || "Ordner", offen: true };
    this.aendern((a) => a.ordner.push(neu));
    return { ...neu };
  }

  async ordnerAendern(id: string, teil: Partial<Pick<Ordner, "name" | "offen">>): Promise<Ordner> {
    if (!this.ablage.ordner.some((o) => o.id === id)) throw new Quellfehler("Ordner nicht gefunden", 404);
    this.aendern((a) => Object.assign(a.ordner.find((o) => o.id === id)!, teil));
    return { ...this.ablage.ordner.find((o) => o.id === id)! };
  }

  async ordnerLoeschen(id: string): Promise<number> {
    const geloest = this.ablage.abos.filter((x) => x.ordnerId === id).length;
    this.aendern((a) => {
      a.ordner = a.ordner.filter((o) => o.id !== id);
      for (const x of a.abos) if (x.ordnerId === id) x.ordnerId = null;
    });
    return geloest;
  }

  async ordnerOrdnen(ids: string[]): Promise<void> {
    this.aendern((a) => {
      const rang = new Map(ids.map((id, i) => [id, i]));
      a.ordner.sort((x, y) => (rang.get(x.id) ?? Infinity) - (rang.get(y.id) ?? Infinity));
    });
  }

  async zuordnen(aboId: number, ordnerId: string | null): Promise<void> {
    this.aboDaten(aboId);
    this.aendern((a) => void (a.abos.find((x) => x.id === aboId)!.ordnerId = ordnerId));
  }

  /** Treffer der Verzeichnisse, aber nur die, deren Feed der Browser lesen kann (RAD-109); geprüft wird zugleich, in
   *  der Reihenfolge der Verzeichnisse */
  async suchen(text: string, signal?: AbortSignal): Promise<Fundstueck[]> {
    const funde = await verzeichnisSuchen(this.o.verzeichnis, text, signal, 20, this.abruf);
    const offen = [...funde.keys()];
    const gut = new Array<boolean>(funde.length).fill(false);
    await Promise.all(Array.from({ length: Math.min(this.gleichzeitig * 2, offen.length) }, async () => {
      for (let i = offen.shift(); i !== undefined; i = offen.shift()) gut[i] = await this.lesbar(funde[i].feed, signal);
    }));
    if (signal?.aborted) throw new DOMException("abgebrochen", "AbortError");
    const lesbare = funde.filter((_, i) => gut[i]);
    for (const f of lesbare) this.funde.set(f.feed, f);
    return lesbare;
  }

  // ----- Folgen --------------------------------------------------------------------------------------------------------
  folgen(abfrage: Folgenabfrage): Promise<Folgenseite> {
    return this.auswahl(abfrage);
  }

  async einzelfolge(id: number): Promise<Folge | null> {
    if (!this.eintrag(id)) await this.alleHolen(this.ablage.abos.map((a) => a.id));
    const e = this.eintrag(id);
    return e ? this.folge(e, false) : null;
  }

  folgenSuchen(text: string, abfrage: Folgenabfrage): Promise<Folgenseite> {
    return this.auswahl(abfrage, text);
  }

  private folgeAendern(id: number, teil: { stelle?: number; gehoert?: boolean }): void {
    const e = this.eintrag(id);
    if (!e) throw new Quellfehler("Folge nicht gefunden", 404);
    this.aendern((a) => {
      const alt = a.folgen[String(id)] ?? { a: e.aboId, stelle: 0, gehoert: false };
      const neu = { ...alt, ...teil };
      if (!neu.stelle && !neu.gehoert) delete a.folgen[String(id)];   // nichts zu merken: kein Eintrag
      else a.folgen[String(id)] = neu;
    });
  }

  async gehoert(id: number, an: boolean): Promise<void> {
    this.folgeAendern(id, an ? { gehoert: true, stelle: 0 } : { gehoert: false });
  }

  async stelleMerken(id: number, sekunden: number): Promise<void> {
    this.folgeAendern(id, { stelle: Math.max(0, Math.round(sekunden)) });
  }

  async speichern(): Promise<void> {
    throw new Quellfehler(NICHT_HIER, 501);
  }

  dateiAdresse(id: number): string {
    return this.eintrag(id)?.adresse ?? "";
  }

  async wiedergabe(f: Folge, liste: Folge[] = [f]): Promise<Folgenwiedergabe> {
    const abo = this.ablage.abos.find((a) => a.id === f.aboId);
    const roh = (x: Folge) => {
      const e = this.eintrag(x.id);
      const s = this.stand(x.id);
      return e ? { id: e.id, podcast_id: e.aboId, title: e.titel, description: e.beschreibung, duration: e.dauer,
                   published_at: e.datum, remote_audio_url: e.adresse, image_url: e.bild, resume_position: s?.stelle ?? 0,
                   is_played: !!s?.gehoert, is_downloaded: false } : null;
    };
    const folge = roh(f);
    if (!folge) throw new Quellfehler("Folge nicht gefunden", 404);
    const rohListe = liste.map((x) => (x.id === f.id ? folge : roh(x))).filter((x): x is NonNullable<typeof x> => !!x);
    return {
      folge, liste: rohListe.length ? rohListe : [folge],
      abo: { id: f.aboId, title: abo?.titel || abo?.feed || "", author: abo?.autor ?? "", image_url: abo?.bild ?? "" },
    };
  }
}
