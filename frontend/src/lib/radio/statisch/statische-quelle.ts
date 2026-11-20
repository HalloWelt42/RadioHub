// Senderquelle der Webversion (RAD-4, Entscheidungen 25 bis 28): die statische Senderliste (sender.json) und die eigenen
// Angaben im Speicher des Browsers. Verhält sich wie die Senderquelle des Backends (backend/app/services/senderquelle/),
// soweit die Webversion es kann; was sie nicht kann, steht in `faehig` und wirft beim Aufruf einen klaren Fehler.
// Die Liste wird beim ersten Zugriff einmal geladen und als Index gebaut, danach läuft alles im Speicher.
import { ausEintrag, type Einspielbericht, type Faehigkeiten, type Kategorie, type LandZahl, type Messwert, type Senderquelle,
  type Steckbrief, type Wiedergabesender } from "../quelle";
import type {
  Abfrageergebnis, Abgleichstand, AusgeblendetAnfrage, AusgeblendetSeite, Bewertung, Kandidat, KandidatenArt, RegelAenderung,
  RegelEntwurf, RegelFolgen, Regeluebersicht, RegelVorschau, SenderEintrag, Sichtbarkeit, StationQuery,
} from "../typen";
import { abfragePruefen, durchgangSchluessel, durchgehen, eintrag, kurz, nachStimmen, seite, type Durchgang } from "./abfrage";
import { angabenAusText, bericht, leereAngaben, type EigeneAngaben } from "./angaben";
import { ausgeblendetSeite, kandidaten, laender } from "./auswahl";
import { NichtGefunden, NichtVerfuegbar, Quellfehler } from "./fehler";
import { bestandLesen, type Senderbestand } from "./format";
import { EINZELSPERREN, entwurfPruefen, inhalt, istBewertung, titel, treffer } from "./regeln";
import { Sicht } from "./sicht";
import type { Speicher } from "./speicher";
import { vergleichen } from "./text";

export const SPEICHER_SCHLUESSEL = "radiohub.web.angaben";

export interface StatischeOptionen {
  /** liefert den Inhalt von sender.json (die Webversion per fetch, Tests eine Probe) */
  laden: () => Promise<unknown>;
  speicher: Speicher;
}

const BEISPIELE = 5;

export class StatischeQuelle implements Senderquelle {
  readonly faehig: Faehigkeiten = { abgleich: false, eigeneAdresse: false, messen: false, kategorien: false, titelBewerten: false,
                                    werbung: false, datei: true };
  private readonly laden: () => Promise<unknown>;
  private readonly speicher: Speicher;
  private liste: Promise<Senderbestand> | null = null;
  private angaben: EigeneAngaben;
  private sichtStand: Sicht | null = null;
  private gemerkt: { schluessel: string; durchgang: Durchgang } | null = null;
  private letzteZeit = 0;

  constructor({ laden, speicher }: StatischeOptionen) {
    this.laden = laden;
    this.speicher = speicher;
    this.angaben = this.angabenLesen();
    this.uhrNachziehen(this.angaben);
  }

  /** die Uhr nie hinter gespeicherte Zeitpunkte zurück (Reihenfolge der Regeln über Neustarts) */
  private uhrNachziehen(a: EigeneAngaben): void {
    for (const r of a.regeln) this.letzteZeit = Math.max(this.letzteZeit, Date.parse(r.angelegt_am), Date.parse(r.geaendert_am));
  }

  // ----- Grundlagen -------------------------------------------------------------------------------------------------

  /** Zeitpunkt, streng steigend (Regeln, die in derselben Millisekunde entstehen, bleiben in ihrer Reihenfolge) */
  private jetzt(): string {
    this.letzteZeit = Math.max(Date.now(), this.letzteZeit + 1);
    return new Date(this.letzteZeit).toISOString();
  }

  /** Gespeicherte Angaben; eine unlesbare Fassung bleibt unter eigenem Schlüssel erhalten, nichts geht verloren. */
  private angabenLesen(): EigeneAngaben {
    const text = this.speicher.lesen(SPEICHER_SCHLUESSEL);
    if (text === null) return leereAngaben(this.jetzt());
    try {
      return angabenAusText(text, this.jetzt());
    } catch {
      try {
        this.speicher.schreiben(`${SPEICHER_SCHLUESSEL}.unlesbar`, text);
      } catch {
        /* ohne Speicher bleibt sie, wo sie ist: unter dem eigentlichen Schlüssel, bis zur ersten Änderung */
      }
      return leereAngaben(this.jetzt());
    }
  }

