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
  verweis?: { text: string; pfad: string };
  art?: "gut" | "fehler";
}

/** Felder der Wiedergabe aus dem Eintrag, solange die des Verzeichnisses noch nicht geholt sind */

export class Radiobedienung {
  readonly liste: Senderliste;
  bestand = $state<Bestand | null>(null);
  band = $state<BandInhalt | null>(null);
  /** Felder der Wiedergabe je Sender, sobald geholt (für Vor und Zurück über die Liste) */
  private wiedergabe = $state<Record<string, Wiedergabesender>>({});
  private messung: AbortController | null = null;
  /** zuletzt eine Variante aus der aufgeklappten Zeile eines anderen Senders gespielt (RAD-41): welche, aus welcher Zeile */
  private ausZeile: { uuid: string; zeile: string } | null = null;

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
      this.liste.aendern(e.uuid, { favorit: an });
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
        this.liste.aendern(e.uuid, { ausnahme: s.gruende });
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
      this.liste.aendern(e.uuid, { ausnahme: s.sichtbar ? s.gruende : [] });
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
