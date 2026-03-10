<script>
  /**
   * PodcastHeader - Detail-Header für ein einzelnes Podcast-Abo
   * Cover, Titel, Autor, Beschreibung, Kategorien, Stats, Aktions-Buttons.
   */
  import CoverArt from '../shared/CoverArt.svelte';
  import SanitizedHtml from '../shared/SanitizedHtml.svelte';
  import InfoBadge from '../shared/InfoBadge.svelte';
  import { api } from '../../lib/api.js';

  let {
    podcast,
    episodeCount = 0,
    unplayedCount = 0,
    downloadedCount = 0,
    isRefreshing = false,
    onrefresh = () => {},
    ondownloadall = () => {},
    onunsubscribe = () => {},
    onautodownloadtoggle = () => {},
    onback = () => {}
  } = $props();

  let imageUrl = $derived(
    podcast?.id ? api.getPodcastImageUrl(podcast.id) : podcast?.image_url || null
  );

  let categories = $derived(
    podcast?.categories ? podcast.categories.split(',').map(c => c.trim()).filter(Boolean) : []
  );
</script>

<div class="podcast-header">
  <button class="back-btn" onclick={onback} title="Zurück zur Übersicht">
    <i class="fa-solid fa-chevron-left"></i>
  </button>

  <div class="header-cover">
    <CoverArt src={imageUrl} alt={podcast?.title} size="lg" />
  </div>

  <div class="header-info">
    <div class="header-title">{podcast?.title || ''}</div>
    <div class="header-author">{podcast?.author || ''}</div>

    {#if podcast?.description}
      <div class="header-description">
        <SanitizedHtml html={podcast.description} maxHeight="60px" />
      </div>
    {/if}

    <div class="header-meta-row">
      <div class="header-stats">
        <div class="stat">
          <span class="stat-value">{episodeCount}</span>
          <span class="stat-label">Episoden</span>
        </div>
        <div class="stat">
          <span class="stat-value">{unplayedCount}</span>
          <span class="stat-label">Ungehört</span>
        </div>
        <div class="stat">
          <span class="stat-value">{downloadedCount}</span>
          <span class="stat-label">Downloads</span>
        </div>
      </div>

      {#if categories.length > 0}
        <div class="header-categories">
          {#each categories as cat}
            <InfoBadge type="default" label={cat} />
          {/each}
        </div>
      {/if}

      {#if podcast?.auto_download}
        <InfoBadge type="auto" label="Auto-DL" />
      {/if}
    </div>
  </div>

  <div class="header-actions">
    <button class="hifi-btn hifi-btn-small" onclick={onrefresh} disabled={isRefreshing} title="Feed aktualisieren">
      <i class="fa-solid fa-arrows-rotate" class:fa-spin={isRefreshing}></i>
    </button>
    <button class="hifi-btn hifi-btn-small" onclick={ondownloadall} title="Alle Episoden herunterladen">
      <i class="fa-solid fa-download"></i>
    </button>
    <button
      class="hifi-btn hifi-btn-small"
      class:active={podcast?.auto_download}
      onclick={onautodownloadtoggle}
      title={podcast?.auto_download ? 'Auto-Download deaktivieren' : 'Auto-Download aktivieren'}
    >
      <i class="fa-solid fa-bolt"></i>
    </button>
    <button class="hifi-btn hifi-btn-danger hifi-btn-small" onclick={onunsubscribe} title="Podcast-Abo entfernen">
      <i class="fa-solid fa-trash"></i>
    </button>
  </div>
</div>

<style>
  .podcast-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    background: var(--hifi-bg-panel);
    border-bottom: 1px solid var(--hifi-border-dark);
  }

  .back-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    background: var(--hifi-bg-tertiary);
    border: none;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    border-radius: var(--hifi-border-radius-sm, 4px);
    box-shadow: var(--hifi-shadow-button);
    transition: all 0.15s;
    flex-shrink: 0;
  }

  .back-btn:hover {
    background: var(--hifi-bg-secondary);
    color: var(--hifi-text-primary);
  }

  .back-btn:active {
    box-shadow: var(--hifi-shadow-inset);
  }

  .header-cover {
    flex-shrink: 0;
  }

  .header-info {
    flex: 1;
    min-width: 0;
  }

  .header-title {
    font-family: 'Barlow', sans-serif;
    font-size: 18px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .header-author {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    color: var(--hifi-text-secondary);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .header-description {
    margin-top: 4px;
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    line-height: 1.4;
    color: var(--hifi-text-secondary);
    opacity: 0.7;
  }

  .header-meta-row {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 8px;
    flex-wrap: wrap;
  }

  .header-categories {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .header-stats {
    display: flex;
    gap: 16px;
  }

  .stat {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .stat-value {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 13px;
    font-weight: 700;
    color: var(--hifi-accent);
  }

  .stat-label {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
  }

  .header-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
    align-self: flex-start;
  }

  .header-actions :global(.hifi-btn) {
    box-shadow: var(--hifi-shadow-button);
    border: none;
    background: var(--hifi-bg-tertiary);
  }

  .header-actions :global(.hifi-btn:hover) {
    box-shadow: 2px 2px 4px var(--hifi-shadow-dark), -2px -2px 4px var(--hifi-shadow-light);
    background: var(--hifi-bg-secondary);
  }

  .header-actions :global(.hifi-btn:active) {
    box-shadow: var(--hifi-shadow-inset);
  }

  .hifi-btn.active {
    background: var(--hifi-accent);
    color: white;
  }
</style>
