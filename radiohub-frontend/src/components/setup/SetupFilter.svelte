<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { actions } from '../../lib/store.svelte.js';
  import { translateCountry, COUNTRY_NAMES } from '../../lib/countryNames.js';
  import { t } from '../../lib/i18n.svelte.js';

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
    if (excludedLanguages.length > 0) parts.push(`${excludedLanguages.length} ${t('filter.sprachen')}`);
    if (excludedTags.length > 0) parts.push(`${excludedTags.length} ${t('filter.tags')}`);
    if (minVotes > 0) parts.push(`Min. ${minVotes} Votes`);
    return parts;
  });

  // === TAGS ===
  let tagInput = $state('');
  const tagSuggestions = ['tv', 'television', 'test', 'webcam', 'video'];

  // === LÄNDER ===
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
      // Netzwerkfehler ignorieren
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

  // === LÄNDER-AKTIONEN ===
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
      // Netzwerkfehler ignorieren
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
      actions.showToast(t('filter.senderAusgeblendet', { count: data.hidden_count, total: data.total_hidden }));
      previewCount = null;
    } catch (e) {
      actions.showToast(t('filter.ausblendenFehler'), 'error');
      // Netzwerkfehler ignorieren
    }
    isPushing = false;
  }
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}

<div class="filter-root">
  <!-- Sub-Tab-Bar mit integrierter Summary -->
  <div class="sub-tab-bar">
    <button class="sub-tab-btn" class:active={subTab === 'filter'} onclick={() => subTab = 'filter'}>
      <HiFiLed color={subTab === 'filter' ? 'green' : 'off'} size="small" />
      {t('filter.suchfilter')}
    </button>
    <button class="sub-tab-btn" class:active={subTab === 'laender'} onclick={() => subTab = 'laender'}>
      <HiFiLed color={subTab === 'laender' ? 'green' : 'off'} size="small" />
      {t('filter.laender')}
      {#if visibleCountries.length > 0}
        <span class="sub-tab-badge">{visibleCountries.length}</span>
      {/if}
    </button>
    {#if subTab === 'filter' && activeFilterSummary().length > 0}
      <span class="filter-summary">
        <HiFiLed color="amber" size="small" />
        {t('filter.aktiv')} {activeFilterSummary().join(', ')}
      </span>
    {/if}
  </div>

  {#if subTab === 'filter'}
    <!-- === 2-Spalten-Layout === -->
    <div class="filter-columns">

      <!-- Linke Spalte: Sprachen -->
      <div class="filter-col-main">
        <div class="filter-section">
          <div class="filter-section-header">
            <span class="filter-section-label">{t('filter.sprachenAusschliessen')}</span>
            <div class="filter-bulk-actions">
              <button class="mini-btn" onclick={selectAllLanguages}>{t('filter.alle')}</button>
              <button class="mini-btn" onclick={selectNoLanguages}>{t('filter.keine')}</button>
            </div>
          </div>
          <div class="filter-toolbar">
            <span class="rare-label">&le;</span>
            <input type="number" min="1" max="999" bind:value={rareThreshold} class="filter-input rare-input" onchange={saveFilterState} />
            <button class="mini-btn" onclick={selectRareLanguages}>{t('filter.seltene')} ({rareCount})</button>
            <div class="toolbar-spacer"></div>
            <input
              type="text"
              class="filter-input search-input"
              placeholder={t('filter.spracheSuchen')}
              bind:value={languageSearch}
            />
          </div>
          <div class="filter-list">
            {#each filteredLanguages as lang}
              <button
                class="filter-list-item"
                class:excluded={excludedLanguages.includes(lang.name)}
                onclick={() => toggleLanguage(lang.name)}
              >
                <HiFiLed color={!excludedLanguages.includes(lang.name) ? 'green' : 'off'} size="small" />
                <span class="filter-list-name">{lang.name}</span>
                <span class="filter-list-count">{lang.count}</span>
              </button>
            {/each}
          </div>
        </div>
      </div>

      <!-- Rechte Spalte: Tags + Votes + Block -->
      <div class="filter-col-side">

        <!-- Tags -->
        <div class="filter-section side-section">
          <div class="filter-section-header">
            <span class="filter-section-label">{t('filter.tagsAusschliessen')}</span>
          </div>
          <div class="side-content">
            {#if excludedTags.length > 0}
              <div class="tag-chips">
                {#each excludedTags as tag}
                  <span class="tag-chip">
                    {tag}
                    <button class="tag-remove" onclick={() => removeTag(tag)}>&times;</button>
                  </span>
                {/each}
              </div>
            {/if}
            <div class="tag-input-row">
              <input
                type="text"
                class="filter-input tag-input"
                placeholder={t('filter.tagHinzufuegen')}
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
        <div class="filter-section side-section">
          <div class="filter-section-header">
            <span class="filter-section-label">{t('filter.minVotes')}</span>
          </div>
          <div class="side-content">
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
          <span class="block-zone-label">{t('filter.permanentAusblenden')}</span>
          <span class="block-zone-hint">{t('filter.permanentHint')}</span>
          <div class="block-actions">
            <button class="action-btn preview-btn" onclick={preview} disabled={isPreviewing}>
              {isPreviewing ? t('filter.zaehle') : t('filter.vorschau')}
            </button>
            {#if previewCount !== null}
              <span class="preview-count">{previewCount} {t('filter.betroffen')}</span>
            {/if}
            <button
              class="action-btn block-btn"
              onclick={push}
              disabled={isPushing || (excludedLanguages.length === 0 && excludedTags.length === 0 && minVotes === 0)}
            >
              {isPushing ? t('filter.blendeAus') : t('filter.ausblenden')}
            </button>
          </div>
        </div>

      </div>
    </div>

  {:else if subTab === 'laender'}
    <!-- === Länder: Volle Höhe === -->
    <div class="filter-full">
      <div class="filter-section">
        <div class="filter-section-header">
          <span class="filter-section-label">{t('filter.sichtbareLaender')}</span>
          <div class="filter-bulk-actions">
            <button class="mini-btn" onclick={selectAllCountries}>{t('filter.alle')}</button>
            <button class="mini-btn" onclick={selectNoCountries}>{t('filter.keine')}</button>
          </div>
        </div>
        <div class="filter-toolbar">
          <input
            type="text"
            class="filter-input search-input search-full"
            placeholder={t('filter.landSuchen')}
            bind:value={countrySearch}
          />
        </div>
        <div class="filter-list">
          {#each filteredCountries() as country}
            <button
              class="filter-list-item"
              class:active={visibleCountries.includes(country.code)}
              onclick={() => toggleCountry(country.code)}
            >
              <HiFiLed color={visibleCountries.includes(country.code) ? 'green' : 'off'} size="small" />
              <span class="filter-list-name">{translateCountry(country.name)}</span>
              <span class="filter-list-count">{country.count}</span>
            </button>
          {/each}
        </div>
      </div>
    </div>
  {/if}
</div>

{/if}

<style>
  /* === Root: füllt verfügbaren Platz === */
  .filter-root {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  /* === Sub-Tab Bar === */
  .sub-tab-bar {
    display: flex;
    align-items: center;
    gap: 2px;
    margin-bottom: 12px;
    flex-shrink: 0;
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
    color: var(--hifi-text-green, #4caf50);
  }

  .filter-summary {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-left: auto;
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-amber, #e5a00d);
    padding: 4px 10px;
    background: rgba(229, 160, 13, 0.08);
    border-radius: var(--hifi-border-radius-sm);
  }

  /* === 2-Spalten Layout (Suchfilter) === */
  .filter-columns {
    display: flex;
    flex: 1;
    min-height: 0;
    gap: 16px;
  }

  .filter-col-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }

  .filter-col-side {
    width: 260px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    overflow-y: auto;
  }

  /* === Volle Höhe (Länder) === */
  .filter-full {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  /* === Filter Section (leichter Container) === */
  .filter-section {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
  }

  .side-section {
    flex: none;
  }

  .filter-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
  }

  .filter-section-label {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .filter-bulk-actions {
    display: flex;
    gap: 4px;
  }

  /* === Toolbar (Seltene + Suche) === */
  .filter-toolbar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
  }

  .toolbar-spacer {
    flex: 1;
  }

  .search-input {
    width: 160px;
    flex-shrink: 0;
  }

  .search-full {
    width: 100%;
    flex-shrink: 1;
  }

  /* === Filter-Liste (gemeinsam für Sprachen + Länder) === */
  .filter-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    padding: 4px;
  }

  .filter-list-item {
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
    flex-shrink: 0;
  }

  .filter-list-item:hover {
    background: var(--hifi-row-hover);
  }

  .filter-list-item.excluded {
    opacity: 0.4;
  }

  .filter-list-name {
    flex: 1;
    text-transform: capitalize;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .filter-list-count {
    font-size: 9px;
    color: var(--hifi-text-secondary);
    min-width: 40px;
    text-align: right;
    flex-shrink: 0;
  }

  /* === Side Content === */
  .side-content {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 12px;
  }

  /* === Shared Buttons === */
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
    padding: 6px 10px;
    font-family: var(--hifi-font-values);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-primary);
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    outline: none;
    box-shadow: var(--hifi-shadow-inset);
  }

  .filter-input:focus {
    box-shadow: var(--hifi-shadow-inset), 0 0 0 1px rgba(255,255,255,0.15);
  }

  .filter-input::placeholder {
    color: var(--hifi-text-secondary);
  }

  .votes-input {
    width: 90px;
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
    gap: 6px;
    padding: 10px 12px;
    border: 1px solid rgba(255, 60, 60, 0.25);
    border-radius: var(--hifi-border-radius-sm);
    background: rgba(255, 60, 60, 0.04);
  }

  .block-zone-label {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--hifi-led-red);
    text-transform: uppercase;
  }

  .block-zone-hint {
    font-family: var(--hifi-font-body);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    font-style: italic;
  }

  .block-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .preview-count {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    color: var(--hifi-accent);
    flex: 1;
  }

  .action-btn {
    padding: 6px 12px;
    font-family: var(--hifi-font-display);
    font-size: 10px;
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
