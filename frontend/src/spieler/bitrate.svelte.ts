// Vorgabe der Bitrate des Zeitversatzes, geteilt von Anzeige (Leuchtschrift im Glas) und Steuerung (Drehwahl): gemerkt im
// Browser wie bisher (radiohub_bitrate_override); der Zeitversatz startet mit ihr neu. Beim Drehen über mehrere Rasten
// startet er nur einmal: nach dem Loslassen oder, bei Mausrad und Tasten, wenn die Drehwahl kurz ruht.
import { bitrateLesen, bitrateSetzen } from "./aktionen";

const RUHE_MS = 900;

export class Bitrate {
  vorgabe = $state<number | null>(bitrateLesen());
  wechselt = $state(false);
  private uhr: ReturnType<typeof setTimeout> | null = null;
  private angewandt: number | null = this.vorgabe;

  /** Drehwahl bewegt: zeigen, nach kurzer Ruhe anwenden */
  vormerken(kbit: number | null): void {
    this.vorgabe = kbit;
    if (this.uhr) clearTimeout(this.uhr);
    this.uhr = setTimeout(() => this.anwenden(), RUHE_MS);
  }

  /** losgelassen: sofort anwenden */
  async anwenden(): Promise<void> {
    if (this.uhr) clearTimeout(this.uhr);
    this.uhr = null;
    if (this.vorgabe === this.angewandt || this.wechselt) return;
    const neu = this.vorgabe;
    this.angewandt = neu;
    this.wechselt = true;
    try {
      await bitrateSetzen(neu);
    } finally {
      this.wechselt = false;
    }
    if (this.vorgabe !== this.angewandt) this.anwenden();
  }
}