  /** Die Liste: beim ersten Zugriff geladen und gebaut; schlägt das fehl, versucht es der nächste Zugriff erneut. */
  private bestand(): Promise<Senderbestand> {
    this.liste ??= this.laden().then(bestandLesen).catch((f: unknown) => {
      this.liste = null;
      throw f;
    });
    return this.liste;
  }

  private async bereit(signal?: AbortSignal): Promise<{ b: Senderbestand; s: Sicht }> {
    const b = await this.bestand();
    signal?.throwIfAborted();
    this.sichtStand ??= new Sicht(b, this.angaben);
    return { b, s: this.sichtStand };
  }

  /** Ändert eine Kopie der Angaben, speichert sie und übernimmt sie erst dann (alles oder nichts). */
  private aendern(arbeit: (a: EigeneAngaben) => void): void {
    const neu = structuredClone(this.angaben);
    arbeit(neu);
    this.uebernehmen(neu);
  }

  private uebernehmen(neu: EigeneAngaben): void {
    try {
      this.speicher.schreiben(SPEICHER_SCHLUESSEL, JSON.stringify(neu));
    } catch {
      throw new Quellfehler("Der Browser speichert die eigenen Angaben nicht (Speicher voll oder gesperrt)", 507);
    }
    this.angaben = neu;
    this.sichtStand = null;
    this.gemerkt = null;
  }

  private stelle(b: Senderbestand, uuid: string): number {
    const i = b.nachUuid.get(uuid);
    if (i === undefined) throw new NichtGefunden("Sender nicht gefunden");
    return i;
  }

  // ----- Liste ------------------------------------------------------------------------------------------------------

  async abfragen(q: StationQuery, signal?: AbortSignal): Promise<Abfrageergebnis> {
    const { b, s } = await this.bereit(signal);
    const a = abfragePruefen(q);
    const schluessel = durchgangSchluessel(a);
    if (this.gemerkt?.schluessel !== schluessel) this.gemerkt = { schluessel, durchgang: durchgehen(b, s, a) };
    return seite(b, s, a, this.gemerkt.durchgang, this.angaben.laender_leiste);
  }

  async varianten(uuid: string): Promise<SenderEintrag[]> {
    const { b, s } = await this.bereit();
    const i = b.nachUuid.get(uuid);
    if (i === undefined) return [];
    const glieder = (b.glieder.get(b.gruppe[i]) ?? []).filter((x) => s.sichtbar[x]);
    // wie das Backend: Vertreter vorn, dann Qualität, Bitrate, Stimmen, uuid
    const beste = (x: number, y: number) => s.vertreter[y] - s.vertreter[x] || b.qualitaetRang[y] - b.qualitaetRang[x]
      || b.kbps[y] - b.kbps[x] || b.stimmen[y] - b.stimmen[x] || vergleichen(b.uuid[x], b.uuid[y]);
    return glieder.sort(beste).map((x) => eintrag(b, s, x));
  }

  async sender(uuid: string): Promise<SenderEintrag | null> {
    return (await this.varianten(uuid)).find((e) => e.uuid === uuid) ?? null;
  }

  async sichtbarkeit(uuid: string): Promise<Sichtbarkeit> {
    const { b, s } = await this.bereit();
    const i = this.stelle(b, uuid);
    return { uuid, sichtbar: !!s.sichtbar[i], verschwunden: false, favorit: !!s.favorit[i], freigegeben: !!s.freigegeben[i],
             gesperrt: this.angaben.sperren.includes(uuid), gruende: s.gruende(i) };
  }

  async steckbrief(e: SenderEintrag): Promise<Steckbrief> {
    return { adresse: e.adresse_aufgeloest || e.adresse, eigeneAdresse: null, titel: null, titelGuete: null, widerspruch: false };
  }

  async wiedergabe(e: SenderEintrag): Promise<Wiedergabesender> {
    return ausEintrag(e);
  }

  /** ohne Messung in der Webversion */
  async gespielt(): Promise<Messwert | null> {
    return null;
  }

  // ----- Eigene Angaben ---------------------------------------------------------------------------------------------

  async favorit(e: SenderEintrag, an: boolean): Promise<void> {
    this.aendern((a) => {
      a.favoriten = a.favoriten.filter((u) => u !== e.uuid);
      if (an) a.favoriten.push(e.uuid);
    });
  }

  /** Sterne gibt es je Sender einmal: eine neue Stufe ersetzt die alte; aus nimmt die Sterne ganz weg (wie das Backend). */
  async bewerten(uuid: string, bewertung: Bewertung, an: boolean): Promise<void> {
    if (!istBewertung(bewertung)) throw new Quellfehler(`Unbekannte Bewertung: ${String(bewertung)}`, 422);
    const sterne = bewertung.startsWith("sterne:");
    this.aendern((a) => {
      const liste = (a.bewertungen[uuid] ?? []).filter((x) => (sterne ? !x.startsWith("sterne:") : x !== bewertung));
      if (an) liste.push(bewertung);
      if (liste.length) a.bewertungen[uuid] = liste;
      else delete a.bewertungen[uuid];
    });
  }

