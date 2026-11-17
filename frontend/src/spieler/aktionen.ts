// Aktionen der Kanzel: dieselben Wege in Engine und Store wie früher in HiFiPlayer (Wiedergabe, Pause, Stopp, Aufnahme,
// Senderwechsel, Spulen, Live, Original oder Zeitversatz, Reihenfolge, Bitrate des Zeitversatzes, Sprung zur Quelle).
// Die Bausteine rufen nur diese Funktionen; die Technik der Wiedergabe bleibt in lib/playerEngine.js.
import { actions } from "../lib/store.svelte.js";
import { app } from "./app";
import * as engine from "../lib/playerEngine.js";
import { naechsteReihenfolge } from "./kanzel";

/** Spielen, anhalten oder fortsetzen; ein direkter Strom lässt sich nicht anhalten, nur beenden */
export function spielenOderAnhalten(): void {
  if (app.isRecording) return;
  if (app.isPlaying && !app.isPaused) {
    if (app.playerMode === "direct") engine.stop();
    else engine.togglePause();
    return;
  }
  if (app.isPaused) {
    engine.resume();
    return;
  }
  quelleStarten();
}

/** Die gewählte Quelle von vorn laden (auch: neu verbinden nach einem Fehler) */
export function quelleStarten(): void {
  if (app.currentStation) engine.playStation(app.currentStation);
  else if (app.currentEpisode) engine.playPodcast(app.currentEpisode, app.currentEpisode?.podcast);
  else if (app.currentRecording) engine.playRecording(app.currentRecording);
}

/** Stopp beendet Hören und Aufnahme */
export function stoppen(): void {
  engine.stop();
}

/** Aufnahme starten; beenden nur über Stopp */
export function aufnehmen(): void {
  if (app.isRecording) return;
  actions.startRecording();
}

export function zurueck(): void {
  if (!app.isRecording) actions.navigatePrev();
}

export function vor(): void {
  if (!app.isRecording) actions.navigateNext();
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
export function zurQuelle(): void {
  const modus = app.playerMode;
  const ts = Date.now();
  if (app.currentEpisode && (modus === "podcast" || modus === "hls")) {
    const podcast = app.podcastPlaylistPodcast;
    app.sourceJumpRequest = { type: "podcast", id: podcast?.id, ts };
    actions.navigateTo(podcast?.id ? `/podcasts/${podcast.id}` : "/podcasts");
  } else if (modus === "hls" || modus === "direct") {
    const uuid = app.currentStation?.uuid;
    app.sourceJumpRequest = { type: "radio", id: uuid, ts };
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
