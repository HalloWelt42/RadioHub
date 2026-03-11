<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import HiFiDisplay from '../hifi/HiFiDisplay.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';

  let cacheStats = $state({ total_stations: 0, countries: 0, last_sync: null });
  let isSyncing = $state(false);

  $effect(() => {
    loadCacheStats();
  });

  async function loadCacheStats() {
    try {
      cacheStats = await api.getCacheStats();
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
  }

  async function syncCache() {
    isSyncing = true;
    try {
      const result = await api.syncCache(true);
      actions.showToast(`${result.count} Sender geladen`, 'success');
      loadCacheStats();
    } catch (e) {
      // Netzwerkfehler ignorieren
      actions.showToast('Sync fehlgeschlagen', 'error');
    }
    isSyncing = false;
  }
</script>

<!-- Cache -->
<div class="hifi-panel">
  <div class="hifi-panel-header">
    <span class="hifi-font-label">STATION CACHE</span>
  </div>
  <div class="hifi-flex hifi-gap-lg" style="padding:16px; align-items:center;">
    <HiFiDisplay size="medium">{cacheStats.total_stations.toLocaleString()} STATIONS</HiFiDisplay>
    <HiFiDisplay size="small">{cacheStats.countries} COUNTRIES</HiFiDisplay>
    <div style="flex:1;"></div>
    <button class="hifi-btn hifi-btn-primary" onclick={syncCache} disabled={isSyncing}>
      {isSyncing ? 'SYNCING...' : 'SYNC NOW'}
    </button>
  </div>
</div>

<!-- System Info -->
<div class="hifi-panel">
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
      <span class="hifi-font-label">BACKEND v0.2.4</span>
    </div>
    <div style="margin-top:16px; color:var(--hifi-text-secondary); font-size:11px;">
      HalloWelt42 - Private Use Only
    </div>
  </div>
</div>
