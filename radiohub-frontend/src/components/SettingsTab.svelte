<script>
  import HiFiKnob from './hifi/HiFiKnob.svelte';
  import HiFiLed from './hifi/HiFiLed.svelte';
  import HiFiDisplay from './hifi/HiFiDisplay.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  
  let config = $state({});
  let cacheStats = $state({ total_stations: 0, countries: 0, last_sync: null });
  let isLoading = $state(true);
  let isSyncing = $state(false);
  
  $effect(() => {
    loadConfig();
    loadCacheStats();
  });
  
  async function loadConfig() {
    try {
      config = await api.getConfig();
    } catch (e) {}
    isLoading = false;
  }
  
  async function loadCacheStats() {
    try {
      cacheStats = await api.getCacheStats();
    } catch (e) {}
  }
  
  async function saveConfig(key, value) {
    try {
      await api.updateConfig({ [key]: value });
      config[key] = value;
      actions.showToast('Saved', 'success');
    } catch (e) {
      actions.showToast('Error', 'error');
    }
  }
  
  async function syncCache() {
    isSyncing = true;
    try {
      const result = await api.syncCache(true);
      actions.showToast(`${result.count} stations loaded`, 'success');
      loadCacheStats();
    } catch (e) {
      actions.showToast('Sync failed', 'error');
    }
    isSyncing = false;
  }
</script>

<div class="settings-tab">
  {#if isLoading}
    <div class="hifi-flex" style="justify-content:center; padding:60px;">
      <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
    </div>
  {:else}
    <!-- Theme Section -->
    <div class="hifi-panel" style="margin:16px;">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">DISPLAY THEME</span>
      </div>
      <div class="hifi-flex hifi-gap-md" style="padding:16px; align-items:center;">
        <button 
          class="theme-btn"
          class:active={appState.theme === 'dark'}
          onclick={() => actions.setTheme('dark')}
        >
          <HiFiLed color={appState.theme === 'dark' ? 'green' : 'off'} />
          <span>DARK</span>
        </button>
        <button 
          class="theme-btn"
          class:active={appState.theme === 'light'}
          onclick={() => actions.setTheme('light')}
        >
          <HiFiLed color={appState.theme === 'light' ? 'green' : 'off'} />
          <span>LIGHT</span>
        </button>
      </div>
    </div>
    
    <!-- Audio Section -->
    <div class="hifi-panel" style="margin:16px;">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">AUDIO SETTINGS</span>
      </div>
      <div class="hifi-flex hifi-gap-xl" style="padding:24px; justify-content:center;">
        <HiFiKnob 
          bind:value={config.volume}
          min={0}
          max={100}
          label="DEFAULT VOLUME"
          onchange={(e) => saveConfig('volume', e.value)}
        />
        <HiFiKnob 
          bind:value={config.recording_bitrate}
          min={64}
          max={320}
          step={32}
          unit="kbps"
          label="REC BITRATE"
          onchange={(e) => saveConfig('recording_bitrate', e.value)}
        />
      </div>
    </div>
    
    <!-- HLS Buffer Section -->
    <div class="hifi-panel" style="margin:16px;">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">TIMESHIFT BUFFER</span>
      </div>
      <div class="hifi-flex hifi-gap-xl" style="padding:24px; justify-content:center;">
        <HiFiKnob 
          bind:value={config.hls_min_bitrate}
          min={32}
          max={128}
          step={16}
          unit="kbps"
          label="MIN BITRATE"
          onchange={(e) => saveConfig('hls_min_bitrate', e.value)}
        />
        <HiFiKnob 
          bind:value={config.hls_max_bitrate}
          min={64}
          max={320}
          step={32}
          unit="kbps"
          label="MAX BITRATE"
          onchange={(e) => saveConfig('hls_max_bitrate', e.value)}
        />
      </div>
      <div style="padding:0 16px 16px; text-align:center;">
        <span class="hifi-font-small" style="color:var(--hifi-text-muted);">
          Output-Bitrate wird automatisch an Input angepasst (nicht höher als Quelle)
        </span>
      </div>
    </div>
    
    <!-- Cache Section -->
    <div class="hifi-panel" style="margin:16px;">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">STATION CACHE</span>
      </div>
      <div class="hifi-flex hifi-gap-lg" style="padding:16px; align-items:center;">
        <HiFiDisplay size="medium">{cacheStats.total_stations.toLocaleString()} STATIONS</HiFiDisplay>
        <HiFiDisplay size="small">{cacheStats.countries} COUNTRIES</HiFiDisplay>
        <div style="flex:1;"></div>
        <button class="hifi-btn hifi-btn-primary" onclick={syncCache} disabled={isSyncing}>
          {#if isSyncing}
            SYNCING...
          {:else}
            SYNC NOW
          {/if}
        </button>
      </div>
    </div>
    
    <!-- About Section -->
    <div class="hifi-panel" style="margin:16px;">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">SYSTEM INFO</span>
      </div>
      <div class="hifi-flex hifi-flex-col hifi-gap-md" style="padding:16px; align-items:center;">
        <div class="hifi-display hifi-display-large" style="padding:16px 32px;">
          RadioHub
        </div>
        <div style="display:flex; gap:16px;">
          <HiFiLed color="green" />
          <span class="hifi-font-label">FRONTEND v0.3.3</span>
        </div>
        <div style="display:flex; gap:16px;">
          <HiFiLed color="green" />
          <span class="hifi-font-label">BACKEND v0.2.3</span>
        </div>
        <div style="margin-top:16px; color:var(--hifi-text-secondary); font-size:11px;">
          © HalloWelt42 - Private Use Only
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .settings-tab {
    height: 100%;
    overflow-y: auto;
    max-width: 800px;
    margin: 0 auto;
  }
  
  .theme-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-md);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-family);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: var(--hifi-shadow-outset);
  }
  
  .theme-btn:hover {
    background: var(--hifi-bg-secondary);
  }
  
  .theme-btn.active {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }
</style>
