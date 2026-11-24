/**
 * RadioHub App Store v0.6.1
 * Globaler State mit Svelte 5 Runes
 *
 * v0.6.0: Volume-Persistierung in localStorage
 * v0.5.0: Player-Logik delegiert an playerEngine.js
 *         Neue Felder: isPaused, playerMode, streamQuality, recordingElapsed
 */

import { api } from './api.js';
import * as engine from './playerEngine.js';
import { nachbarstelle } from './reihenfolge.js';
import { dauer } from './aufnahmen/anzeige';
import * as router from './router.js';
import { t } from './i18n.svelte.js';

// === App State ===
export const appState = $state({
  // Navigation
  activeTab: 'radio',
  routeSegments: /** @type {string[]} */ ([]),    // Sub-Pfad-Segmente nach Tab-Prefix (z.B. ['radio', 'filter'] für /setup/radio/filter)

  // Thema, Vorlage und Schriftstufe führt lib/darstellung.svelte.ts

  // Player - Core
  isPlaying: false,
  isPaused: false,
  currentStation: null,
  currentEpisode: null,
  volume: Number(localStorage.getItem('radiohub_volume')) || 70,
  devMode: localStorage.getItem('radiohub_devmode') === 'true',

  // Player - Mode & Quality
  playerMode: 'none',      // 'none' | 'direct' | 'hls' | 'podcast' | 'recording'
  streamQuality: null,      // { inputCodec, inputBitrate, outputBitrate, sampleRate }
  // playerError entfernt - nutzt jetzt das zentrale toast-System

  // Recording
  isRecording: false,
  recordingType: 'none',    // 'none' | 'direct'
  recordingVorlaufS: 0,     // so viel Ton hatte die Aufnahme beim Start (aus dem Puffer, RAD-46)
  recordingStoppt: false,   // die Aufnahme wird gerade beendet (Ablegen dauert einige Sekunden)
  recordingSession: null,
  recordingStationUuid: null,  // Sender der laufenden Aufnahme (sie läuft auch beim Senderwechsel weiter, RAD-46)
  recordingElapsed: 0,
  recordingIcyCount: 0,     // Anzahl erkannter Titelwechsel (live)
  recordingIcyEntries: [],  // [{title, t, ignored, raw_title}] live ICY-Einträge
  recordingEvents: [],      // [{type, t, detail}] Gap/Stall/Codec-Events
  currentRecording: null,   // {path, name, session_id, station_name, date, duration, playUrl}
  /** @type {{ path: string, name: string, session_id?: string, station_name?: string, date?: string, duration?: number, playUrl: string, source?: string }[]} */
  recordingPlaylist: [],    // Titel einer Aufnahme oder Dateien eines Ordners für Vor und Zurück
  playMode: 'linear',       // 'linear' | 'reverse' | 'loop' | 'shuffle' - Wiedergabe-Modus für Playlists

  // Podcast-Playlist
  podcastPlaylist: [],          // [{id, title, audio_url, ...}, ...]
  podcastPlaylistPodcast: null, // Podcast-Objekt für die aktuelle Playlist
  podcastSpeed: 1.0,            // 0.75 | 1.0 | 1.25 | 1.5 | 1.75 | 2.0

  // HLS Buffer
  hlsActive: false,
  hlsStatus: null,
  isLive: true,
  currentSegment: null,

  // Stream Mode Capabilities
  canPlayDirect: true,   // true=ja, false=Codec nicht abspielbar
  canPlayHLS: null,      // null=unbekannt, true=Segmente verfügbar, false=Start fehlgeschlagen
  werbeStart: null,      // RAD-33: Spot beim Verbinden läuft noch ({ stelle, rest }), die Wiedergabe beginnt danach

  // Data
  stations: [],
  favorites: [],
  podcasts: [],

  // Navigation Index (für Blättern)
  currentEpisodeIndex: -1,

  // ICY Now Playing
  streamTitle: null,   // Aktueller ICY-StreamTitle (Musiktitel)

  // HLS-REC Config

  // UI
  toast: null,

  // Source-Navigation Signal (Transport-Label Klick)
  sourceJumpRequest: null  // { type: 'podcast'|'recording'|'radio', id: number, ts: number }
});

