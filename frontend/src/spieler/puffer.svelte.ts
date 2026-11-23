// Der Zeitversatz mit seinen Abschnitten (RAD-46, Entwurf mockups/radio-filter/puffer.html): Titel, Werbung und
// Einschübe im Puffer (vom Server, Grenzen nach dem Feinschnitt), die Stelle, die man hört, Springen zwischen Titeln,
// Aufnahme ab einem Titel und einen Bereich als Aufnahme sichern. Eine Instanz für Kanzel, Großansicht und Telefon;
// sie hängt am einen Tonelement der Seite und lädt die Abschnitte, solange ein Sender aus dem Zeitversatz spielt.
import { untrack } from "svelte";
import { appState } from "../lib/store.svelte.js";
import * as engine from "../lib/playerEngine.js";
import { netz, type Anfrage } from "../lib/radio/netz";
import { formatTimeShort } from "../lib/formatters.js";
import { bei, naechster, vorheriger, type Abschnitt } from "../lib/radio/abschnitte";
import { anhaengen, tonelement } from "./tonelement";
import { t } from "../lib/i18n.svelte.js";

/** so oft kommen die Abschnitte neu (ein neuer Titel, das wachsende laufende Stück) */
const LADEN_MS = 8000;
/** so weit darf der gemessene Abstand zu live vom gezeigten abweichen, bevor er neu gilt (Sekunden): mehr als ein
 *  Schritt der Live-Kante (der Stand kommt alle 2 s), weniger als der kleinste Sprung beim Spulen */
const HINTER_RUHE_S = 3;

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
  /** Abstand der Stelle zu live in ganzen Sekunden, beruhigt (RAD-54): die Live-Kante wächst in ganzen Stücken, die
   *  Stelle fließend, gemessen pendelt der Abstand um eine Sekunde, obwohl er beim Hören gleich bleibt. Er gilt neu erst
   *  bei einer größeren Abweichung (Springen, Spulen, Stocken), so zählt keine Anzeige vor und zurück. */
  hinter = $state(0);
  /** der erste Messwert einer Sitzung gilt sofort */
  private hinterGemessen = false;
  private sitzung: string | null = null;
  private ladetakt: ReturnType<typeof setInterval> | undefined;

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

  /** Zahl der Titel im Puffer (ohne Werbung und Einschübe) */
  get titelZahl(): number {
    return this.geladen.filter((a) => a.art === "titel").length;
  }

  /** Uhrzeit, zu der Sekunde 0 des Puffers gesendet wurde: die Sitzung heißt nach ihrem Beginn ("JJJJMMTT_HHMMSS") */
  get beginn(): number | null {
    const m = /^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/.exec(String(this.status?.session_id ?? ""));
    return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]).getTime() : null;
  }

  /** Uhrzeit einer Sekunde des Puffers (Stunde und Minute); ohne bekannten Beginn der Abstand zu live */
  uhr(sekunde: number): string {
    const b = this.beginn;
    return b === null ? `-${formatTimeShort(Math.max(0, this.ende - sekunde))}`
      : new Date(b + sekunde * 1000).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  }

  /** Name eines Abschnitts in allen Ansichten: Titel, Werbung (am Anfang: beim Verbinden) oder Einschub */
  benennen(a: Abschnitt): string {
    if (a.art === "werbung") return a.von <= this.anfang + 1 ? t("puffer.werbungBeimVerbinden") : t("puffer.werbung");
    return a.art === "einschub" ? t("puffer.einschub") : a.titel;
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
    this.hinterGemessen = false;
    clearInterval(this.ladetakt);
    this.ladetakt = undefined;
    if (id) {
      void this.laden();
      this.ladetakt = setInterval(() => void this.laden(), LADEN_MS);
    }
  }

  stelleMessen(ton: HTMLAudioElement): void {
    if (!this.aktiv) {
      this.stelle = null;
      return;
    }
    this.stelle = appState.isLive ? this.ende : (engine.tonZuPuffer(ton.currentTime) ?? this.ende);
    this.hinterMessen(false);
  }

  private hinterMessen(neu: boolean): void {
    const roh = this.stelle === null || appState.isLive ? 0 : Math.max(0, this.ende - this.stelle);
    if (neu || !this.hinterGemessen || Math.abs(roh - this.hinter) >= HINTER_RUHE_S || roh === 0) this.hinter = Math.round(roh);
    if (this.stelle !== null) this.hinterGemessen = true;
  }

  springen(sekunde: number): void {
    if (!engine.springeZuPuffer(sekunde)) return;
    this.stelle = sekunde;
    this.hinterMessen(true);
  }

  vorher(): void {
    const ziel = this.stelle === null ? null : vorheriger(this.abschnitte, this.stelle);
    if (ziel !== null) this.springen(ziel);
  }

  /** zum nächsten Titel; false, wenn keiner mehr kommt (die Stelle liegt im laufenden) */
  weiter(): boolean {
    const ziel = this.stelle === null ? null : naechster(this.abschnitte, this.stelle);
    if (ziel !== null) this.springen(ziel);
    return ziel !== null;
  }

  /** Aufnahme ab dem Anfang eines Abschnitts (Sekunden des Puffers), läuft bis Stopp; ohne `von` am Anfang des
   *  laufenden Titels (wie die Taste Aufnahme) */
  async aufnehmenAb(von?: number): Promise<Aufnahmestart> {
    const r = await this.a<Aufnahmestart>("/api/hls/aufnahme", { methode: "POST", daten: { von_s: von ?? null } });
    await engine.checkAndRecoverRecordingState();
    return r;
  }

  /** den fertigen Titel als eigene Aufnahme sichern (RAD-132), auch während eine Aufnahme läuft */
  async titelSichern(a: Abschnitt): Promise<void> {
    const r = await this.a<{ session_id: string }>("/api/hls/titel", { methode: "POST", daten: { bei_s: (a.von + a.bis) / 2 } });
    this.geladen = this.geladen.map((x) => (x.von === a.von ? { ...x, gesichert: r.session_id } : x));
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
