<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';

  // === SUB-TAB ===
  let subTab = $state('werbung');

  // === AD-DETECTION ===
  let adEnabled = $state(true);
  let adMethods = $state(['url_check', 'header_check']);
  let adThreshold = $state(0.80);
  let adSummary = $state(null);
  let suspects = $state([]);
  let isLoadingSuspects = $state(false);
  let scanProgress = $state(null);
  let isScanning = $state(false);
  let scanAbort = $state(false);

  // === GESPERRTE SENDER ===
  let blockedData = $state(null);
  let isLoadingBlocked = $state(false);
  let isReleasing = $state(false);
  let expandedCategory = $state(null);
  let expandedReason = $state(null);

  // === INIT ===
  let isLoading = $state(true);

  $effect(() => {
    loadAll();
  });

  async function loadAll() {
    try {
      const config = await api.getConfig();
      if (config.ad_detection_enabled != null) {
        adEnabled = config.ad_detection_enabled === true || config.ad_detection_enabled === 'true';
      }
      if (config.ad_detection_methods) {
        try {
          const m = typeof config.ad_detection_methods === 'string'
            ? JSON.parse(config.ad_detection_methods) : config.ad_detection_methods;
          if (Array.isArray(m)) adMethods = m;
        } catch { /* ignore */ }
      }
      if (config.ad_detection_threshold != null) {
        adThreshold = Number(config.ad_detection_threshold) || 0.80;
      }
    } catch (e) {
      console.error('SetupSender: Config laden fehlgeschlagen:', e);
    }
    isLoading = false;
    loadSuspects();
    loadBlocked();
    loadAdSummary();
  }

  function saveAdSettings() {
    api.updateConfig({
      ad_detection_enabled: adEnabled,
      ad_detection_methods: JSON.stringify(adMethods),
      ad_detection_threshold: adThreshold
    });
    loadSuspects();
  }

  function toggleAdMethod(method) {
    if (adMethods.includes(method)) {
      adMethods = adMethods.filter(m => m !== method);
    } else {
      adMethods = [...adMethods, method];
    }
    saveAdSettings();
  }

  async function loadSuspects() {
    isLoadingSuspects = true;
    try {
      suspects = await api.getAdSuspects(adThreshold);
    } catch (e) {
      console.error('SetupSender: Suspects laden fehlgeschlagen:', e);
      suspects = [];
    }
    isLoadingSuspects = false;
  }

  async function loadBlocked() {
    isLoadingBlocked = true;
    try {
      blockedData = await api.getHiddenStations();
    } catch (e) {
      console.error('SetupSender: Blocklist laden fehlgeschlagen:', e);
    }
    isLoadingBlocked = false;
  }

  async function loadAdSummary() {
    try {
      adSummary = await api.getAdSummary();
    } catch (e) {
      console.error('SetupSender: Ad-Summary laden fehlgeschlagen:', e);
    }
  }

  // === SCAN ===
  function runScan() {
    isScanning = true;
    scanAbort = false;
    let totalChecked = 0;
    let totalSuspects = 0;
    const remaining = adSummary?.remaining ?? 0;
    scanProgress = { progress: 0, total: remaining, current: '' };

    function startBatch() {
      if (scanAbort) { finishScan(); return; }
      const baseUrl = window.RADIOHUB_API_URL || 'http://localhost:9091';
      const es = new EventSource(`${baseUrl}/api/ad-detection/scan-stream?batch_size=50`);

      es.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.done) {
          es.close();
          totalChecked += data.checked;
          totalSuspects += data.new_suspects;
          if (data.remaining > 0 && !scanAbort) {
            scanProgress = { ...scanProgress, total: totalChecked + data.remaining };
            startBatch();
          } else {
            finishScan();
          }
        } else {
          scanProgress = {
            progress: totalChecked + data.progress,
            total: totalChecked + (data.total - data.progress) + (adSummary?.remaining ?? 0),
            current: data.current,
          };
        }
      };

      es.onerror = () => { es.close(); finishScan(); };
    }

    async function finishScan() {
      if (totalChecked > 0) {
        actions.showToast(`${totalChecked} Sender geprueft, ${totalSuspects} verdaechtig`);
      } else {
        actions.showToast('Scan beendet', 'info');
      }
      scanProgress = null;
      isScanning = false;
      scanAbort = false;
      await loadAdSummary();
      await loadSuspects();
    }

    startBatch();
  }

  function stopScan() {
    scanAbort = true;
  }

  // === SUSPECT-ENTSCHEIDUNGEN ===
  async function decideSuspect(uuid, action) {
    try {
      await api.decideAd(uuid, action);
      suspects = suspects.filter(s => s.uuid !== uuid);
      if (action === 'block') {
        actions.showToast('Sender ausgeblendet', 'info');
        loadBlocked();
      } else {
        actions.showToast('Sender freigegeben', 'info');
      }
    } catch (e) {
      actions.showToast('Entscheidung fehlgeschlagen', 'error');
    }
  }

  function decideAllSuspects(action) {
    return async () => {
      const uuids = suspects.map(s => s.uuid);
      let count = 0;
      for (const uuid of uuids) {
        try { await api.decideAd(uuid, action); count++; } catch { /* skip */ }
      }
      suspects = [];
      if (action === 'block') {
        actions.showToast(`${count} Sender ausgeblendet`, 'info');
        loadBlocked();
      } else {
        actions.showToast(`${count} Sender freigegeben`, 'info');
      }
      await loadAdSummary();
    };
  }

  // === RELEASE-AKTIONEN ===
  async function releaseByReason(reason) {
    isReleasing = true;
    try {
      const data = await api.releaseStations({ reason });
      actions.showToast(`${data.released_count} Sender freigegeben`);
      await loadBlocked();
    } catch (e) {
      actions.showToast('Freigabe fehlgeschlagen', 'error');
    }
    isReleasing = false;
  }

  async function releaseAll() {
    isReleasing = true;
    try {
      const data = await api.releaseStations({ all: true });
      actions.showToast(`${data.released_count} Sender freigegeben`);
      await loadBlocked();
    } catch (e) {
      actions.showToast('Freigabe fehlgeschlagen', 'error');
    }
    isReleasing = false;
  }

  async function releaseSingle(uuid) {
    isReleasing = true;
    try {
      await api.releaseStations({ uuids: [uuid] });
      actions.showToast('Sender freigegeben');
      await loadBlocked();
    } catch (e) {
      actions.showToast('Freigabe fehlgeschlagen', 'error');
    }
    isReleasing = false;
  }

  async function releaseByCategory(cat) {
    isReleasing = true;
    try {
      const catData = blockedData?.categories?.[cat];
      if (catData) {
        for (const reason of Object.keys(catData.reasons)) {
          await api.releaseStations({ reason });
        }
      }
      actions.showToast('Kategorie freigegeben');
      await loadBlocked();
    } catch (e) {
      actions.showToast('Freigabe fehlgeschlagen', 'error');
    }
    isReleasing = false;
  }

  function toggleCategory(cat) {
    expandedCategory = expandedCategory === cat ? null : cat;
    expandedReason = null;
  }

  function toggleReason(reason) {
    expandedReason = expandedReason === reason ? null : reason;
  }

  function stationsForReason(reason) {
    if (!blockedData?.stations) return [];
    return blockedData.stations.filter(s => (s.reason || 'manual') === reason);
  }

  function categoryLabel(cat) {
    if (cat === 'manual') return 'MANUELL';
    if (cat === 'filter') return 'FILTER';
    if (cat === 'ad') return 'WERBUNG';
    return cat.toUpperCase();
  }

  function categoryLed(cat) {
    if (cat === 'manual') return 'red';
    return 'amber';
  }

  function formatReason(reason) {
    if (!reason || reason === 'manual') return 'Manuell blockiert';
    if (reason === 'ad:manual') return 'Werbung (manuell gemeldet)';
    if (reason === 'ad:URL_KNOWN_AD_NETWORK') return 'Werbung (Werbenetzwerk)';
    if (reason === 'ad:URL_SSAI_DOMAIN') return 'Werbung (SSAI-Domain)';
    if (reason === 'ad:URL_AD_PATH_PATTERN') return 'Werbung (Ad-URL-Muster)';
    if (reason === 'ad:URL_AGGREGATOR_RELAY') return 'Werbung (Aggregator-Relay)';
    if (reason === 'ad:URL_TRACKING_REDIRECT') return 'Werbung (Tracking-Redirect)';
    if (reason === 'ad:DOMAIN_BLACKLIST_MATCH') return 'Werbung (Domain-Blacklist)';
    if (reason?.startsWith('ad:')) return `Werbung (${reason.slice(3)})`;
    const parts = reason.split(', ');
    const types = {};
    for (const p of parts) {
      const [type] = p.split(':');
      types[type] = (types[type] || 0) + 1;
    }
    const labels = [];
    if (types.language) labels.push(`${types.language} Sprache${types.language > 1 ? 'n' : ''}`);
    if (types.country) labels.push(`${types.country} Land/Laender`);
    if (types.tag) labels.push(`${types.tag} Tag${types.tag > 1 ? 's' : ''}`);
    for (const p of parts) {
      if (p.startsWith('votes<')) labels.push(`Votes < ${p.split('<')[1]}`);
    }
    return labels.length > 0 ? labels.join(', ') : reason;
  }
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}

  <!-- Sub-Tab: Werbung / Gesperrt -->
  <div class="sub-tab-bar">
    <button class="sub-tab-btn" class:active={subTab === 'werbung'} onclick={() => subTab = 'werbung'}>
      <HiFiLed color={subTab === 'werbung' ? 'amber' : 'off'} size="small" />
      AD-BLOCKER
      {#if suspects.length > 0}
        <span class="sub-tab-badge-warn">{suspects.length}</span>
      {/if}
    </button>
    <button class="sub-tab-btn" class:active={subTab === 'gesperrt'} onclick={() => subTab = 'gesperrt'}>
      <HiFiLed color={subTab === 'gesperrt' ? 'red' : 'off'} size="small" />
      AUSGEBLENDET
      {#if blockedData?.count > 0}
        <span class="sub-tab-badge-warn">{blockedData.count}</span>
      {/if}
    </button>
  </div>

  {#if subTab === 'werbung'}
    <!-- Werbeerkennung -->
    <div class="ad-zone">
      <div class="zone-header">
        <span class="zone-label zone-label-ad">WERBEERKENNUNG</span>
        <span class="zone-hint">Sender auf Werbung pruefen und entscheiden</span>
      </div>

      <!-- Status Grid -->
      <div class="ad-status-grid">
        <div class="ad-stat">
          <span class="ad-stat-value">{adSummary?.total_checked ?? 0}</span>
          <span class="ad-stat-label">geprueft</span>
        </div>
        <div class="ad-stat">
          <span class="ad-stat-value ad-stat-clean">{adSummary?.clean ?? 0}</span>
          <span class="ad-stat-label">sauber</span>
        </div>
        <div class="ad-stat">
          <span class="ad-stat-value ad-stat-suspect">{adSummary?.suspect ?? 0}</span>
          <span class="ad-stat-label">verdaechtig</span>
        </div>
        <div class="ad-stat">
          <span class="ad-stat-value ad-stat-blocked">{(adSummary?.manual_blocked ?? 0) + (adSummary?.auto_blocked ?? 0)}</span>
          <span class="ad-stat-label">ausgeblendet</span>
        </div>
      </div>

      <!-- Scan -->
      <div class="ad-scan-row">
        {#if isScanning}
          <button class="action-btn scan-btn scan-stop" onclick={stopScan}>STOPP</button>
        {:else}
          <button
            class="action-btn scan-btn"
            onclick={runScan}
            disabled={!adEnabled || (adSummary?.remaining ?? 0) === 0}
          >ALLE SCANNEN</button>
        {/if}
        {#if !isScanning && adSummary?.remaining != null}
          <span class="scan-remaining">{adSummary.remaining} noch nicht geprueft</span>
        {/if}
      </div>
      {#if scanProgress}
        <div class="scan-progress">
          <div class="scan-progress-bar">
            <div class="scan-progress-fill" style="width: {scanProgress.total > 0 ? (scanProgress.progress / scanProgress.total * 100) : 0}%"></div>
          </div>
          <span class="scan-progress-text">{scanProgress.progress}/{scanProgress.total} -- {scanProgress.current}</span>
        </div>
      {/if}

      <!-- Verdaechtige Sender (inline) -->
      {#if suspects.length > 0}
        <div class="suspects-section">
          <div class="suspects-header">
            <span class="ad-sub-label">VERDAECHTIG ({suspects.length})</span>
            <div class="suspects-batch-actions">
              <button class="mini-btn suspect-block" onclick={decideAllSuspects('block')}>ALLE AUSBLENDEN</button>
              <button class="mini-btn suspect-allow" onclick={decideAllSuspects('allow')}>ALLE OK</button>
            </div>
          </div>
          <div class="suspects-list">
            {#each suspects as suspect (suspect.uuid)}
              <div class="suspect-row">
                <div class="suspect-info">
                  <HiFiLed color="amber" size="small" />
                  <span class="suspect-name">{suspect.name || suspect.uuid}</span>
                  <span class="suspect-conf">{Math.round(suspect.confidence * 100)}%</span>
                </div>
                <div class="suspect-actions">
                  <button class="mini-btn suspect-block" onclick={() => decideSuspect(suspect.uuid, 'block')}>AUSBLENDEN</button>
                  <button class="mini-btn suspect-allow" onclick={() => decideSuspect(suspect.uuid, 'allow')}>OK</button>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Einstellungen -->
      <div class="zone-divider"></div>
      <div class="ad-settings">
        <div class="ad-toggle-row">
          <span class="ad-toggle-label">Werbeerkennung</span>
          <button
            class="toggle-btn"
            class:active={adEnabled}
            onclick={() => { adEnabled = !adEnabled; saveAdSettings(); }}
          >
            <HiFiLed color={adEnabled ? 'green' : 'off'} size="small" />
            {adEnabled ? 'EIN' : 'AUS'}
          </button>
        </div>

        {#if adEnabled}
          <div class="ad-toggle-row">
            <div class="ad-toggle-group">
              <span class="ad-toggle-label">Adress-Pruefung</span>
              <span class="ad-toggle-hint">Erkennt Werbe-Begriffe in der Stream-URL</span>
            </div>
            <button
              class="toggle-btn"
              class:active={adMethods.includes('url_check')}
              onclick={() => toggleAdMethod('url_check')}
            >
              <HiFiLed color={adMethods.includes('url_check') ? 'green' : 'off'} size="small" />
              {adMethods.includes('url_check') ? 'EIN' : 'AUS'}
            </button>
          </div>
          <div class="ad-toggle-row">
            <div class="ad-toggle-group">
              <span class="ad-toggle-label">Server-Pruefung</span>
              <span class="ad-toggle-hint">Erkennt Werbe-Server anhand der Antwort-Daten</span>
            </div>
            <button
              class="toggle-btn"
              class:active={adMethods.includes('header_check')}
              onclick={() => toggleAdMethod('header_check')}
            >
              <HiFiLed color={adMethods.includes('header_check') ? 'green' : 'off'} size="small" />
              {adMethods.includes('header_check') ? 'EIN' : 'AUS'}
            </button>
          </div>
          <div class="ad-threshold">
            <span class="ad-sub-label">AB WANN VERDAECHTIG?</span>
            <span class="ad-threshold-hint">Sender unter diesem Wert werden ignoriert</span>
            <div class="threshold-row">
              <input
                type="range"
                min="0.4"
                max="1.0"
                step="0.05"
                bind:value={adThreshold}
                class="threshold-slider"
                onchange={saveAdSettings}
              />
              <span class="threshold-value">{Math.round(adThreshold * 100)}%</span>
            </div>
          </div>
        {/if}
      </div>
    </div>

  {:else if subTab === 'gesperrt'}
    <!-- Gesperrte Sender -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">
          AUSGEBLENDETE SENDER
          {#if blockedData}
            <span class="blocked-count">({blockedData.count})</span>
          {/if}
        </span>
        {#if blockedData?.count > 0}
          <button class="action-btn release-all-btn" onclick={releaseAll} disabled={isReleasing}>
            ALLE FREIGEBEN
          </button>
        {/if}
      </div>

      <div class="blocked-list">
        {#if isLoadingBlocked}
          <div class="status-text">Lade...</div>
        {:else if blockedData?.categories && Object.keys(blockedData.categories).length > 0}
          {#each Object.entries(blockedData.categories) as [cat, catData]}
            <div class="category-group">
              <div class="category-row" onclick={() => toggleCategory(cat)} tabindex="0">
                <span class="reason-arrow" class:open={expandedCategory === cat}>
                  <i class="fa-solid fa-chevron-right"></i>
                </span>
                <HiFiLed color={categoryLed(cat)} size="small" />
                <span class="category-label">{categoryLabel(cat)}</span>
                <span class="reason-count">({catData.count})</span>
                <button
                  class="mini-btn release-btn"
                  onclick={(e) => { e.stopPropagation(); releaseByCategory(cat); }}
                  disabled={isReleasing}
                >FREIGEBEN</button>
              </div>

              {#if expandedCategory === cat}
                <div class="category-reasons">
                  {#each Object.entries(catData.reasons) as [reason, count]}
                    <div class="reason-group">
                      <div class="reason-row" onclick={() => toggleReason(reason)} tabindex="0">
                        <span class="reason-arrow sub" class:open={expandedReason === reason}>
                          <i class="fa-solid fa-chevron-right"></i>
                        </span>
                        <span class="reason-label">{formatReason(reason)}</span>
                        <span class="reason-count">({count})</span>
                        <button
                          class="mini-btn release-btn"
                          onclick={(e) => { e.stopPropagation(); releaseByReason(reason); }}
                          disabled={isReleasing}
                        >FREIGEBEN</button>
                      </div>
                      {#if expandedReason === reason}
                        <div class="station-sublist">
                          {#each stationsForReason(reason) as station (station.uuid)}
                            <div class="station-row-blocked">
                              <HiFiLed color="off" size="small" />
                              <span class="station-name-blocked">{station.name}</span>
                              <button
                                class="unblock-btn"
                                onclick={() => releaseSingle(station.uuid)}
                                disabled={isReleasing}
                                title="Sender freigeben"
                              >
                                <i class="fa-solid fa-xmark"></i>
                              </button>
                            </div>
                          {/each}
                        </div>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/each}
        {:else}
          <div class="status-text">Keine ausgeblendeten Sender</div>
        {/if}
      </div>
    </div>
  {/if}

{/if}

<style>
  /* === Sub-Tab Bar === */
  .sub-tab-bar {
    display: flex;
    gap: 2px;
    margin-bottom: 12px;
  }

  .sub-tab-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 6px 14px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
  }

  .sub-tab-btn:hover {
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-primary);
  }

  .sub-tab-btn.active {
    background: var(--hifi-bg-tertiary);
    border-color: var(--hifi-border-dark);
    color: var(--hifi-accent);
  }

  .sub-tab-badge-warn {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    color: var(--hifi-led-red);
  }

  /* === Shared === */
  .mini-btn {
    padding: 3px 9px;
    background: var(--hifi-bg-tertiary);
    border: none;
    box-shadow: var(--hifi-shadow-button);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-body);
    font-size: 10px;
    cursor: pointer;
    border-radius: var(--hifi-border-radius-sm);
  }

  .mini-btn:hover { color: var(--hifi-text-primary); }
  .mini-btn:disabled { opacity: 0.4; cursor: default; }

  .action-btn {
    padding: 8px 16px;
    font-family: var(--hifi-font-display);
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    cursor: pointer;
    text-transform: uppercase;
  }

  .action-btn:disabled { opacity: 0.4; cursor: default; }

  .zone-header {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }

  .zone-label {
    font-family: var(--hifi-font-display);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
  }

  .zone-label-ad { color: var(--hifi-led-amber, #e5a00d); }

  .zone-hint {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    font-style: italic;
  }

  .zone-divider {
    height: 1px;
    background: var(--hifi-border-dark);
    margin: 12px 0;
  }

  .status-text {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    text-align: center;
    padding: 12px;
  }

  /* === Ad Zone === */
  .ad-zone {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    border: 1px solid rgba(229, 160, 13, 0.25);
    border-radius: var(--hifi-border-radius-sm);
    background: rgba(229, 160, 13, 0.04);
  }

  .ad-status-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
  }

  .ad-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 4px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
  }

  .ad-stat-value {
    font-family: var(--hifi-font-display);
    font-size: 16px;
    font-weight: 700;
    color: var(--hifi-text-primary);
  }

  .ad-stat-clean { color: var(--hifi-led-green, #4caf50); }
  .ad-stat-suspect { color: var(--hifi-led-amber, #e5a00d); }
  .ad-stat-blocked { color: var(--hifi-led-red); }

  .ad-stat-label {
    font-family: var(--hifi-font-body);
    font-size: 9px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  /* === Scan === */
  .ad-scan-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .scan-btn {
    background: var(--hifi-led-amber, #e5a00d);
    color: #000;
    font-weight: 600;
  }

  .scan-stop {
    background: var(--hifi-led-red, #e53935);
    color: #fff;
  }

  .scan-remaining {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }

  .scan-progress {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .scan-progress-bar {
    height: 4px;
    background: var(--hifi-bg-tertiary);
    border-radius: 2px;
    overflow: hidden;
  }

  .scan-progress-fill {
    height: 100%;
    background: var(--hifi-led-amber, #e5a00d);
    transition: width 0.2s ease;
  }

  .scan-progress-text {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* === Suspects === */
  .suspects-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .suspects-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .suspects-batch-actions {
    display: flex;
    gap: 4px;
  }

  .ad-sub-label {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .suspects-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
    max-height: 240px;
    overflow-y: auto;
  }

  .suspect-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 8px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
  }

  .suspect-info {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .suspect-name {
    flex: 1;
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .suspect-conf {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    color: var(--hifi-led-amber, #e5a00d);
    font-weight: 700;
  }

  .suspect-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .suspect-block { color: var(--hifi-led-red); font-weight: 600; }
  .suspect-allow { color: var(--hifi-accent); font-weight: 600; }

  /* === Ad Settings === */
  .ad-settings {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .ad-toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .ad-toggle-label {
    font-family: var(--hifi-font-body);
    font-size: 12px;
    color: var(--hifi-text-primary);
  }

  .ad-toggle-group {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .ad-toggle-hint {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.7;
  }

  .toggle-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-display);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    cursor: pointer;
  }

  .toggle-btn.active {
    color: var(--hifi-text-primary);
  }

  .ad-threshold {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding-left: 8px;
  }

  .ad-threshold-hint {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.7;
  }

  .threshold-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .threshold-slider {
    flex: 1;
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    background: var(--hifi-bg-tertiary);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .threshold-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px;
    height: 14px;
    background: var(--hifi-accent);
    border-radius: 50%;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }

  .threshold-value {
    font-family: var(--hifi-font-display);
    font-size: 12px;
    font-weight: 700;
    color: var(--hifi-led-amber, #e5a00d);
    min-width: 36px;
    text-align: right;
  }

  /* === Blocked Section === */
  .blocked-count {
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-body);
    font-weight: 400;
    font-size: 10px;
  }

  .release-all-btn {
    background: var(--hifi-led-red);
    color: #fff;
    font-size: 9px;
    padding: 4px 10px;
  }

  .blocked-list {
    overflow-y: auto;
    max-height: 500px;
    display: flex;
    flex-direction: column;
    gap: 3px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-inset);
    padding: 6px;
  }

  /* === Category Groups === */
  .category-group {
    display: flex;
    flex-direction: column;
  }

  .category-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px;
    background: var(--hifi-bg-secondary);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-family: var(--hifi-font-body);
  }

  .category-row:hover {
    background: var(--hifi-row-hover);
  }

  .category-label {
    flex: 1;
    font-family: var(--hifi-font-display);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-primary);
    text-transform: uppercase;
  }

  .category-reasons {
    padding-left: 16px;
  }

  .reason-group {
    display: flex;
    flex-direction: column;
  }

  .reason-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-family: var(--hifi-font-body);
  }

  .reason-row:hover {
    background: var(--hifi-row-hover);
  }

  .reason-arrow {
    font-size: 8px;
    color: var(--hifi-text-secondary);
    transition: transform 0.15s;
    width: 10px;
    flex-shrink: 0;
  }

  .reason-arrow.open {
    transform: rotate(90deg);
  }

  .reason-arrow.sub {
    width: 8px;
    font-size: 7px;
  }

  .reason-label {
    flex: 1;
    font-size: 12px;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .reason-count {
    font-size: 9px;
    color: var(--hifi-text-secondary);
  }

  .release-btn {
    color: var(--hifi-led-red);
    font-size: 9px;
  }

  /* === Station Subliste === */
  .station-sublist {
    display: flex;
    flex-direction: column;
    max-height: 240px;
    overflow-y: auto;
  }

  .station-row-blocked {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 12px 5px 24px;
    border-bottom: 1px solid var(--hifi-border-dark);
    transition: background 0.1s ease;
  }

  .station-row-blocked:hover {
    background: var(--hifi-row-hover);
  }

  .station-name-blocked {
    flex: 1;
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--hifi-text-primary);
  }

  .unblock-btn {
    background: none;
    border: none;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    padding: 4px 6px;
    font-size: 11px;
    border-radius: var(--hifi-border-radius-sm);
    flex-shrink: 0;
  }

  .unblock-btn:hover {
    color: var(--hifi-led-red);
    background: rgba(255, 60, 60, 0.1);
  }

  .unblock-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }
</style>
