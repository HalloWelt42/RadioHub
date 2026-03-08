/**
 * RadioHub App Store v0.4.0
 * Globaler State mit Svelte 5 Runes
 * 
 * v0.4.0: HLS Timeshift Buffer
 */

import { api } from './api.js';

// === App State ===
export const appState = $state({
  // Navigation
  activeTab: 'radio',
  
  // Theme
  theme: 'dark', // 'dark' | 'light'
  
  // Player
  isPlaying: false,
  currentStation: null,
  currentEpisode: null,
  volume: 70,
  
  // Recording
  isRecording: false,
  recordingSession: null,
  
  // HLS Buffer
  hlsActive: false,
  hlsStatus: null,
  isLive: true,
  
  // Data
  stations: [],
  favorites: [],
  podcasts: [],
  
  // Navigation Index (für Blättern)
  currentStationIndex: -1,
  currentEpisodeIndex: -1,
  
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
  
  // Player
  async playStation(station) {
    // HLS stoppen falls aktiv
    if (appState.hlsActive) {
      try {
        await api.stopHLS();
      } catch (e) {
        console.error('HLS stop error:', e);
      }
      appState.hlsActive = false;
      appState.hlsStatus = null;
    }
    
    appState.currentStation = station;
    appState.currentEpisode = null;
    appState.isPlaying = true;
    appState.isLive = true;
    
    // HLS Buffer starten (fire and forget)
    api.startHLS(station).then(result => {
      if (result.status === 'started' || result.status === 'already_active') {
        appState.hlsActive = true;
        appState.hlsStatus = result;
        console.log('HLS Buffer gestartet:', result);
      }
    }).catch(e => {
      console.error('HLS start error:', e);
      // Radio spielt trotzdem weiter (ohne Buffer)
    });
    
    // Last station speichern
    api.updateConfig({
      last_station_uuid: station.uuid,
      last_station_name: station.name
    }).catch(e => console.error('Config save error:', e));
  },
  
  playEpisode(episode, podcast) {
    // HLS stoppen (Wechsel von Radio zu Podcast)
    if (appState.hlsActive) {
      api.stopHLS().catch(e => console.error('HLS stop error:', e));
      appState.hlsActive = false;
      appState.hlsStatus = null;
    }
    
    appState.currentEpisode = { ...episode, podcast };
    appState.currentStation = null;
    appState.isPlaying = true;
    appState.isLive = true;
  },
  
  stop() {
    appState.isPlaying = false;
    
    // HLS stoppen (fire and forget)
    if (appState.hlsActive) {
      api.stopHLS().catch(e => console.error('HLS stop error:', e));
      appState.hlsActive = false;
      appState.hlsStatus = null;
      appState.isLive = true;
    }
  },
  
  setVolume(vol) {
    appState.volume = vol;
  },
  
  // Recording
  async startRecording() {
    if (!appState.currentStation) return;
    
    try {
      const result = await api.startRecording({
        station_uuid: appState.currentStation.uuid,
        station_name: appState.currentStation.name,
        stream_url: appState.currentStation.url_resolved || appState.currentStation.url,
        bitrate: appState.currentStation.bitrate || 128
      });
      
      if (result.success) {
        appState.isRecording = true;
        appState.recordingSession = result.session_id;
        actions.showToast('Aufnahme gestartet', 'success');
      }
    } catch (e) {
      actions.showToast('Aufnahme fehlgeschlagen', 'error');
    }
  },
  
  async stopRecording() {
    try {
      const result = await api.stopRecording();
      if (result.success) {
        appState.isRecording = false;
        appState.recordingSession = null;
        actions.showToast(`Aufnahme gespeichert (${Math.round(result.duration)}s)`, 'success');
      }
    } catch (e) {
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
  
  // Navigation durch Sender/Podcasts
  navigatePrev() {
    if (appState.currentStation && appState.stations.length > 0) {
      const idx = appState.stations.findIndex(s => s.uuid === appState.currentStation.uuid);
      if (idx > 0) {
        actions.playStation(appState.stations[idx - 1]);
      } else if (idx === 0) {
        actions.playStation(appState.stations[appState.stations.length - 1]);
      }
    }
  },
  
  navigateNext() {
    if (appState.currentStation && appState.stations.length > 0) {
      const idx = appState.stations.findIndex(s => s.uuid === appState.currentStation.uuid);
      if (idx < appState.stations.length - 1) {
        actions.playStation(appState.stations[idx + 1]);
      } else {
        actions.playStation(appState.stations[0]);
      }
    }
  },
  
  // HLS Status Update (für Polling)
  async updateHLSStatus() {
    if (!appState.hlsActive) return;
    
    try {
      const status = await api.getHLSStatus();
      appState.hlsStatus = status;
    } catch (e) {
      // Stille Fehler - Polling kann mal scheitern
    }
  },
  
  // Live-Modus setzen (wird vom HiFiPlayer aufgerufen)
  setLive(isLive) {
    appState.isLive = isLive;
  }
};
