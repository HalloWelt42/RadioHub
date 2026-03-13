<script>
  /**
   * PodcastSearch - Dynamische Volltextsuche
   * Erscheint unter den Sidebar-Buttons, ersetzt Abo-Liste mit Ergebnissen.
   * Scope-Badges: Episoden, Abos, Extern.
   * Treffer-Markierung in Titeln und Snippets.
   */
  import CoverArt from '../shared/CoverArt.svelte';
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import * as sfx from '../../lib/uiSounds.js';

  let {
    onselectepisode = () => {},
    onselectpodcast = () => {},
    onsubscribe = () => {},
    onclose = () => {},
    subscribedFeedUrls = new Set()
  } = $props();

  let query = $state('');
  let scope = $state('episodes'); // 'episodes' | 'subscriptions' | 'extern'
  let isSearching = $state(false);
  let episodeResults = $state([]);
  let subResults = $state([]);
  let externResults = $state([]);
  let totalEpisodes = $state(0);
  let debounceTimer = null;
  let inputEl;

  const scopes = [
    { key: 'episodes', label: 'Episoden', icon: 'fa-list' },
    { key: 'subscriptions', label: 'Abos', icon: 'fa-rss' },
    { key: 'extern', label: 'Extern', icon: 'fa-globe' }
  ];

  $effect(() => {
    if (inputEl) inputEl.focus();
  });

  function handleInput(e) {
    query = e.target.value;
    clearTimeout(debounceTimer);
    if (query.length >= 2) {
      debounceTimer = setTimeout(() => doSearch(), 300);
    } else {
      episodeResults = [];
      subResults = [];
      externResults = [];
      totalEpisodes = 0;
    }
  }

  function handleScopeChange(newScope) {
    scope = newScope;
    sfx.click();
    if (query.length >= 2) {
      doSearch();
    }
  }

  async function doSearch() {
    if (query.length < 2) return;
    isSearching = true;

    try {
      if (scope === 'episodes') {
        const result = await api.searchEpisodes(query, 50);
        episodeResults = result.episodes || [];
        totalEpisodes = result.total || 0;
      } else if (scope === 'subscriptions') {
        const result = await api.searchSubscriptions(query);
        subResults = result.subscriptions || [];
      } else if (scope === 'extern') {
        const result = await api.searchPodcasts(query);
        externResults = result.results || [];
      }
    } catch (e) {
      // Netzwerkfehler ignorieren
    }

    isSearching = false;
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      if (query) {
        query = '';
        episodeResults = [];
        subResults = [];
        externResults = [];
        totalEpisodes = 0;
      } else {
        onclose();
      }
    }
  }

  function highlightMatch(text, q) {
    if (!text || !q || q.length < 2) return text || '';
    const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }
</script>

