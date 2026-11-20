// Senderquelle gegen das eigene Backend (RAD-7): die Schnittstelle /api/radio für Liste, Regeln, Ausgeblendete, Sperren,
// Freigaben und Abgleich; für eigene Angaben (Favoriten, Bewertungen, Kategorien, eigene Adresse) und Messungen die
// bisherigen Wege des Backends, bis sie in die Senderquelle wandern. Ohne Bausteine der Oberfläche: was die App danach
// tun muss (Favoriten im Zustand nachziehen), bekommt sie über `beiFavoriten` mit.
import { netz, Netzfehler, type Anfrage } from "./netz";
import {
  ausEintrag, type Faehigkeiten, type Kategorie, type LandZahl, type Messwert, type Senderquelle, type Steckbrief, type TitelGuete,
  type Wiedergabesender,
} from "./quelle";
import {
  WEGE, type Abfrageergebnis, type Abgleichstand, type AusgeblendetAnfrage, type AusgeblendetSeite, type Bewertung,
  type Kandidat, type KandidatenArt, type RegelAenderung, type RegelEntwurf, type RegelFolgen, type Regeluebersicht,
  type RegelVorschau, type SenderEintrag, type Sichtbarkeit, type StationQuery,
} from "./typen";

/** Ein Sender, wie ihn der bisherige Weg /api/stations/<uuid> liefert (nur die genutzten Felder). */
interface RohSender {
  error?: string;
  name?: string;
  url?: string;
  url_resolved?: string;
  favicon?: string;
  country?: string;
  countrycode?: string;
  tags?: string;
  codec?: string;
  bitrate?: number;
  homepage?: string;
}

interface Messung {
  bitrate?: number;
  codec?: string;
  icy?: boolean;
  icy_quality?: "good" | "poor" | null;
}

export interface BackendOptionen {
  anfrage?: Anfrage;
  /** nach jeder Änderung eines Favoriten (die App lädt ihre Liste der Favoriten neu) */
  beiFavoriten?: () => void;
  /** so lange nach dem Start, bis der Messwert gelesen wird */
  messenNachMs?: number;
}

const kodiert = encodeURIComponent;
const GUETE: Record<string, TitelGuete> = { good: "genau", poor: "ungenau" };

/** Warten, abbrechbar */
function warten(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((fertig, abbruch) => {
    const uhr = setTimeout(fertig, ms);
    signal?.addEventListener("abort", () => { clearTimeout(uhr); abbruch(new DOMException("abgebrochen", "AbortError")); }, { once: true });
  });
}

/** 404 beim Entfernen heißt: war schon nicht da */
async function ohneNichtDa(arbeit: Promise<unknown>): Promise<void> {
  try {
    await arbeit;
  } catch (f) {
    if (!(f instanceof Netzfehler && f.status === 404)) throw f;
  }
}

export class BackendQuelle implements Senderquelle {
  readonly faehig: Faehigkeiten = { abgleich: true, eigeneAdresse: true, messen: true, kategorien: true, titelBewerten: true };
  private readonly a: Anfrage;
  private readonly beiFavoriten: () => void;
  private readonly messenNachMs: number;
  /** Felder für die Wiedergabe je Sender (ändern sich nur mit der eigenen Adresse oder dem nächtlichen Abgleich) */
  private readonly fuerWiedergabe = new Map<string, Wiedergabesender>();

  constructor({ anfrage = netz(), beiFavoriten = () => {}, messenNachMs = 10_000 }: BackendOptionen = {}) {
    this.a = anfrage;
    this.beiFavoriten = beiFavoriten;
    this.messenNachMs = messenNachMs;
  }

  // ----- Liste -----------------------------------------------------------------------------------------------------

  abfragen(q: StationQuery, signal?: AbortSignal): Promise<Abfrageergebnis> {
    return this.a(WEGE.abfrage, { methode: "POST", daten: q, signal });
  }

  varianten(uuid: string): Promise<SenderEintrag[]> {
    return this.a(WEGE.varianten(uuid));
  }

  async sender(uuid: string): Promise<SenderEintrag | null> {
    try {
      return (await this.varianten(uuid)).find((e) => e.uuid === uuid) ?? null;
    } catch (f) {
      if (f instanceof Netzfehler && f.status === 404) return null;
      throw f;
    }
  }

  sichtbarkeit(uuid: string): Promise<Sichtbarkeit> {
    return this.a(WEGE.sichtbarkeit(uuid));
  }

  async steckbrief(eintrag: SenderEintrag): Promise<Steckbrief> {
    const [w, messung, widerspruch] = await Promise.all([
      this.wiedergabe(eintrag),
      this.a<{ bitrates?: Record<string, Messung> }>("/api/stations/bitrates", { methode: "POST", daten: { uuids: [eintrag.uuid] } })
        .then((r) => r.bitrates?.[eintrag.uuid] ?? null).catch(() => null),
      this.werbungWiderspruch(eintrag.uuid).catch(() => false),
    ]);
    return {
      adresse: this.fuerWiedergabe.get(eintrag.uuid)?.url || w.url,
      eigeneAdresse: eintrag.eigene_adresse,
      titel: messung ? !!messung.icy : null,
      titelGuete: GUETE[messung?.icy_quality ?? ""] ?? null,
      widerspruch,
    };
  }

