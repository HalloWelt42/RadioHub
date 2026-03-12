/**
 * RadioHub API Client v0.1.0
 * Kommunikation mit Backend
 */

// API Base URL - relativ für Vite-Proxy, überschreibbar für Docker/Produktion
const API_BASE = window.RADIOHUB_API_URL || '';

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
      let detail = `API Error: ${response.status}`;
      try {
        const body = await response.json();
        if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      } catch {}
      throw new Error(detail);
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
  async getCategories(scope = null) {
    const url = scope ? `/api/categories?scope=${scope}` : '/api/categories';
    return this.fetch(url);
  }

  async createCategory(name, sortOrder = 0, scope = 'radio') {
    return this.fetch('/api/categories', {
      method: 'POST',
      body: JSON.stringify({ name, sort_order: sortOrder, scope })
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

  // === Category Podcast Assignments ===
  async assignPodcast(categoryId, podcastId) {
    return this.fetch(`/api/categories/${categoryId}/podcasts/${podcastId}`, {
      method: 'POST'
    });
  }

  async unassignPodcast(categoryId, podcastId) {
    return this.fetch(`/api/categories/${categoryId}/podcasts/${podcastId}`, {
      method: 'DELETE'
    });
  }

  async getPodcastAssignments(ids) {
    return this.fetch('/api/categories/podcast-assignments', {
      method: 'POST',
      body: JSON.stringify({ ids })
    });
  }

  // === Category Session Assignments ===
  async assignSession(categoryId, sessionId) {
    return this.fetch(`/api/categories/${categoryId}/sessions/${sessionId}`, {
      method: 'POST'
    });
  }

  async unassignSession(categoryId, sessionId) {
    return this.fetch(`/api/categories/${categoryId}/sessions/${sessionId}`, {
      method: 'DELETE'
    });
  }

  async getSessionAssignments(ids) {
    return this.fetch('/api/categories/session-assignments', {
      method: 'POST',
      body: JSON.stringify({ ids })
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

  async customSplit(sessionId, cutPoints, trimStart = false, trimEnd = false) {
    return this.fetch(`/api/recording/sessions/${sessionId}/custom-split`, {
      method: 'POST',
      body: JSON.stringify({
        cut_points: cutPoints,
        trim_start: trimStart,
        trim_end: trimEnd
      })
    });
  }

  // === Audio-Nachbearbeitung ===
  async getAudioInfo(sessionId) {
    return this.fetch(`/api/recording/sessions/${sessionId}/audio-info`);
  }

  async normalizeSession(sessionId, targetLufs = -16.0, segmentIds = null) {
    const body = { target_lufs: targetLufs };
    if (segmentIds) body.segment_ids = segmentIds;
    return this.fetch(`/api/recording/sessions/${sessionId}/normalize`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  normalizeSessionSSE(sessionId, targetLufs = -16.0, segmentIds = null) {
    const url = `${this.baseUrl}/api/recording/sessions/${sessionId}/normalize`;
    const body = { target_lufs: targetLufs };
    if (segmentIds) body.segment_ids = segmentIds;
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  }

  async convertSession(sessionId, format, bitrate = 192, mono = false, segmentIds = null) {
    const body = { format, bitrate, mono };
    if (segmentIds) body.segment_ids = segmentIds;
    return this.fetch(`/api/recording/sessions/${sessionId}/convert`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  convertSessionSSE(sessionId, format, bitrate = 192, mono = false, segmentIds = null) {
    const url = `${this.baseUrl}/api/recording/sessions/${sessionId}/convert`;
    const body = { format, bitrate, mono };
    if (segmentIds) body.segment_ids = segmentIds;
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  }

  async getFormatBitrates() {
    return this.fetch('/api/recording/audio-processing/presets');
  }

  async getPeaksInfo(sessionId) {
    return this.fetch(`/api/recording/sessions/${sessionId}/peaks/info`);
  }

  async getPeaksChunk(sessionId, start = 0, duration = 300) {
    const url = `${this.baseUrl}/api/recording/sessions/${sessionId}/peaks?start=${start}&duration=${duration}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Peaks Error: ${response.status}`);
    return response.arrayBuffer();
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

  getSessionAudioUrl(sessionId) {
    return `${this.baseUrl}/api/recording/sessions/${sessionId}/audio`;
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

  async searchEpisodes(query, limit = 50, offset = 0, searchIn = 'all') {
    const params = `q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}&search_in=${searchIn}`;
    return this.fetch(`/api/podcasts/episodes/search?${params}`);
  }

  async searchSubscriptions(query) {
    return this.fetch(`/api/podcasts/subscriptions/search?q=${encodeURIComponent(query)}`);
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

  async getRefreshStatus() {
    return this.fetch('/api/podcasts/refresh-status');
  }

  // === Recording Folders ===
  async getRecordingFolders() {
    return this.fetch('/api/recording/folders');
  }

  async createRecordingFolder(name) {
    return this.fetch('/api/recording/folders', {
      method: 'POST',
      body: JSON.stringify({ name })
    });
  }

  async updateRecordingFolder(id, updates) {
    return this.fetch(`/api/recording/folders/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  }

  async deleteRecordingFolder(id) {
    return this.fetch(`/api/recording/folders/${id}`, { method: 'DELETE' });
  }

  async activateRecordingFolder(id) {
    return this.fetch(`/api/recording/folders/${id}/activate`, { method: 'PUT' });
  }

  async deactivateRecordingFolder() {
    return this.fetch('/api/recording/folders/deactivate', { method: 'PUT' });
  }

  async moveSession(sessionId, folderId) {
    return this.fetch(`/api/recording/folders/move-session/${sessionId}`, {
      method: 'PUT',
      body: JSON.stringify({ folder_id: folderId })
    });
  }

  // === File Explorer ===
  async getPodcastFiles() {
    return this.fetch('/api/files/podcasts');
  }

  async getRecordingFiles() {
    return this.fetch('/api/files/recordings');
  }

  async deleteFileExplorer(path) {
    return this.fetch(`/api/files/delete?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
  }

  async deleteOrphanedFolders() {
    return this.fetch('/api/files/delete-orphaned', { method: 'DELETE' });
  }

  getFilesZipDownloadUrl() {
    return `${this.baseUrl}/api/files/download-zip`;
  }

  async downloadFilesZip(files, includePlaylist = true) {
    const url = `${this.baseUrl}/api/files/download-zip`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files, include_playlist: includePlaylist })
    });
    if (!response.ok) throw new Error(`ZIP-Download fehlgeschlagen: ${response.status}`);
    return response;
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

  // === Storage Zones ===

  async getStorageZones() {
    return this.fetch('/api/storage/zones');
  }

  async updateStorageZone(zone, path) {
    return this.fetch(`/api/storage/zones/${zone}`, {
      method: 'PUT',
      body: JSON.stringify({ path })
    });
  }

  async validateStoragePath(path) {
    return this.fetch(`/api/storage/validate?path=${encodeURIComponent(path)}`);
  }

  // === Externe Dienste ===

  async getServices() {
    return this.fetch('/api/services');
  }

  async updateServiceUrl(serviceId, value) {
    return this.fetch(`/api/services/${serviceId}`, {
      method: 'PUT',
      body: JSON.stringify({ value })
    });
  }

  async resetServiceUrl(serviceId) {
    return this.fetch(`/api/services/${serviceId}/reset`, { method: 'POST' });
  }
}

export const api = new RadioHubAPI(API_BASE);
