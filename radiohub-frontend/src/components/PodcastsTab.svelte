<script>
  /**
   * PodcastsTab v0.5.0 - Orchestrator
   * Koordiniert Sidebar, Suche, Podcast-Detail, Episoden-Liste.
   * Delegiert Rendering und UI-Logik an Subkomponenten.
   */
  import PodcastSidebar from './podcasts/PodcastSidebar.svelte';
  import PodcastSearchView from './podcasts/PodcastSearchView.svelte';
  import PodcastHeader from './podcasts/PodcastHeader.svelte';
  import EpisodeList from './podcasts/EpisodeList.svelte';
  import SearchBarWithHistory from './shared/SearchBarWithHistory.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  import * as sfx from '../lib/uiSounds.js';

  // === View State ===
  let view = $state('episodes');           // 'episodes' | 'search' | 'all-episodes'
  let selectedPodcastId = $state(null);
  let selectedPodcast = $state(null);

  // === Daten ===
  let subscriptions = $state([]);
  let episodes = $state([]);
  let searchResults = $state([]);
  let stats = $state({});

  // === Filter/Sort ===
  let filterStatus = $state('all');
  let sortBy = $state('published_at');
  let sortOrder = $state('desc');

  // === UI State ===
  let sidebarWidth = $state(Number(localStorage.getItem('radiohub_podcast_sidebar_width')) || 280);
  let selectedEpisodeId = $state(null);
  let focusedIndex = $state(-1);
  let offset = $state(0);
  let hasMore = $state(true);
  let isLoading = $state(false);
  let isLoadingMore = $state(false);
  let isSearching = $state(false);
  let isRefreshing = $state(false);
  let downloadProgress = $state({});

  // === Derived ===
  let subscribedFeedUrls = $derived(new Set(subscriptions.map(s => s.feed_url)));
  let podcastMap = $derived(Object.fromEntries(subscriptions.map(s => [s.id, s])));

  // === Init ===
  $effect(() => {
    loadSubscriptions();
    loadStats();
  });

  // === Daten laden ===
  async function loadSubscriptions() {
    try {
      const result = await api.getSubscriptions();
      subscriptions = result.subscriptions || [];
    } catch (e) {
      console.error('Abonnements laden fehlgeschlagen:', e);
    }
  }

  async function loadStats() {
    try {
      stats = await api.getPodcastStats();
    } catch (e) {
      console.error('Stats laden fehlgeschlagen:', e);
    }
  }

  async function loadEpisodes(podcastId, reset = true) {
    if (reset) {
      offset = 0;
      episodes = [];
      hasMore = true;
      selectedEpisodeId = null;
      focusedIndex = -1;
    }
    if (!hasMore && !reset) return;

    isLoading = reset;
    isLoadingMore = !reset;

    try {
      const result = await api.getEpisodes(podcastId, 100, offset, filterStatus, sortBy, sortOrder);
      const newEpisodes = result.episodes || [];
      if (reset) {
        episodes = newEpisodes;
      } else {
        episodes = [...episodes, ...newEpisodes];
      }
      hasMore = newEpisodes.length >= 100;
      offset += newEpisodes.length;
    } catch (e) {
      console.error('Episoden laden fehlgeschlagen:', e);
    }

    isLoading = false;
    isLoadingMore = false;
  }

  async function loadAllEpisodes(reset = true) {
    if (reset) {
      offset = 0;
      episodes = [];
      hasMore = true;
      selectedEpisodeId = null;
      focusedIndex = -1;
    }
    if (!hasMore && !reset) return;

    isLoading = reset;
    isLoadingMore = !reset;

    try {
      const result = await api.getAllEpisodes({
        limit: 100, offset, filterStatus, sortBy, sortOrder
      });
      const newEpisodes = result.episodes || [];
      if (reset) {
        episodes = newEpisodes;
      } else {
        episodes = [...episodes, ...newEpisodes];
      }
      hasMore = newEpisodes.length >= 100;
      offset += newEpisodes.length;
    } catch (e) {
      console.error('Alle Episoden laden fehlgeschlagen:', e);
    }

    isLoading = false;
    isLoadingMore = false;
  }

  // === Sidebar Callbacks ===
  function handleSelectPodcast(podcast) {
    selectedPodcastId = podcast.id;
    selectedPodcast = podcast;
    view = 'episodes';
    loadEpisodes(podcast.id);
  }

  function handleFilterChange(status) {
    filterStatus = status;
    // Episoden neu laden mit neuem Filter
    if (view === 'episodes' && selectedPodcastId) {
      loadEpisodes(selectedPodcastId);
    } else if (view === 'all-episodes') {
      loadAllEpisodes();
    }
  }

  function handleSidebarResize(newWidth) {
    sidebarWidth = newWidth;
    localStorage.setItem('radiohub_podcast_sidebar_width', String(newWidth));
  }

  function handleSearchClick() {
    view = 'search';
    searchResults = [];
  }

  function handleAllEpisodesClick() {
    selectedPodcastId = null;
    selectedPodcast = null;
    view = 'all-episodes';
    loadAllEpisodes();
  }

  async function handleRefreshAll() {
    try {
      actions.showToast('Aktualisiere alle Feeds...', 'info');
      await api.refreshAllPodcasts();
      await loadSubscriptions();
      await loadStats();
      if (view === 'episodes' && selectedPodcastId) {
        loadEpisodes(selectedPodcastId);
      } else if (view === 'all-episodes') {
        loadAllEpisodes();
      }
      actions.showToast('Alle Feeds aktualisiert', 'success');
    } catch (e) {
      actions.showToast('Aktualisierung fehlgeschlagen', 'error');
    }
  }

  // === Search ===
  async function handleSearch(query) {
    isSearching = true;
    view = 'search';
    try {
      const result = await api.searchPodcasts(query);
      searchResults = result.results || [];
    } catch (e) {
      actions.showToast('Suche fehlgeschlagen', 'error');
      searchResults = [];
    }
    isSearching = false;
  }

  async function handleSubscribe(podcast) {
    try {
      await api.subscribePodcast(podcast.feed_url);
      actions.showToast(`"${podcast.title}" abonniert`, 'success');
      sfx.click();
      await loadSubscriptions();
      await loadStats();
    } catch (e) {
      actions.showToast('Abonnieren fehlgeschlagen', 'error');
    }
  }

  // === Podcast Header Callbacks ===
  async function handleRefreshPodcast() {
    if (!selectedPodcastId) return;
    isRefreshing = true;
    try {
      await api.refreshPodcast(selectedPodcastId);
      await loadEpisodes(selectedPodcastId);
      await loadSubscriptions();
      actions.showToast('Feed aktualisiert', 'success');
    } catch (e) {
      actions.showToast('Aktualisierung fehlgeschlagen', 'error');
    }
    isRefreshing = false;
  }

  async function handleDownloadAll() {
    if (!selectedPodcastId || episodes.length === 0) return;
    const undownloaded = episodes.filter(e => !e.is_downloaded).map(e => e.id);
    if (undownloaded.length === 0) {
      actions.showToast('Alle Episoden bereits heruntergeladen', 'info');
      return;
    }
    try {
      actions.showToast(`Lade ${undownloaded.length} Episoden herunter...`, 'info');
      for (const id of undownloaded) {
        downloadProgress = { ...downloadProgress, [id]: 'downloading' };
      }
      await api.downloadEpisodesBatch(selectedPodcastId, undownloaded);
      for (const id of undownloaded) {
        downloadProgress = { ...downloadProgress, [id]: 'done' };
      }
      await loadEpisodes(selectedPodcastId);
      await loadStats();
      actions.showToast(`${undownloaded.length} Episoden heruntergeladen`, 'success');
    } catch (e) {
      actions.showToast('Batch-Download fehlgeschlagen', 'error');
    }
  }

  async function handleMarkAllPlayed() {
    if (!selectedPodcastId) return;
    try {
      await api.markAllPlayed(selectedPodcastId);
      await loadEpisodes(selectedPodcastId);
      await loadSubscriptions();
      actions.showToast('Alle als gehört markiert', 'success');
    } catch (e) {
      actions.showToast('Markierung fehlgeschlagen', 'error');
    }
  }

  async function handleUnsubscribe() {
    if (!selectedPodcastId) return;
    try {
      await api.unsubscribePodcast(selectedPodcastId);
      actions.showToast('Abo entfernt', 'success');
      selectedPodcastId = null;
      selectedPodcast = null;
      view = 'episodes';
      episodes = [];
      await loadSubscriptions();
      await loadStats();
    } catch (e) {
      actions.showToast('Entfernen fehlgeschlagen', 'error');
    }
  }

  async function handleAutoDownloadToggle() {
    if (!selectedPodcast) return;
    try {
      const newVal = !selectedPodcast.auto_download;
      await api.setAutoDownload(selectedPodcastId, newVal);
      selectedPodcast = { ...selectedPodcast, auto_download: newVal };
      subscriptions = subscriptions.map(s =>
        s.id === selectedPodcastId ? { ...s, auto_download: newVal } : s
      );
      actions.showToast(newVal ? 'Auto-Download aktiviert' : 'Auto-Download deaktiviert', 'info');
    } catch (e) {
      actions.showToast('Einstellung fehlgeschlagen', 'error');
    }
  }

  function handleBack() {
    selectedPodcastId = null;
    selectedPodcast = null;
    view = 'episodes';
    episodes = [];
  }

  // === Episode Callbacks ===
  function handleEpisodeSelect(episode) {
    selectedEpisodeId = selectedEpisodeId === episode.id ? null : episode.id;
    sfx.click();
  }

  function handleEpisodePlay(episode) {
    // Playlist zusammenstellen
    const playlist = episodes.map(e => ({
      ...e,
      audio_url: e.is_downloaded ? api.getEpisodePlayUrl(e.id) : e.audio_url
    }));
    const podcast = selectedPodcast || podcastMap[episode.podcast_id] || null;
    actions.playEpisodeFromList(
      { ...episode, audio_url: episode.is_downloaded ? api.getEpisodePlayUrl(episode.id) : episode.audio_url },
      podcast,
      playlist
    );
    sfx.click();
  }

  async function handleEpisodeDownload(episode) {
    downloadProgress = { ...downloadProgress, [episode.id]: 'downloading' };
    try {
      await api.downloadEpisode(episode.id);
      downloadProgress = { ...downloadProgress, [episode.id]: 'done' };
      // Episode in der Liste aktualisieren
      episodes = episodes.map(e =>
        e.id === episode.id ? { ...e, is_downloaded: true } : e
      );
      await loadStats();
      actions.showToast('Episode heruntergeladen', 'success');
    } catch (e) {
      downloadProgress = { ...downloadProgress, [episode.id]: 'error' };
      actions.showToast('Download fehlgeschlagen', 'error');
    }
  }

  async function handleDeleteDownload(episode) {
    try {
      await api.deleteEpisodeDownload(episode.id);
      episodes = episodes.map(e =>
        e.id === episode.id ? { ...e, is_downloaded: false, file_size: 0 } : e
      );
      await loadStats();
      actions.showToast('Download gelöscht', 'success');
    } catch (e) {
      actions.showToast('Löschen fehlgeschlagen', 'error');
    }
  }

  async function handleTogglePlayed(episode) {
    try {
      if (episode.is_played) {
        await api.markEpisodeUnplayed(episode.id);
      } else {
        await api.markEpisodePlayed(episode.id);
      }
      episodes = episodes.map(e =>
        e.id === episode.id ? { ...e, is_played: !e.is_played } : e
      );
      await loadSubscriptions();
    } catch (e) {
      actions.showToast('Markierung fehlgeschlagen', 'error');
    }
  }

  // === Sort ===
  function handleSort(column, order) {
    sortBy = column;
    sortOrder = order;
    if (view === 'episodes' && selectedPodcastId) {
      loadEpisodes(selectedPodcastId);
    } else if (view === 'all-episodes') {
      loadAllEpisodes();
    }
  }

  // === Scroll (Nachladen) ===
  function handleScroll() {
    if (isLoadingMore || !hasMore) return;
    if (view === 'episodes' && selectedPodcastId) {
      loadEpisodes(selectedPodcastId, false);
    } else if (view === 'all-episodes') {
      loadAllEpisodes(false);
    }
  }

  // === Keyboard Navigation ===
  function handleKeydown(e) {
    if (episodes.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusedIndex = Math.min(focusedIndex + 1, episodes.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusedIndex = Math.max(focusedIndex - 1, 0);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (focusedIndex >= 0 && focusedIndex < episodes.length) {
        handleEpisodePlay(episodes[focusedIndex]);
      }
    } else if (e.key === 'Escape') {
      selectedEpisodeId = null;
      focusedIndex = -1;
    }
  }
</script>

<div class="podcasts-tab">
  <!-- Sidebar (links) -->
  <PodcastSidebar
    {subscriptions}
    {selectedPodcastId}
    {filterStatus}
    {stats}
    width={sidebarWidth}
    onselectpodcast={handleSelectPodcast}
    onfilterchange={handleFilterChange}
    onsearchclick={handleSearchClick}
    onallepisodesclick={handleAllEpisodesClick}
    onrefreshall={handleRefreshAll}
    onresize={handleSidebarResize}
  />

  <!-- Content (rechts) -->
  <main class="podcast-content">
    {#if view === 'search'}
      <!-- Suchleiste -->
      <div class="content-toolbar">
        <SearchBarWithHistory
          placeholder="Podcasts suchen..."
          storageKey="radiohub_podcast_search"
          onsearch={handleSearch}
        />
      </div>
      <PodcastSearchView
        results={searchResults}
        isLoading={isSearching}
        {subscribedFeedUrls}
        onsubscribe={handleSubscribe}
        onopen={(p) => {
          const sub = subscriptions.find(s => s.feed_url === p.feed_url);
          if (sub) handleSelectPodcast(sub);
        }}
      />

    {:else if view === 'all-episodes'}
      <!-- Alle Episoden -->
      <div class="content-toolbar">
        <div class="toolbar-title">
          <i class="fa-solid fa-layer-group"></i>
          <span>Alle Episoden</span>
        </div>
      </div>
      {#if isLoading}
        <div class="loading-center">
          <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
        </div>
      {:else}
        <EpisodeList
          {episodes}
          {sortBy}
          {sortOrder}
          {selectedEpisodeId}
          {focusedIndex}
          showPodcastColumn={true}
          {podcastMap}
          {isLoadingMore}
          {downloadProgress}
          onsort={handleSort}
          onselect={handleEpisodeSelect}
          onplay={handleEpisodePlay}
          onscroll={handleScroll}
          ondownload={handleEpisodeDownload}
          ondeletedownload={handleDeleteDownload}
          ontoggleplayed={handleTogglePlayed}
          onkeydown={handleKeydown}
        />
      {/if}

    {:else if selectedPodcast}
      <!-- Podcast Detail -->
      <PodcastHeader
        podcast={selectedPodcast}
        episodeCount={selectedPodcast?.episode_count || episodes.length}
        unplayedCount={selectedPodcast?.unplayed_count || 0}
        downloadedCount={selectedPodcast?.downloaded_count || 0}
        {isRefreshing}
        onrefresh={handleRefreshPodcast}
        ondownloadall={handleDownloadAll}
        onunsubscribe={handleUnsubscribe}
        onautodownloadtoggle={handleAutoDownloadToggle}
        onback={handleBack}
      />
      {#if isLoading}
        <div class="loading-center">
          <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
        </div>
      {:else}
        <EpisodeList
          {episodes}
          {sortBy}
          {sortOrder}
          {selectedEpisodeId}
          {focusedIndex}
          {isLoadingMore}
          {downloadProgress}
          onsort={handleSort}
          onselect={handleEpisodeSelect}
          onplay={handleEpisodePlay}
          onscroll={handleScroll}
          ondownload={handleEpisodeDownload}
          ondeletedownload={handleDeleteDownload}
          ontoggleplayed={handleTogglePlayed}
          onkeydown={handleKeydown}
        />
      {/if}

    {:else}
      <!-- Willkommen / Kein Podcast ausgewählt -->
      <div class="welcome-center">
        <i class="fa-solid fa-podcast welcome-icon"></i>
        <div class="welcome-title">Podcast-Bibliothek</div>
        <div class="welcome-hint">
          {#if subscriptions.length > 0}
            Podcast in der Seitenleiste auswählen
          {:else}
            Podcasts suchen und abonnieren
          {/if}
        </div>
        {#if subscriptions.length === 0}
          <button class="hifi-btn hifi-btn-primary" onclick={() => { view = 'search'; sfx.click(); }}>
            <i class="fa-solid fa-magnifying-glass"></i> Podcasts suchen
          </button>
        {/if}
      </div>
    {/if}
  </main>
</div>

<style>
  .podcasts-tab {
    display: flex;
    height: 100%;
    gap: 1px;
    background: var(--hifi-border-dark);
    overflow: hidden;
    font-family: 'Barlow', sans-serif;
    user-select: none;
  }

  .podcast-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
    background: var(--hifi-bg-secondary);
  }

  .content-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    background: var(--hifi-bg-panel);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    flex-shrink: 0;
  }

  .toolbar-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--hifi-font-segment, 'Orbitron', monospace);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: var(--hifi-text-secondary);
  }

  .loading-center {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .welcome-center {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 40px;
  }

  .welcome-icon {
    font-size: 48px;
    color: var(--hifi-text-secondary);
    opacity: 0.2;
  }

  .welcome-title {
    font-family: var(--hifi-font-segment, 'Orbitron', monospace);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .welcome-hint {
    font-family: var(--hifi-font-family, 'Barlow', sans-serif);
    font-size: 13px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }
</style>
