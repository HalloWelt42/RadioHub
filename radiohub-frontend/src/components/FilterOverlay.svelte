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

  // rareThreshold aus Config laden (einmalig)
  let _filterInitialized = false;

  // Daten laden beim Oeffnen
  $effect(() => {
    if (open) {
      loadLanguages();
      loadCountries();
      loadBlocked();
      if (!_filterInitialized) loadRareThreshold();
    }
  });

  async function loadRareThreshold() {
    try {
      const config = await api.getConfig();
      if (config.filter_rare_threshold != null) {
        rareThreshold = Number(config.filter_rare_threshold) || 3;
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
      actions.showToast(`${data.hidden_count} Sender blockiert (${data.total_hidden} gesamt)`);
      previewCount = null;
      await loadBlocked();
    } catch (e) {
      actions.showToast('Blockieren fehlgeschlagen', 'error');
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
          class:active={activeTab === 'gesperrt'}
          onclick={() => activeTab = 'gesperrt'}
        >
          <HiFiLed color={activeTab === 'gesperrt' ? 'red' : 'off'} size="small" />
          GESPERRT
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

        <!-- ZONE 1: SUCHFILTER -->
        <div class="filter-zone">
          <div class="zone-header">
            <span class="zone-label">SUCHFILTER</span>
            <span class="zone-hint">beeinflusst Suchergebnisse</span>
          </div>

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

        <!-- ZONE 2: MASSENBLOCKIERUNG -->
        <div class="block-zone">
          <div class="zone-header">
            <span class="zone-label zone-label-block">MASSENBLOCKIERUNG</span>
            <span class="zone-hint">Sender mit obigen Filtern permanent sperren</span>
          </div>
          <div class="filter-action-row">
            <button class="action-btn preview-btn" onclick={preview} disabled={isPreviewing}>
              {isPreviewing ? 'ZAEHLE...' : 'VORSCHAU'}
            </button>
            {#if previewCount !== null}
              <span class="preview-count">{previewCount} Sender</span>
            {/if}
            <button
              class="action-btn block-btn"
              onclick={push}
              disabled={isPushing || (excludedLanguages.length === 0 && excludedTags.length === 0 && minVotes === 0)}
            >
              {isPushing ? 'BLOCKIERE...' : 'BLOCKIEREN'}
            </button>
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
        <div class="blocked-section">
          <div class="blocked-header">
            <span class="group-label">
              GESPERRTE SENDER
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
            {:else if blockedData && Object.keys(blockedData.reasons).length > 0}
              {#each Object.entries(blockedData.reasons) as [reason, count]}
                <div class="reason-group">
                  <div class="reason-row" onclick={() => toggleReason(reason)} tabindex="0">
                    <span class="reason-arrow" class:open={expandedReason === reason}>
                      <i class="fa-solid fa-chevron-right"></i>
                    </span>
                    <HiFiLed color={isAdReason(reason) ? 'amber' : 'red'} size="small" />
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
            {:else}
              <div class="status-text">Keine gesperrten Sender</div>
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
    width: 520px;
    height: 600px;
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

  .status-text {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    text-align: center;
    padding: 12px;
  }
</style>
