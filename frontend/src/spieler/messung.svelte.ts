// Messmodus (RAD-143) in der Oberfläche: hängt sich ans Tonelement und an den Zustand der Wiedergabe und schickt, was geschieht,
// alle paar Sekunden ans eigene Backend. Ob er an ist, sagt der Server (Einstellung messmodus); aus, hängt nichts am Ton.
import { appState } from "../lib/store.svelte.js";
import { beiAuffaelligem } from "../lib/playerEngine.js";
import { Messsammler, tonlage } from "../lib/messung";
import { netz } from "../lib/radio/netz";
import { anhaengen, tonelement } from "./tonelement";

const NACHFRAGEN_MS = 30_000, SENDEN_MS = 5_000, LAGE_MS = 10_000, HAENGT_MS = 400;
const TON = ["loadstart", "emptied", "seeking", "seeked", "waiting", "playing", "play", "pause", "stalled", "ended", "ratechange"] as const;

const anfrage = netz();
const sammler = new Messsammler();
const geraet = `${/Mobi|Android|iPhone/.test(navigator.userAgent) ? "Telefon" : "Rechner"} ${Math.random().toString(36).slice(2, 6)}`;
let abbau: (() => void) | null = null;

const lage = () => tonlage(tonelement());

async function senden(): Promise<void> {
  const ereignisse = sammler.nehmen();
  if (!ereignisse.length) return;
  try {
    if (!(await anfrage<{ aktiv: boolean }>("/api/messung", { methode: "POST", daten: { geraet, ereignisse: ereignisse.map((e) => ({ art: e.art, werte: e.werte, vor_ms: Math.max(0, Date.now() - e.um) })) } })).aktiv) schalten(false);
  } catch {
    sammler.zurueck(ereignisse);
  }
}

function beginnen(): () => void {
  const ton = tonelement();
  const ab = [anhaengen(Object.fromEntries(TON.map((n) => [n, () => sammler.ton(n, performance.now(), lage())])))];
  ab.push(anhaengen({ error: () => sammler.merken("ton_fehler", { code: ton.error?.code, text: ton.error?.message, ...lage() }) }));
  beiAuffaelligem((art: string, werte: Record<string, unknown>) => sammler.merken(art, { ...werte, ...lage() }));
  ab.push(() => beiAuffaelligem(null));

  const fenster = (name: string, f: (e: never) => void) => { window.addEventListener(name, f as EventListener); ab.push(() => window.removeEventListener(name, f as EventListener)); };
  fenster("error", (e: ErrorEvent) => sammler.merken("seite_fehler", { text: e.message, wo: `${e.filename?.split("/").pop()}:${e.lineno}` }));
  fenster("unhandledrejection", (e: PromiseRejectionEvent) => sammler.merken("seite_fehler", { text: String(e.reason?.message ?? e.reason) }));
  fenster("offline", () => sammler.merken("netz_weg"));
  fenster("online", () => sammler.merken("netz_da"));
  const sichtbar = () => sammler.merken("sichtbar", { an: document.visibilityState === "visible" });
  document.addEventListener("visibilitychange", sichtbar);
  ab.push(() => document.removeEventListener("visibilitychange", sichtbar));

  // Seite hängt: lange Aufgaben des Browsers (nicht überall messbar)
  if (globalThis.PerformanceObserver?.supportedEntryTypes?.includes("longtask")) {
    const beobachter = new PerformanceObserver((liste) => {
      for (const e of liste.getEntries()) if (e.duration >= HAENGT_MS) sammler.merken("seite_haengt", { dauer_s: Math.round(e.duration) / 1000 });
    });
    beobachter.observe({ entryTypes: ["longtask"] });
    ab.push(() => beobachter.disconnect());
  }

  // Zustand der Wiedergabe: was die Kanzel daraus macht
  ab.push($effect.root(() => {
    $effect(() => {
      sammler.geaendert("zustand", { weg: appState.playerMode, spielt: appState.isPlaying, pause: appState.isPaused, live: appState.isLive,
        nimmt_auf: appState.isRecording, sender: (appState.currentStation as { name?: string } | null)?.name ?? "", werbung_start: !!appState.werbeStart });
    });
  }));

  const uhren = [setInterval(() => void senden(), SENDEN_MS), setInterval(() => { if (!ton.paused) sammler.merken("lage", { ...lage() }); }, LAGE_MS)];
  ab.push(() => uhren.forEach(clearInterval));
  sammler.merken("beginn", { breite: innerWidth, hoehe: innerHeight, seite: location.pathname });
  return () => { for (const f of ab) f(); };
}

function schalten(an: boolean): void {
  if (an === (abbau !== null)) return;
  if (an) abbau = beginnen();
  else { abbau?.(); abbau = null; sammler.leeren(); }
}

async function nachfragen(): Promise<void> {
  try {
    schalten((await anfrage<{ aktiv: boolean }>("/api/messung/aktiv")).aktiv);
  } catch { /* Server weg: so weitermessen wie bisher */ }
}

let gestartet = false;

/** einmal je Seite (PRO) */
export function messungStarten(): void {
  if (gestartet) return;
  gestartet = true;
  void nachfragen();
  setInterval(() => void nachfragen(), NACHFRAGEN_MS);
}

/** gleich nach dem Speichern der Einstellung */
export const messungPruefen = nachfragen;
