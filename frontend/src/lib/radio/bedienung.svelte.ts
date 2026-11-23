// Bedienung der Radio-Liste, gemeinsam für Rechner und Telefon: Liste zum Filter laden, Bestand für den Hinweis auf
// ausgeblendete Sender, Abspielen (mit Messung danach), Favorit, Ausblenden mit Rückgängig (startet keinen anderen
// Sender, Vorgabe 5) und die Liste für Vor und Zurück der Wiedergabe (die sichtbare Liste, Vorgabe 7). Kennt nur die
// Senderquelle und die Aktionen der Wiedergabe, keine Bausteine der Oberfläche.
import { t } from "../i18n.js";
import { actions, appState } from "../store.svelte.js";
import { ausEintrag, type Senderquelle, type Wiedergabesender } from "./quelle";
import { Senderliste } from "./senderliste.svelte";
import type { Bestand, SenderEintrag, StationQuery } from "./typen";

/** Inhalt des Rückgängig-Bands */
/** einzeln ausgeblendet, aber als Favorit sichtbar geblieben (Ausnahme mit dem Grund der einzelnen Sperre) */
export const einzelnAusgeblendet = (e: SenderEintrag): boolean => e.ausnahme.some((g) => g.art === "einzeln");

export interface BandInhalt {
  symbol: string;
  text: string;
  /** fett vor dem Text, etwa der Name des Senders */
  name?: string;
  rueckgaengig?: () => Promise<void> | void;
  /** Verweis auf eine Adresse oder, in einer Ansicht mit eigenem Zustand (Podcasts, RAD-104), eine Aktion */
  verweis?: { text: string; pfad: string } | { text: string; aktion: () => void };
  art?: "gut" | "fehler";
}

/** so nah am Ende der geladenen Liste lädt der laufende Sender die nächste Seite vor */
const VORRAT = 2;
/** so viele Seiten lädt die Suche nach dem laufenden Sender höchstens nach, wenn seine Stelle nicht bekannt ist */
const SUCHSEITEN = 10;

export class Radiobedienung {
  readonly liste: Senderliste;
  bestand = $state<Bestand | null>(null);
  band = $state<BandInhalt | null>(null);
  /** Felder der Wiedergabe je Sender, sobald geholt (für Vor und Zurück über die Liste) */
  private wiedergabe = $state<Record<string, Wiedergabesender>>({});
  private messung: AbortController | null = null;
  /** zuletzt eine Variante aus der aufgeklappten Zeile eines anderen Senders gespielt (RAD-41): welche, aus welcher Zeile */
  private ausZeile: { uuid: string; zeile: string } | null = null;
  /** wo der laufende Sender zuletzt in der Liste stand (RAD-124): die Stelle gilt auch, wenn er inzwischen ausgeblendet ist
   *  oder die Liste wieder bei ihrer ersten Seite beginnt, solange es dieselbe Abfrage ist */
  private platz: { zeile: string; stelle: number; abfrage: string } | null = null;
  /** der spielende Sender, wenn er nicht in der geladenen Liste steht (für Auge und Stern im großen Spieler, RAD-94) */
  private einzeln = $state<SenderEintrag | null>(null);

  constructor(private readonly quelle: Senderquelle) {
    this.liste = new Senderliste(quelle);
  }

  laden(abfrage: StationQuery): Promise<void> {
    return this.liste.laden(abfrage);
  }

  async bestandLaden(): Promise<void> {
    try {
      this.bestand = (await this.quelle.regeln()).bestand;
    } catch {
      /* ohne Bestand fehlt nur der Hinweis */
    }
  }

  /** die Liste, wie die Wiedergabe sie für Vor und Zurück braucht */
  fuerWiedergabe(): Wiedergabesender[] {
    return this.liste.eintraege.map((e) => this.wiedergabe[e.uuid] ?? ausEintrag(e));
  }

  private async holen(e: SenderEintrag): Promise<Wiedergabesender> {
    const w = await this.quelle.wiedergabe(e);
    if (w.url) this.wiedergabe = { ...this.wiedergabe, [e.uuid]: w };
    return w;
  }

