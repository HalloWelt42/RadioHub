<script>
  /**
   * PodcastSearchView - Suchergebnisse als Karten
   * Cover, Titel, Autor, Beschreibung (gekürzt), Abo-Button.
   */
  import CoverArt from '../shared/CoverArt.svelte';

  let {
    results = [],
    isLoading = false,
    subscribedFeedUrls = new Set(),
    onsubscribe = () => {},
    onopen = () => {}
  } = $props();
</script>

<div class="search-view">
  {#if isLoading}
    <div class="loading-center">
      <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
    </div>
  {:else if results.length === 0}
    <div class="empty-center">
      <i class="fa-solid fa-magnifying-glass empty-icon"></i>
      <div class="empty-text">Podcasts suchen</div>
      <div class="empty-hint">Suchbegriff oben eingeben</div>
    </div>
  {:else}
    <div class="search-results">
      {#each results as podcast}
        {@const isSubscribed = subscribedFeedUrls.has(podcast.feed_url)}
        <div class="result-card" onclick={() => isSubscribed ? onopen(podcast) : null}>
          <div class="card-cover">
            <CoverArt src={podcast.image_url} alt={podcast.title} size="lg" />
          </div>

          <div class="card-info">
            <div class="card-title">{podcast.title}</div>
            <div class="card-author">{podcast.author || ''}</div>
            {#if podcast.description}
              <div class="card-description">
                {podcast.description.replace(/<[^>]*>/g, '').slice(0, 150)}{podcast.description.length > 150 ? '...' : ''}
              </div>
            {/if}
            <div class="card-meta">
              {#if podcast.source}
                <span class="card-source">{podcast.source}</span>
              {/if}
            </div>
          </div>

          <div class="card-action">
            {#if isSubscribed}
              <button class="hifi-btn hifi-btn-small" disabled title="Bereits abonniert">
                <i class="fa-solid fa-check"></i> Abonniert
              </button>
            {:else}
              <button
                class="hifi-btn hifi-btn-success hifi-btn-small"
                onclick={(e) => { e.stopPropagation(); onsubscribe(podcast); }}
                title="Podcast abonnieren"
              >
                <i class="fa-solid fa-plus"></i> Abo
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .search-view {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
  }

  .loading-center,
  .empty-center {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    gap: 12px;
  }

  .empty-icon {
    font-size: 32px;
    color: var(--hifi-text-secondary);
    opacity: 0.3;
  }

  .empty-text {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 13px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .empty-hint {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
  }

  .search-results {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .result-card {
    display: flex;
    gap: 12px;
    padding: 12px;
    background: var(--hifi-bg-panel);
    border-radius: var(--hifi-border-radius-sm, 4px);
    border-bottom: 1px solid var(--hifi-border-dark);
    transition: background 0.1s ease;
  }

  .result-card:hover {
    background: var(--hifi-row-hover);
  }

  .card-cover {
    flex-shrink: 0;
  }

  .card-info {
    flex: 1;
    min-width: 0;
  }

  .card-title {
    font-family: 'Barlow', sans-serif;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 2px;
  }

  .card-author {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    margin-bottom: 6px;
  }

  .card-description {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    line-height: 1.4;
    opacity: 0.7;
    margin-bottom: 6px;
  }

  .card-meta {
    display: flex;
    gap: 8px;
  }

  .card-source {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .card-action {
    display: flex;
    align-items: flex-start;
    flex-shrink: 0;
  }
</style>
