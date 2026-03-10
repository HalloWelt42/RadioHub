<script>
  /**
   * EpisodeList - Container für Episoden
   * Sticky Column-Headers, Sortierung, Keyboard-Nav, Infinite Scroll.
   */
  import EpisodeRow from './EpisodeRow.svelte';
  import EpisodeDetails from './EpisodeDetails.svelte';
  import { appState } from '../../lib/store.svelte.js';

  let {
    episodes = [],
    sortBy = 'published_at',
    sortOrder = 'desc',
    selectedEpisodeId = null,
    focusedIndex = -1,
    showPodcastColumn = false,
    podcastMap = {},
    isLoadingMore = false,
    downloadProgress = {},
    onsort = () => {},
    onselect = () => {},
    onplay = () => {},
    onscroll = () => {},
    ondownload = () => {},
    ondeletedownload = () => {},
    ontoggleplayed = () => {},
    onkeydown = () => {}
  } = $props();

  let listEl;

  function handleScroll(e) {
    const el = e.target;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 200) {
      onscroll();
    }
  }

  function handleListKeydown(e) {
    onkeydown(e);
  }

  function toggleSort(column) {
    if (sortBy === column) {
      onsort(column, sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      onsort(column, column === 'title' ? 'asc' : 'desc');
    }
  }

  export function scrollToIndex(idx) {
    if (!listEl) return;
    const rows = listEl.querySelectorAll('.episode-row');
    if (rows[idx]) {
      rows[idx].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }
</script>

<div
  class="episode-list"
  bind:this={listEl}
  onscroll={handleScroll}
  onkeydown={handleListKeydown}
  tabindex="0"
>
  <!-- Sticky Column Headers -->
  <div class="column-headers">
    <div class="col-led"></div>
    <div class="col-cover"></div>
    <div
      class="col-title"
      class:col-active={sortBy === 'title'}
      onclick={() => toggleSort('title')}
    >
      TITEL
      {#if sortBy === 'title'}
        <i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>
      {/if}
    </div>
    <div class="col-badges"></div>
    <div
      class="col-date"
      class:col-active={sortBy === 'published_at'}
      onclick={() => toggleSort('published_at')}
    >
      DATUM
      {#if sortBy === 'published_at'}
        <i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>
      {/if}
    </div>
    <div
      class="col-duration"
      class:col-active={sortBy === 'duration'}
      onclick={() => toggleSort('duration')}
    >
      DAUER
      {#if sortBy === 'duration'}
        <i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>
      {/if}
    </div>
  </div>

  <!-- Episode Rows -->
  {#if episodes.length === 0}
    <div class="empty">
      <div class="empty-text">Keine Episoden</div>
    </div>
  {:else}
    {#each episodes as episode, idx (episode.id)}
      {@const isPlaying = appState.currentEpisode?.id === episode.id && appState.isPlaying}
      {@const isSelected = selectedEpisodeId === episode.id}
      {@const isFocused = focusedIndex === idx}

      <EpisodeRow
        {episode}
        {isPlaying}
        {isFocused}
        {isSelected}
        {showPodcastColumn}
        podcastTitle={podcastMap[episode.podcast_id]?.title || ''}
        onclick={(ep) => onselect(ep)}
        onplay={(ep) => onplay(ep)}
      />

      {#if isSelected}
        <EpisodeDetails
          {episode}
          isDownloading={downloadProgress[episode.id] === 'downloading'}
          onplay={(ep) => onplay(ep)}
          ondownload={(ep) => ondownload(ep)}
          ondeletedownload={(ep) => ondeletedownload(ep)}
          ontoggleplayed={(ep) => ontoggleplayed(ep)}
        />
      {/if}
    {/each}

    {#if isLoadingMore}
      <div class="loading-more">
        <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .episode-list {
    flex: 1;
    overflow-y: auto;
    outline: none;
    background: var(--hifi-bg-panel);
  }

  .column-headers {
    display: grid;
    grid-template-columns: 28px 36px 1fr auto 110px 70px;
    gap: 12px;
    padding: 6px 24px 6px 16px;
    position: sticky;
    top: -1px;
    z-index: 20;
    background: var(--hifi-bg-tertiary);
    border-bottom: none;
    box-shadow: 0 2px 0 0 var(--hifi-bg-tertiary);
    font-family: var(--hifi-font-segment, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--hifi-text-secondary);
    user-select: none;
  }

  .column-headers > div {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .col-title,
  .col-date,
  .col-duration {
    cursor: pointer;
    transition: color 0.15s;
  }

  .col-title:hover,
  .col-date:hover,
  .col-duration:hover {
    color: var(--hifi-text-primary);
  }

  .col-active {
    color: var(--hifi-accent) !important;
  }

  .col-date,
  .col-duration {
    justify-content: flex-end;
  }

  .empty {
    display: flex;
    justify-content: center;
    padding: 60px 20px;
  }

  .empty-text {
    font-family: var(--hifi-font-segment, 'Orbitron', monospace);
    font-size: 12px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .loading-more {
    display: flex;
    justify-content: center;
    padding: 20px;
  }
</style>