  werbungWidersprechen(): Promise<void> {
    return Promise.reject(new NichtVerfuegbar("Werbeerkennung"));
  }

  kategorien(): Promise<Kategorie[]> {
    return Promise.reject(new NichtVerfuegbar("eigene Kategorien"));
  }

  kategorieZuordnen(): Promise<void> {
    return Promise.reject(new NichtVerfuegbar("eigene Kategorien"));
  }

  eigeneAdresse(): Promise<void> {
    return Promise.reject(new NichtVerfuegbar("eigene Stream-Adresse"));
  }

  titelBewerten(): Promise<void> {
    return Promise.reject(new NichtVerfuegbar("Titelangaben bewerten"));
  }

  // ----- Regeln -----------------------------------------------------------------------------------------------------

  async regeln(): Promise<Regeluebersicht> {
    const { s } = await this.bereit();
    return { bestand: s.bestand(), regeln: s.alleRegeln() };
  }

  private gleicheRegel(entwurf: RegelEntwurf): string | null {
    const gesucht = inhalt(entwurf);
    return this.angaben.regeln.find((r) => r.art === entwurf.art && r.entwurf && inhalt(r.entwurf) === gesucht)?.id ?? null;
  }

  async vorschau(roh: RegelEntwurf, signal?: AbortSignal): Promise<RegelVorschau> {
    const { b, s } = await this.bereit(signal);
    const entwurf = entwurfPruefen(roh);
    const getroffen = [...treffer(b, this.angaben, entwurf.art, entwurf)];
    const neu = getroffen.filter((i) => s.sichtbar[i] && !s.favorit[i] && !s.freigegeben[i]);
    const favoriten = getroffen.filter((i) => s.favorit[i]);
    return { titel: titel(b, entwurf.art, entwurf), betroffen: getroffen.length, neu_ausgeblendet: neu.length,
             favoriten: favoriten.length, favoriten_namen: favoriten.map((i) => b.name[i]).sort(vergleichen).slice(0, 10),
             beispiele: nachStimmen(b, neu, BEISPIELE).map((i) => kurz(b, i)), gleiche_regel: this.gleicheRegel(entwurf) };
  }

  /** Ändert eine Regel und meldet, wie viele Sender dadurch aus- oder eingeblendet wurden. */
  private async regelAendern(id: string | null, arbeit: (a: EigeneAngaben, zeit: string) => string | null): Promise<RegelAenderung> {
    const vorher = (await this.bereit()).s.sichtbarAnzahl;
    let bleibt: string | null = id;
    this.aendern((a) => { bleibt = arbeit(a, this.jetzt()); });
    const { s } = await this.bereit();
    const nachher = s.sichtbarAnzahl;
    return { regel: bleibt ? s.regel(bleibt) : null, bestand: s.bestand(), ausgeblendet: Math.max(0, vorher - nachher),
             wieder_sichtbar: Math.max(0, nachher - vorher) };
  }

  async anlegen(roh: RegelEntwurf): Promise<RegelAenderung> {
    await this.bereit();
    const entwurf = entwurfPruefen(roh);
    const gleich = this.gleicheRegel(entwurf);
    if (gleich) throw new Quellfehler(`Diese Regel gibt es schon (${gleich})`, 409);
    const id = crypto.randomUUID().replace(/-/g, "").slice(0, 12);
    return this.regelAendern(id, (a, zeit) => {
      a.regeln.push({ id, art: entwurf.art, an: true, herkunft: "nutzer", entwurf,
                      angelegt_am: zeit, geaendert_am: zeit });
      return id;
    });
  }

  private regelDa(id: string): void {
    if (!this.angaben.regeln.some((r) => r.id === id)) throw new NichtGefunden("Regel nicht gefunden");
  }

  async schalten(id: string, an: boolean): Promise<RegelAenderung> {
    await this.bereit();
    this.regelDa(id);
    return this.regelAendern(id, (a, zeit) => {
      const r = a.regeln.find((x) => x.id === id);
      if (r) Object.assign(r, { an, geaendert_am: zeit });
      return id;
    });
  }

  async folgen(id: string): Promise<RegelFolgen> {
    const { b, s } = await this.bereit();
    const t = s.regeln.get(id);
    const regel = s.regel(id);
    if (!t || !regel) throw new NichtGefunden("Regel nicht gefunden");
    const wieder = [...t.sender].filter((i) => s.wuerdeSichtbar(i, t));
    return { regel, wieder_sichtbar: wieder.length, beispiele: nachStimmen(b, wieder, BEISPIELE).map((i) => kurz(b, i)) };
  }