  /** Nachbarn des spielenden Senders vorbereiten, damit Vor und Zurück mit allen Feldern spielen */
  nachbarnVorbereiten(uuid: string | null): void {
    const zeile = this.zeileFuer(uuid);
    if (!zeile) return;
    const liste = this.liste.eintraege;
    const i = liste.findIndex((e) => e.uuid === zeile);
    if (i < 0 || !liste.length) return;
    this.platz = { zeile, stelle: i, abfrage: this.liste.schluessel };
    if (i >= liste.length - VORRAT) void this.liste.mehr();
    for (const j of [i - 1, i + 1]) {
      const e = liste[(j + liste.length) % liste.length];
      if (e && !this.wiedergabe[e.uuid]) void this.holen(e).catch(() => {});
    }
  }

  /** Die Zeile der Liste, die für den laufenden Sender steht: bei einer Variante die Zeile, aus der sie gespielt wurde
   *  (sie kann selbst weit weg in der Liste stehen oder gar nicht), sonst der Sender selbst */
  zeileFuer(uuid: string | null): string | null {
    return uuid && this.ausZeile?.uuid === uuid ? this.ausZeile.zeile : uuid;
  }

  /** Der Sender vor (-1) oder nach (1) dem laufenden, für Vor, Zurück und Ausblenden (RAD-124): folgt der sichtbaren Liste
   *  (Vorgabe 7) und lädt nach, statt am Ende der geladenen Seite von vorn zu beginnen. Rundum geht es erst, wenn die Liste
   *  wirklich zu Ende ist. Steht der laufende nicht mehr darin, gilt seine letzte Stelle; kennt die Liste ihn gar nicht,
   *  beginnt Vor beim ersten. */
  async nachbar(uuid: string, schritt: -1 | 1): Promise<Wiedergabesender | null> {
    const zeile = this.zeileFuer(uuid) ?? uuid;
    const jetzt = () => this.liste.eintraege.findIndex((e) => e.uuid === zeile);
    const gemerkt = this.platz?.zeile === zeile && this.platz.abfrage === this.liste.schluessel ? this.platz.stelle : null;
    const unbekannt = () => jetzt() < 0 && (gemerkt === null || this.liste.eintraege.length <= gemerkt);
    for (let seite = 0; unbekannt() && (gemerkt !== null || seite < SUCHSEITEN); seite++) if (!(await this.nachladen())) break;
    const stelle = jetzt() >= 0 ? jetzt() : gemerkt;
    if (stelle === null && schritt < 0) return null;
    // ist er ausgeblendet (auch während des Nachladens), rückt der nächste an seine Stelle
    const ziel = () => {
      const i = jetzt();
      if (i >= 0) return i + schritt;
      return stelle === null ? 0 : schritt > 0 ? stelle : stelle - 1;
    };
    if (ziel() >= this.liste.eintraege.length) await this.nachladen();
    const n = this.liste.eintraege.length;
    if (!n) return null;
    const e = this.liste.eintraege[(Math.min(ziel(), n) + n) % n];
    return this.wiedergabe[e.uuid] ?? ausEintrag(e);
  }

  /** die nächste Seite holen; ob Sender dazukamen */
  private async nachladen(): Promise<boolean> {
    const vorher = this.liste.eintraege.length;
    await this.liste.mehr();
    return this.liste.eintraege.length > vorher;
  }

  /** Eintrag eines Senders aus der Liste oder, falls schon geholt, von der Quelle (RAD-94) */
  eintragVon(uuid: string | null): SenderEintrag | null {
    if (!uuid) return null;
    return this.liste.eintraege.find((e) => e.uuid === uuid) ?? (this.einzeln?.uuid === uuid ? this.einzeln : null);
  }

  /** den Eintrag eines Senders bereitstellen, der nicht in der Liste steht; die Liste selbst bleibt, wie sie ist */
  async eintragHolen(uuid: string | null): Promise<void> {
    if (!uuid || this.eintragVon(uuid)) return;
    const e = await this.quelle.sender(uuid).catch(() => null);
    if (e) this.einzeln = e;
  }

  private eintragAendern(uuid: string, teil: Partial<SenderEintrag>): void {
    this.liste.aendern(uuid, teil);
    if (this.einzeln?.uuid === uuid) this.einzeln = { ...this.einzeln, ...teil };
  }

