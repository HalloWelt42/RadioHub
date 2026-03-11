<script>
  import HiFiKnob from '../hifi/HiFiKnob.svelte';
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';

  let config = $state({});
  let isLoading = $state(true);
  let autoRefresh = $state(true);
  let refreshHours = $state(6);

  $effect(() => {
    loadConfig();
  });

  async function loadConfig() {
    try {
      config = await api.getConfig();
      autoRefresh = config.podcast_auto_refresh !== false;
      // Sekunden -> Stunden
      const secs = Number(config.podcast_refresh_interval) || 21600;
      refreshHours = Math.round(secs / 3600);
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
    isLoading = false;
  }

  async function saveConfig(key, value) {
    try {
      await api.updateConfig({ [key]: value });
      config[key] = value;
    } catch (e) {
      actions.showToast(t('toast.speichernFehler'), 'error');
    }
  }

  function toggleAutoRefresh() {
    autoRefresh = !autoRefresh;
    saveConfig('podcast_auto_refresh', autoRefresh);
  }

  function handleRefreshChange(e) {
    refreshHours = e.value;
    // Stunden -> Sekunden
    saveConfig('podcast_refresh_interval', e.value * 3600);
  }
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}
  <div class="podcast-grid">
    <!-- Auto-Refresh -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">{t('podcast.autoRefresh')}</span>
      </div>
      <div class="hifi-flex hifi-gap-md" style="padding:16px; align-items:center;">
        <button
          class="toggle-btn"
          class:active={autoRefresh}
          onclick={toggleAutoRefresh}
        >
          <HiFiLed color={autoRefresh ? 'green' : 'off'} />
          <span>{autoRefresh ? t('podcast.aktiv') : t('podcast.aus')}</span>
        </button>
      </div>
      <div style="padding:0 16px 16px; text-align:center;">
        <span class="hifi-font-small" style="color:var(--hifi-text-muted);">
          {t('podcast.refreshHint')}
        </span>
      </div>
    </div>

    <!-- Refresh-Intervall -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">{t('podcast.refreshIntervall')}</span>
      </div>
      <div class="hifi-flex hifi-gap-xl" style="padding:24px; justify-content:center;">
        <HiFiKnob
          value={refreshHours}
          min={1}
          max={48}
          step={1}
          unit="h"
          label={t('podcast.intervall')}
          onchange={handleRefreshChange}
        />
      </div>
      <div style="padding:0 16px 16px; text-align:center;">
        <span class="hifi-font-small" style="color:var(--hifi-text-muted);">
          {t('podcast.refreshHintDynamic', { hours: refreshHours })}
        </span>
      </div>
    </div>

  </div>
{/if}

<style>
  .podcast-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .span-full {
    grid-column: 1 / -1;
  }

  .toggle-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 18px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-pill);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .toggle-btn:hover {
    background: var(--hifi-bg-secondary);
    color: var(--hifi-text-primary);
  }

  .toggle-btn.active {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }
</style>