// === Actions ===
/** Wer den Nachbarn des laufenden Senders kennt: die Bedienung der sichtbaren Liste (RAD-124). Sie lädt nach; die Liste
 *  hier (appState.stations) ist nur ihr gerade geladener Ausschnitt.
 *  @type {((uuid: string, schritt: -1 | 1) => Promise<any>) | null} */
let senderfolge = null;
export function senderfolgeSetzen(folge) {
  senderfolge = folge;
}

/** Steuert dieses Gerät ein anderes (RAD-96), spielt dort, was man in einer Liste antippt. Nur diese Wege fragen; der Wecker,
 *  die Übergabe und Vor und Zurück spielen immer hier.
 *  @type {((art: string, quelle: any, podcast?: any, stelle?: number) => boolean) | null} */
let umleitung = null;
export function umleitungSetzen(weg) {
  umleitung = weg;
}

async function zumNachbarn(schritt) {
  const jetzt = appState.currentStation;
  if (!jetzt || !senderfolge) return;
  const ziel = await senderfolge(jetzt.uuid, schritt);
  // inzwischen anders gewählt: nichts überfahren
  if (ziel && appState.currentStation?.uuid === jetzt.uuid) await engine.playStation(ziel);
}

/** Zum Nachbarn dessen, was spielt: Folge oder Titel nach der gewählten Reihenfolge (ohne Nachbarn geschieht nichts), sonst Sender
 * @param {-1 | 1} schritt */
function blaettern(schritt) {
  if (appState.currentEpisode && appState.podcastPlaylist.length > 0) {
    const ziel = nachbarstelle(appState.podcastPlaylist.length, appState.currentEpisodeIndex, schritt, appState.playMode);
    if (ziel === null) return;
    appState.currentEpisodeIndex = ziel;
    return engine.playPodcast(appState.podcastPlaylist[ziel], appState.podcastPlaylistPodcast);
  }
  if (appState.playerMode === 'recording') {
    const reihe = appState.recordingPlaylist;
    const ziel = nachbarstelle(reihe.length, reihe.findIndex((x) => x.path === appState.currentRecording?.path), schritt, appState.playMode);
    if (ziel === null) return;
    return engine.playRecording(reihe[ziel]);
  }
  return zumNachbarn(schritt);
}

/** @type {Promise<void> | null} läuft gerade ein Stopp der Aufnahme */
let stoppt = null;

