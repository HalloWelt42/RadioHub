// Der Zeitversatz mit seinen Abschnitten (RAD-46, Entwurf mockups/radio-filter/puffer.html): Titel, Werbung und
// Einschübe im Puffer (vom Server, Grenzen nach dem Feinschnitt), die Stelle, die man hört, Springen zwischen Titeln,
// Aufnahme ab einem Titel und einen Bereich als Aufnahme sichern. Eine Instanz für Kanzel, Großansicht und Telefon;
// sie hängt am einen Tonelement der Seite und lädt die Abschnitte, solange ein Sender aus dem Zeitversatz spielt.
import { untrack } from "svelte";
import { appState } from "../lib/store.svelte.js";
import * as engine from "../lib/playerEngine.js";
import { netz, type Anfrage } from "../lib/radio/netz";
import { bei, naechster, vorheriger, type Abschnitt } from "../lib/radio/abschnitte";
import { anhaengen, tonelement } from "./tonelement";

/** so oft kommen die Abschnitte neu (ein neuer Titel, das wachsende laufende Stück) */
const LADEN_MS = 8000;

interface Pufferstatus {
  session_id?: string;
  first_segment?: number | null;
  last_segment?: number | null;
  segment_duration?: number;
  max_segments?: number;
}

export interface Aufnahmestart {
  success: boolean;
  session_id?: string;
  vorlauf_s?: number;
}

class Puffer {
  /** so, wie der Server sie zuletzt geliefert hat */
  private geladen = $state<Abschnitt[]>([]);
  /** Sekunde des Puffers, die man hört; null ohne Zeitversatz */
  stelle = $state<number | null>(null);
  private sitzung: string | null = null;
  private uhr: ReturnType<typeof setInterval> | undefined;

  constructor(private readonly a: Anfrage = netz()) {}

  private get status(): Pufferstatus | null {
    return (appState.hlsStatus as Pufferstatus | null) ?? null;
  }

  /** spielt ein Sender aus dem Zeitversatz (nicht eine Folge im Puffer) */
  get aktiv(): boolean {
    return appState.playerMode === "hls" && !!appState.currentStation && !appState.currentEpisode && !!appState.hlsActive;
  }

  get dauerJeStueck(): number {
    return this.status?.segment_duration || 1;
  }

  /** ältester Ton im Puffer */
  get anfang(): number {
    return (this.status?.first_segment ?? 0) * this.dauerJeStueck;
  }

  /** Live-Kante */
  get ende(): number {
    const s = this.status;
    return s?.last_segment != null ? (s.last_segment + 1) * this.dauerJeStueck : 0;
  }

  /** größter Puffer (Maßstab des Balkens in der Kanzel) */
  get groesste(): number {
    return (this.status?.max_segments || 0) * this.dauerJeStueck;
  }

  /** die Abschnitte; der laufende reicht bis zur Live-Kante (er wächst zwischen zwei Abrufen weiter) */
  get abschnitte(): Abschnitt[] {
    const ende = this.ende;
    return this.geladen.map((a) => (a.laufend && ende > a.bis ? { ...a, bis: ende } : a));
  }

  get laufend(): Abschnitt | null {
    return this.stelle === null ? null : bei(this.abschnitte, this.stelle);
  }

  async laden(): Promise<void> {
    if (!this.aktiv) return;
    try {
      const r = await this.a<{ abschnitte: Abschnitt[] }>("/api/hls/abschnitte");
      if (this.aktiv) this.geladen = r.abschnitte;
    } catch {
      // ohne Abschnitte bleibt der Balken ohne Marken
    }
  }

  /** Sitzung des Puffers gewechselt (anderer Sender, neu verbunden): alte Abschnitte gelten nicht mehr */
  sitzungPruefen(): void {
    const id = this.aktiv ? (this.status?.session_id ?? null) : null;
    if (id === this.sitzung) return;
    this.sitzung = id;
    this.geladen = [];
    clearInterval(this.uhr);
    this.uhr = undefined;
    if (id) {
      void this.laden();
      this.uhr = setInterval(() => void this.laden(), LADEN_MS);
    }
  }

  stelleMessen(ton: HTMLAudioElement): void {
    if (!this.aktiv) {
      this.stelle = null;
      return;
    }
    this.stelle = appState.isLive ? this.ende : (engine.tonZuPuffer(ton.currentTime) ?? this.ende);
  }

  springen(sekunde: number): void {
    if (engine.springeZuPuffer(sekunde)) this.stelle = sekunde;
  }

  vorher(): void {
    const ziel = this.stelle === null ? null : vorheriger(this.abschnitte, this.stelle);
    if (ziel !== null) this.springen(ziel);
  }

  weiter(): void {
    const ziel = this.stelle === null ? null : naechster(this.abschnitte, this.stelle);
    if (ziel !== null) this.springen(ziel);
  }

  /** Aufnahme ab dem Anfang eines Abschnitts (Sekunden des Puffers), läuft bis Stopp; ohne `von` am Anfang des
   *  laufenden Titels (wie die Taste Aufnahme) */
  async aufnehmenAb(von?: number): Promise<Aufnahmestart> {
    const r = await this.a<Aufnahmestart>("/api/hls/aufnahme", { methode: "POST", daten: { von_s: von ?? null } });
    await engine.checkAndRecoverRecordingState();
    return r;
  }

  /** Einen Bereich als fertige Aufnahme sichern; sie endet von selbst an seinem Ende */
  async bereichSichern(von: number, bis: number): Promise<Aufnahmestart> {
    const r = await this.a<Aufnahmestart>("/api/hls/aufnahme", { methode: "POST", daten: { von_s: von, bis_s: bis } });
    await engine.checkAndRecoverRecordingState();
    return r;
  }
}

export const puffer = new Puffer();

let gestartet = false;

/** einmal je Seite (App.svelte): der Sitzung des Zeitversatzes folgen und die Stelle am Tonelement messen */
export function pufferStarten(): void {
  if (gestartet) return;
  gestartet = true;
  $effect.root(() => {
    $effect(() => {
      void appState.hlsStatus;
      void appState.playerMode;
      void appState.currentStation;
      untrack(() => puffer.sitzungPruefen());
    });
  });
  const ton = tonelement();
  anhaengen({ timeupdate: () => puffer.stelleMessen(ton), seeked: () => puffer.stelleMessen(ton) });
}
