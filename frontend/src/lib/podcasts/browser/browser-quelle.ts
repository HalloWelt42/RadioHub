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
  /** Text des Hinweises, wenn ein Feed den Abruf aus dem Browser nicht erlaubt */
  gesperrtText: () => string;
  abruf?: typeof fetch;
  parser?: () => DOMParser;
  /** so viele Feeds zugleich abrufen */
  gleichzeitig?: number;
}

const SEITE = 50;
const TAG_MS = 86_400_000;

/** eine Folge im Speicher der Sitzung: aus dem Feed, mit ihrer festen Kennung */
interface Eintrag extends FeedFolge {
  id: number;
  aboId: number;
}

interface Feedstand {
  folgen: Eintrag[];
  /** der Server erlaubt den Abruf aus dem Browser nicht (oder der Feed ist nicht lesbar) */
  gesperrt: boolean;
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

  /** Text des Feeds; ein http-Feed zuerst über https (die Seite selbst ist https, http sperrt der Browser) */
  private async feedText(feed: string): Promise<string> {
    const versuche = feed.startsWith("http://") ? [feed.replace(/^http:/, "https:"), feed] : [feed];
    let fehler: unknown = null;
    for (const adresse of versuche) {
      try {
        const antwort = await this.abruf(adresse);
        if (antwort.ok) return await antwort.text();
        fehler = new Feedfehler(`Feed antwortet ${antwort.status}`);
      } catch (f) {
        fehler = f;
      }
    }
    throw fehler;
  }

  private async lesen(feed: string): Promise<Feedinhalt> {
    return feedLesen(await this.feedText(feed), this.parser());
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
      try {
        const inhalt = await this.lesen(abo.feed);
        const stand = { folgen: this.eintraege(id, abo.feed, inhalt), gesperrt: false };
        this.feeds.set(id, stand);
        this.aendern((a) => {
          const x = a.abos.find((y) => y.id === id);
          if (!x) return;
          x.aktualisiert = new Date().toISOString();
          // Angaben des Feeds nachziehen (Name, Bild), wenn er sie hat
          if (inhalt.titel) x.titel = inhalt.titel;
          if (inhalt.autor) x.autor = inhalt.autor;
          if (inhalt.beschreibung) x.beschreibung = inhalt.beschreibung;
          if (inhalt.bild) x.bild = inhalt.bild;
        });
        return stand;
      } catch {
        const stand = { folgen: this.feeds.get(id)?.folgen ?? [], gesperrt: !this.feeds.get(id)?.folgen.length };
        this.feeds.set(id, stand);
        return stand;
      } finally {
        this.laeuft.delete(id);
      }
    })();
    this.laeuft.set(id, arbeit);
    return arbeit;
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
    if (a.abos?.length === 1 && this.feeds.get(ids[0])?.gesperrt) throw new FeedGesperrt(this.o.gesperrtText());
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
    if (!this.ablage.abos.some((a) => a.id === id)) {
      const fund = this.funde.get(adresse);
      this.aendern((a) => a.abos.push({ id, feed: adresse, titel: fund?.titel ?? "", autor: fund?.autor ?? "",
                                        beschreibung: fund?.beschreibung ?? "", bild: fund?.bild ?? "", angeheftet: false,
                                        sortierung: "", ordnerId: null, aktualisiert: "" }));
    }
    await this.feedHolen(id, true);
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

  async aktualisieren(id?: number): Promise<void> {
    await this.alleHolen(id == null ? this.ablage.abos.map((a) => a.id) : [id], true);
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

  async suchen(text: string, signal?: AbortSignal): Promise<Fundstueck[]> {
    const funde = await verzeichnisSuchen(this.o.verzeichnis, text, signal, 20, this.abruf);
    for (const f of funde) this.funde.set(f.feed, f);
    return funde;
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