  async entfernen(id: string): Promise<RegelAenderung> {
    await this.bereit();
    if (id === EINZELSPERREN) throw new Quellfehler("Die Einzelsperren sind keine entfernbare Regel; einzelne Sender gibt das Auge frei");
    this.regelDa(id);
    return this.regelAendern(null, (a) => {
      a.regeln = a.regeln.filter((r) => r.id !== id);
      return null;
    });
  }

  async kandidaten(art: KandidatenArt, suche: string, grenze = 20, signal?: AbortSignal): Promise<Kandidat[]> {
    const { b, s } = await this.bereit(signal);
    return kandidaten(b, s, art, suche, grenze);
  }

  // ----- Ausgeblendete, Sperren, Freigaben ----------------------------------------------------------------------------

  async ausgeblendet(anfrage: AusgeblendetAnfrage, signal?: AbortSignal): Promise<AusgeblendetSeite> {
    const { b, s } = await this.bereit(signal);
    return ausgeblendetSeite(b, s, anfrage);
  }

  private async fuerSender(uuid: string, arbeit: (a: EigeneAngaben, s: Sicht, i: number) => void): Promise<Sichtbarkeit> {
    const { b, s } = await this.bereit();
    const i = this.stelle(b, uuid);
    this.aendern((a) => arbeit(a, s, i));
    return this.sichtbarkeit(uuid);
  }

  /** Einzelsperre (Auge); hebt eine Freigabe desselben Senders auf */
  sperren(uuid: string): Promise<Sichtbarkeit> {
    return this.fuerSender(uuid, (a) => {
      if (!a.sperren.includes(uuid)) a.sperren.push(uuid);
      a.freigaben = a.freigaben.filter((u) => u !== uuid);
    });
  }

  entsperren(uuid: string): Promise<Sichtbarkeit> {
    return this.fuerSender(uuid, (a) => { a.sperren = a.sperren.filter((u) => u !== uuid); });
  }

  /** Wieder sichtbar: die Einzelsperre fällt weg; trifft ihn noch eine andere eingeschaltete Regel, bleibt er als
   *  Ausnahme (Freigabe) sichtbar. */
  freigeben(uuid: string): Promise<Sichtbarkeit> {
    return this.fuerSender(uuid, (a, s, i) => {
      a.sperren = a.sperren.filter((u) => u !== uuid);
      if (s.andereRegel(i, EINZELSPERREN) && !a.freigaben.includes(uuid)) a.freigaben.push(uuid);
    });
  }

  freigabeZuruecknehmen(uuid: string): Promise<Sichtbarkeit> {
    return this.fuerSender(uuid, (a) => { a.freigaben = a.freigaben.filter((u) => u !== uuid); });
  }

  // ----- Länder der Seitenleiste ----------------------------------------------------------------------------------------

  async laender(): Promise<LandZahl[]> {
    const { b, s } = await this.bereit();
    return laender(b, s);
  }

  /** eigene Wahl; leer heißt wie im Backend: die Facette zeigt alle Länder, die mit den meisten Sendern zuerst */
  async laenderLeiste(): Promise<string[]> {
    return [...this.angaben.laender_leiste];
  }

  async laenderLeisteSetzen(codes: string[]): Promise<void> {
    const sauber = [...new Set(codes.filter((c) => typeof c === "string" && c.length === 2).map((c) => c.toUpperCase()))]
      .filter((c) => /^[A-Z]{2}$/.test(c));
    this.aendern((a) => { a.laender_leiste = sauber; });
  }

  // ----- Abgleich ---------------------------------------------------------------------------------------------------

  abgleich(): Promise<Abgleichstand> {
    return Promise.reject(new NichtVerfuegbar("Abgleich mit dem Senderverzeichnis"));
  }

  abgleichStarten(): Promise<string> {
    return Promise.reject(new NichtVerfuegbar("Abgleich mit dem Senderverzeichnis"));
  }

  // ----- Eigene Angaben als Datei ---------------------------------------------------------------------------------------

  async sichern(): Promise<string> {
    return JSON.stringify({ ...this.angaben, gesichert_am: this.jetzt() }, null, 2);
  }

  async pruefen(text: string): Promise<Einspielbericht> {
    return bericht(angabenAusText(text, this.jetzt()));
  }

  /** ersetzt alle eigenen Angaben durch die der Datei (nach derselben Prüfung wie `pruefen`) */
  async einspielen(text: string): Promise<Einspielbericht> {
    const neu = angabenAusText(text, this.jetzt());
    this.uebernehmen(neu);
    this.uhrNachziehen(neu);
    return bericht(neu);
  }
}
