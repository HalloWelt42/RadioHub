<script>
  /**
   * PodcastSidebar - Linkes Panel
   * Abo-Liste, Status-Filter, Speicher-Info.
   */
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import CoverArt from '../shared/CoverArt.svelte';
  import PodcastSearch from './PodcastSearch.svelte';
  import { api } from '../../lib/api.js';
  import { tick } from 'svelte';
  import * as sfx from '../../lib/uiSounds.js';
  import { t } from '../../lib/i18n.svelte.js';

  let showSearch = $state(false);

  let hoverPodcast = $state(null);
  let hoverY = $state(0);

  function handleSubMouseEnter(e, podcast) {
    hoverPodcast = podcast;
    const rect = e.currentTarget.getBoundingClientRect();
    const sidebar = e.currentTarget.closest('.podcast-sidebar');
    const sidebarRect = sidebar?.getBoundingClientRect();
    hoverY = rect.top - (sidebarRect?.top || 0);
  }

  function handleSubMouseLeave() {
    hoverPodcast = null;
  }

  let {
    subscriptions = [],
    selectedPodcastId = null,
    filterStatus = 'all',
    stats = {},
    width = 280,
    subscribedFeedUrls = new Set(),
    fileExplorerActive = false,
    refreshCountdown = '',
    currentlyPlayingPodcastId = null,
    onselectpodcast = () => {},
    onfilterchange = () => {},
    onsearchclick = () => {},
    onallepisodesclick = () => {},
    onrefreshall = () => {},
    onrefreshpodcast = () => {},
    onautodownloadtoggle = () => {},
    onselectepisode = () => {},
    onsubscribe = () => {},
    onfileexplorer = () => {},
    onresize = () => {}
  } = $props();

  let totalEpisodes = $derived(subscriptions.reduce((sum, s) => sum + (s.episode_count || 0), 0));

  let filters = $derived([
    { key: 'today', label: t('podcasts.heute'), count: stats.today || 0, unplayed: stats.today_unplayed || 0 },
    { key: 'week', label: t('podcasts.woche'), count: stats.week || 0, unplayed: stats.week_unplayed || 0 },
    { key: 'all', label: t('podcasts.alle'), count: totalEpisodes, unplayed: null }
  ]);

  // === Resize Handle ===
  let isDragging = $state(false);
  let startX = 0;
  let startWidth = 0;

  function handleResizeStart(e) {
    e.preventDefault();
    isDragging = true;
    startX = e.clientX;
    startWidth = width;
    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function handleResizeMove(e) {
    if (!isDragging) return;
    const delta = e.clientX - startX;
    const newWidth = Math.min(Math.max(startWidth + delta, 200), 500);
    onresize(newWidth);
  }

  function handleResizeEnd() {
    isDragging = false;
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }

  // Spielenden Podcast in Sicht scrollen
  $effect(() => {
    if (currentlyPlayingPodcastId) {
      tick().then(() => {
        const el = document.querySelector(`.sub-item[data-podcast-id="${currentlyPlayingPodcastId}"]`);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    }
  });
</script>

<aside class="podcast-sidebar" style="width: {width}px; min-width: {width}px;">
  <!-- Action Row -->
  <div class="sidebar-actions">
    <button
      class="action-btn"
      class:active={showSearch}
      onclick={() => { showSearch = !showSearch; sfx.click(); }}
      title={showSearch ? t('podcasts.sucheSchliessen') : t('podcasts.suchen')}
    >
      <i class="fa-solid {showSearch ? 'fa-xmark' : 'fa-magnifying-glass'}"></i>
    </button>
    <button
      class="action-btn"
      onclick={() => { onallepisodesclick(); sfx.click(); }}
      title={t('podcasts.alleEpisodenAnzeigen')}
    >
      <i class="fa-solid fa-layer-group"></i>
    </button>
    <button
      class="action-btn"
      class:active={fileExplorerActive}
      onclick={() => { onfileexplorer(); sfx.click(); }}
      title={fileExplorerActive ? t('podcasts.dateiExplorerSchliessen') : t('podcasts.dateiExplorerOeffnen')}
    >
      <i class="fa-solid fa-folder-tree"></i>
    </button>
    <button
      class="action-btn"
      onclick={() => { onrefreshall(); sfx.click(); }}
      title={t('podcasts.alleFeedsHolen')}
    >
      <i class="fa-solid fa-cloud-arrow-down"></i>
    </button>
  </div>

  <div class="sidebar-divider"></div>

  {#if showSearch}
    <!-- Suche -->
    <PodcastSearch
      {subscribedFeedUrls}
      onselectepisode={(ep) => { showSearch = false; onselectepisode(ep); }}
      onselectpodcast={(p) => { showSearch = false; onselectpodcast(p); }}
      onsubscribe={onsubscribe}
      onclose={() => { showSearch = false; }}
    />
  {:else}
    <!-- Abo-Liste -->
    <div class="section-scrollable">
      <div class="section-header">
        <span class="section-label">{t('podcasts.abonnements')}</span>
        <span class="section-count">{subscriptions.length}</span>
      </div>

      {#if subscriptions.length === 0}
        <div class="empty-hint" onclick={() => { showSearch = true; sfx.click(); }} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); showSearch = true; sfx.click(); } }}>
          {t('podcasts.podcastsSuchenAbonnieren')}
        </div>
      {:else}
        <div class="sub-list">
          {#each subscriptions as podcast (podcast.id)}
            {@const isSelected = selectedPodcastId === podcast.id}
            {@const isPlaying = currentlyPlayingPodcastId === podcast.id}
            {@const hasUnplayed = (podcast.unplayed_count || 0) > 0}
            {@const hasDownloads = (podcast.downloaded_count || 0) > 0}
            <button
              class="sub-item"
              class:selected={isSelected}
              class:playing={isPlaying}
              data-podcast-id={podcast.id}
              onclick={() => { onselectpodcast(podcast); sfx.click(); }}
              onmouseenter={(e) => { handleSubMouseEnter(e, podcast); sfx.hover(); }}
              onmouseleave={handleSubMouseLeave}
            >
              <CoverArt
                src={podcast.id ? api.getPodcastImageUrl(podcast.id) : podcast.image_url}
                alt={podcast.title}
                size="sm"
              />
              <div class="sub-info">
                <div class="sub-title">{podcast.title}</div>
                <div class="sub-meta">
                  {podcast.episode_count || 0} Ep.
                  {#if hasUnplayed}
                    <span class="unplayed-count">{podcast.unplayed_count} neu</span>
                  {/if}
                </div>
              </div>
              {#if podcast.auto_download}
                <i
                  class="fa-solid fa-arrows-rotate sub-auto-icon active"
                  title={t('podcasts.autoDownloadAus')}
                  onclick={(e) => { e.stopPropagation(); onautodownloadtoggle(podcast); sfx.click(); }}
                  role="button"
                  tabindex="-1"
                  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onautodownloadtoggle(podcast); sfx.click(); } }}
                ></i>
              {/if}
              <i
                class="fa-solid fa-cloud-arrow-down sub-fetch-icon"
                class:has-episodes={(podcast.episode_count || 0) > 0}
                title={t('podcasts.episodenLaden')}
                onclick={(e) => { e.stopPropagation(); onrefreshpodcast(podcast); sfx.click(); }}
                role="button"
                tabindex="-1"
                onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onrefreshpodcast(podcast); sfx.click(); } }}
              ></i>
              <HiFiLed color={isPlaying ? 'green' : isSelected ? 'blue' : hasUnplayed ? 'green' : 'off'} size="small" pulse={isPlaying} title={isPlaying ? t('podcasts.wirdAbgespielt') : isSelected ? t('podcasts.ausgewaehltStatus') : hasUnplayed ? t('podcasts.neueEpisoden') : t('podcasts.keineNeuen')} />
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="sidebar-divider"></div>

    <!-- Status-Filter -->
    <div class="section-fixed">
      <div class="section-header">
        <span class="section-label">{t('podcasts.filterLabel')}</span>
      </div>
      <div class="filter-list">
        {#each filters as f}
          {@const isActive = filterStatus === f.key}
          <button
            class="filter-item"
            class:selected={isActive}
            onclick={() => { onfilterchange(f.key); sfx.click(); }}
          >
            <HiFiLed color={isActive ? 'yellow' : 'off'} size="small" title={isActive ? t('podcasts.filterAktiv') : t('podcasts.filterInaktiv')} />
            <span class="filter-label">{f.label}</span>
            {#if f.unplayed != null && f.unplayed > 0}
              <span class="filter-unplayed">{f.unplayed}</span>
            {/if}
            <span class="filter-count">{f.count}</span>
          </button>
        {/each}
      </div>
    </div>
  {/if}


  <!-- Refresh Timer -->
  {#if refreshCountdown}
    <div class="refresh-timer" title={t('podcasts.naechsterRefresh')}>
      <i class="fa-solid fa-clock"></i>
      <span class="timer-label">{t('stationDetail.refresh')}</span>
      <span class="timer-value">{refreshCountdown}</span>
    </div>
  {/if}

  <!-- Hover Preview -->
  {#if hoverPodcast}
    <div class="hover-preview" style="top: {hoverY}px;">
      <img
        src={hoverPodcast.id ? api.getPodcastImageUrl(hoverPodcast.id) : hoverPodcast.image_url}
        alt={hoverPodcast.title}
        class="preview-img"
      />
      <div class="preview-info">
        <div class="preview-title">{hoverPodcast.title}</div>
        {#if hoverPodcast.author}
          <div class="preview-author">{hoverPodcast.author}</div>
        {/if}
        <div class="preview-stats">
          {hoverPodcast.episode_count || 0} {t('podcasts.episodenLabel')}
          {#if (hoverPodcast.unplayed_count || 0) > 0}
            -- {hoverPodcast.unplayed_count} neu
          {/if}
        </div>
      </div>
    </div>
  {/if}

  <!-- Resize Handle -->
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="resize-handle"
    class:active={isDragging}
    onmousedown={handleResizeStart}
    title={t('podcasts.breiteAnpassen')}
    role="separator"
  ></div>
</aside>

<style>
  .podcast-sidebar {
    position: relative;
    display: flex;
    flex-direction: column;
    background: var(--hifi-bg-panel);
    overflow: hidden;
    flex-shrink: 0;
  }

  /* Hover Preview */
  .hover-preview {
    position: absolute;
    left: calc(100% + 8px);
    z-index: 50;
    display: flex;
    gap: 10px;
    padding: 10px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm, 4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    pointer-events: none;
    min-width: 240px;
    max-width: 320px;
  }

  .preview-img {
    width: 80px;
    height: 80px;
    object-fit: cover;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .preview-info {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
  }

  .preview-title {
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: var(--hifi-text-primary);
  }

  .preview-author {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-secondary);
  }

  .preview-stats {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    margin-top: 4px;
  }

  .resize-handle {
    position: absolute;
    top: 0;
    right: -3px;
    width: 6px;
    height: 100%;
    cursor: col-resize;
    z-index: 20;
    transition: background 0.15s;
  }

  .resize-handle:hover,
  .resize-handle.active {
    background: var(--hifi-accent);
    opacity: 0.5;
  }

  .sidebar-actions {
    display: flex;
    gap: 4px;
    padding: 10px 10px;
  }

  .action-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 34px;
    padding: 0;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-sm, 4px);
    color: var(--hifi-text-secondary);
    cursor: pointer;
    font-size: 12px;
    transition: all 0.15s;
    box-shadow: var(--hifi-shadow-button);
  }

  .action-btn:hover {
    color: var(--hifi-text-primary);
    box-shadow: 2px 2px 4px var(--hifi-shadow-dark),
                -2px -2px 4px var(--hifi-shadow-light);
  }

  .action-btn:active {
    box-shadow: var(--hifi-shadow-inset);
  }

  .action-btn.active {
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }

  .sidebar-divider {
    height: 1px;
    background: var(--hifi-border-dark);
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px 4px;
  }

  .section-label {
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    font-weight: 400;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
  }

  .section-count {
    margin-left: auto;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-accent);
  }

  .section-scrollable {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .section-fixed {
    flex-shrink: 0;
  }

  .empty-hint {
    padding: 12px 10px;
    font-family: var(--hifi-font-family, 'Barlow', sans-serif);
    font-size: 11px;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
    cursor: pointer;
    text-align: center;
  }

  .empty-hint:hover {
    color: var(--hifi-accent);
    opacity: 1;
  }

  .sub-list {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 0 4px 4px;
  }

  .sub-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 6px;
    background: none;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.15s;
    text-align: left;
    width: 100%;
  }

  .sub-item:hover {
    background: var(--hifi-row-hover);
  }

  .sub-item.selected {
    background: rgba(51, 153, 255, 0.08);
  }

  .sub-item.playing {
    background: rgba(76, 175, 80, 0.08);
    border-left: 2px solid rgba(76, 175, 80, 0.5);
  }

  .sub-info {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .sub-title {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 500;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sub-meta {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
    margin-top: 1px;
    white-space: nowrap;
  }

  .unplayed-count {
    color: var(--hifi-text-green);
    opacity: 1;
  }

  .sub-fetch-icon {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0;
    cursor: pointer;
    transition: opacity 0.15s, color 0.15s;
    flex-shrink: 0;
  }

  .sub-fetch-icon.has-episodes {
    opacity: 0.4;
    color: var(--hifi-text-secondary);
  }

  .sub-item:hover .sub-fetch-icon {
    opacity: 1;
  }

  .sub-fetch-icon:hover {
    color: var(--hifi-accent) !important;
  }

  .sub-auto-icon {
    font-size: 9px;
    color: var(--hifi-text-secondary);
    opacity: 0;
    cursor: pointer;
    transition: opacity 0.15s, color 0.15s;
    flex-shrink: 0;
  }

  .sub-auto-icon.active {
    opacity: 0.5;
    color: var(--hifi-text-green);
  }

  .sub-item:hover .sub-auto-icon {
    opacity: 1;
  }

  .sub-auto-icon:hover {
    color: var(--hifi-text-red, #ef5350) !important;
  }

  .filter-list {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 0 4px 4px;
  }

  .filter-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 10px 5px 6px;
    background: none;
    border: none;
    border-radius: var(--hifi-border-radius-sm, 4px);
    cursor: pointer;
    transition: background 0.15s;
    text-align: left;
    width: 100%;
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 400;
    color: var(--hifi-text-primary);
  }

  .filter-item:hover {
    background: var(--hifi-row-hover);
  }

  .filter-item.selected {
    color: var(--hifi-accent);
  }

  .filter-label {
    flex: 1;
    font-size: inherit;
    font-weight: inherit;
    color: inherit;
  }

  .filter-unplayed {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-green);
    background: rgba(76, 175, 80, 0.12);
    padding: 1px 5px;
    border-radius: 8px;
    margin-left: auto;
  }

  .filter-count {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-accent);
    text-align: right;
    min-width: 30px;
    letter-spacing: 0.3px;
  }

  /* Refresh Timer */
  .refresh-timer {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-top: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
  }

  .refresh-timer i {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .timer-label {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .timer-value {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    margin-left: auto;
  }

</style>
