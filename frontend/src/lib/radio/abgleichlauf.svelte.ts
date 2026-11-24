// Abgleich mit dem Senderverzeichnis (RAD-119): Alter des Bestands und der laufende Auftrag, einmal für den Knopf der
// Radio-Ansicht und den Reiter der Einstellungen. Wer nach dem Lauf etwas auffrischen muss, sagt es bei `starten`.
import { hole, type Auftrag } from "appkern-oberflaeche";
import { senderquelle } from ".";
import type { Abgleichstand } from "./typen";

const TAKT_MS = 2000;
const laeuft = (a: Auftrag | null): boolean => a?.zustand === "wartet" || a?.zustand === "laeuft";

/** nach dem Lauf: leer, wenn er gelang, sonst der Grund */
type Danach = (fehler: string) => void;

class Abgleichlauf {
  stand = $state<Abgleichstand | null>(null);
  auftrag = $state<Auftrag | null>(null);
  fehler = $state("");
  readonly offen = $derived(laeuft(this.auftrag));
  private uhr: ReturnType<typeof setTimeout> | undefined;
  private danach: Danach | null = null;

  /** Stand holen; einem schon laufenden Auftrag (Nacht, anderes Gerät) folgen */
  async laden(danach?: Danach): Promise<void> {
    if (danach) this.danach = danach;
    try {
      this.stand = await senderquelle.abgleich();
      if (this.stand.auftrag && this.stand.auftrag !== this.auftrag?.id) await this.verfolgen(this.stand.auftrag);
    } catch (f) {
      this.fehler = (f as Error).message;
    }
  }

  async starten(danach?: Danach): Promise<void> {
    if (this.offen) return;
    if (danach) this.danach = danach;
    this.fehler = "";
    try {
      await this.verfolgen(await senderquelle.abgleichStarten());
    } catch (f) {
      this.fehler = (f as Error).message;
      this.danach?.(this.fehler);
    }
  }

  private async verfolgen(id: string): Promise<void> {
    clearTimeout(this.uhr);
    try {
      this.auftrag = await hole<Auftrag>(`/auftraege/${encodeURIComponent(id)}`);
    } catch (f) {
      this.fehler = (f as Error).message;
      return;
    }
    if (laeuft(this.auftrag)) {
      this.uhr = setTimeout(() => void this.verfolgen(id), TAKT_MS);
      return;
    }
    this.stand = await senderquelle.abgleich().catch(() => this.stand);
    this.danach?.(this.auftrag.zustand === "fertig" ? "" : (this.auftrag.fehler ?? ""));
  }
}

export const abgleichlauf = new Abgleichlauf();