export const actions = {
  // Navigation
  setTab(tab) {
    appState.activeTab = tab;
    const path = router.getDefaultPath(tab);
    appState.routeSegments = router.parsePath(path).segments;
    router.navigate(path);
  },

  navigateTo(path, { replace = false } = {}) {
    const info = router.parsePath(path);
    appState.activeTab = info.tab;
    appState.routeSegments = info.segments;
    router.navigate(path, { replace });
  },

  toggleDevMode() {
    appState.devMode = !appState.devMode;
    localStorage.setItem('radiohub_devmode', String(appState.devMode));
  },

  async initConfig() {
    try {
      // Sprache und Rückblick der Puffer-Aufnahme: eine Stelle für Start und Speichern (RAD-11)
      const { wirkungen } = await import('./einstellungen/wirkung');
      wirkungen(await api.getConfig());
    } catch (e) {
      // ohne Server (Basic) oder nicht erreichbar: Vorgaben
    }
  },

  // Toast
  showToast(message, type = 'info') {
    appState.toast = { message, type };
    setTimeout(() => {
      appState.toast = null;
    }, 3000);
  },

  // === Player (delegiert an Engine) ===

  async playStation(station) {
    await engine.playStation(station);
  },

  /** ein Sender aus einer Liste angetippt */
  async playStationFromList(station) {
    if (umleitung?.('sender', station)) return;
    await engine.playStation(station);
  },

  playEpisode(episode, podcast) {
    engine.playPodcast(episode, podcast);
  },

  playEpisodeFromList(episode, podcast, playlist) {
    if (umleitung?.('folge', episode, podcast)) return;
    appState.podcastPlaylist = playlist || [];
    appState.podcastPlaylistPodcast = podcast || null;
    appState.currentEpisodeIndex = playlist ? playlist.findIndex(e => e.id === episode.id) : -1;
    engine.playPodcast(episode, podcast);
  },

  /** die laufende Folge in einer anderen Fassung weiterhören (leer: Original) */
  folgenfassung(fassung) {
    return engine.folgenfassung(fassung);
  },

  setPodcastSpeed(speed) {
    appState.podcastSpeed = speed;
    engine.setPlaybackRate(speed);
  },

  stop() {
    engine.stop();
  },

  pause() {
    engine.pause();
  },

  resume() {
    engine.resume();
  },

  togglePause() {
    engine.togglePause();
  },

  setVolume(vol) {
    engine.setVolume(vol);
  },

  // Recording-Wiedergabe
  async playRecording(recording, startTime = 0) {
    if (umleitung?.('aufnahme', recording, null, startTime)) return;
    await engine.playRecording(recording, startTime);
  },

  // Recording (delegiert an Engine)
  async startRecording() {
    const result = await engine.startRecording();
    if (result?.success) {
      actions.showToast(t('toast.recGestartet'), 'success');
    } else {
      actions.showToast(t('toast.recFehler'), 'error');
    }
  },

  /** Aufnahme beenden: das Ablegen dauert einige Sekunden (RAD-139). Solange zeigen die Tasten Arbeit, ein zweiter Druck
   *  wartet auf denselben Stopp. */
  stopRecording() {
    stoppt ??= (async () => {
      appState.recordingStoppt = true;
      try {
        const result = await engine.stopRecording();
        if (result?.success) {
          actions.showToast(`${t('toast.recGespeichert')}${result.duration ? ` (${dauer(result.duration)})` : ''}`, 'success');
        } else {
          actions.showToast(t('toast.stopFehler'), 'error');
        }
      } finally {
        appState.recordingStoppt = false;
        stoppt = null;
      }
    })();
    return stoppt;
  },

  // Favorites
  async loadFavorites() {
    try {
      const favs = await api.getFavoritesAll();
      appState.favorites = favs;
    } catch (e) {
      // Netzwerkfehler bei Seitenlade ignorieren
    }
  },

  async toggleFavorite(station) {
    const uuid = station.uuid || station.stationuuid;
    const isFav = appState.favorites.some(f => f.uuid === uuid);

    try {
      if (isFav) {
        await api.removeFavorite(uuid);
        appState.favorites = appState.favorites.filter(f => f.uuid !== uuid);
        actions.showToast(t('toast.favEntfernt'), 'info');
      } else {
        await api.addFavorite(station);
        appState.favorites = [...appState.favorites, { ...station, uuid }];
        actions.showToast(t('toast.favHinzu'), 'success');
      }
    } catch (e) {
      actions.showToast(t('common.fehler'), 'error');
    }
  },

  isFavorite(uuid) {
    return appState.favorites.some(f => f.uuid === uuid);
  },

  // Podcasts
  async loadPodcasts() {
    try {
      const result = await api.getSubscriptions();
      appState.podcasts = result.subscriptions || [];
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
  },

  // Blättern: Folgen des Podcasts, Titel der Aufnahme, sonst Sender
  navigatePrev() {
    return blaettern(-1);
  },

  navigateNext() {
    return blaettern(1);
  },

  // Stream-Modus wechseln (Original/HLS)
  toggleStreamMode() {
    engine.toggleStreamMode();
  }
};

engine.beiVollemPlatz(() => actions.showToast(t('toast.recVoll'), 'error'));
