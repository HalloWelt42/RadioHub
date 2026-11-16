<script>
  /**
   * DownloadJobPanel - Schmales Panel für Massendownload-Steuerung
   * Zeigt Fortschritt, erlaubt Pause/Fortsetzen/Abbrechen.
   */
  import { formatSize } from '../../lib/formatters.js';
  import { t } from '../../lib/i18n.svelte.js';

  let {
    active = false,
    total = 0,
    done = 0,
    failed = 0,
    currentName = '',
    paused = false,
    onpause = () => {},
    onresume = () => {},
    oncancel = () => {}
  } = $props();

  let percent = $derived(total > 0 ? Math.round((done / total) * 100) : 0);
  let remaining = $derived(total - done);
</script>

{#if active}
  <div class="download-job-panel">
    <div class="job-header">
      <i class="fa-solid fa-arrow-down job-icon"></i>
      <span class="job-title">{t('downloadPanel.massendownload')}</span>
      <span class="job-counter">{done} / {total}</span>
      {#if failed > 0}
        <span class="job-failed">{failed} {t('downloadPanel.fehlgeschlagen')}</span>
      {/if}
    </div>

    <div class="job-bar-row">
      <div class="job-bar">
        <div
          class="job-fill"
          class:paused={paused}
          style="width: {percent}%"
        ></div>
      </div>
      <span class="job-percent">{percent}%</span>
    </div>

    {#if currentName}
      <div class="job-current">
        <i class="fa-solid {paused ? 'fa-pause' : 'fa-spinner fa-spin'} job-status-icon"></i>
        <span class="job-current-name">{currentName}</span>
      </div>
    {/if}

    <div class="job-actions">
      {#if paused}
        <button class="job-btn job-btn-resume" onclick={onresume} title={t('downloadPanel.fortsetzen')}>
          <i class="fa-solid fa-play"></i>
          <span>{t('downloadPanel.fortsetzen')}</span>
        </button>
      {:else}
        <button class="job-btn job-btn-pause" onclick={onpause} title={t('downloadPanel.pausieren')}>
          <i class="fa-solid fa-pause"></i>
          <span>{t('downloadPanel.pause')}</span>
        </button>
      {/if}
      <button class="job-btn job-btn-cancel" onclick={oncancel} title={t('downloadPanel.abbrechen')}>
        <i class="fa-solid fa-xmark"></i>
        <span>{t('downloadPanel.abbrechen')}</span>
      </button>
    </div>
  </div>
{/if}

<style>
  .download-job-panel {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 16px;
    background: var(--hifi-bg-tertiary);
    border-top: 1px solid var(--hifi-border-dark);
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
    animation: slideDown 0.2s ease;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      max-height: 0;
      padding: 0 16px;
    }
    to {
      opacity: 1;
      max-height: 120px;
      padding: 8px 16px;
    }
  }

  .job-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .job-icon {
    font-size: 11px;
    color: var(--hifi-accent, #3399ff);
  }

  .job-title {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: var(--hifi-text-secondary);
  }

  .job-counter {
    margin-left: auto;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 11px;
    font-weight: 700;
    color: var(--hifi-accent, #3399ff);
  }

  .job-failed {
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    color: var(--hifi-led-red, #ff3333);
  }

  .job-bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .job-bar {
    flex: 1;
    height: 4px;
    background: var(--hifi-border-dark);
    border-radius: 2px;
    overflow: hidden;
  }

  .job-fill {
    height: 100%;
    background: var(--hifi-accent, #3399ff);
    border-radius: 2px;
    transition: width 0.3s ease;
  }

  .job-fill.paused {
    background: var(--hifi-led-yellow, #ffcc00);
  }

  .job-percent {
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    min-width: 32px;
    text-align: right;
  }

  .job-current {
    display: flex;
    align-items: center;
    gap: 6px;
    overflow: hidden;
  }

  .job-status-icon {
    font-size: 9px;
    color: var(--hifi-accent, #3399ff);
    flex-shrink: 0;
  }

  .job-current-name {
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .job-actions {
    display: flex;
    gap: 6px;
  }

  .job-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border: none;
    border-radius: var(--hifi-border-radius-sm, 4px);
    cursor: pointer;
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    font-weight: 500;
    transition: all 0.15s;
    background: var(--hifi-bg-panel);
    color: var(--hifi-text-secondary);
    box-shadow: var(--hifi-shadow-button);
  }

  .job-btn:hover {
    color: var(--hifi-text-primary);
    box-shadow: 2px 2px 4px var(--hifi-shadow-dark), -2px -2px 4px var(--hifi-shadow-light);
  }

  .job-btn:active {
    box-shadow: var(--hifi-shadow-inset);
  }

  .job-btn i {
    font-size: 9px;
  }

  .job-btn-cancel:hover {
    color: var(--hifi-led-red, #ff3333);
  }

  .job-btn-resume:hover {
    color: var(--hifi-text-green, #33cc33);
  }

  .job-btn-pause:hover {
    color: var(--hifi-led-yellow, #ffcc00);
  }
</style>
