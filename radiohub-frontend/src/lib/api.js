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

  // === Bitrate Detection ===
  async verifyBitrate(uuids) {
    return this.fetch('/api/stations/verify-bitrate', {
      method: 'POST',
      body: JSON.stringify({ uuids })
    });
  }

  async getDetectedBitrates(uuids) {
    return this.fetch('/api/stations/bitrates', {
      method: 'POST',
      body: JSON.stringify({ uuids })
    });
  }

  // === Now Playing (ICY Title) ===
  async getNowPlaying(uuid) {
    return this.fetch(`/api/stations/${uuid}/now-playing`);
  }

  async setIcyQuality(uuid, quality) {
    return this.fetch(`/api/stations/${uuid}/icy-quality`, {
      method: 'PUT',
      body: JSON.stringify({ quality })
    });
  }

  // === Categories ===
  async getCategories() {
    return this.fetch('/api/categories');
  }

  async createCategory(name, sortOrder = 0) {
    return this.fetch('/api/categories', {
      method: 'POST',
      body: JSON.stringify({ name, sort_order: sortOrder })
    });
  }

  async updateCategory(id, updates) {
    return this.fetch(`/api/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  }

  async deleteCategory(id) {
    return this.fetch(`/api/categories/${id}`, { method: 'DELETE' });
  }

  // === Category Station Assignments ===
  async assignStation(categoryId, stationUuid) {
    return this.fetch(`/api/categories/${categoryId}/stations/${stationUuid}`, {
      method: 'POST'
    });
  }

  async unassignStation(categoryId, stationUuid) {
    return this.fetch(`/api/categories/${categoryId}/stations/${stationUuid}`, {
      method: 'DELETE'
    });
  }

  async getStationAssignments(uuids) {
    return this.fetch('/api/categories/station-assignments', {
      method: 'POST',
      body: JSON.stringify({ uuids })
    });
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

  // === HLS-REC ===
  async startHlsRecording(lookbackSeconds = 300) {
    return this.fetch('/api/recording/hls-start', {
      method: 'POST',
      body: JSON.stringify({ lookback_seconds: lookbackSeconds })
    });
  }

  async stopHlsRecording() {
    return this.fetch('/api/recording/hls-stop', { method: 'POST' });
  }

  async getHlsRecordingStatus() {
    return this.fetch('/api/recording/hls-status');
  }

  async getSessions() {
    return this.fetch('/api/recording/sessions');
  }

  async getSession(id) {
    return this.fetch(`/api/recording/sessions/${id}`);
  }

  async deleteSession(id) {
    return this.fetch(`/api/recording/sessions/${id}`, { method: 'DELETE' });
  }

  getSessionDownloadUrl(filename) {
    return `${this.baseUrl}/api/recording/download/${encodeURIComponent(filename)}`;
  }

  async getSessionMetadata(sessionId) {
    return this.fetch(`/api/recording/sessions/${sessionId}/metadata`);
  }

  async getSegments(sessionId) {
    return this.fetch(`/api/recording/sessions/${sessionId}/segments`);
  }

  async getAllSegments() {
    return this.fetch('/api/recording/segments');
  }

  async deleteSegment(sessionId, segmentId) {
    return this.fetch(`/api/recording/sessions/${sessionId}/segments/${segmentId}`, { method: 'DELETE' });
  }

  getSegmentPlayUrl(segmentId) {
    return `${this.baseUrl}/api/recording/segments/${segmentId}/play`;
  }

  getSegmentDownloadUrl(segmentId) {
    return `${this.baseUrl}/api/recording/segments/${segmentId}/download`;
  }

  getFullDownloadUrl(sessionId) {
    return `${this.baseUrl}/api/recording/sessions/${sessionId}/download-full`;
  }

  getZipDownloadUrl(sessionId) {
    return `${this.baseUrl}/api/recording/sessions/${sessionId}/download-zip`;
  }

  async splitSession(sessionId) {
    return this.fetch(`/api/recording/sessions/${sessionId}/split`, { method: 'POST' });
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

  async getEpisodes(podcastId, limit = 50, offset = 0, filterStatus = 'all', sortBy = 'published_at', sortOrder = 'desc') {
    const params = `limit=${limit}&offset=${offset}&filter_status=${filterStatus}&sort_by=${sortBy}&sort_order=${sortOrder}`;
    return this.fetch(`/api/podcasts/${podcastId}/episodes?${params}`);
  }

  async getAllEpisodes({ limit = 50, offset = 0, filterStatus = 'all', sortBy = 'published_at', sortOrder = 'desc', podcastIds = null } = {}) {
    let params = `limit=${limit}&offset=${offset}&filter_status=${filterStatus}&sort_by=${sortBy}&sort_order=${sortOrder}`;
    if (podcastIds?.length) params += `&podcast_ids=${podcastIds.join(',')}`;
    return this.fetch(`/api/podcasts/episodes/all?${params}`);
  }

  async getEpisode(episodeId) {
    return this.fetch(`/api/podcasts/episodes/${episodeId}`);
  }

  async updateEpisodePosition(episodeId, positionSeconds) {
    return this.fetch(`/api/podcasts/episodes/${episodeId}/position`, {
      method: 'PUT',
      body: JSON.stringify({ position_seconds: positionSeconds })
    });
  }

  async markEpisodePlayed(episodeId) {
    return this.fetch(`/api/podcasts/episodes/${episodeId}/played`, { method: 'PUT' });
  }

  async markEpisodeUnplayed(episodeId) {
    return this.fetch(`/api/podcasts/episodes/${episodeId}/unplayed`, { method: 'PUT' });
  }

  async markAllPlayed(podcastId) {
    return this.fetch(`/api/podcasts/${podcastId}/mark-all-played`, { method: 'PUT' });
  }

  async downloadEpisode(episodeId) {
    return this.fetch(`/api/podcasts/episodes/${episodeId}/download`, { method: 'POST' });
  }

  async downloadEpisodesBatch(podcastId, episodeIds) {
    return this.fetch(`/api/podcasts/${podcastId}/download-batch`, {
      method: 'POST',
      body: JSON.stringify({ episode_ids: episodeIds })
    });
  }

  async deleteEpisodeDownload(episodeId) {
    return this.fetch(`/api/podcasts/episodes/${episodeId}/download`, { method: 'DELETE' });
  }

  async deletePlayedDownloads(podcastId) {
    return this.fetch(`/api/podcasts/${podcastId}/played-downloads`, { method: 'DELETE' });
  }

  async refreshAllPodcasts() {
    return this.fetch('/api/podcasts/refresh-all', { method: 'POST' });
  }

  async getPodcastStats() {
    return this.fetch('/api/podcasts/stats');
  }

  async updatePodcastCategories(podcastId, categories) {
    return this.fetch(`/api/podcasts/${podcastId}/categories`, {
      method: 'PUT',
      body: JSON.stringify({ categories })
    });
  }

  async setAutoDownload(podcastId, enabled) {
    return this.fetch(`/api/podcasts/${podcastId}/auto-download`, {
      method: 'PUT',
      body: JSON.stringify({ enabled })
    });
  }

  getEpisodePlayUrl(episodeId) {
    return `${this.baseUrl}/api/podcasts/episodes/${episodeId}/play`;
  }

  getPodcastImageUrl(podcastId) {
    return `${this.baseUrl}/api/podcasts/${podcastId}/image`;
  }

  getEpisodeImageUrl(episodeId) {
    return `${this.baseUrl}/api/podcasts/episodes/${episodeId}/image`;
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
        max_minutes: 120
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
    const overrideBitrate = JSON.parse(localStorage.getItem('radiohub_bitrate_override') || '0');
    return this.fetch('/api/hls/start', {
      method: 'POST',
      body: JSON.stringify({
        station_uuid: station.uuid || station.stationuuid,
        station_name: station.name,
        stream_url: station.url_resolved || station.url,
        bitrate: station.bitrate || 128,
        max_minutes: 120,
        override_bitrate: overrideBitrate || 0
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

  async getAvailableCountries() {
    return this.fetch('/api/filters/countries');
  }

  // === Ad-Detection ===
  async checkAds(uuid, streamUrl, name = null) {
    return this.fetch('/api/ad-detection/check', {
      method: 'POST',
      body: JSON.stringify({ uuid, stream_url: streamUrl, name })
    });
  }

  async reportAd(uuid, streamUrl, name, note = null) {
    return this.fetch('/api/ad-detection/report', {
      method: 'POST',
      body: JSON.stringify({ uuid, stream_url: streamUrl, name, note })
    });
  }

  async reportAdMarkOnly(uuid, streamUrl, name, note = null) {
    return this.fetch('/api/ad-detection/report-mark', {
      method: 'POST',
      body: JSON.stringify({ uuid, stream_url: streamUrl, name, note })
    });
  }

  async markFalsePositive(uuid) {
    return this.fetch('/api/ad-detection/false-positive', {
      method: 'POST',
      body: JSON.stringify({ uuid })
    });
  }

  async getAdSummary() {
    return this.fetch('/api/ad-detection/summary/overview');
  }

  async getAdSuspects(minConfidence = 0) {
    const params = minConfidence > 0 ? `?min_confidence=${minConfidence}` : '';
    return this.fetch(`/api/ad-detection/suspects${params}`);
  }

  async decideAd(uuid, action) {
    return this.fetch('/api/ad-detection/decide', {
      method: 'POST',
      body: JSON.stringify({ uuid, action })
    });
  }

  async scanAds(batchSize = 50) {
    return this.fetch('/api/ad-detection/scan', {
      method: 'POST',
      body: JSON.stringify({ batch_size: batchSize })
    });
  }

  async getAdBatchStatus(uuids) {
    return this.fetch('/api/ad-detection/batch-status', {
      method: 'POST',
      body: JSON.stringify({ uuids })
    });
  }
}

export const api = new RadioHubAPI(API_BASE);