<div class="podcast-search">
  <!-- Suchfeld -->
  <div class="search-input-row">
    <i class="fa-solid fa-magnifying-glass search-icon"></i>
    <input
      bind:this={inputEl}
      type="text"
      class="search-input"
      placeholder="Suchen..."
      value={query}
      oninput={handleInput}
      onkeydown={handleKeydown}
    />
    {#if query}
      <button class="search-clear" aria-label="Suche leeren" onclick={() => { query = ''; episodeResults = []; subResults = []; externResults = []; totalEpisodes = 0; }}>
        <i class="fa-solid fa-xmark"></i>
      </button>
    {/if}
  </div>

  <!-- Scope-Badges -->
  <div class="scope-badges">
    {#each scopes as s}
      <button
        class="scope-badge"
        class:active={scope === s.key}
        onclick={() => handleScopeChange(s.key)}
      >
        <i class="fa-solid {s.icon}"></i>
        {s.label}
      </button>
    {/each}
  </div>

  <!-- Ergebnisse -->
  <div class="search-results">
    {#if isSearching}
      <div class="search-status">
        <i class="fa-solid fa-spinner fa-spin"></i> Suche...
      </div>
    {:else if query.length < 2}
      <div class="search-status search-hint">Mindestens 2 Zeichen</div>
    {:else if scope === 'episodes'}
      {#if episodeResults.length === 0}
        <div class="search-status">Keine Episoden gefunden</div>
      {:else}
        <div class="result-count">{totalEpisodes} Treffer</div>
        {#each episodeResults as ep (ep.id)}
          {@const ctx = ep.match_context || {}}
          <button
            class="result-item"
            onclick={() => { onselectepisode(ep); sfx.click(); }}
          >
            <CoverArt
              src={ep.local_image_path ? api.getEpisodeImageUrl(ep.id) : ep.image_url}
              alt={ep.title}
              size="sm"
            />
            <div class="result-info">
              <div class="result-title">{@html highlightMatch(ep.title, query)}</div>
              <div class="result-podcast">{ep.podcast_title || ''}</div>
              {#if ctx.description}
                <div class="result-snippet">{@html highlightMatch(ctx.description, query)}</div>
              {/if}
              {#if ctx.transcript}
                <div class="result-snippet transcript-snippet">
                  <i class="fa-solid fa-closed-captioning snippet-icon"></i>
                  {@html highlightMatch(ctx.transcript, query)}
                </div>
              {/if}
            </div>
            <HiFiLed color={ep.is_downloaded ? 'blue' : 'off'} size="small" />
          </button>
        {/each}
      {/if}

    {:else if scope === 'subscriptions'}
      {#if subResults.length === 0}
        <div class="search-status">Keine Abos gefunden</div>
      {:else}
        {#each subResults as podcast (podcast.id)}
          <button
            class="result-item"
            onclick={() => { onselectpodcast(podcast); sfx.click(); }}
          >
            <CoverArt
              src={podcast.id ? api.getPodcastImageUrl(podcast.id) : podcast.image_url}
              alt={podcast.title}
              size="sm"
            />
            <div class="result-info">
              <div class="result-title">{@html highlightMatch(podcast.title, query)}</div>
              <div class="result-podcast">{@html highlightMatch(podcast.author || '', query)}</div>
            </div>
          </button>
        {/each}
      {/if}

    {:else if scope === 'extern'}
      {#if externResults.length === 0}
        <div class="search-status">Keine externen Podcasts gefunden</div>
      {:else}
        {#each externResults as podcast}
          {@const isSubscribed = subscribedFeedUrls.has(podcast.feed_url)}
          <button
            class="result-item"
            onclick={() => { if (!isSubscribed) { onsubscribe(podcast); sfx.click(); } }}
            disabled={isSubscribed}
          >
            <CoverArt
              src={podcast.image_url}
              alt={podcast.title}
              size="sm"
            />
            <div class="result-info">
              <div class="result-title">{@html highlightMatch(podcast.title, query)}</div>
              <div class="result-podcast">{@html highlightMatch(podcast.author || '', query)}</div>
            </div>
            {#if isSubscribed}
              <i class="fa-solid fa-check subscribed-icon"></i>
            {:else}
              <i class="fa-solid fa-plus subscribe-icon"></i>
            {/if}
          </button>
        {/each}
      {/if}
    {/if}
  </div>
</div>

<style>
  .podcast-search {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .search-input-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    margin: 0 6px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm, 4px);
    box-shadow: var(--hifi-shadow-inset);
  }

  .search-icon {
    font-size: 11px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    border: none;
    background: none;
    outline: none;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 11px;
    font-weight: 700;
    color: var(--hifi-text-primary);
    min-width: 0;
  }

  .search-input::placeholder {
    color: var(--hifi-text-secondary);
    opacity: 0.4;
    font-weight: 400;
  }

  .search-clear {
    border: none;
    background: none;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    font-size: 10px;
    padding: 2px;
    opacity: 0.5;
    flex-shrink: 0;
  }

  .search-clear:hover {
    opacity: 1;
    color: var(--hifi-text-primary);
  }

  .scope-badges {
    display: flex;
    gap: 4px;
    padding: 6px 6px 4px;
  }

  .scope-badge {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    padding: 3px 0;
    border: none;
    border-radius: var(--hifi-border-radius-sm, 4px);
    background: none;
    color: var(--hifi-text-secondary);
    font-family: 'Barlow', sans-serif;
    font-size: 9px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    opacity: 0.5;
  }

  .scope-badge i {
    font-size: 8px;
  }

  .scope-badge:hover {
    opacity: 0.8;
  }

  .scope-badge.active {
    opacity: 1;
    color: var(--hifi-accent);
    background: rgba(51, 153, 255, 0.1);
  }

  .search-results {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    padding: 0 4px 4px;
  }

  .search-status {
    padding: 16px 8px;
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    text-align: center;
    opacity: 0.6;
  }

  .search-hint {
    opacity: 0.3;
  }

  .result-count {
    padding: 4px 8px 2px;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .result-item {
    display: flex;
    align-items: flex-start;
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

  .result-item:hover {
    background: var(--hifi-row-hover);
  }

  .result-item:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .result-info {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .result-title {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 500;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-podcast {
    font-family: 'Barlow', sans-serif;
    font-size: 9px;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 1px;
  }

  .result-snippet {
    font-family: 'Barlow', sans-serif;
    font-size: 9px;
    color: var(--hifi-text-secondary);
    opacity: 0.7;
    margin-top: 2px;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .transcript-snippet {
    opacity: 0.5;
  }

  .snippet-icon {
    font-size: 8px;
    margin-right: 3px;
  }

  /* Treffer-Markierung */
  .result-title :global(mark),
  .result-podcast :global(mark),
  .result-snippet :global(mark) {
    background: rgba(255, 204, 0, 0.3);
    color: inherit;
    padding: 0 1px;
    border-radius: 1px;
  }

  .subscribed-icon {
    font-size: 10px;
    color: var(--hifi-text-green, #33cc33);
    opacity: 0.6;
    flex-shrink: 0;
    margin-top: 4px;
  }

  .subscribe-icon {
    font-size: 10px;
    color: var(--hifi-accent);
    flex-shrink: 0;
    margin-top: 4px;
  }
</style>
