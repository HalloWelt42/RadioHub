// Aktionen der Kanzel: dieselben Wege in Engine und Store wie früher in HiFiPlayer (Wiedergabe, Pause, Stopp, Aufnahme,
// Senderwechsel, Spulen, Live, Original oder Zeitversatz, Reihenfolge, Bitrate des Zeitversatzes, Sprung zur Quelle).
// Die Bausteine rufen nur diese Funktionen; die Technik der Wiedergabe bleibt in lib/playerEngine.js.
import { actions } from "../lib/store.svelte.js";
import { app } from "./app";
import * as engine from "../lib/playerEngine.js";
import { naechsteReihenfolge } from "./kanzel";
import { tonelement } from "./tonelement";
import { puffer } from "./puffer.svelte";
import { blaetternInAufnahme, springtTitel } from "./kanzel";

/** Die Taste Spielen (und die Leertaste), streng nach einer Regel (Nutzer 20.11.2026): sie bleibt Spielen und beendet
 *  nie; beendet wird nur über Stopp. Gestoppt startet sie die Quelle, beim Spielen hält sie an, in der Pause geht es
 *  weiter (Zeitversatz, Folge und Aufnahme an derselben Stelle, ein direkter Strom neu ab live, playerEngine.resume).
 *  Während einer Aufnahme tut sie nichts. */
export function spielenOderPause(): void {
  if (app.isRecording) return;
  if (app.isPaused) engine.resume();
  else if (app.isPlaying) engine.pause();
  else quelleStarten();
}

/** Die geladene Quelle an der Stelle `sekunde` hören: springen und, war sie angehalten, weiterspielen. Liefert false,
 *  wenn gerade nichts geladen ist (dann muss die Quelle erst gestartet werden). */
export function hoerenAb(sekunde: number): boolean {
  if (app.isRecording || !(app.isPlaying || app.isPaused)) return false;
  const ton = tonelement();
  ton.currentTime = sekunde;
  if (app.isPaused) engine.resume();
  // angehalten, ohne dass die Kanzel es weiß (etwa über die Medientasten des Rechners): das Tonelement selbst spielen
  else if (ton.paused) void ton.play().catch(() => {});
  return true;
}

/** Die gewählte Quelle von vorn laden (auch: neu verbinden nach einem Fehler) */
export function quelleStarten(): void {
  if (app.currentStation) engine.playStation(app.currentStation);
  else if (app.currentEpisode) engine.playPodcast(app.currentEpisode, app.currentEpisode?.podcast);
  else if (app.currentRecording) engine.playRecording(app.currentRecording);
}

/** Stopp beendet das Hören und eine laufende Aufnahme (RAD-83, Nutzer 22.11.2026) */
export async function stoppen(): Promise<void> {
  if (app.isRecording) await actions.stopRecording();
  engine.stop();
}

/** Taste Aufnahme: starten, läuft sie schon, beenden */
export function aufnehmen(): void {
  if (app.isRecording) actions.stopRecording();
  else actions.startRecording();
}

/** Zurück (RAD-60): hinter live im Zeitversatz an den Anfang des Titels, kurz nach dem Anfang zum vorherigen;
 *  sonst der vorherige Sender (Folge, Aufnahme) */
export function zurueck(): void {
  if (app.isRecording) {
    if (blaetternInAufnahme(app, -1)) puffer.vorher();
    return;
  }
  if (springtTitel(app)) puffer.vorher();
  else actions.navigatePrev();
}

/** Vor (RAD-60): hinter live im Zeitversatz zum nächsten Titel, nach dem letzten an live; sonst der nächste Sender */
export function vor(): void {
  if (app.isRecording) {
    if (blaetternInAufnahme(app, 1) && !puffer.weiter()) live();
    return;
  }
  if (!springtTitel(app)) actions.navigateNext();
  else if (!puffer.weiter()) live();
}

/** lang gedrückt: immer der Sender (Folge, Aufnahme), auch im Zeitversatz; während einer Aufnahme wie kurz (RAD-83) */
export function zurueckSender(): void {
  if (app.isRecording) zurueck();
  else actions.navigatePrev();
}

export function vorSender(): void {
  if (app.isRecording) vor();
  else actions.navigateNext();
}

export function spulen(sekunden: number): void {
  engine.skip(sekunden);
}

export function live(): void {
  engine.goLive();
}

export function lautstaerke(wert: number): void {
  engine.setVolume(wert);
}

export function reihenfolgeWeiter(): void {
  app.playMode = naechsteReihenfolge(app.playMode);
}

/** Original oder Zeitversatz; die Kanzel hält die Taste gedrückt, bis der neue Modus gilt */
export function modusWechseln(): string {
  const vorher = app.playerMode;
  engine.toggleStreamMode();
  return vorher;
}

// ─── Bitrate des Zeitversatzes: Vorgabe des Nutzers, dauerhaft im Browser ───
const BITRATE_SCHLUESSEL = "radiohub_bitrate_override";

export function bitrateLesen(): number | null {
  try {
    const wert = JSON.parse(localStorage.getItem(BITRATE_SCHLUESSEL) || "null");
    return typeof wert === "number" ? wert : null;
  } catch {
    return null;
  }
}

/** Neue Bitrate merken; läuft der Zeitversatz, startet er mit ihr neu (höchstens 15 Sekunden, bis er wieder steht) */
export async function bitrateSetzen(wert: number | null): Promise<void> {
  if (wert !== null) localStorage.setItem(BITRATE_SCHLUESSEL, JSON.stringify(wert));
  else localStorage.removeItem(BITRATE_SCHLUESSEL);
  if (app.playerMode !== "hls" || !app.currentStation) return;
  await engine.restartHLS();
  for (let i = 0; i < 30 && !app.hlsActive; i++) await new Promise((r) => setTimeout(r, 500));
}

// ─── Sprung zur Quelle: Sender, Podcast oder Aufnahme in ihrem Bereich ───
export function zurQuelle(varianten = false): void {
  const modus = app.playerMode;
  const ts = Date.now();
  if (app.currentEpisode && (modus === "podcast" || modus === "hls")) {
    const podcast = app.podcastPlaylistPodcast;
    app.sourceJumpRequest = { type: "podcast", id: podcast?.id, ts };
    actions.navigateTo(podcast?.id ? `/podcasts/${podcast.id}` : "/podcasts");
  } else if (modus === "hls" || modus === "direct") {
    const uuid = app.currentStation?.uuid;
    app.sourceJumpRequest = { type: "radio", id: uuid, ts, varianten };
    actions.navigateTo(uuid ? `/radio/${uuid}` : "/radio");
  } else if (modus === "recording") {
    const aufnahme = app.currentRecording;
    app.sourceJumpRequest = { type: "recording", id: aufnahme?.session_id, ts };
    actions.navigateTo(aufnahme?.session_id ? `/aufnahmen/${aufnahme.session_id}` : "/aufnahmen");
    setTimeout(() => {
      document.querySelector(".session-item.playing, .segment-entry.playing")?.scrollIntoView({ block: "center", behavior: "smooth" });
    }, 150);
  }
}

/** Andere Variante des Senders wählen (nach einem Fehler: Codec, Verbindung): zum Sender, seine Varianten aufgeklappt */
export function andereVariante(): void {
  zurQuelle(true);
}
