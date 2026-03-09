<script>
  import { api } from '../lib/api.js';
  import { actions } from '../lib/store.svelte.js';
  import { translateCountry, COUNTRY_NAMES } from '../lib/countryNames.js';
  import HiFiLed from './hifi/HiFiLed.svelte';

  let {
    open = false,
    onclose,
    visibleCountries = $bindable([]),
    excludedLanguages = $bindable([]),
    excludedTags = $bindable([]),
    minVotes = $bindable(0)
  } = $props();

  // === TABS ===
  let activeTab = $state('filter');

  // === MASSENFILTER ===
  let languages = $state([]);
  let languageSearch = $state('');
  let rareThreshold = $state(3);
  let countries = $state([]);
  let countrySearch = $state('');
  let tagInput = $state('');
  let previewCount = $state(null);
  let isPreviewing = $state(false);
  let isPushing = $state(false);

  const tagSuggestions = ['tv', 'television', 'test', 'webcam', 'video'];

  let filteredLanguages = $derived(
    languageSearch
      ? languages.filter(l => l.name.includes(languageSearch.toLowerCase()))
      : languages
  );

  let rareCount = $derived(languages.filter(l => l.count <= rareThreshold).length);

  // Aktive Filter-Zusammenfassung
  let activeFilterSummary = $derived(() => {
    const parts = [];
    if (excludedLanguages.length > 0) parts.push(`${excludedLanguages.length} Sprachen`);
    if (excludedTags.length > 0) parts.push(`${excludedTags.length} Tags`);
    if (minVotes > 0) parts.push(`Min. ${minVotes} Votes`);
    return parts;
  });

  // Bekannte Länder (im Mapping oder >= 20 Sender)
  let knownCountries = $derived(
    countries.filter(c => c.name in COUNTRY_NAMES || c.count >= 20)
  );

  let filteredCountries = $derived(() => {
    const base = knownCountries;
    if (!countrySearch) return base;
    const q = countrySearch.toLowerCase();
    return base.filter(c => {
      const translated = translateCountry(c.name).toLowerCase();
      return translated.includes(q) || c.code.toLowerCase().includes(q) || c.name.toLowerCase().includes(q);
    });
  });

  // === GESPERRTE SENDER ===
  let blockedData = $state(null);
  let isLoadingBlocked = $state(false);
  let isReleasing = $state(false);
  let expandedReason = $state(null);
  let expandedCategory = $state(null);

  // === VERDAECHTIGE SENDER ===
  let suspects = $state([]);
  let isLoadingSuspects = $state(false);

  // === AD-DETECTION EINSTELLUNGEN ===
  let adEnabled = $state(true);
  let adMethods = $state(['url_check', 'header_check']);
  let adThreshold = $state(0.80);
  let adSummary = $state(null);
  let scanProgress = $state(null);
  let isScanning = $state(false);
  let scanAbort = $state(false);

  // rareThreshold aus Config laden (einmalig)
  let _filterInitialized = false;

  // Daten laden beim Oeffnen
  $effect(() => {
    if (open) {
      loadLanguages();
      loadCountries();
      loadBlocked();
      loadSuspects();
      loadAdSummary();
      if (!_filterInitialized) loadRareThreshold();
    }
  });

  async function loadRareThreshold() {
    try {
      const config = await api.getConfig();
      if (config.filter_rare_threshold != null) {
        rareThreshold = Number(config.filter_rare_threshold) || 3;
      }
      // Ad-Detection Settings
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
    } catch { /* ignore */ }
    _filterInitialized = true;
  }

  function saveFilterState() {
    api.updateConfig({
      filter_excluded_languages: excludedLanguages,
      filter_excluded_tags: excludedTags,
      filter_min_votes: minVotes,
      filter_rare_threshold: rareThreshold
    });
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

  async function loadLanguages() {
    try {
      const data = await api.getAvailableLanguages();
      languages = data.languages || [];
    } catch (e) {
      console.error('Languages laden fehlgeschlagen:', e);
    }
  }

  async function loadCountries() {
    try {
      const data = await api.getAvailableCountries();
      countries = data.countries || [];
    } catch (e) {
      console.error('Countries laden fehlgeschlagen:', e);
    }
  }

  async function loadBlocked() {
    isLoadingBlocked = true;
    try {
      blockedData = await api.getHiddenStations();
    } catch (e) {
      console.error('Blocklist laden fehlgeschlagen:', e);
    }
    isLoadingBlocked = false;
  }

  async function loadSuspects() {
    isLoadingSuspects = true;
    try {
      suspects = await api.getAdSuspects(adThreshold);
    } catch (e) {
      console.error('Suspects laden fehlgeschlagen:', e);
      suspects = [];
    }
    isLoadingSuspects = false;
  }

  async function loadAdSummary() {
    try {
      adSummary = await api.getAdSummary();
    } catch (e) {
      console.error('Ad-Summary laden fehlgeschlagen:', e);
    }
  }

  function runScan() {
    isScanning = true;
    scanAbort = false;
    let totalChecked = 0;
    let totalSuspects = 0;
    const remaining = adSummary?.remaining ?? 0;
    scanProgress = { progress: 0, total: remaining, current: '' };

    function startBatch() {
      if (scanAbort) {
        finishScan();
        return;
      }
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

      es.onerror = () => {
        es.close();
        finishScan();
      };
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
        try {
          await api.decideAd(uuid, action);
          count++;
        } catch { /* skip */ }
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

  // === Filter-Aktionen ===

  function toggleLanguage(langName) {
    if (excludedLanguages.includes(langName)) {
      excludedLanguages = excludedLanguages.filter(l => l !== langName);
    } else {
      excludedLanguages = [...excludedLanguages, langName];
    }
    previewCount = null;
    saveFilterState();
  }

  function selectAllLanguages() {
    excludedLanguages = [];
    previewCount = null;
    saveFilterState();
  }

  function selectNoLanguages() {
    excludedLanguages = languages.map(l => l.name);
    previewCount = null;
    saveFilterState();
  }

  function selectRareLanguages() {
    const rare = languages.filter(l => l.count <= rareThreshold).map(l => l.name);
    excludedLanguages = [...new Set([...excludedLanguages, ...rare])];
    previewCount = null;
    saveFilterState();
  }

  function toggleCountry(code) {
    if (visibleCountries.includes(code)) {
      visibleCountries = visibleCountries.filter(c => c !== code);
    } else {
      visibleCountries = [...visibleCountries, code];
    }
  }

  function selectAllCountries() {
    visibleCountries = [];
  }

  function selectNoCountries() {
    visibleCountries = countries.map(c => c.code);
  }

  function addTag(tag) {
    tag = tag.trim().toLowerCase();
    if (tag && !excludedTags.includes(tag)) {
      excludedTags = [...excludedTags, tag];
      previewCount = null;
      saveFilterState();
    }
    tagInput = '';
  }

  function removeTag(tag) {
    excludedTags = excludedTags.filter(t => t !== tag);
    previewCount = null;
    saveFilterState();
  }

  function handleTagKeydown(e) {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      addTag(tagInput);
    }
  }

  async function preview() {
    if (excludedLanguages.length === 0 && excludedTags.length === 0 && minVotes === 0) {
      previewCount = 0;
      return;
    }
    isPreviewing = true;
    try {
      const data = await api.filterPreview({
        excluded_languages: excludedLanguages,
        excluded_tags: excludedTags,
        min_votes: minVotes
      });
      previewCount = data.count;
    } catch (e) {
      console.error('Preview fehlgeschlagen:', e);
    }
    isPreviewing = false;
  }

  async function push() {
    if (excludedLanguages.length === 0 && excludedTags.length === 0 && minVotes === 0) return;
    isPushing = true;
    try {
      const data = await api.filterPush({
        excluded_languages: excludedLanguages,
        excluded_tags: excludedTags,
        min_votes: minVotes
      });
      actions.showToast(`${data.hidden_count} Sender ausgeblendet (${data.total_hidden} gesamt)`);
      previewCount = null;
      await loadBlocked();
    } catch (e) {
      actions.showToast('Ausblenden fehlgeschlagen', 'error');
      console.error('Push fehlgeschlagen:', e);
    }
    isPushing = false;
  }

  // === Release-Aktionen ===

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
      const data = await api.releaseStations({ uuids: [uuid] });
      actions.showToast(`Sender freigegeben`);
      await loadBlocked();
    } catch (e) {
      actions.showToast('Freigabe fehlgeschlagen', 'error');
    }
    isReleasing = false;
  }

  async function releaseByCategory(cat) {
    isReleasing = true;
    try {
      // Alle Reasons dieser Kategorie freigeben
      const catData = blockedData?.categories?.[cat];
      if (catData) {
        for (const reason of Object.keys(catData.reasons)) {
          await api.releaseStations({ reason });
        }
      }
      actions.showToast(`Kategorie freigegeben`);
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
    return blockedData.stations.filter(s => {
      const r = s.reason || 'manual';
      return r === reason;
    });
  }

  function categoryLabel(cat) {
    if (cat === 'manual') return 'MANUELL';
    if (cat === 'filter') return 'FILTER';
    if (cat === 'ad') return 'WERBUNG';
    return cat.toUpperCase();
  }

  function categoryLed(cat) {
    if (cat === 'manual') return 'red';
    if (cat === 'filter') return 'amber';
    if (cat === 'ad') return 'amber';
    return 'red';
  }

  function close() {
    onclose?.();
  }

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) close();
  }

  function isAdReason(reason) {
    return reason?.startsWith('ad:');
  }

  function formatReason(reason) {
    if (!reason || reason === 'manual') return 'Manuell blockiert';

    // Ad-Detection Reasons
    if (reason === 'ad:manual') return 'Werbung (manuell gemeldet)';
    if (reason === 'ad:URL_KNOWN_AD_NETWORK') return 'Werbung (Werbenetzwerk)';
    if (reason === 'ad:URL_SSAI_DOMAIN') return 'Werbung (SSAI-Domain)';
    if (reason === 'ad:URL_AD_PATH_PATTERN') return 'Werbung (Ad-URL-Muster)';
    if (reason === 'ad:URL_AGGREGATOR_RELAY') return 'Werbung (Aggregator-Relay)';
    if (reason === 'ad:URL_TRACKING_REDIRECT') return 'Werbung (Tracking-Redirect)';
    if (reason === 'ad:DOMAIN_BLACKLIST_MATCH') return 'Werbung (Domain-Blacklist)';
    if (reason?.startsWith('ad:')) return `Werbung (${reason.slice(3)})`;

    // Filter-Reasons
    const parts = reason.split(', ');
    const types = {};
    for (const p of parts) {
      const [type] = p.split(':');
      types[type] = (types[type] || 0) + 1;
    }
    const labels = [];
    if (types.language) labels.push(`${types.language} Sprache${types.language > 1 ? 'n' : ''}`);
    if (types.country) labels.push(`${types.country} Land/Länder`);
    if (types.tag) labels.push(`${types.tag} Tag${types.tag > 1 ? 's' : ''}`);
    for (const p of parts) {
      if (p.startsWith('votes<')) labels.push(`Votes < ${p.split('<')[1]}`);
    }
    return labels.length > 0 ? labels.join(', ') : reason;
  }
