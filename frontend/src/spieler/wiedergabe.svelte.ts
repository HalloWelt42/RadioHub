// Was der Tonausgang je Augenblick meldet: Zeit, Dauer, Lage auf der Spulbahn, Laden, Puffern, Fehler und die Hördauer
// eines Senders. Hochfrequent, darum nicht in appState, sondern hier für die Kanzel (früher lokal in HiFiPlayer). Die
// Lage rechnet weiter die Engine (lib/playerEngine.js handleTimeUpdate und seek); diese Klasse hält nur fest, was sie
// liefert und was das Audio-Element meldet.
import * as engine from "../lib/playerEngine.js";
import type { Medium } from "./kanzel";

/** so lange nach dem Loslassen der Spulbahn bleibt die Lage stehen, bis die Engine die neue Stelle meldet */
const NACH_SPULEN_MS = 300;
/** Fehler 4 (Quelle nicht nutzbar) tritt beim Wechsel der Quelle kurz auf; erst wenn danach nichts lädt, gilt er */
const FEHLER_4_MS = 1500;

export class Wiedergabe {
  zeit = $state(0);
  dauer = $state(0);
  /** Lage auf der Spulbahn, 0 bis 100 */
  lage = $state(0);
  zieht = $state(false);
  sucht = $state(false);
  medium = $state<Medium>("ruhe");
  fehlerCode = $state<number | null>(null);
  /** Sekunden, die der laufende Sender schon gehört wird (ohne Pausen) */
  hoerdauer = $state(0);

  private hatGespielt = false;
  private loslassen: ReturnType<typeof setTimeout> | null = null;
  private fehlerUhr: ReturnType<typeof setTimeout> | null = null;

  // ─── Zeit ───
  zeitAktualisieren(): void {
    if (this.zieht || this.sucht) return;
    const r = engine.handleTimeUpdate();
    if (!r) return;
    this.zeit = r.currentTime;
    this.dauer = r.duration;
    this.lage = r.seekPosition;
  }

  // ─── Spulbahn: Ziehen hält die Anzeige an, Loslassen springt ───
  ziehenBeginnen(): void {
    this.zieht = true;
    if (this.loslassen) clearTimeout(this.loslassen);
    this.loslassen = null;
  }

  ziehen(lage: number): void {
    if (!this.zieht) this.ziehenBeginnen();
    this.lage = lage;
  }

  /** Loslassen ohne neue Stelle (nur angetippt): Anzeige wieder freigeben */
  freigeben(): void {
    if (!this.zieht || this.loslassen) return;
    this.loslassen = setTimeout(() => { this.zieht = false; this.loslassen = null; }, NACH_SPULEN_MS);
  }

  springen(): void {
    if (this.loslassen) clearTimeout(this.loslassen);
    engine.seek(this.lage);
    // erst danach freigeben, sonst setzt die nächste Zeitmeldung die alte Lage zurück
    this.loslassen = setTimeout(() => { this.zieht = false; this.loslassen = null; }, NACH_SPULEN_MS);
  }

  // ─── Medium: was das Audio-Element meldet ───
  laden(): void {
    this.fehlerUhrAus();
    this.hatGespielt = false;
    this.medium = "laedt";
    this.fehlerCode = null;
  }

  warten(): void {
    if (this.medium !== "fehler") this.medium = this.hatGespielt ? "puffert" : "laedt";
  }

  spielen(): void {
    this.fehlerUhrAus();
    this.hatGespielt = true;
    this.medium = "spielt";
    this.fehlerCode = null;
  }

  fehler(code: number | undefined): void {
    if (!code) return;
    this.fehlerUhrAus();
    if (code === 4) {
      // wie die Engine: beim Wechsel der Quelle vorübergehend; bleibt er stehen, ist die Quelle nicht nutzbar
      this.fehlerUhr = setTimeout(() => { this.medium = "fehler"; this.fehlerCode = 4; }, FEHLER_4_MS);
      return;
    }
    this.medium = "fehler";
    this.fehlerCode = code;
  }

  // ─── Hördauer ───
  hoerdauerZaehlen(): void {
    this.hoerdauer++;
  }

  hoerdauerNull(): void {
    this.hoerdauer = 0;
  }

  private fehlerUhrAus(): void {
    if (this.fehlerUhr) clearTimeout(this.fehlerUhr);
    this.fehlerUhr = null;
  }
}
