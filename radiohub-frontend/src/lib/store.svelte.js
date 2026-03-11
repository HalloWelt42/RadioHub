/**
 * RadioHub App Store v0.5.1
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
  recordingPlaylist: [],    // [{path, name, session_id, playUrl, ...}] Segment-Liste fuer Prev/Next
  playMode: 'linear',       // 'linear' | 'reverse' | 'loop' | 'shuffle' -- Wiedergabe-Modus fuer Playlists

  // Podcast-Playlist
  podcastPlaylist: [],          // [{id, title, audio_url, ...}, ...]
  podcastPlaylistPodcast: null, // Podcast-Objekt fuer die aktuelle Playlist
  podcastSpeed: 1.0,            // 0.75 | 1.0 | 1.25 | 1.5 | 1.75 | 2.0

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

  playEpisodeFromList(episode, podcast, playlist) {
    appState.podcastPlaylist = playlist || [];
    appState.podcastPlaylistPodcast = podcast || null;
    appState.currentEpisodeIndex = playlist ? playlist.findIndex(e => e.id === episode.id) : -1;
    engine.playPodcast(episode, podcast);
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

  // Navigation durch Sender oder Recording-Segmente
  navigatePrev() {
    // Podcast-Modus: durch Playlist navigieren
    if (appState.playerMode === 'podcast' && appState.podcastPlaylist.length > 0) {
      const playlist = appState.podcastPlaylist;
      const idx = appState.currentEpisodeIndex;
      const podcast = appState.podcastPlaylistPodcast;

      if (appState.playMode === 'shuffle') {
        const candidates = playlist.length > 1 ? playlist.filter((_, i) => i !== idx) : playlist;
        const next = candidates[Math.floor(Math.random() * candidates.length)];
        appState.currentEpisodeIndex = playlist.indexOf(next);
        engine.playPodcast(next, podcast);
        return;
      }

      if (idx > 0) {
        appState.currentEpisodeIndex = idx - 1;
        engine.playPodcast(playlist[idx - 1], podcast);
      } else {
        appState.currentEpisodeIndex = playlist.length - 1;
        engine.playPodcast(playlist[playlist.length - 1], podcast);
      }
      return;
    }

    // Recording-Modus: durch Playlist navigieren
    if (appState.playerMode === 'recording' && appState.recordingPlaylist.length > 0) {
      const playlist = appState.recordingPlaylist;
      const idx = playlist.findIndex(s => s.path === appState.currentRecording?.path);

      if (appState.playMode === 'shuffle') {
        const candidates = playlist.length > 1 ? playlist.filter((_, i) => i !== idx) : playlist;
        engine.playRecording(candidates[Math.floor(Math.random() * candidates.length)]);
        return;
      }

      if (idx > 0) {
        engine.playRecording(playlist[idx - 1]);
      } else if (idx === 0) {
        engine.playRecording(playlist[playlist.length - 1]);
      }
      return;
    }
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
    // Podcast-Modus: durch Playlist navigieren
    if (appState.playerMode === 'podcast' && appState.podcastPlaylist.length > 0) {
      const playlist = appState.podcastPlaylist;
      const idx = appState.currentEpisodeIndex;
      const podcast = appState.podcastPlaylistPodcast;

      if (appState.playMode === 'shuffle') {
        const candidates = playlist.length > 1 ? playlist.filter((_, i) => i !== idx) : playlist;
        const next = candidates[Math.floor(Math.random() * candidates.length)];
        appState.currentEpisodeIndex = playlist.indexOf(next);
        engine.playPodcast(next, podcast);
        return;
      }

      if (idx >= 0 && idx < playlist.length - 1) {
        appState.currentEpisodeIndex = idx + 1;
        engine.playPodcast(playlist[idx + 1], podcast);
      } else {
        appState.currentEpisodeIndex = 0;
        engine.playPodcast(playlist[0], podcast);
      }
      return;
    }

    // Recording-Modus: durch Playlist navigieren
    if (appState.playerMode === 'recording' && appState.recordingPlaylist.length > 0) {
      const playlist = appState.recordingPlaylist;
      const idx = playlist.findIndex(s => s.path === appState.currentRecording?.path);

      if (appState.playMode === 'shuffle') {
        const candidates = playlist.length > 1 ? playlist.filter((_, i) => i !== idx) : playlist;
        engine.playRecording(candidates[Math.floor(Math.random() * candidates.length)]);
        return;
      }

      if (idx >= 0 && idx < playlist.length - 1) {
        engine.playRecording(playlist[idx + 1]);
      } else {
        engine.playRecording(playlist[0]);
      }
      return;
    }
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
