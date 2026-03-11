<script>
  /**
   * EpisodeRow - Einzelne Episoden-Zeile
   * LED, Cover, Titel, Badges, Datum, Dauer.
   */
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import CoverArt from '../shared/CoverArt.svelte';
  import { api } from '../../lib/api.js';
  import { formatDurationHuman, formatDate } from '../../lib/formatters.js';
  import { t } from '../../lib/i18n.svelte.js';

  let {
    episode,
    isPlaying = false,
    isFocused = false,
    isSelected = false,
    isDownloading = false,
    showPodcast = false,
    podcastTitle = '',
    onclick = () => {},
    onplay = () => {}
  } = $props();

  let imageUrl = $derived(
    episode.local_image_path
      ? api.getEpisodeImageUrl(episode.id)
      : episode.image_url || null
  );

  function handlePlayClick(e) {
    e.stopPropagation();
    onplay(episode);
  }
</script>

<div
  class="episode-row"
  class:playing={isPlaying}
  class:selected={isSelected && !isPlaying}
  class:focused={isFocused && !isPlaying && !isSelected}
  data-id={episode.id}
  onclick={() => onclick(episode)}
  role="button"
  tabindex="-1"
>
  <div class="ep-led" onclick={handlePlayClick}>
    <HiFiLed color={isPlaying ? 'green' : isFocused ? 'yellow' : episode.is_downloaded ? 'blue' : 'off'} size="small" />
  </div>

  <div class="ep-cover" onclick={handlePlayClick}>
    <CoverArt src={imageUrl} alt={episode.title} size="sm" />
  </div>

  <div class="ep-info">
    <div class="ep-title">
      <i class="fa-solid fa-play hover-play-icon"></i>
      <span>{episode.title}</span>
    </div>
    {#if showPodcast && podcastTitle}
      <div class="ep-podcast-name">{podcastTitle}</div>
    {/if}
  </div>

  <div class="ep-badges">
    {#if episode.is_played}
      <i class="fa-solid fa-check played-icon" title={t('podcasts.gehoert')}></i>
    {:else if episode.resume_position > 0}
      <i class="fa-solid fa-rotate-left resume-icon" title={t('podcasts.fortsetzen')}></i>
    {/if}
  </div>

  <div class="ep-date">{formatDate(episode.published_at)}</div>
  <div class="ep-duration">{formatDurationHuman(episode.duration)}</div>

  {#if isDownloading}
    <div class="ep-progress">
      <div class="ep-progress-bar"></div>
    </div>
  {/if}
</div>

<style>
  .episode-row {
    display: grid;
    grid-template-columns: 28px 36px 1fr auto 110px 70px;
    align-items: center;
    gap: 12px;
    padding: 6px 24px 6px 16px;
    cursor: pointer;
    border-bottom: 1px solid var(--hifi-border-dark);
    transition: background 0.1s ease;
  }

  .episode-row:hover {
    background: var(--hifi-row-hover);
  }

  .episode-row.playing {
    background: var(--hifi-row-selected);
  }

  .episode-row.selected {
    background: rgba(51, 153, 255, 0.08);
    box-shadow: inset 0 1px 0 rgba(51, 153, 255, 0.06), inset 0 -1px 0 rgba(51, 153, 255, 0.06);
  }

  .episode-row.focused {
    background: rgba(255, 204, 0, 0.06);
    box-shadow: inset 0 1px 0 rgba(255, 204, 0, 0.04), inset 0 -1px 0 rgba(255, 204, 0, 0.04);
  }

  .ep-led {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .ep-info {
    min-width: 0;
    overflow: hidden;
  }

  .ep-title {
    font-family: 'Barlow', sans-serif;
    font-size: 14px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: flex;
    align-items: center;
    gap: 0;
  }

  .hover-play-icon {
    font-size: 10px;
    color: var(--hifi-display-amber);
    width: 0;
    opacity: 0;
    transition: width 0.15s, opacity 0.15s, margin-right 0.15s;
    flex-shrink: 0;
    overflow: hidden;
  }

  .episode-row:hover .hover-play-icon {
    width: 12px;
    opacity: 1;
    margin-right: 4px;
  }

  .ep-podcast-name {
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 1px;
  }

  .ep-badges {
    display: flex;
    gap: 4px;
    align-items: center;
  }

  .played-icon {
    font-size: 10px;
    color: var(--hifi-text-green, #33cc33);
    opacity: 0.5;
  }

  .resume-icon {
    font-size: 10px;
    color: var(--hifi-led-yellow, #ffcc00);
    opacity: 0.6;
  }

  .ep-date {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 11px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    text-align: right;
    white-space: nowrap;
  }

  .ep-duration {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 11px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    text-align: right;
    white-space: nowrap;
  }

  .ep-progress {
    grid-column: 1 / -1;
    height: 2px;
    background: var(--hifi-border-dark);
    overflow: hidden;
  }

  .ep-progress-bar {
    height: 100%;
    width: 30%;
    background: var(--hifi-accent, #3399ff);
    animation: progress-slide 1.2s ease-in-out infinite;
  }

  @keyframes progress-slide {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }
</style>