  async wiedergabe(eintrag: SenderEintrag): Promise<Wiedergabesender> {
    const gemerkt = this.fuerWiedergabe.get(eintrag.uuid);
    if (gemerkt) return gemerkt;
    // der Eintrag trägt seine Stream-Adressen: spielen ohne weitere Abfrage
    if (eintrag.adresse) return ausEintrag(eintrag);
    let roh: RohSender = {};
    try {
      roh = await this.a<RohSender>(`/api/stations/${kodiert(eintrag.uuid)}`);
    } catch {
      /* ohne Felder des Verzeichnisses spielt der Sender trotzdem (der Durchleiter nimmt die Kennung) */
    }
    const url = roh.error ? "" : (roh.url ?? "");
    const sender: Wiedergabesender = {
      uuid: eintrag.uuid,
      name: eintrag.name,
      url,
      // die eigene Adresse gilt vor der des Verzeichnisses, auch für Zeitversatz und Aufnahme
      url_resolved: eintrag.eigene_adresse || (roh.error ? "" : (roh.url_resolved ?? "")) || url,
      favicon: roh.favicon ?? "",
      country: roh.country || eintrag.land_name,
      countrycode: roh.countrycode || eintrag.land,
      tags: roh.tags ?? eintrag.genres.join(","),
      codec: eintrag.codec,
      bitrate: eintrag.kbps ?? roh.bitrate ?? 0,
      homepage: eintrag.homepage,
    };
    if (url) this.fuerWiedergabe.set(eintrag.uuid, sender);
    return sender;
  }

  async gespielt(eintrag: SenderEintrag, signal?: AbortSignal): Promise<Messwert | null> {
    const uuids = [eintrag.uuid];
    await this.a("/api/stations/verify-bitrate", { methode: "POST", daten: { uuids }, signal }).catch(() => null);
    // Werbeprüfung im Hintergrund, nur über die Kennung (Regel B6)
    void this.a("/api/ad-detection/check", { methode: "POST", daten: { uuid: eintrag.uuid, name: eintrag.name } }).catch(() => null);
    await warten(this.messenNachMs, signal);
    const r = await this.a<{ bitrates?: Record<string, Messung> }>("/api/stations/bitrates", { methode: "POST", daten: { uuids }, signal });
    const m = r.bitrates?.[eintrag.uuid];
    if (!m) return null;
    return { kbps: m.bitrate && m.bitrate > 0 ? m.bitrate : null, codec: m.codec ? m.codec.toUpperCase() : null };
  }

  // ----- Eigene Angaben --------------------------------------------------------------------------------------------

  async favorit(eintrag: SenderEintrag, an: boolean): Promise<void> {
    if (an) {
      const w = await this.wiedergabe(eintrag);
      await this.a("/api/favorites", {
        methode: "POST",
        daten: { stationuuid: w.uuid, name: w.name, url: w.url, url_resolved: w.url_resolved, favicon: w.favicon,
                 country: w.country, countrycode: w.countrycode, tags: w.tags, bitrate: w.bitrate },
      });
    } else {
      await ohneNichtDa(this.a(`/api/favorites/${kodiert(eintrag.uuid)}`, { methode: "DELETE" }));
    }
    this.beiFavoriten();
  }

  private markieren(uuid: string, schluessel: string, wert: string | null): Promise<void> {
    const weg = `/api/station-tags/${kodiert(uuid)}/${kodiert(schluessel)}`;
    if (wert === null) return ohneNichtDa(this.a(`${weg}?source=user`, { methode: "DELETE" }));
    return this.a<void>(weg, { methode: "PUT", daten: { tag_key: schluessel, tag_value: wert, source: "user" } });
  }

  async bewerten(uuid: string, bewertung: Bewertung, an: boolean): Promise<void> {
    const [schluessel, wert] = bewertung.startsWith("sterne:") ? ["sterne", bewertung.slice(7)] : [bewertung, "true"];
    await this.markieren(uuid, schluessel, an ? wert : null);
    // "Werbung" und "kein Werbeverdacht" schließen sich aus
    if (an && schluessel === "werbung") await this.markieren(uuid, "werbung_widerspruch", null);
  }

  async werbungWidersprechen(uuid: string, an: boolean): Promise<void> {
    await this.markieren(uuid, "werbung_widerspruch", an ? "true" : null);
    if (an) await this.markieren(uuid, "werbung", null);
  }

  private async werbungWiderspruch(uuid: string): Promise<boolean> {
    const r = await this.a<{ tags?: { tag_key: string; source: string }[] }>(`/api/station-tags/${kodiert(uuid)}`);
    return (r.tags ?? []).some((t) => t.tag_key === "werbung_widerspruch" && t.source === "user");
  }

