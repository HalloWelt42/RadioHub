// Typisierte Sicht auf appState für die Kanzel: lib/store.svelte.js ist JavaScript und legt viele Felder mit null an,
// TypeScript hielte sie sonst für "never". Dasselbe Objekt, nur mit den Feldern, die Kanzel und Tonausgang lesen und
// schreiben.
import { appState } from "../lib/store.svelte.js";
import type { HlsStand } from "./kanzel";

interface Sender { uuid: string; name: string; icy?: boolean; codec?: string; bitrate?: number }
interface Podcast { id?: number; title?: string }
interface Folge { id?: number; title?: string; duration?: number; podcast?: Podcast | null }
interface Aufnahme { path?: string; name?: string; session_id?: string; station_name?: string; source?: string }

export interface AppZustand {
  isPlaying: boolean;
  isPaused: boolean;
  isRecording: boolean;
  playerMode: string;
  isLive: boolean;
  volume: number;
  currentStation: Sender | null;
  currentEpisode: Folge | null;
  currentRecording: Aufnahme | null;
  streamTitle: string | null;
  streamQuality: { inputCodec?: string; inputBitrate?: number; outputBitrate?: number } | null;
  hlsStatus: HlsStand | null;
  hlsActive: boolean;
  currentSegment: number | null;
  recordingElapsed: number;
  recordingStoppt: boolean;
  recordingStationUuid: string | null;
  recordingVorlaufS: number;
  recordingIcyCount: number;
  canPlayDirect: boolean;
  canPlayHLS: boolean | null;
  playMode: string;
  /** Tempo der Folge (0,75 bis 2) */
  podcastSpeed: number;
  stations: Sender[];
  podcastPlaylist: Folge[];
  podcastPlaylistPodcast: Podcast | null;
  currentEpisodeIndex: number;
  recordingPlaylist: Aufnahme[];
  /** Sprung zur Quelle; varianten: beim Sender gleich seine Varianten aufklappen (andere Variante wählen) */
  sourceJumpRequest: { type: "radio" | "podcast" | "recording"; id: string | number | undefined; ts: number; varianten?: boolean } | null;
}

export const app = appState as unknown as AppZustand;
