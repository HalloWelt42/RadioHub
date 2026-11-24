// Werbung in einer Folge (RAD-32): die Stellen, ihre Arbeit (suchen, markieren, verwerfen, ohne Werbung speichern) und der Schalter des
// Abos. Ein Zustand je aufgeklappter Folge, geteilt von den Tasten in ihrer Reihe und der Liste der Stellen.
import { actions } from "../lib/store.svelte.js";
import { t } from "../lib/i18n.svelte.js";
import type { Fortschritt } from "../lib/ereignisstrom";
import { tonelement } from "./tonelement";
import { werbesprung } from "./werbesprung.svelte";
import { aboliste, werbequelle, type Abo, type Folge, type Werbeherkunft, type Werbestelle } from "../lib/podcasts";

export class Folgenwerbung {
  stellen = $state<Werbestelle[]>([]);
  quellen = $state<Werbeherkunft[]>([]);
  geladen = $state(false);
  verworfen = $state<Werbestelle | null>(null);
  /** Beginn einer Stelle, die gerade von Hand markiert wird */
  beginn = $state<number | null>(null);
  auftrag = $state<{ was: string; f: Fortschritt | null } | null>(null);

  /** `geaendert`: Zahl und Dauer der Stellen haben sich geändert (für die Zeile) */
  constructor(private readonly folge: () => Folge, private readonly abo: () => Abo | undefined,
              private readonly geaendert: (werbung: { anzahl: number; dauer: number }) => void) {}

  get summe(): number {
    return this.stellen.reduce((s, x) => s + x.bis - x.von, 0);
  }

  async laden(): Promise<void> {
    try {
      const r = await werbequelle.stellen(this.folge().id);
      this.stellen = r.stellen;
      this.quellen = r.quellen;
    } finally {
      this.geladen = true;
    }
  }

  verwerfen = (s: Werbestelle): Promise<void> => this.sicher(async () => {
    await werbequelle.verwerfen(s.id, true);
    this.stellen = this.stellen.filter((x) => x.id !== s.id);
    this.verworfen = s;
    this.melden();
  });

  zurueckholen = (): Promise<void> => this.sicher(async () => {
    const s = this.verworfen;
    if (!s) return;
    await werbequelle.verwerfen(s.id, false);
    this.verworfen = null;
    this.einsetzen(s);
  });

  /** beim Hören: erst am Beginn, dann am Ende der Werbung */
  markieren = (): void => {
    const jetzt = tonelement().currentTime;
    if (this.beginn === null) { this.beginn = jetzt; return; }
    const [von, bis] = [Math.min(this.beginn, jetzt), Math.max(this.beginn, jetzt)];
    this.beginn = null;
    void this.sicher(async () => this.einsetzen(await werbequelle.setzen(this.folge().id, von, bis)));
  };

  suchen = (): Promise<void> => this.alsAuftrag(t("podcastAnsicht.werbung.suchen"), async (f) => {
    const gefunden = await werbequelle.suchen(this.folge().id, f);
    const zahl = Object.values(gefunden).reduce((s, n) => s + n, 0);
    actions.showToast(t(zahl === 1 ? "podcastAnsicht.werbung.gefundenEins" : "podcastAnsicht.werbung.gefunden", { n: zahl }), "success");
    await this.laden();
    this.melden();
  });

  ohneWerbung = (): Promise<void> => this.alsAuftrag(t("podcastAnsicht.werbung.ohneSpeichern"), async (f) => {
    const pfad = await werbequelle.ohneWerbung(this.folge().id, f);
    actions.showToast(t("podcastAnsicht.werbung.ohneFertig", { pfad }), "success");
  });

  ueberspringen = (an: boolean): Promise<void> => this.sicher(async () => {
    const abo = this.abo();
    if (!abo) return;
    await werbequelle.aboSetzen(abo.id, { ueberspringen: an });
    aboliste.aendern(abo.id, { werbungUeberspringen: an });
  });

  private einsetzen(s: Werbestelle): void {
    this.stellen = [...this.stellen, s].sort((a, b) => a.von - b.von);
    this.melden();
  }

  private melden(): void {
    this.geaendert({ anzahl: this.stellen.length, dauer: this.summe });
    werbesprung.neu(this.folge().id);
  }

  private async alsAuftrag(was: string, arbeit: (f: (f: Fortschritt) => void) => Promise<void>): Promise<void> {
    this.auftrag = { was, f: null };
    await this.sicher(() => arbeit((f) => (this.auftrag = { was, f })));
    this.auftrag = null;
  }

  private async sicher(arbeit: () => Promise<void>): Promise<void> {
    try {
      await arbeit();
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }
}