  async kategorien(): Promise<Kategorie[]> {
    const r = await this.a<{ categories?: { id: number; name: string }[] }>("/api/categories?scope=radio");
    return (r.categories ?? []).map((k) => ({ id: k.id, name: k.name }));
  }

  kategorieZuordnen(uuid: string, kategorie: number, an: boolean): Promise<void> {
    const weg = `/api/categories/${kategorie}/stations/${kodiert(uuid)}`;
    return an ? this.a<void>(weg, { methode: "POST" }) : ohneNichtDa(this.a(weg, { methode: "DELETE" }));
  }

  async eigeneAdresse(uuid: string, adresse: string | null): Promise<void> {
    const weg = `/api/station-custom-urls/${kodiert(uuid)}`;
    if (adresse && adresse.trim()) await this.a(weg, { methode: "PUT", daten: { custom_url: adresse.trim(), note: "" } });
    else await ohneNichtDa(this.a(weg, { methode: "DELETE" }));
    this.fuerWiedergabe.delete(uuid);
  }

  titelBewerten(uuid: string, guete: TitelGuete): Promise<void> {
    const quality = guete === "genau" ? "good" : guete === "ungenau" ? "poor" : null;
    return this.a<void>(`/api/stations/${kodiert(uuid)}/icy-quality`, { methode: "PUT", daten: { quality } });
  }

  // ----- Regeln ----------------------------------------------------------------------------------------------------

  regeln(): Promise<Regeluebersicht> {
    return this.a(WEGE.regeln);
  }

  vorschau(entwurf: RegelEntwurf, signal?: AbortSignal): Promise<RegelVorschau> {
    return this.a(WEGE.vorschau, { methode: "POST", daten: entwurf, signal });
  }

  anlegen(entwurf: RegelEntwurf): Promise<RegelAenderung> {
    return this.a(WEGE.regeln, { methode: "POST", daten: entwurf });
  }

  schalten(id: string, an: boolean): Promise<RegelAenderung> {
    return this.a(WEGE.regel(id), { methode: "PATCH", daten: { an } });
  }

  folgen(id: string): Promise<RegelFolgen> {
    return this.a(WEGE.folgen(id));
  }

  entfernen(id: string): Promise<RegelAenderung> {
    return this.a(`${WEGE.regel(id)}?bestaetigt=true`, { methode: "DELETE" });
  }

  kandidaten(art: KandidatenArt, suche: string, grenze = 20, signal?: AbortSignal): Promise<Kandidat[]> {
    const p = new URLSearchParams({ art, suche, grenze: String(grenze) });
    return this.a(`${WEGE.kandidaten}?${p}`, { signal });
  }

  // ----- Ausgeblendete, Sperren, Freigaben ---------------------------------------------------------------------------

  ausgeblendet(anfrage: AusgeblendetAnfrage, signal?: AbortSignal): Promise<AusgeblendetSeite> {
    return this.a(WEGE.ausgeblendet, { methode: "POST", daten: anfrage, signal });
  }

  sperren(uuid: string): Promise<Sichtbarkeit> {
    return this.a(WEGE.sperren, { methode: "POST", daten: { uuid } });
  }

  entsperren(uuid: string): Promise<Sichtbarkeit> {
    return this.a(`${WEGE.sperren}/${kodiert(uuid)}`, { methode: "DELETE" });
  }

  freigeben(uuid: string): Promise<Sichtbarkeit> {
    return this.a(WEGE.freigaben, { methode: "POST", daten: { uuid } });
  }

  freigabeZuruecknehmen(uuid: string): Promise<Sichtbarkeit> {
    return this.a(`${WEGE.freigaben}/${kodiert(uuid)}`, { methode: "DELETE" });
  }

  // ----- Länder der Seitenleiste -------------------------------------------------------------------------------------

  async laender(): Promise<LandZahl[]> {
    const r = await this.a<{ countries?: { code: string; name: string; count: number }[] }>("/api/filters/countries");
    return (r.countries ?? []).filter((l) => /^[A-Z]{2}$/.test(l.code)).map((l) => ({ code: l.code, name: l.name, anzahl: l.count }));
  }

  async laenderLeiste(): Promise<string[]> {
    const r = await this.a<{ sidebar_countries?: string[] | string }>("/api/config");
    const wert = r.sidebar_countries;
    const liste = typeof wert === "string" ? (JSON.parse(wert) as unknown) : wert;
    return Array.isArray(liste) ? liste.filter((c): c is string => typeof c === "string") : [];
  }

  laenderLeisteSetzen(codes: string[]): Promise<void> {
    return this.a<void>("/api/config", { methode: "PUT", daten: { updates: { sidebar_countries: codes } } });
  }

  // ----- Abgleich ----------------------------------------------------------------------------------------------------

  abgleich(): Promise<Abgleichstand> {
    return this.a(WEGE.abgleich);
  }

  async abgleichStarten(): Promise<string> {
    const auftrag = await this.a<{ id: string }>(WEGE.abgleich, { methode: "POST" });
    return auftrag.id;
  }
}
