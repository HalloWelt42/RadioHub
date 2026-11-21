// Werbung in Podcast-Folgen überspringen (RAD-32): zur laufenden Folge ihre Werbestellen laden; erreicht die
// Wiedergabe eine, springt sie an ihr Ende und meldet es (die Meldung bietet Zurück und anhören, dann gilt die Stelle
// für diese Folge als angehört). Ob übersprungen wird, sagt das Abo (Schalter "Werbung überspringen"). Die Datei bleibt
// vollständig. Hängt am einen Tonelement der Seite, gleich ob Rechner oder Telefon.
import { untrack } from "svelte";
import { appState } from "../lib/store.svelte.js";
import { aboliste, werbequelle, type Werbestelle } from "../lib/podcasts";
import { anhaengen, tonelement } from "./tonelement";
import { werbehinweis } from "./werbehinweis.svelte";

/** so lange steht der Hinweis */
const HINWEIS_MS = 9000;
/** so nah am Ende einer Stelle wird nicht mehr gesprungen (der Sprung würde nur Ruckeln) */
const RAND_S = 0.6;

class Werbesprung {
  folgeId = $state<number | null>(null);
  stellen = $state<Werbestelle[]>([]);
  /** zuletzt übersprungene Stelle, solange der Hinweis steht */
  hinweis = $state<Werbestelle | null>(null);
  private angehoert = new Set<number>();
  private vorgemerkt: { folgeId: number; von: number } | null = null;
  private uhr: ReturnType<typeof setTimeout> | undefined;
  private lauf = 0;

  /** gilt das Überspringen für die laufende Folge (Schalter des Abos, ohne Abo an) */
  get an(): boolean {
    const aboId = (appState.currentEpisode as { podcast_id?: number } | null)?.podcast_id;
    return aboId === undefined ? false : aboliste.abo(aboId)?.werbungUeberspringen !== false;
  }

  async folgen(folgeId: number | null): Promise<void> {
    const meiner = ++this.lauf;
    if (folgeId !== this.folgeId) this.angehoert.clear();
    this.folgeId = folgeId;
    this.stellen = [];
    werbehinweis.stellen = [];
    if (folgeId === null) return;
    try {
      const r = await werbequelle.stellen(folgeId);
      if (meiner !== this.lauf) return;
      this.stellen = r.stellen;
      werbehinweis.stellen = r.stellen.map(({ von, bis }) => ({ von, bis }));
      this.vormerkenAnwenden();
    } catch {
      // ohne Stellen wird eben nichts übersprungen
    }
  }

  /** nach Änderungen (Stelle gesetzt, verworfen, Suche) die laufende Folge neu laden */
  neu(folgeId: number): void {
    if (folgeId === this.folgeId) void this.folgen(folgeId);
  }

  pruefen(ton: HTMLAudioElement): void {
    if (!this.stellen.length || !this.an || ton.paused || ton.seeking) return;
    const t = ton.currentTime;
    const s = this.stellen.find((x) => t >= x.von && t < x.bis - RAND_S && !this.angehoert.has(x.id));
    if (!s) return;
    ton.currentTime = s.bis;
    this.zeigen(s);
  }

  private zeigen(s: Werbestelle): void {
    this.hinweis = s;
    werbehinweis.jetzt = { dauer: s.bis - s.von, herkunft: s.herkunft, zurueck: () => this.zurueck(), schliessen: () => this.schliessen() };
    clearTimeout(this.uhr);
    this.uhr = setTimeout(() => this.schliessen(), HINWEIS_MS);
  }

  /** eine Stelle bewusst hören (Anhören im Detail): die dort beginnende wird nicht übersprungen, auch wenn die
   *  Folge gerade erst startet (dann gilt es, sobald ihre Stellen geladen sind) */
  durchlassen(folgeId: number, von: number): void {
    this.vorgemerkt = { folgeId, von };
    this.vormerkenAnwenden();
  }

  private vormerkenAnwenden(): void {
    const v = this.vorgemerkt;
    if (!v || v.folgeId !== this.folgeId || !this.stellen.length) return;
    for (const x of this.stellen) if (Math.abs(x.von - v.von) < 0.5) this.angehoert.add(x.id);
    this.vorgemerkt = null;
  }

  /** Zurück an den Anfang der eben übersprungenen Stelle; sie gilt dann als angehört */
  zurueck(): void {
    const s = this.hinweis;
    if (!s) return;
    this.angehoert.add(s.id);
    tonelement().currentTime = s.von;
    this.schliessen();
  }

  schliessen(): void {
    clearTimeout(this.uhr);
    this.hinweis = null;
    werbehinweis.jetzt = null;
  }
}

export const werbesprung = new Werbesprung();

let gestartet = false;

/** einmal je Seite: der laufenden Folge folgen und am Tonelement prüfen (Rechner und Telefon rufen es beim Aufbau) */
export function werbesprungStarten(): void {
  if (gestartet) return;
  gestartet = true;
  $effect.root(() => {
    $effect(() => {
      const id = (appState.currentEpisode as { id?: number } | null)?.id ?? null;
      untrack(() => void werbesprung.folgen(id));
    });
  });
  const ton = tonelement();
  anhaengen({ timeupdate: () => werbesprung.pruefen(ton) });
}
