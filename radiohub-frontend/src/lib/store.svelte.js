/**
 * RadioHub App Store v0.5.0
 * Globaler State mit Svelte 5 Runes
 *
 * v0.5.0: Player-Logik delegiert an playerEngine.js
 *         Neue Felder: isPaused, playerMode, streamQuality, playerError, recordingElapsed
 */

import { api } from './api.js';
import * as engine from './playerEngine.js';

// === App State ===
export const appState = $state({
  // Navigation
  activeTab: 'radio',

  // Theme
  theme: 'dark', // 'dark' | 'light'

  // Player - Core
  isPlaying: false,
  isPaused: false,
  currentStation: null,
  currentEpisode: null,
  volume: 70,

  // Player - Mode & Quality
  playerMode: 'none',      // 'none' | 'direct' | 'hls' | 'podcast' | 'recording'
  streamQuality: null,      // { inputCodec, inputBitrate, outputBitrate, sampleRate }
  playerError: null,        // Fehlermeldung oder null

  // Recording
  isRecording: false,
  recordingType: 'none',    // 'none' | 'direct' | 'hls-rec'
  recordingSession: null,
  recordingElapsed: 0,
  recordingIcyCount: 0,     // Anzahl erkannter Titelwechsel (live)
  recordingIcyEntries: [],  // [{title, t}] live ICY-Eintraege
  currentRecording: null,   // {path, name, session_id, station_name, date, duration, playUrl}

  // HLS Buffer
  hlsActive: false,
  hlsStatus: null,
  isLive: true,
  currentSegment: null,

  // Stream Mode Capabilities
  canPlayDirect: true,   // true=ja, false=Codec nicht abspielbar
  canPlayHLS: null,      // null=unbekannt, true=Segmente verfügbar, false=Start fehlgeschlagen

  // Data
  stations: [],
  favorites: [],
  podcasts: [],

  // Navigation Index (für Blättern)
  currentStationIndex: -1,
  currentEpisodeIndex: -1,

  // ICY Now Playing
  streamTitle: null,   // Aktueller ICY-StreamTitle (Musiktitel)

  // Setup Deep-Link
  setupSubTab: null,   // Wechsel zu Sub-Tab in Setup: 'filter', 'kategorien', etc.

  // HLS-REC Config
  hlsRecLookbackMinutes: 5,  // Lookback in Minuten (1-120)

  // UI
  isLoading: false,
  error: null,
  toast: null
});

// === Actions ===
export const actions = {
  // Navigation
  setTab(tab) {
    appState.activeTab = tab;
  },

  // Theme
  setTheme(theme) {
    appState.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('radiohub-theme', theme);
  },

  toggleTheme() {
    const newTheme = appState.theme === 'dark' ? 'light' : 'dark';
    actions.setTheme(newTheme);
  },

  initTheme() {
    const saved = localStorage.getItem('radiohub-theme');
    if (saved) {
      actions.setTheme(saved);
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

  playEpisode(episode, podcast) {
    engine.playPodcast(episode, podcast);
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
  async playRecording(recording) {
    await engine.playRecording(recording);
  },

  // Recording (delegiert an Engine)
  async startRecording() {
    const result = await engine.startRecording();
    if (result?.success) {
      actions.showToast('Aufnahme gestartet', 'success');
    } else {
      actions.showToast('Aufnahme fehlgeschlagen', 'error');
    }
  },

  async stopRecording() {
    const result = await engine.stopRecording();
    if (result?.success) {
      const dur = result.duration ? ` (${Math.round(result.duration)}s)` : '';
      actions.showToast(`Aufnahme gespeichert${dur}`, 'success');
    } else {
      actions.showToast('Stoppen fehlgeschlagen', 'error');
    }
  },

  // Favorites
  async loadFavorites() {
    try {
      const favs = await api.getFavoritesAll();
      appState.favorites = favs;
    } catch (e) {
      console.error('Favorites laden fehlgeschlagen:', e);
    }
  },

  async toggleFavorite(station) {
    const uuid = station.uuid || station.stationuuid;
    const isFav = appState.favorites.some(f => f.uuid === uuid);

    try {
      if (isFav) {
        await api.removeFavorite(uuid);
        appState.favorites = appState.favorites.filter(f => f.uuid !== uuid);
        actions.showToast('Favorit entfernt', 'info');
      } else {
        await api.addFavorite(station);
        appState.favorites = [...appState.favorites, { ...station, uuid }];
        actions.showToast('Favorit hinzugefügt', 'success');
      }
    } catch (e) {
      actions.showToast('Fehler', 'error');
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
      console.error('Podcasts laden fehlgeschlagen:', e);
    }
  },

  // Navigation durch Sender
  navigatePrev() {
    if (appState.currentStation && appState.stations.length > 0) {
      const idx = appState.stations.findIndex(s => s.uuid === appState.currentStation.uuid);
      if (idx > 0) {
        engine.playStation(appState.stations[idx - 1]);
      } else if (idx === 0) {
        engine.playStation(appState.stations[appState.stations.length - 1]);
      }
    }
  },

  navigateNext() {
    if (appState.currentStation && appState.stations.length > 0) {
      const idx = appState.stations.findIndex(s => s.uuid === appState.currentStation.uuid);
      if (idx < appState.stations.length - 1) {
        engine.playStation(appState.stations[idx + 1]);
      } else {
        engine.playStation(appState.stations[0]);
      }
    }
  },

  // HLS Status Update - NICHT MEHR NÖTIG, Engine pollt selbst
  async updateHLSStatus() {
    // Backward-Compat: wird von altem Code aufgerufen, macht jetzt nichts
  },

  // Stream-Modus wechseln (Original/HLS)
  toggleStreamMode() {
    engine.toggleStreamMode();
  },

  // Live-Modus setzen
  setLive(isLive) {
    appState.isLive = isLive;
  }
};
