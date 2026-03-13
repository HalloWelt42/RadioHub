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
  import DownloadJobPanel from './podcasts/DownloadJobPanel.svelte';
  import FileExplorer from './shared/FileExplorer.svelte';
  import HiFiDisplay from './hifi/HiFiDisplay.svelte';
  import SearchBarWithHistory from './shared/SearchBarWithHistory.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import * as sfx from '../lib/uiSounds.js';

  // === View State (aus Route abgeleitet) ===
  const VIEW_MAP = { search: 'search', all: 'all-episodes', files: 'file-explorer' };
  const VIEW_TO_ROUTE = { 'episodes': '/podcast', 'search': '/podcast/search', 'all-episodes': '/podcast/all', 'file-explorer': '/podcast/files' };

  let view = $derived.by(() => {
    if (appState.activeTab !== 'podcasts') return 'episodes';
    const seg = appState.routeSegments?.[0];
    return VIEW_MAP[seg] || 'episodes';
  });

  function setView(v) {
    actions.navigateTo(VIEW_TO_ROUTE[v] || '/podcast');
  }
  let selectedPodcastId = $state(null);
  let selectedPodcast = $state(null);

  // === Daten ===
  let subscriptions = $state([]);
  let episodes = $state([]);
  let searchResults = $state([]);
  let stats = $state({});

  // === Filter/Sort ===
  let filterStatus = $state('today');
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

  // === File Explorer ===
  let fileExplorerFolders = $state([]);
  let fileExplorerTotalSize = $state(0);
  let fileExplorerTotalFiles = $state(0);
  let fileExplorerLoading = $state(false);

  // === Refresh Timer ===
  let refreshCountdown = $state('');
  let nextRefreshAt = $state(null);
  let timerInterval = null;

  function updateCountdown() {
    if (!nextRefreshAt) { refreshCountdown = ''; return; }
    const now = Date.now();
    const target = new Date(nextRefreshAt).getTime();
    const diff = Math.max(0, Math.floor((target - now) / 1000));
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    const s = diff % 60;
    refreshCountdown = `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  async function loadRefreshStatus() {
    try {
      const status = await api.getRefreshStatus();
      nextRefreshAt = status.next_refresh_at;
      updateCountdown();
    } catch (e) {
      // Kein Fehler anzeigen - Timer ist optional
    }
  }

  // === Aktuell spielender Podcast ===
  let currentlyPlayingPodcastId = $derived(
    appState.playerMode === 'podcast' && appState.podcastPlaylistPodcast
      ? appState.podcastPlaylistPodcast.id
      : null
  );

  // === Init ===
  $effect(() => {
    loadSubscriptions();
    loadStats();
    loadRefreshStatus();
    timerInterval = setInterval(updateCountdown, 1000);
    return () => { if (timerInterval) clearInterval(timerInterval); };
  });

  // === Daten laden ===
  async function loadSubscriptions() {
    try {
      const result = await api.getSubscriptions();
      subscriptions = result.subscriptions || [];
      // selectedPodcast mit frischen Daten synchronisieren
      if (selectedPodcastId) {
        const fresh = subscriptions.find(s => s.id === selectedPodcastId);
        if (fresh) selectedPodcast = fresh;
      }
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
  }

  async function loadStats() {
    try {
      stats = await api.getPodcastStats();
    } catch (e) {
      // Netzwerkfehler ignorieren
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
      // Netzwerkfehler ignorieren
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
      // Netzwerkfehler ignorieren
    }

    isLoading = false;
    isLoadingMore = false;
  }

  // === Sidebar Callbacks ===
  function handleSelectPodcast(podcast) {
    selectedPodcastId = podcast.id;
    selectedPodcast = podcast;
    setView('episodes');
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
    setView('search');
    searchResults = [];
  }

  function handleFileExplorer() {
    if (view === 'file-explorer') {
      setView('episodes');
    } else {
      setView('file-explorer');
      loadFileExplorer();
    }
  }

  async function loadFileExplorer() {
    fileExplorerLoading = true;
    try {
      const result = await api.getPodcastFiles();
      fileExplorerFolders = result.folders || [];
      fileExplorerTotalSize = result.total_size || 0;
      fileExplorerTotalFiles = result.total_files || 0;
    } catch (e) {
      actions.showToast(t('podcasts.dateienLadenFehler'), 'error');
    }
    fileExplorerLoading = false;
  }

  async function handleFileDelete(file) {
    try {
      await api.deleteFileExplorer(file.path);
      actions.showToast(t('toast.dateiGeloescht'), 'success');
      await loadFileExplorer();
    } catch (e) {
      actions.showToast(t('toast.loeschenFehler'), 'error');
    }
  }

  function handleFilePlay(file) {
    // Podcast-Datei als Recording abspielen
    actions.playRecording({
      path: file.path,
      name: file.name,
      playUrl: api.getPlayUrl(file.path.replace(/^.*\/recordings\//, '')),
      source: 'podcast'
    });
  }

  function handleAllEpisodesClick() {
    selectedPodcastId = null;
    selectedPodcast = null;
    setView('all-episodes');
    loadAllEpisodes();
  }

  async function handleRefreshAll() {
    try {
      actions.showToast(t('podcasts.aktualisiereFeeds'), 'info');
      await api.refreshAllPodcasts();
      await loadSubscriptions();
      await loadStats();
      if (view === 'episodes' && selectedPodcastId) {
        loadEpisodes(selectedPodcastId);
      } else if (view === 'all-episodes') {
        loadAllEpisodes();
      }
      actions.showToast(t('podcasts.alleFeedsAktualisiert'), 'success');
      await loadRefreshStatus();  // Timer zurücksetzen
    } catch (e) {
      actions.showToast(t('podcasts.aktualisiereFehler'), 'error');
    }
  }

  // === Search ===
  async function handleSearch(query) {
    isSearching = true;
    setView('search');
    try {
      const result = await api.searchPodcasts(query);
      searchResults = result.results || [];
    } catch (e) {
      actions.showToast(t('podcasts.sucheFehler'), 'error');
      searchResults = [];
    }
    isSearching = false;
  }

  async function handleSubscribe(podcast) {
    try {
      await api.subscribePodcast(podcast.feed_url);
      actions.showToast(`"${podcast.title}" ${t('toast.abonniert')}`, 'success');
      sfx.click();
      await loadSubscriptions();
      await loadStats();
    } catch (e) {
      actions.showToast(t('podcasts.abonnierenFehler'), 'error');
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
      actions.showToast(t('toast.feedAktualisiert'), 'success');
    } catch (e) {
      actions.showToast(t('podcasts.aktualisiereFehler'), 'error');
    }
    isRefreshing = false;
  }

  // Download-Batch State
  let batchTotal = $state(0);
  let batchDone = $state(0);
  let batchFailed = $state(0);
  let batchActive = $state(false);
  let batchPaused = $state(false);
  let batchCancelled = $state(false);
  let batchCurrentName = $state('');

  // Pause/Resume Promise-Paar
  let pauseResolve = null;

  function waitForResume() {
    return new Promise(resolve => { pauseResolve = resolve; });
  }

  function handleBatchPause() {
    batchPaused = true;
  }

  function handleBatchResume() {
    batchPaused = false;
    if (pauseResolve) {
      pauseResolve();
      pauseResolve = null;
    }
  }

  function handleBatchCancel() {
    batchCancelled = true;
    batchPaused = false;
    if (pauseResolve) {
      pauseResolve();
      pauseResolve = null;
    }
  }

  async function handleDownloadAll() {
    if (!selectedPodcastId || episodes.length === 0) return;
    const undownloaded = episodes.filter(e => !e.is_downloaded);
    if (undownloaded.length === 0) {
      actions.showToast(t('podcasts.alleBereitsHeruntergeladen'), 'info');
      return;
    }
    batchTotal = undownloaded.length;
    batchDone = 0;
    batchFailed = 0;
    batchActive = true;
    batchPaused = false;
    batchCancelled = false;
    batchCurrentName = '';

    for (const ep of undownloaded) {
      if (batchCancelled) break;

      // Bei Pause warten
      if (batchPaused) {
        await waitForResume();
        if (batchCancelled) break;
      }

      batchCurrentName = ep.title || `Episode ${ep.id}`;
      downloadProgress = { ...downloadProgress, [ep.id]: 'downloading' };

      try {
        await api.downloadEpisode(ep.id);
        downloadProgress = { ...downloadProgress, [ep.id]: 'done' };
        batchDone++;
        // Episode in der Liste aktualisieren
        episodes = episodes.map(e =>
          e.id === ep.id ? { ...e, is_downloaded: true } : e
        );
      } catch {
        downloadProgress = { ...downloadProgress, [ep.id]: 'error' };
        batchFailed++;
        batchDone++;
      }
    }

    const wasCancelled = batchCancelled;
    batchActive = false;
    batchCurrentName = '';
    downloadProgress = {};
    await loadSubscriptions();
    await loadStats();

    if (wasCancelled) {
      actions.showToast(t('podcasts.downloadAbgebrochen', { done: batchDone, total: batchTotal }), 'warning');
    } else if (batchFailed > 0) {
      actions.showToast(t('cutterExtra.heruntergeladenFailed', { ok: batchTotal - batchFailed, failed: batchFailed }), 'warning');
    } else {
      actions.showToast(t('podcasts.episodenHeruntergeladen', { total: batchTotal }), 'success');
    }
  }

  async function handleSidebarAutoDownloadToggle(podcast) {
    try {
      const newVal = !podcast.auto_download;
      await api.setAutoDownload(podcast.id, newVal);
      subscriptions = subscriptions.map(s =>
        s.id === podcast.id ? { ...s, auto_download: newVal } : s
      );
      if (selectedPodcast && selectedPodcast.id === podcast.id) {
        selectedPodcast = { ...selectedPodcast, auto_download: newVal };
      }
      actions.showToast(newVal ? t('podcasts.autoDownloadAktiviert') : t('podcasts.autoDownloadDeaktiviert'), 'info');
    } catch (e) {
      actions.showToast(t('podcasts.einstellungFehler'), 'error');
    }
  }

  async function handleRefreshSinglePodcast(podcast) {
    try {
      actions.showToast(t('cutterExtra.ladePodcast', { title: podcast.title }), 'info');
      await api.refreshPodcast(podcast.id);
      await loadSubscriptions();
      // Wenn dieser Podcast gerade angezeigt wird, Episoden neu laden
      if (selectedPodcastId === podcast.id) {
        await loadEpisodes(podcast.id);
      }
      actions.showToast(t('cutterExtra.podcastAktualisiert', { title: podcast.title }), 'success');
    } catch (e) {
      actions.showToast(t('podcasts.aktualisiereFehler'), 'error');
    }
  }

  async function handleUnsubscribe() {
    if (!selectedPodcastId) return;
    try {
      await api.unsubscribePodcast(selectedPodcastId);
      actions.showToast(t('podcasts.aboEntfernt'), 'success');
      selectedPodcastId = null;
      selectedPodcast = null;
      setView('episodes');
      episodes = [];
      await loadSubscriptions();
      await loadStats();
    } catch (e) {
      actions.showToast(t('podcasts.entfernenFehler'), 'error');
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
      actions.showToast(newVal ? t('podcasts.autoDownloadAktiviert') : t('podcasts.autoDownloadDeaktiviert'), 'info');
    } catch (e) {
      actions.showToast(t('podcasts.einstellungFehler'), 'error');
    }
  }

  function handleBack() {
    selectedPodcastId = null;
    selectedPodcast = null;
    setView('episodes');
    episodes = [];
  }

  // === Search Episode Select ===
  async function handleSearchEpisodeSelect(episode) {
    // Zum Podcast der Episode wechseln
    const podId = episode.podcast_id;
    const podcast = subscriptions.find(s => s.id === podId);
    if (podcast) {
      selectedPodcastId = podId;
      selectedPodcast = podcast;
      setView('episodes');
      await loadEpisodes(podId);
      // Episode aufklappen
      selectedEpisodeId = episode.id;
      // Zum Eintrag scrollen
      setTimeout(() => {
        const el = document.querySelector(`.episode-row[data-id="${episode.id}"]`);
        if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }, 200);
    }
  }

  // === Episode Callbacks ===
  function handleEpisodeSelect(episode) {
    selectedEpisodeId = selectedEpisodeId === episode.id ? null : episode.id;
    sfx.click();
  }

  function handleEpisodePlay(episode) {
    // Playlist zusammenstellen - immer ueber Backend (play = lokal, stream = Proxy)
    const playlist = episodes.map(e => ({
      ...e,
      audio_url: e.is_downloaded ? api.getEpisodePlayUrl(e.id) : api.getEpisodeStreamUrl(e.id)
    }));
    const podcast = selectedPodcast || podcastMap[episode.podcast_id] || null;
    actions.playEpisodeFromList(
      { ...episode, audio_url: episode.is_downloaded ? api.getEpisodePlayUrl(episode.id) : api.getEpisodeStreamUrl(episode.id) },
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
      await loadSubscriptions();
      await loadStats();
      actions.showToast(t('podcasts.episodeHeruntergeladen'), 'success');
    } catch (e) {
      downloadProgress = { ...downloadProgress, [episode.id]: 'error' };
      actions.showToast(t('podcasts.downloadFehler'), 'error');
    }
  }

  async function handleDeleteDownload(episode) {
    try {
      await api.deleteEpisodeDownload(episode.id);
      episodes = episodes.map(e =>
        e.id === episode.id ? { ...e, is_downloaded: false, file_size: 0 } : e
      );
      await loadSubscriptions();
      await loadStats();
      actions.showToast(t('podcasts.downloadGeloescht'), 'success');
    } catch (e) {
      actions.showToast(t('toast.loeschenFehler'), 'error');
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
      actions.showToast(t('podcasts.markierungFehler'), 'error');
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
    {subscribedFeedUrls}
    width={sidebarWidth}
    fileExplorerActive={view === 'file-explorer'}
    {refreshCountdown}
    {currentlyPlayingPodcastId}
    onselectpodcast={handleSelectPodcast}
    onfilterchange={handleFilterChange}
    onsearchclick={handleSearchClick}
    onallepisodesclick={handleAllEpisodesClick}
    onrefreshall={handleRefreshAll}
    onrefreshpodcast={handleRefreshSinglePodcast}
    onautodownloadtoggle={handleSidebarAutoDownloadToggle}
    onselectepisode={handleSearchEpisodeSelect}
    onsubscribe={handleSubscribe}
    onfileexplorer={handleFileExplorer}
    onresize={handleSidebarResize}
  />

  <!-- Content (rechts) -->
  <main class="podcast-content">
    {#if view === 'file-explorer'}
      <!-- Datei-Explorer -->
      <div class="content-toolbar">
        <div class="toolbar-title">
          <i class="fa-solid fa-folder-tree"></i>
          <span>{t('podcasts.podcastDateien')}</span>
        </div>
      </div>
      <FileExplorer
        type="podcast"
        folders={fileExplorerFolders}
        totalSize={fileExplorerTotalSize}
        totalFiles={fileExplorerTotalFiles}
        isLoading={fileExplorerLoading}
        onplay={handleFilePlay}
        ondelete={handleFileDelete}
        onrefresh={loadFileExplorer}
      />

    {:else if view === 'search'}
      <!-- Suchleiste -->
      <div class="content-toolbar">
        <SearchBarWithHistory
          placeholder={t('podcasts.podcastsSuchen')}
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
          <span>{t('podcasts.alleEpisoden')}</span>
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
        totalDuration={selectedPodcast?.total_duration || 0}
        {isRefreshing}
        {batchActive}
        {batchTotal}
        {batchDone}
        onrefresh={handleRefreshPodcast}
        ondownloadall={handleDownloadAll}
        onunsubscribe={handleUnsubscribe}
        onautodownloadtoggle={handleAutoDownloadToggle}
        onback={handleBack}
      />
      <DownloadJobPanel
        active={batchActive}
        total={batchTotal}
        done={batchDone}
        failed={batchFailed}
        currentName={batchCurrentName}
        paused={batchPaused}
        onpause={handleBatchPause}
        onresume={handleBatchResume}
        oncancel={handleBatchCancel}
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
      <div class="welcome-state">
        <i class="fa-solid fa-podcast welcome-icon"></i>
        <HiFiDisplay size="medium">{t('nav.podcast')}</HiFiDisplay>
        <p class="welcome-hint">
          {#if subscriptions.length > 0}
            {t('podcasts.podcastAuswaehlen')}
          {:else}
            {t('podcasts.podcastsSuchenAbonnieren')}
          {/if}
        </p>
        {#if subscriptions.length === 0}
          <button class="hifi-btn hifi-btn-primary" onclick={() => { setView('search'); sfx.click(); }}>
            <i class="fa-solid fa-magnifying-glass"></i> {t('podcasts.podcastsSuchenBtn')}
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
    padding: 10px 10px;
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

  .welcome-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: var(--hifi-text-secondary);
  }

  .welcome-icon {
    font-size: 40px;
    opacity: 0.15;
  }

  .welcome-hint {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }
</style>
