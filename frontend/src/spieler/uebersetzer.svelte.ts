// Die Übersetzerstimme (RAD-130): spielt die gesprochenen Absätze des Mitlesens nacheinander. Vom Einschalten bis zum Ausschalten
// ist das Radio stumm und läuft weiter (Puffer und Aufnahme merken nichts): der Sender spricht nie in die Stimme hinein, auch
// nicht, während sie auf den nächsten Absatz wartet. Pause am Radio hält sie an, die Lautstärke ist die des Radios.
import { appState } from "../lib/store.svelte.js";
import { mitlesen } from "../lib/radio/mitlesen.svelte";
import { naechster } from "../lib/radio/stimmplan";
import { stummSetzen } from "../lib/stumm";
import { tonelement } from "./tonelement";

const TAKT_MS = 400;
/** kürzester gültiger Ton: gibt das Abspielen im Klick frei, der die Stimme einschaltet */
const STILLE = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=";

class Uebersetzer {
  an = $state(false);
  /** der Absatz, der gerade gesprochen wird */
  spricht = $state<number | null>(null);
  private zuletzt = 0;
  private begonnen = false;
  /** der Server hat das Einschalten bestätigt; vorher sagt sein Stand noch nichts */
  private bestaetigt = false;
  private ton: HTMLAudioElement | null = null;
  private takt: ReturnType<typeof setInterval> | undefined;

  async schalten(an: boolean): Promise<void> {
    if (an) this.starten();
    else this.halt();
    try {
      await mitlesen.sprechen(an);
      this.bestaetigt = true;
    } catch (f) {
      this.halt();
      throw f;
    }
  }

  private starten(): void {
    this.an = true;
    this.begonnen = this.bestaetigt = false;
    stummSetzen("uebersetzer", true);
    // ab jetzt: was schon gelesen ist, wird nicht nachgesprochen, außer den letzten beiden als Vorlauf
    this.zuletzt = mitlesen.absaetze.filter((a) => a.uebersetzung).at(-3)?.nr ?? 0;
    this.ton ??= new Audio();
    this.ton.preservesPitch = true;
    this.ton.onended = this.ton.onerror = () => this.fertig();
    this.ton.src = STILLE;
    void this.ton.play().catch(() => undefined);
    this.takt = setInterval(() => this.pruefen(), TAKT_MS);
  }

  /** Aus: sofort still, das Original ist wieder da */
  halt(): void {
    clearInterval(this.takt);
    this.an = false;
    this.spricht = null;
    this.begonnen = false;
    this.ton?.pause();
    stummSetzen("uebersetzer", false);
  }

  private fertig(): void {
    if (this.spricht === null) return;
    this.zuletzt = this.spricht;
    this.spricht = null;
    this.pruefen();
  }

  private pruefen(): void {
    if (!this.an || !this.ton) return;
    if (!this.bestaetigt) return;
    if (!mitlesen.uuid || !mitlesen.stand?.laeuft || !mitlesen.stand.sprechen) return this.halt();
    const radio = tonelement();
    this.ton.volume = Math.min(1, Math.max(0, appState.volume / 100));
    if (this.spricht !== null) {
      if (radio.paused && !this.ton.paused) this.ton.pause();
      else if (!radio.paused && this.ton.paused) void this.ton.play().catch(() => undefined);
      return;
    }
    if (radio.paused) return;
    const s = naechster(mitlesen.absaetze, this.zuletzt, this.begonnen);
    if (!s) return;
    this.begonnen = true;
    this.spricht = s.nr;
    this.ton.src = `/api/mitlesen/ton/${s.nr}`;
    this.ton.playbackRate = s.tempo;
    void this.ton.play().catch(() => this.fertig());
  }
}

export const uebersetzer = new Uebersetzer();
