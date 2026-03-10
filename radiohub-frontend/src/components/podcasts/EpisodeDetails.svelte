<script>
  /**
   * EpisodeDetails - Expand-Bereich für eine Episode
   * Cover (groß), Beschreibung, Metadaten, Aktions-Buttons.
   */
  import CoverArt from '../shared/CoverArt.svelte';
  import SanitizedHtml from '../shared/SanitizedHtml.svelte';
  import InfoBadge from '../shared/InfoBadge.svelte';
  import { api } from '../../lib/api.js';
  import { formatDurationHuman, formatDate, formatSize } from '../../lib/formatters.js';

  let {
    episode,
    isDownloading = false,
    onplay = () => {},
    ondownload = () => {},
    ondeletedownload = () => {},
    ontoggleplayed = () => {}
  } = $props();

  let imageUrl = $derived(
    episode.local_image_path
      ? api.getEpisodeImageUrl(episode.id)
      : episode.image_url || null
  );
</script>

<div class="episode-details">
  <div class="details-top">
    <div class="details-cover">
      <CoverArt src={imageUrl} alt={episode.title} size="lg" />
    </div>

    <div class="details-meta">
      <div class="details-title">{episode.title}</div>

      <div class="details-meta-grid">
        <div class="meta-item">
          <span class="meta-label">Datum</span>
          <span class="meta-value">{formatDate(episode.published_at)}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Dauer</span>
          <span class="meta-value">{formatDurationHuman(episode.duration)}</span>
        </div>
        {#if episode.file_size > 0}
          <div class="meta-item">
            <span class="meta-label">Größe</span>
            <span class="meta-value">{formatSize(episode.file_size)}</span>
          </div>
        {/if}
        {#if episode.season_number}
          <div class="meta-item">
            <span class="meta-label">Staffel</span>
            <span class="meta-value">S{episode.season_number}{episode.episode_number ? 'E' + episode.episode_number : ''}</span>
          </div>
        {/if}
      </div>

      <div class="details-badges">
        {#if episode.is_downloaded}
          <InfoBadge type="downloaded" label="Heruntergeladen" />
        {/if}
        {#if episode.is_played}
          <InfoBadge type="played" label="Gehört" />
        {:else if episode.resume_position > 0}
          <InfoBadge type="resume" label="Fortsetzen bei {formatDurationHuman(episode.resume_position)}" />
        {/if}
      </div>

      <div class="details-actions">
        <button class="hifi-btn hifi-btn-success hifi-btn-small" onclick={() => onplay(episode)} title="Episode abspielen">
          <i class="fa-solid fa-play"></i> Abspielen
        </button>

        {#if episode.is_downloaded}
          <button class="hifi-btn hifi-btn-danger hifi-btn-small" onclick={() => ondeletedownload(episode)} title="Download löschen">
            <i class="fa-solid fa-trash"></i> Löschen
          </button>
        {:else}
          <button class="hifi-btn hifi-btn-small" onclick={() => ondownload(episode)} disabled={isDownloading} title="Episode herunterladen">
            <i class="fa-solid {isDownloading ? 'fa-spinner fa-spin' : 'fa-download'}"></i>
            {isDownloading ? 'Lade...' : 'Download'}
          </button>
        {/if}

        <button
          class="hifi-btn hifi-btn-small"
          onclick={() => ontoggleplayed(episode)}
          title={episode.is_played ? 'Als ungehört markieren' : 'Als gehört markieren'}
        >
          <i class="fa-solid {episode.is_played ? 'fa-eye-slash' : 'fa-check'}"></i>
          {episode.is_played ? 'Ungehört' : 'Gehört'}
        </button>
      </div>
    </div>
  </div>

  {#if episode.description}
    <div class="details-description">
      <SanitizedHtml html={episode.description} maxHeight="150px" />
    </div>
  {/if}
</div>

<style>
  .episode-details {
    padding: 6px 16px 6px 40px;
    background: var(--hifi-bg-tertiary);
    border-top: 1px solid var(--hifi-border-dark);
  }

  .details-top {
    display: flex;
    gap: 12px;
    margin-bottom: 8px;
  }

  .details-cover {
    flex-shrink: 0;
  }

  .details-meta {
    flex: 1;
    min-width: 0;
  }

  .details-title {
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 6px;
  }

  .details-meta-grid {
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin-bottom: 8px;
  }

  .meta-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }

  .meta-label {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    min-width: 60px;
    flex-shrink: 0;
  }

  .meta-value {
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    color: var(--hifi-text-primary);
  }

  .details-badges {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
  }

  .details-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    padding: 8px 0 0;
    border-top: 1px solid var(--hifi-border-dark);
    margin-top: 8px;
  }

  .details-actions :global(.hifi-btn) {
    box-shadow: none;
    border: 1px solid var(--hifi-border-dark);
  }

  .details-actions :global(.hifi-btn:hover) {
    box-shadow: none;
    background: var(--hifi-bg-secondary);
    border-color: rgba(255, 255, 255, 0.15);
  }

  .details-actions :global(.hifi-btn:active) {
    box-shadow: var(--hifi-shadow-inset);
  }

  .details-description {
    border-top: 1px solid var(--hifi-border-dark);
    padding-top: 8px;
    margin-top: 8px;
  }
</style>
