<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';
  import { translateCountry, COUNTRY_NAMES } from '../../lib/countryNames.js';

  // === FILTER STATE ===
  let excludedLanguages = $state([]);
  let excludedTags = $state([]);
  let minVotes = $state(0);
  let rareThreshold = $state(3);

  // === SPRACHEN ===
  let languages = $state([]);
  let languageSearch = $state('');

  let filteredLanguages = $derived(
    languageSearch
      ? languages.filter(l => l.name.includes(languageSearch.toLowerCase()))
      : languages
  );
  let rareCount = $derived(languages.filter(l => l.count <= rareThreshold).length);

  let activeFilterSummary = $derived(() => {
    const parts = [];
    if (excludedLanguages.length > 0) parts.push(`${excludedLanguages.length} Sprachen`);
    if (excludedTags.length > 0) parts.push(`${excludedTags.length} Tags`);
    if (minVotes > 0) parts.push(`Min. ${minVotes} Votes`);
    return parts;
  });

  // === TAGS ===
  let tagInput = $state('');
  const tagSuggestions = ['tv', 'television', 'test', 'webcam', 'video'];

  // === LAENDER ===
  let countries = $state([]);
  let countrySearch = $state('');
  let visibleCountries = $state([]);

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

  // === PREVIEW / PUSH ===
  let previewCount = $state(null);
  let isPreviewing = $state(false);
  let isPushing = $state(false);

  // === SUB-TAB ===
  let subTab = $state('filter');

  // === INIT ===
  let isLoading = $state(true);

  $effect(() => {
    loadAll();
  });

  async function loadAll() {
    try {
      const [config, langData, countryData] = await Promise.all([
        api.getConfig(),
        api.getAvailableLanguages(),
        api.getAvailableCountries()
      ]);

      // Config auslesen
      if (config.filter_excluded_languages) {
        const saved = typeof config.filter_excluded_languages === 'string'
          ? JSON.parse(config.filter_excluded_languages) : config.filter_excluded_languages;
        if (Array.isArray(saved)) excludedLanguages = saved;
      }
      if (config.filter_excluded_tags) {
        const saved = typeof config.filter_excluded_tags === 'string'
          ? JSON.parse(config.filter_excluded_tags) : config.filter_excluded_tags;
        if (Array.isArray(saved)) excludedTags = saved;
      }
      minVotes = Number(config.filter_min_votes) || 0;
      rareThreshold = Number(config.filter_rare_threshold) || 3;

      if (config.sidebar_countries) {
        const saved = typeof config.sidebar_countries === 'string'
          ? JSON.parse(config.sidebar_countries) : config.sidebar_countries;
        if (Array.isArray(saved)) visibleCountries = saved;
      }

      languages = langData.languages || [];
      countries = countryData.countries || [];
    } catch (e) {
      console.error('SetupFilter: Daten laden fehlgeschlagen:', e);
    }
    isLoading = false;
  }

  function saveFilterState() {
    api.updateConfig({
      filter_excluded_languages: excludedLanguages,
      filter_excluded_tags: excludedTags,
      filter_min_votes: minVotes,
      filter_rare_threshold: rareThreshold
    });
  }

  function saveCountries() {
    api.updateConfig({ sidebar_countries: visibleCountries });
  }

  // === SPRACH-AKTIONEN ===
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

  // === TAG-AKTIONEN ===
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

  // === LAENDER-AKTIONEN ===
  function toggleCountry(code) {
    if (visibleCountries.includes(code)) {
      visibleCountries = visibleCountries.filter(c => c !== code);
    } else {
      visibleCountries = [...visibleCountries, code];
    }
    saveCountries();
  }

  function selectAllCountries() {
    visibleCountries = [];
    saveCountries();
  }

  function selectNoCountries() {
    visibleCountries = countries.map(c => c.code);
    saveCountries();
  }

  // === PREVIEW / PUSH ===
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
      console.error('SetupFilter: Preview fehlgeschlagen:', e);
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
    } catch (e) {
      actions.showToast('Ausblenden fehlgeschlagen', 'error');
      console.error('SetupFilter: Push fehlgeschlagen:', e);
    }
    isPushing = false;
  }
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}

  <!-- Sub-Tab: Filter / Laender -->
  <div class="sub-tab-bar">
    <button class="sub-tab-btn" class:active={subTab === 'filter'} onclick={() => subTab = 'filter'}>
      <HiFiLed color={subTab === 'filter' ? 'green' : 'off'} size="small" />
      SUCHFILTER
    </button>
    <button class="sub-tab-btn" class:active={subTab === 'laender'} onclick={() => subTab = 'laender'}>
      <HiFiLed color={subTab === 'laender' ? 'green' : 'off'} size="small" />
      LAENDER
      {#if visibleCountries.length > 0}
        <span class="sub-tab-badge">{visibleCountries.length}</span>
      {/if}
    </button>
  </div>

  {#if subTab === 'filter'}
    <!-- Aktive Filter-Zusammenfassung -->
    {#if activeFilterSummary().length > 0}
      <div class="active-filter-summary">
        <HiFiLed color="amber" size="small" />
        <span class="summary-text">Aktiv: {activeFilterSummary().join(', ')} ausgeschlossen</span>
      </div>
    {/if}

    <!-- Sprachen -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">SPRACHEN AUSSCHLIESSEN</span>
        <div class="group-actions">
          <button class="mini-btn" onclick={selectAllLanguages}>Alle</button>
          <button class="mini-btn" onclick={selectNoLanguages}>Keine</button>
        </div>
      </div>
      <div class="filter-content">
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
    </div>

    <!-- Tags -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">TAGS AUSSCHLIESSEN</span>
      </div>
      <div class="filter-content">
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
    </div>

    <!-- Min Votes -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">MIN VOTES</span>
      </div>
      <div class="filter-content">
        <input
          type="number"
          class="filter-input votes-input"
          min="0"
          bind:value={minVotes}
          onchange={() => { previewCount = null; saveFilterState(); }}
        />
      </div>
    </div>

    <!-- Permanent Ausblenden -->
    <div class="block-zone">
      <div class="zone-header">
        <span class="zone-label zone-label-block">PERMANENT AUSBLENDEN</span>
      </div>
      <span class="zone-hint">Sender mit obigen Kriterien dauerhaft entfernen</span>
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

  {:else if subTab === 'laender'}
    <!-- Laender-Konfiguration -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">SICHTBARE LAENDER</span>
        <div class="group-actions">
          <button class="mini-btn" onclick={selectAllCountries}>Alle</button>
          <button class="mini-btn" onclick={selectNoCountries}>Keine</button>
        </div>
      </div>
      <div class="filter-content">
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

  .sub-tab-badge {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    color: var(--hifi-led-green, #4caf50);
  }

  /* === Filter Content (innerhalb Panels) === */
  .filter-content {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 16px;
  }

  /* === Active Filter Summary === */
  .active-filter-summary {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: rgba(229, 160, 13, 0.08);
    border: 1px solid rgba(229, 160, 13, 0.2);
    border-radius: var(--hifi-border-radius-sm);
    margin-bottom: 8px;
  }

  .summary-text {
    font-family: var(--hifi-font-body);
    font-size: 11px;
    color: var(--hifi-led-amber, #e5a00d);
  }

  /* === Shared Buttons === */
  .group-actions {
    display: flex;
    gap: 4px;
  }

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

  .mini-btn:hover {
    color: var(--hifi-text-primary);
  }

  .mini-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  /* === Inputs === */
  .filter-input {
    padding: 7px 10px;
    font-family: var(--hifi-font-body);
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

  /* === Language/Country List === */
  .language-list {
    max-height: 200px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-inset);
    padding: 4px;
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

  .lang-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-body);
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
    font-family: var(--hifi-font-body);
    font-size: 10px;
    cursor: pointer;
  }

  .suggestion-chip:hover {
    color: var(--hifi-text-primary);
  }

  /* === Block Zone === */
  .block-zone {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    border: 1px solid rgba(255, 60, 60, 0.25);
    border-radius: var(--hifi-border-radius-sm);
    background: rgba(255, 60, 60, 0.04);
    margin-top: 8px;
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
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    font-style: italic;
  }

  .filter-action-row {
    display: flex;
    align-items: center;
    gap: 8px;
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
</style>
