<script>
  /**
   * PodcastHeader - Detail-Header für ein einzelnes Podcast-Abo
   * Cover, Titel, Autor, Beschreibung, Kategorien, Stats, Aktions-Buttons.
   */
  import CoverArt from '../shared/CoverArt.svelte';
  import SanitizedHtml from '../shared/SanitizedHtml.svelte';
  import InfoBadge from '../shared/InfoBadge.svelte';
  import { api } from '../../lib/api.js';
  import { formatTotalDuration } from '../../lib/formatters.js';

  let {
    podcast,
    episodeCount = 0,
    unplayedCount = 0,
    downloadedCount = 0,
    totalDuration = 0,
    isRefreshing = false,
    batchActive = false,
    batchTotal = 0,
    batchDone = 0,
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
        {#if totalDuration > 0}
          <div class="stat">
            <span class="stat-value">{formatTotalDuration(totalDuration)}</span>
            <span class="stat-label">Gesamt</span>
          </div>
        {/if}
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
    <button class="hifi-btn hifi-btn-small" onclick={onrefresh} disabled={isRefreshing} title="Feed vom Server holen">
      <i class="fa-solid fa-cloud-arrow-down" class:fa-spin={isRefreshing}></i>
    </button>
    <button
      class="hifi-btn hifi-btn-small"
      onclick={ondownloadall}
      disabled={batchActive || downloadedCount >= episodeCount}
      title={downloadedCount >= episodeCount ? 'Alle Episoden bereits lokal' : 'Alle Episoden lokal herunterladen'}
    >
      <i class="fa-solid fa-download"></i>
    </button>
    <button
      class="hifi-btn hifi-btn-small"
      class:active={podcast?.auto_download}
      onclick={onautodownloadtoggle}
      title={podcast?.auto_download ? 'Auto-Download deaktivieren: Neue Episoden werden nicht automatisch heruntergeladen' : 'Auto-Download aktivieren: Neue Episoden werden automatisch heruntergeladen'}
    >
      <i class="fa-solid fa-wand-magic-sparkles"></i>
    </button>
    <button class="hifi-btn hifi-btn-danger hifi-btn-small" onclick={onunsubscribe} title="Podcast-Abo entfernen (lokale Dateien bleiben erhalten)">
      <i class="fa-solid fa-trash"></i>
    </button>
  </div>

  {#if batchActive}
    <div class="batch-progress">
      <div class="batch-bar">
        <div class="batch-fill" style="width: {batchTotal > 0 ? (batchDone / batchTotal * 100) : 0}%"></div>
      </div>
      <span class="batch-label">{batchDone} / {batchTotal}</span>
    </div>
  {/if}
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

  .header-actions :global(.hifi-btn:disabled) {
    opacity: 0.3;
    cursor: not-allowed;
    pointer-events: none;
  }

  .hifi-btn.active {
    background: var(--hifi-accent);
    color: white;
  }

  .batch-progress {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 0;
    width: 100%;
  }

  .batch-bar {
    flex: 1;
    height: 4px;
    background: var(--hifi-border-dark);
    border-radius: 2px;
    overflow: hidden;
  }

  .batch-fill {
    height: 100%;
    background: var(--hifi-accent, #3399ff);
    border-radius: 2px;
    transition: width 0.3s ease;
  }

  .batch-label {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
  }
</style>
