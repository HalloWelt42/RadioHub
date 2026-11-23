// Werbung im Radio überspringen (RAD-33): spielt ein Sender aus dem Zeitversatz, kennt der Puffer die Werbestellen aus
// den Sendedaten (Sekunden des Tons). Erreicht die Wiedergabe eine, springt sie an ihr Ende, wenn es schon im Puffer
// liegt, sonst schaltet sie stumm, bis die Stelle vorbei ist; der Hinweis sagt es, mit Zurück und anhören bzw. Ton an
// (danach gilt die Stelle als angehört). Den Spot beim Verbinden wartet die Engine ab (appState.werbeStart); hier steht
// nur sein Hinweis mit Trotzdem hören. Was zu tun ist, entscheiden die Regeln in lib/radio/sendewerbung.ts. Hängt am
// einen Tonelement der Seite, gleich ob Rechner oder Telefon.
import { untrack } from "svelte";
import { appState } from "../lib/store.svelte.js";
import { springeZuPuffer, tonZuPuffer, vorabHoeren } from "../lib/playerEngine.js";
import { herkunftVon, stellenSchluessel, werbetat, type Pufferstand, type Werbestelle } from "../lib/radio/sendewerbung";
import { stummSetzen, stummWegen } from "../lib/stumm";
import { anhaengen, tonelement } from "./tonelement";
import { werbehinweis } from "./werbehinweis.svelte";

/** so lange steht der Hinweis nach einem Sprung */
const HINWEIS_MS = 9000;

type Puffer = Pufferstand & { session_id?: string };

const dauerVon = (s: Werbestelle): number | null =>
  s.angekuendigt_ms ? s.angekuendigt_ms / 1000 : s.bis !== null ? s.bis - s.von : null;

class Radiowerbung {
  private angehoert = new Set<string>();
  private sitzung: string | null = null;
  private uhr: ReturnType<typeof setTimeout> | undefined;

  private get puffer(): Puffer | null {
    if (appState.playerMode !== "hls" || !appState.currentStation || appState.currentEpisode) return null;
    return (appState.hlsStatus as Puffer | null) ?? null;
  }

  private sitzungPruefen(p: Puffer | null): void {
    const id = p?.session_id ?? null;
    if (id !== this.sitzung) {
      this.sitzung = id;
      this.angehoert.clear();
    }
  }

  pruefen(ton: HTMLAudioElement): void {
    const p = this.puffer;
    this.sitzungPruefen(p);
    if (!p) return this.aufheben();
    if (ton.paused || ton.seeking) return;
    const t = tonZuPuffer(ton.currentTime);
    if (t === null) return;
    const tat = werbetat(t, p, (s) => this.angehoert.has(stellenSchluessel(s)));
    if (tat.art === "springen") {
      this.tonAn();
      if (springeZuPuffer(tat.nach)) this.uebersprungen(tat.stelle);
    } else if (tat.art === "stumm") {
      stummSetzen("werbung", true);
      const s = tat.stelle;
      werbehinweis.jetzt = { art: "stumm", dauer: dauerVon(s), rest: tat.rest, herkunft: herkunftVon(s), werbender: s.werbender,
                             anhoeren: () => this.anhoeren(s) };
    } else if (stummWegen("werbung") || werbehinweis.jetzt?.art === "stumm") {
      this.tonAn();
      if (werbehinweis.jetzt?.art === "stumm") werbehinweis.jetzt = null;
    }
  }

  private uebersprungen(s: Werbestelle): void {
    werbehinweis.jetzt = { art: "uebersprungen", dauer: dauerVon(s), herkunft: herkunftVon(s), werbender: s.werbender,
                           anhoeren: () => this.zurueck(s), schliessen: () => this.schliessen() };
    clearTimeout(this.uhr);
    this.uhr = setTimeout(() => this.schliessen(), HINWEIS_MS);
  }

  /** Zurück an den Anfang der übersprungenen Stelle; sie gilt dann als angehört */
  private zurueck(s: Werbestelle): void {
    this.angehoert.add(stellenSchluessel(s));
    springeZuPuffer(s.von);
    this.schliessen();
  }

  /** Ton an: die laufende Stelle doch hören */
  private anhoeren(s: Werbestelle): void {
    this.angehoert.add(stellenSchluessel(s));
    this.tonAn();
    this.schliessen();
  }

  /** Hinweis zum Spot beim Verbinden (die Engine wartet ihn ab) */
  verbinden(start: { stelle: Werbestelle; rest: number | null } | null): void {
    if (!start) {
      if (werbehinweis.jetzt?.art === "verbinden") werbehinweis.jetzt = null;
      return;
    }
    const s = start.stelle;
    werbehinweis.jetzt = { art: "verbinden", dauer: dauerVon(s), rest: start.rest, herkunft: herkunftVon(s), werbender: s.werbender,
                           anhoeren: () => {
                             this.sitzungPruefen(this.puffer ?? (appState.hlsStatus as Puffer | null));
                             this.angehoert.add(stellenSchluessel(s));
                             vorabHoeren();
                             werbehinweis.jetzt = null;
                           } };
  }

  private tonAn(): void {
    stummSetzen("werbung", false);
  }

  private aufheben(): void {
    this.tonAn();
    if (werbehinweis.jetzt && werbehinweis.jetzt.art !== "uebersprungen" && !appState.werbeStart) werbehinweis.jetzt = null;
  }

  schliessen(): void {
    clearTimeout(this.uhr);
    if (werbehinweis.jetzt?.art === "uebersprungen") werbehinweis.jetzt = null;
  }
}

export const radiowerbung = new Radiowerbung();

let gestartet = false;

/** einmal je Seite (PRO): dem Spot beim Verbinden folgen und am Tonelement prüfen */
export function radiowerbungStarten(): void {
  if (gestartet) return;
  gestartet = true;
  $effect.root(() => {
    $effect(() => {
      const start = appState.werbeStart as { stelle: Werbestelle; rest: number | null } | null;
      untrack(() => radiowerbung.verbinden(start));
    });
  });
  const ton = tonelement();
  anhaengen({ timeupdate: () => radiowerbung.pruefen(ton) });
}