</script>

<div class="filter-overlay-bg" class:visible={open} onclick={handleOverlayClick}>
  <div class="filter-panel">
    <!-- Header mit Tabs -->
    <div class="filter-header">
      <div class="tab-bar">
        <button
          class="tab-btn"
          class:active={activeTab === 'filter'}
          onclick={() => activeTab = 'filter'}
        >
          <HiFiLed color={activeTab === 'filter' ? 'green' : 'off'} size="small" />
          FILTER
        </button>
        <button
          class="tab-btn"
          class:active={activeTab === 'laender'}
          onclick={() => activeTab = 'laender'}
        >
          <HiFiLed color={activeTab === 'laender' ? 'green' : 'off'} size="small" />
          LÄNDER
          {#if visibleCountries.length > 0}
            <span class="tab-badge-green">{visibleCountries.length}</span>
          {/if}
        </button>
        <button
          class="tab-btn"
          class:active={activeTab === 'werbung'}
          onclick={() => activeTab = 'werbung'}
        >
          <HiFiLed color={activeTab === 'werbung' ? 'amber' : 'off'} size="small" />
          Ad-Blocker
          {#if suspects.length > 0}
            <span class="tab-badge">{suspects.length}</span>
          {/if}
        </button>
        <button
          class="tab-btn"
          class:active={activeTab === 'gesperrt'}
          onclick={() => activeTab = 'gesperrt'}
        >
          <HiFiLed color={activeTab === 'gesperrt' ? 'red' : 'off'} size="small" />
          AUSGEBLENDET
          {#if blockedData?.count > 0}
            <span class="tab-badge">{blockedData.count}</span>
          {/if}
        </button>
      </div>
      <button class="filter-close" onclick={close} title="Schließen">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- TAB: Filter -->
    {#if activeTab === 'filter'}
      <div class="filter-content">

        <!-- ZONE 1: FILTER -->
        <div class="filter-zone">
          <div class="zone-header">
            <span class="zone-label">FILTER</span>
            <span class="zone-hint">Sender mit diesen Kriterien werden in der Liste nicht angezeigt</span>
          </div>

          <!-- Aktive Filter-Zusammenfassung -->
          {#if activeFilterSummary().length > 0}
            <div class="active-filter-summary">
              <HiFiLed color="amber" size="small" />
              <span class="summary-text">Aktiv: {activeFilterSummary().join(', ')} ausgeschlossen</span>
            </div>
          {/if}

          <!-- Sprachen -->
          <div class="filter-group">
            <div class="group-header">
              <span class="group-label">SPRACHEN AUSSCHLIESSEN</span>
              <div class="group-actions">
                <button class="mini-btn" onclick={selectAllLanguages}>Alle</button>
                <button class="mini-btn" onclick={selectNoLanguages}>Keine</button>
              </div>
            </div>
            <div class="rare-filter-row">
              <span class="rare-label">&le;</span>
              <input type="number" min="1" max="999" bind:value={rareThreshold} class="filter-input rare-input" onchange={saveFilterState} />
              <button class="mini-btn" onclick={selectRareLanguages}>SELTENE ({rareCount})</button>
            </div>
            <input
              type="text"
              class="filter-input"
              placeholder="Sprache suchen..."
              bind:value={languageSearch}
            />
            <div class="language-list">
              {#each filteredLanguages as lang}
                <button
                  class="lang-item"
                  class:excluded={excludedLanguages.includes(lang.name)}
                  onclick={() => toggleLanguage(lang.name)}
                >
                  <HiFiLed color={!excludedLanguages.includes(lang.name) ? 'green' : 'off'} size="small" />
                  <span class="lang-name">{lang.name}</span>
                  <span class="lang-count">{lang.count}</span>
                </button>
              {/each}
            </div>
          </div>

          <!-- Tags -->
          <div class="filter-group">
            <span class="group-label">TAGS AUSSCHLIESSEN</span>
            <div class="tag-chips">
              {#each excludedTags as tag}
                <span class="tag-chip">
                  {tag}
                  <button class="tag-remove" onclick={() => removeTag(tag)}>&times;</button>
                </span>
              {/each}
            </div>
            <div class="tag-input-row">
              <input
                type="text"
                class="filter-input tag-input"
                placeholder="Tag hinzufuegen..."
                bind:value={tagInput}
                onkeydown={handleTagKeydown}
              />
              <button class="mini-btn" onclick={() => addTag(tagInput)} disabled={!tagInput.trim()}>+</button>
            </div>
            <div class="tag-suggestions">
              {#each tagSuggestions.filter(s => !excludedTags.includes(s)) as suggestion}
                <button class="suggestion-chip" onclick={() => addTag(suggestion)}>{suggestion}</button>
              {/each}
            </div>
          </div>

          <!-- Min Votes -->
          <div class="filter-group">
            <span class="group-label">MIN VOTES</span>
            <input
              type="number"
              class="filter-input votes-input"
              min="0"
              bind:value={minVotes}
              onchange={() => { previewCount = null; saveFilterState(); }}
            />
          </div>
        </div>

        <!-- Trennlinie -->
        <div class="zone-divider"></div>

        <!-- ZONE 2: PERMANENT AUSBLENDEN -->
        <div class="block-zone">
          <div class="zone-header">
            <span class="zone-label zone-label-block">PERMANENT AUSBLENDEN</span>
            <span class="zone-hint">Sender mit obigen Kriterien dauerhaft entfernen</span>
          </div>
          <div class="filter-action-row">
            <button class="action-btn preview-btn" onclick={preview} disabled={isPreviewing}>
              {isPreviewing ? 'ZAEHLE...' : 'VORSCHAU'}
            </button>
            {#if previewCount !== null}
              <span class="preview-count">{previewCount} Sender betroffen</span>
            {/if}
            <button
              class="action-btn block-btn"
              onclick={push}
              disabled={isPushing || (excludedLanguages.length === 0 && excludedTags.length === 0 && minVotes === 0)}
            >
              {isPushing ? 'BLENDE AUS...' : 'AUSBLENDEN'}
            </button>
          </div>
        </div>

      </div>
    {/if}

    <!-- TAB: Werbung -->
    {#if activeTab === 'werbung'}
      <div class="filter-content">
        <div class="ad-zone">
          <div class="zone-header">
            <span class="zone-label zone-label-ad">WERBEERKENNUNG</span>
            <span class="zone-hint">Sender auf Werbung prüfen und entscheiden</span>
          </div>

          <!-- Status + Scan -->
          <div class="ad-status-grid">
            <div class="ad-stat">
              <span class="ad-stat-value">{adSummary?.total_checked ?? 0}</span>
              <span class="ad-stat-label">geprüft</span>
            </div>
            <div class="ad-stat">
              <span class="ad-stat-value ad-stat-clean">{adSummary?.clean ?? 0}</span>
              <span class="ad-stat-label">sauber</span>
            </div>
            <div class="ad-stat">
              <span class="ad-stat-value ad-stat-suspect">{adSummary?.suspect ?? 0}</span>
              <span class="ad-stat-label">verdächtig</span>
            </div>
            <div class="ad-stat">
              <span class="ad-stat-value ad-stat-blocked">{(adSummary?.manual_blocked ?? 0) + (adSummary?.auto_blocked ?? 0)}</span>
              <span class="ad-stat-label">ausgeblendet</span>
            </div>
          </div>

          <!-- Scan-Button + Fortschritt -->
          <div class="ad-scan-row">
            {#if isScanning}
              <button class="action-btn scan-btn scan-stop" onclick={stopScan}>
                STOPP
              </button>
            {:else}
              <button
                class="action-btn scan-btn"
                onclick={runScan}
                disabled={!adEnabled || (adSummary?.remaining ?? 0) === 0}
              >
                ALLE SCANNEN
              </button>
            {/if}
            {#if !isScanning && adSummary?.remaining != null}
              <span class="scan-remaining">{adSummary.remaining} noch nicht geprüft</span>
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

          <!-- Verdächtige Sender -->
          {#if suspects.length > 0}
            <div class="ad-suspects-inline">
              <div class="suspects-header">
                <span class="ad-sub-label">VERDÄCHTIG ({suspects.length})</span>
                <div class="suspects-batch-actions">
                  <button class="mini-btn suspect-block" onclick={decideAllSuspects('block')}>ALLE AUSBLENDEN</button>
                  <button class="mini-btn suspect-allow" onclick={decideAllSuspects('allow')}>ALLE OK</button>
                </div>
              </div>
              <div class="ad-suspects-list">
                {#each suspects as suspect (suspect.uuid)}
                  <div class="suspect-row-inline">
                    <div class="suspect-info-inline">
                      <HiFiLed color="amber" size="small" />
                      <span class="suspect-name-inline">{suspect.name || suspect.uuid}</span>
                      <span class="suspect-conf">{Math.round(suspect.confidence * 100)}%</span>
                    </div>
                    <div class="suspect-actions-inline">
                      <button class="mini-btn suspect-block" onclick={() => decideSuspect(suspect.uuid, 'block')}>
                        AUSBLENDEN
                      </button>
                      <button class="mini-btn suspect-allow" onclick={() => decideSuspect(suspect.uuid, 'allow')}>
                        OK
                      </button>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- Einstellungen -->
          <div class="zone-divider"></div>
          <div class="ad-settings-content">
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
                <div class="ad-toggle-label-group">
                  <span class="ad-toggle-label">Adress-Prüfung</span>
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
                <div class="ad-toggle-label-group">
                  <span class="ad-toggle-label">Server-Prüfung</span>
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
                <span class="ad-sub-label">AB WANN VERDÄCHTIG?</span>
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
      </div>
    {/if}

    <!-- TAB: Länder -->
    {#if activeTab === 'laender'}
      <div class="filter-content">
        <div class="filter-section-box">
          <div class="filter-group">
            <div class="group-header">
              <span class="group-label">SICHTBARE LÄNDER</span>
              <div class="group-actions">
                <button class="mini-btn" onclick={selectAllCountries}>Alle</button>
                <button class="mini-btn" onclick={selectNoCountries}>Keine</button>
              </div>
            </div>

            <input
              type="text"
              class="filter-input"
              placeholder="Land suchen..."
              bind:value={countrySearch}
            />

            <div class="country-list">
              {#each filteredCountries() as country}
                <button
                  class="lang-item"
                  class:active={visibleCountries.includes(country.code)}
                  onclick={() => toggleCountry(country.code)}
                >
                  <HiFiLed color={visibleCountries.includes(country.code) ? 'green' : 'off'} size="small" />
                  <span class="lang-name">{translateCountry(country.name)}</span>
                  <span class="lang-count">{country.count}</span>
                </button>
              {/each}
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- TAB: Gesperrt -->
    {#if activeTab === 'gesperrt'}
      <div class="filter-content">

        <!-- Verdaechtige Sender (User muss entscheiden) -->
        {#if suspects.length > 0}
          <div class="suspects-section">
            <div class="zone-header">
              <span class="zone-label zone-label-suspect">VERDACHT</span>
              <span class="zone-hint">{suspects.length} Sender zur Pruefung</span>
            </div>
            <div class="suspects-list">
              {#each suspects as suspect (suspect.uuid)}
                <div class="suspect-row">
                  <div class="suspect-info">
                    <HiFiLed color="amber" size="small" />
                    <span class="suspect-name">{suspect.name || suspect.uuid}</span>
                    <span class="suspect-conf">{Math.round(suspect.confidence * 100)}%</span>
                  </div>
                  <div class="suspect-reasons">
                    {#each suspect.reasons as r}
                      <span class="suspect-tag">{formatReason('ad:' + r.reason)}</span>
                    {/each}
                  </div>
                  <div class="suspect-actions">
                    <button class="mini-btn suspect-block" onclick={() => decideSuspect(suspect.uuid, 'block')}>
                      AUSBLENDEN
                    </button>
                    <button class="mini-btn suspect-allow" onclick={() => decideSuspect(suspect.uuid, 'allow')}>
                      OK
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          </div>
          <div class="zone-divider"></div>
        {/if}

        <!-- Gesperrte Sender nach Kategorien -->
        <div class="blocked-section">
          <div class="blocked-header">
            <span class="group-label">
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
                  <!-- Kategorie-Header -->
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

                  <!-- Reasons innerhalb der Kategorie -->
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
      </div>
    {/if}
  </div>
</div>

<style>
  /* === Overlay Background === */
  .filter-overlay-bg {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 3000;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
  }

  .filter-overlay-bg.visible {
    opacity: 1;
    pointer-events: auto;
  }

  /* === Panel === */
  .filter-panel {
    width: 620px;
    max-height: 80vh;
    height: auto;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-md);
    box-shadow: var(--hifi-shadow-raised), 0 8px 40px rgba(0, 0, 0, 0.4);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* === Header mit Tabs === */
  .filter-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 12px 0 0;
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
  }

  .tab-bar {
    display: flex;
    gap: 0;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 13px 20px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-display);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1.5px;
    cursor: pointer;
    text-transform: uppercase;
    transition: color 0.15s, border-color 0.15s;
  }

  .tab-btn:hover {
    color: var(--hifi-text-primary);
  }

  .tab-btn.active {
    color: var(--hifi-text-primary);
    border-bottom-color: var(--hifi-accent);
  }

  .tab-badge, .tab-badge-green {
    font-family: var(--hifi-font-family);
    font-size: 9px;
    font-weight: 500;
    margin-left: 2px;
  }

  .tab-badge {
    color: var(--hifi-led-red);
  }

  .tab-badge-green {
    color: var(--hifi-led-green, #4caf50);
  }

  .filter-close {
    width: 30px;
    height: 30px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    color: var(--hifi-text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
  }

  .filter-close:hover {
    color: var(--hifi-text-primary);
  }

  /* === Content === */
  .filter-content {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  /* === Zonen === */
  .filter-zone {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

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
    color: var(--hifi-accent);
    text-transform: uppercase;
  }

  .zone-label-block {
    color: var(--hifi-led-red);
  }

  .zone-hint {
    font-family: var(--hifi-font-family);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    font-style: italic;
  }

  .zone-divider {
    height: 1px;
    background: var(--hifi-border-dark);
    margin: 16px 0;
  }

  .active-filter-summary {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: rgba(229, 160, 13, 0.08);
    border: 1px solid rgba(229, 160, 13, 0.2);
    border-radius: var(--hifi-border-radius-sm);
  }

  .summary-text {
    font-family: var(--hifi-font-family);
    font-size: 11px;
    color: var(--hifi-led-amber, #e5a00d);
  }

  .block-zone {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    border: 1px solid rgba(255, 60, 60, 0.25);
    border-radius: var(--hifi-border-radius-sm);
    background: rgba(255, 60, 60, 0.04);
  }

  /* === Section Box === */
  .filter-section-box {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* === Filter Group === */
  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .group-label {
    font-family: var(--hifi-font-display);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1.5px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .group-actions {
    display: flex;
    gap: 4px;
  }

  /* (LEDs via HiFiLed component) */

  /* === Mini Button === */
  .mini-btn {
    padding: 3px 9px;
    background: var(--hifi-bg-tertiary);
    border: none;
    box-shadow: var(--hifi-shadow-button);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-family);
    font-size: 10px;
    cursor: pointer;
    border-radius: var(--hifi-border-radius-sm);
  }

  .mini-btn:hover {
    color: var(--hifi-text-primary);
  }

  .mini-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  /* === Input === */
  .filter-input {
    padding: 7px 10px;
    font-family: var(--hifi-font-family);
    font-size: 12px;
    color: var(--hifi-text-primary);
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    outline: none;
    box-shadow: var(--hifi-shadow-inset);
  }

  .filter-input:focus {
    box-shadow: var(--hifi-shadow-inset), 0 0 0 2px var(--hifi-accent);
  }

  .filter-input::placeholder {
    color: var(--hifi-text-secondary);
  }

  .votes-input {
    width: 90px;
  }

  .rare-filter-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .rare-input {
    width: 55px;
    padding: 4px 8px;
    font-size: 11px;
    text-align: center;
  }

  .rare-label {
    font-size: 12px;
    color: var(--hifi-text-secondary);
  }

  /* === Language List === */
  .language-list {
    max-height: 160px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-inset);
    padding: 4px;
  }

  .lang-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-family);
    font-size: 12px;
    cursor: pointer;
    text-align: left;
    border-radius: 3px;
  }

  .lang-item:hover {
    background: var(--hifi-row-hover);
  }

  .lang-item.excluded {
    opacity: 0.4;
  }

  .country-list {
    max-height: 400px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-inset);
    padding: 4px;
  }

  .lang-name {
    flex: 1;
    text-transform: capitalize;
  }

  .lang-count {
    font-size: 9px;
    color: var(--hifi-text-secondary);
    min-width: 40px;
    text-align: right;
    flex-shrink: 0;
  }

  /* === Tags === */
  .tag-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
  }

  .tag-chip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 3px 8px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    font-size: 11px;
    color: var(--hifi-text-primary);
  }

  .tag-remove {
    background: none;
    border: none;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    font-size: 12px;
    padding: 0 1px;
    line-height: 1;
  }

  .tag-remove:hover {
    color: var(--hifi-led-red);
  }

  .tag-input-row {
    display: flex;
    gap: 4px;
  }

  .tag-input {
    flex: 1;
  }

  .tag-suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
  }

  .suggestion-chip {
    padding: 3px 8px;
    background: var(--hifi-bg-secondary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-family);
    font-size: 10px;
    cursor: pointer;
  }

  .suggestion-chip:hover {
    border-color: var(--hifi-accent);
    color: var(--hifi-text-primary);
  }

  /* === Filter Actions === */
  .filter-action-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-top: 4px;
  }

  .preview-count {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    color: var(--hifi-accent);
    flex: 1;
  }

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

  .action-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .preview-btn {
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-primary);
  }

  .block-btn {
    background: var(--hifi-accent);
    color: #fff;
  }

  /* === Blocked Section === */
  .blocked-section {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .blocked-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .blocked-count {
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-family);
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
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 3px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-inset);
    padding: 6px;
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
    width: 100%;
    text-align: left;
    overflow: hidden;
    min-width: 0;
    font-family: var(--hifi-font-family);
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

  /* === Station Subliste (wie Radioliste) === */
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
    cursor: default;
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
    transition: color 0.15s, background 0.15s;
  }

  .unblock-btn:hover {
    color: var(--hifi-led-red);
    background: rgba(255, 60, 60, 0.1);
  }

  .unblock-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  /* === Kategorie-Gruppen === */
  .category-group {
    display: flex;
    flex-direction: column;
  }

  .category-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 8px;
    background: var(--hifi-bg-secondary);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    width: 100%;
    text-align: left;
    font-family: var(--hifi-font-family);
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

  .reason-arrow.sub {
    width: 8px;
    font-size: 7px;
  }

  /* === Verdaechtige Sender === */
  .suspects-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .zone-label-suspect {
    color: var(--hifi-led-amber, #e5a00d);
  }

  .suspects-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 240px;
    overflow-y: auto;
  }

  .suspect-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 10px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
  }

  .suspect-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .suspect-name {
    flex: 1;
    font-family: 'Barlow', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: var(--hifi-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .suspect-conf {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    color: var(--hifi-led-amber, #e5a00d);
    font-weight: 700;
  }

  .suspect-reasons {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    padding-left: 20px;
  }

  .suspect-tag {
    font-size: 9px;
    padding: 2px 6px;
    background: rgba(229, 160, 13, 0.12);
    color: var(--hifi-led-amber, #e5a00d);
    border-radius: 3px;
    font-family: var(--hifi-font-family);
  }

  .suspect-actions {
    display: flex;
    gap: 6px;
    padding-left: 20px;
  }

  .suspect-block {
    color: var(--hifi-led-red);
    font-weight: 600;
  }

  .suspect-allow {
    color: var(--hifi-accent);
    font-weight: 600;
  }

  /* === Ad-Erkennung Zone === */
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

  .ad-stat-clean {
    color: var(--hifi-led-green, #4caf50);
  }

  .ad-stat-suspect {
    color: var(--hifi-led-amber, #e5a00d);
  }

  .ad-stat-blocked {
    color: var(--hifi-led-red);
  }

  .ad-stat-label {
    font-family: var(--hifi-font-family);
    font-size: 9px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

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
    font-family: var(--hifi-font-family);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .scan-remaining {
    font-family: var(--hifi-font-family);
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }

  .ad-suspects-inline {
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

  .ad-suspects-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
    max-height: 180px;
    overflow-y: auto;
  }

  .suspect-row-inline {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 8px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
  }

  .suspect-info-inline {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .suspect-name-inline {
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

  .suspect-actions-inline {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .ad-settings-details {
    border-top: 1px solid rgba(229, 160, 13, 0.15);
    padding-top: 8px;
  }

  .ad-settings-toggle {
    cursor: pointer;
    user-select: none;
    list-style: none;
  }

  .ad-settings-toggle::-webkit-details-marker {
    display: none;
  }

  .ad-settings-toggle::before {
    content: '\f054';
    font-family: 'Font Awesome 6 Free';
    font-weight: 900;
    font-size: 7px;
    margin-right: 6px;
    color: var(--hifi-text-secondary);
    transition: transform 0.15s;
    display: inline-block;
  }

  .ad-settings-details[open] .ad-settings-toggle::before {
    transform: rotate(90deg);
  }

  .ad-settings-content {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-top: 8px;
  }

  .zone-label-ad {
    color: var(--hifi-led-amber, #e5a00d);
  }

  .ad-toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .ad-toggle-label {
    font-family: var(--hifi-font-family);
    font-size: 12px;
    color: var(--hifi-text-primary);
  }

  .ad-toggle-label-group {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .ad-toggle-hint {
    font-family: var(--hifi-font-family);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.7;
  }

  .ad-settings-hint {
    font-family: var(--hifi-font-family);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.7;
    margin: 0 0 4px 0;
    line-height: 1.4;
  }

  .ad-threshold-hint {
    font-family: var(--hifi-font-family);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.7;
    margin-bottom: 2px;
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

  .ad-methods {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-left: 8px;
  }

  .ad-sub-label {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .ad-threshold {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding-left: 8px;
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

  .ad-hint {
    font-family: var(--hifi-font-family);
    font-size: 9px;
    color: var(--hifi-text-secondary);
    font-style: italic;
  }

  .status-text {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    text-align: center;
    padding: 12px;
  }
</style>
