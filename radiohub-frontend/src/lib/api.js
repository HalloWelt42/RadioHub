/**
 * RadioHub API Client v0.1.0
 * Kommunikation mit Backend
 */

// API Base URL - wird beim Build/Docker überschrieben
const API_BASE = window.RADIOHUB_API_URL || 'http://localhost:9091';

class RadioHubAPI {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async fetch(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  }

  // === Health ===
  async health() {
    return this.fetch('/health');
  }

  // === Cache & Stations ===
  async syncCache(force = false) {
    return this.fetch(`/api/cache/sync?force=${force}`, { method: 'POST' });
  }

  async getCacheStats() {
    return this.fetch('/api/cache/stats');
  }

  async getFilters() {
    return this.fetch('/api/cache/filters');
  }

  async searchStations(params) {
    return this.fetch('/api/stations/search', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }

  async getStation(uuid) {
    return this.fetch(`/api/stations/${uuid}`);
  }

  // === Favorites ===
  async getFavorites() {
    return this.fetch('/api/favorites');
  }

  async getFavoritesAll() {
    return this.fetch('/api/favorites/all');
  }

  async addFavorite(station) {
    return this.fetch('/api/favorites', {
      method: 'POST',
      body: JSON.stringify({
        stationuuid: station.uuid || station.stationuuid,
        name: station.name,
        url: station.url,
        url_resolved: station.url_resolved,
        favicon: station.favicon,
        country: station.country,
        countrycode: station.countrycode,
        tags: station.tags,
        bitrate: station.bitrate || 0
      })
    });
  }

  async removeFavorite(uuid) {
    return this.fetch(`/api/favorites/${uuid}`, { method: 'DELETE' });
  }

  // === Recording ===
  async startRecording(data) {
    return this.fetch('/api/recording/start', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async stopRecording() {
    return this.fetch('/api/recording/stop', { method: 'POST' });
  }

  async getRecordingStatus() {
    return this.fetch('/api/recording/status');
  }

  async getSessions() {
    return this.fetch('/api/recording/sessions');
  }

  async deleteSession(id) {
    return this.fetch(`/api/recording/sessions/${id}`, { method: 'DELETE' });
  }

  // === Recordings Explorer ===
  async getRecordingsStats() {
    return this.fetch('/api/recordings/stats');
  }

  async getRecordingsFolders() {
    return this.fetch('/api/recordings/folders');
  }

  async getRecordingsFiles(path = '/', limit = 50) {
    return this.fetch(`/api/recordings/files?path=${encodeURIComponent(path)}&limit=${limit}`);
  }

  getPlayUrl(path) {
    return `${this.baseUrl}/api/recordings/play?path=${encodeURIComponent(path)}`;
  }

  // === Podcasts ===
  async searchPodcasts(query, source = 'all', limit = 20) {
    return this.fetch(`/api/podcasts/search?q=${encodeURIComponent(query)}&source=${source}&limit=${limit}`);
  }

  async getSubscriptions() {
    return this.fetch('/api/podcasts/subscriptions');
  }

  async subscribePodcast(feedUrl) {
    return this.fetch('/api/podcasts/subscribe', {
      method: 'POST',
      body: JSON.stringify({ feed_url: feedUrl })
    });
  }

  async unsubscribePodcast(id) {
    return this.fetch(`/api/podcasts/${id}`, { method: 'DELETE' });
  }

  async getPodcast(id) {
    return this.fetch(`/api/podcasts/${id}`);
  }

  async refreshPodcast(id) {
    return this.fetch(`/api/podcasts/${id}/refresh`, { method: 'POST' });
  }

  async getEpisodes(podcastId, limit = 50, offset = 0) {
    return this.fetch(`/api/podcasts/${podcastId}/episodes?limit=${limit}&offset=${offset}`);
  }

  async updateEpisodePosition(episodeId, positionSeconds) {
    return this.fetch(`/api/podcasts/episodes/${episodeId}/position`, {
      method: 'PUT',
      body: JSON.stringify({ position_seconds: positionSeconds })
    });
  }

  // === Timeshift Buffer (Legacy) ===
  async getBufferStatus() {
    return this.fetch('/api/buffer/status');
  }

  async startBuffering(station) {
    return this.fetch('/api/buffer/start', {
      method: 'POST',
      body: JSON.stringify({
        station_uuid: station.uuid || station.stationuuid,
        station_name: station.name,
        stream_url: station.url_resolved || station.url,
        bitrate: station.bitrate || 128,
        max_minutes: 10
      })
    });
  }

  async stopBuffering() {
    return this.fetch('/api/buffer/stop', { method: 'POST' });
  }

  async seekBuffer(positionSeconds) {
    return this.fetch('/api/buffer/seek', {
      method: 'POST',
      body: JSON.stringify({ position_seconds: positionSeconds })
    });
  }

  async goLive() {
    return this.fetch('/api/buffer/live', { method: 'POST' });
  }

  getBufferStreamUrl() {
    return `${this.baseUrl}/api/buffer/stream`;
  }

  // === HLS Timeshift Buffer ===
  async startHLS(station) {
    return this.fetch('/api/hls/start', {
      method: 'POST',
      body: JSON.stringify({
        station_uuid: station.uuid || station.stationuuid,
        station_name: station.name,
        stream_url: station.url_resolved || station.url,
        bitrate: station.bitrate || 128,
        max_minutes: 10
      })
    });
  }

  async stopHLS() {
    return this.fetch('/api/hls/stop', { method: 'POST' });
  }

  async getHLSStatus() {
    return this.fetch('/api/hls/status');
  }

  getHLSPlaylistUrl(sessionId) {
    const base = `${this.baseUrl}/api/hls/playlist.m3u8`;
    return sessionId ? `${base}?sid=${sessionId}` : base;
  }

  // === Config ===
  async getConfig() {
    return this.fetch('/api/config');
  }

  async updateConfig(updates) {
    return this.fetch('/api/config', {
      method: 'PUT',
      body: JSON.stringify({ updates })
    });
  }
  
  // === Blocklist ===
  async getBlocklist() {
    return this.fetch('/api/blocklist');
  }
  
  async blockStation(uuid, name, reason = null) {
    return this.fetch('/api/blocklist', {
      method: 'POST',
      body: JSON.stringify({ uuid, name, reason })
    });
  }
  
  async unblockStation(uuid) {
    return this.fetch(`/api/blocklist/${uuid}`, { method: 'DELETE' });
  }
  
  async isBlocked(uuid) {
    return this.fetch(`/api/blocklist/check/${uuid}`);
  }

  // === Station Filters ===
  async filterPreview(filters) {
    return this.fetch('/api/filters/preview', {
      method: 'POST',
      body: JSON.stringify(filters)
    });
  }

  async filterPush(filters) {
    return this.fetch('/api/filters/push', {
      method: 'POST',
      body: JSON.stringify(filters)
    });
  }

  async getHiddenStations(reason = null) {
    const url = reason
      ? `/api/filters/hidden?reason=${encodeURIComponent(reason)}`
      : '/api/filters/hidden';
    return this.fetch(url);
  }

  async releaseStations(payload) {
    return this.fetch('/api/filters/release', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async getAvailableLanguages() {
    return this.fetch('/api/filters/languages');
  }
}

export const api = new RadioHubAPI(API_BASE);