  /** `zeile`: gespielt aus den Varianten dieser Zeile */
  async spielen(e: SenderEintrag, zeile?: SenderEintrag): Promise<void> {
    this.ausZeile = zeile && zeile.uuid !== e.uuid ? { uuid: e.uuid, zeile: zeile.uuid } : null;
    const w = await this.holen(e);
    await actions.playStation(w);
    if (!this.quelle.faehig.messen || (appState.currentStation as { uuid?: string } | null)?.uuid !== e.uuid) return;
    this.messung?.abort();
    const messung = (this.messung = new AbortController());
    try {
      const m = await this.quelle.gespielt(e, messung.signal);
      if (m && (m.kbps || m.codec)) {
        this.liste.aendern(e.uuid, { ...(m.kbps ? { kbps: m.kbps, kbps_gemessen: true } : {}), ...(m.codec ? { codec: m.codec } : {}) });
      }
    } catch {
      /* Messung abgebrochen oder fehlgeschlagen: die Zeile bleibt, wie sie war */
    }
  }

  async favorit(e: SenderEintrag): Promise<void> {
    const an = !e.favorit;
    try {
      await this.quelle.favorit(e, an);
      // war er nur als Favorit trotz Ausblenden sichtbar, verschwindet er jetzt (RAD-28: so angekündigt)
      if (!an && einzelnAusgeblendet(e)) {
        const stelle = this.liste.entfernen(e.uuid);
        this.band = { symbol: "fa-eye-slash", name: e.name, text: t("radio.bandKeinFavoritMehr"),
                      rueckgaengig: async () => { await this.quelle.favorit(e, true); this.liste.einfuegen({ ...e, favorit: true }, stelle); } };
        return;
      }
      this.eintragAendern(e.uuid, { favorit: an });
      actions.showToast(an ? t("toast.favHinzu") : t("toast.favEntfernt"), an ? "success" : "info");
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }

  /** Auge: Einzelsperre; der Sender verschwindet aus der Liste, nichts anderes startet. Ein Favorit bleibt als Ausnahme. */
  async ausblenden(e: SenderEintrag): Promise<void> {
    let stelle = -1;
    try {
      const s = await this.quelle.sperren(e.uuid);
      if (s.sichtbar) {
        this.eintragAendern(e.uuid, { ausnahme: s.gruende });
        this.band = { symbol: "fa-star", name: e.name, text: t("radio.bandBleibtFavorit"), rueckgaengig: () => this.entsperren(e, -1) };
        return;
      }
      stelle = this.liste.entfernen(e.uuid);
      if (this.bestand) this.bestand = { ...this.bestand, ausgeblendet: this.bestand.ausgeblendet + 1, sichtbar: this.bestand.sichtbar - 1 };
      this.band = { symbol: "fa-eye-slash", name: e.name, text: t("radio.bandAusgeblendet"), rueckgaengig: () => this.entsperren(e, stelle),
                    verweis: { text: t("radio.bandListe"), pfad: "/einstellungen/radio/ausgeblendet" } };
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }

  /** einen einzeln ausgeblendeten Sender, der als Favorit sichtbar blieb, wieder einblenden */
  async einblenden(e: SenderEintrag): Promise<void> {
    try {
      await this.entsperren(e, -1);
      this.band = { symbol: "fa-eye", name: e.name, text: t("radio.bandEingeblendet"), rueckgaengig: () => this.ausblenden({ ...e, ausnahme: [] }) };
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }

  private async entsperren(e: SenderEintrag, stelle: number): Promise<void> {
    const s = await this.quelle.entsperren(e.uuid);
    if (stelle >= 0 && s.sichtbar) {
      this.liste.einfuegen(e, stelle);
      if (this.bestand) this.bestand = { ...this.bestand, ausgeblendet: this.bestand.ausgeblendet - 1, sichtbar: this.bestand.sichtbar + 1 };
    } else {
      this.eintragAendern(e.uuid, { ausnahme: s.sichtbar ? s.gruende : [] });
    }
  }

  /** ein Sender für einen Direktlink oder den Sprung von der Spielerleiste, nicht in der geladenen Liste: vorn einfügen */
  async sicherstellen(uuid: string): Promise<boolean> {
    if (this.liste.eintraege.some((e) => e.uuid === uuid)) return true;
    const e = await this.quelle.sender(uuid).catch(() => null);
    if (!e) return false;
    this.liste.einfuegen(e, 0, false);
    return true;
  }
}
