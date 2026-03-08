<script>
  import { api } from '../lib/api.js';
  import { actions } from '../lib/store.svelte.js';

  let { open = false, onclose } = $props();

  // Tabs
  let activeTab = $state('filter'); // 'filter' | 'release' | 'options'

  // === FILTER TAB ===
  let languages = $state([]);
  let languageSearch = $state('');
  let excludedLanguages = $state([]);
  let excludedTags = $state([]);
  let tagInput = $state('');
  let minVotes = $state(0);
  let previewCount = $state(null);
  let isPreviewing = $state(false);
  let isPushing = $state(false);

  // Vorschlaege fuer Tags
  const tagSuggestions = ['tv', 'television', 'test', 'webcam', 'video'];

  // Gefilterte Sprachen (Suchfeld)
  let filteredLanguages = $derived(
    languageSearch
      ? languages.filter(l => l.name.includes(languageSearch.toLowerCase()))
      : languages
  );

  // === RELEASE TAB ===
  let hiddenData = $state(null);
  let isLoadingHidden = $state(false);
  let isReleasing = $state(false);

  // === OPTIONS TAB ===
  let allCountries = $state([]);
  let visibleCountryCodes = $state([]);
  let countrySearch = $state('');
  let isSavingOptions = $state(false);

  let filteredCountries = $derived(
    countrySearch
      ? allCountries.filter(c =>
          c.name.toLowerCase().includes(countrySearch.toLowerCase()) ||
          c.code.toLowerCase().includes(countrySearch.toLowerCase()))
      : allCountries
  );

  // Daten laden beim Oeffnen
  $effect(() => {
    if (open) {
      loadLanguages();
    }
  });

  $effect(() => {
    if (open && activeTab === 'release') {
      loadHidden();
    }
  });

  $effect(() => {
    if (open && activeTab === 'options') {
      loadSidebarConfig();
    }
  });

  async function loadLanguages() {
    try {
      const data = await api.getAvailableLanguages();
      languages = data.languages || [];
    } catch (e) {
      console.error('Languages laden fehlgeschlagen:', e);
    }
  }

  async function loadHidden() {
    isLoadingHidden = true;
    try {
      hiddenData = await api.getHiddenStations();
    } catch (e) {
      console.error('Hidden stations laden fehlgeschlagen:', e);
    }
    isLoadingHidden = false;
  }

  // === Filter-Aktionen ===

  function toggleLanguage(langName) {
    if (excludedLanguages.includes(langName)) {
      excludedLanguages = excludedLanguages.filter(l => l !== langName);
    } else {
      excludedLanguages = [...excludedLanguages, langName];
    }
    previewCount = null;
  }

  function selectAllLanguages() {
    excludedLanguages = [];
    previewCount = null;
  }

  function selectNoLanguages() {
    excludedLanguages = languages.map(l => l.name);
    previewCount = null;
  }

  function addTag(tag) {
    tag = tag.trim().toLowerCase();
    if (tag && !excludedTags.includes(tag)) {
      excludedTags = [...excludedTags, tag];
      previewCount = null;
    }
    tagInput = '';
  }

  function removeTag(tag) {
    excludedTags = excludedTags.filter(t => t !== tag);
    previewCount = null;
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
      // Reset
      excludedLanguages = [];
      excludedTags = [];
      minVotes = 0;
      previewCount = null;
      onclose?.();
    } catch (e) {
      actions.showToast('Push fehlgeschlagen', 'error');
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
      await loadHidden();
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
      await loadHidden();
    } catch (e) {
      actions.showToast('Freigabe fehlgeschlagen', 'error');
    }
    isReleasing = false;
  }

  // === Options-Aktionen ===

  async function loadSidebarConfig() {
    try {
      // Laender vom Cache-Filter laden
      const filters = await api.getFilters();
      allCountries = filters.countries || [];

      // Gespeicherte sichtbare Laender laden
      const config = await api.getConfig();
      if (config.sidebar_countries) {
        visibleCountryCodes = JSON.parse(config.sidebar_countries);
      } else {
        // Default: Top 10
        visibleCountryCodes = allCountries.slice(0, 10).map(c => c.code);
      }
    } catch (e) {
      console.error('Sidebar-Config laden fehlgeschlagen:', e);
    }
  }

  function toggleCountryVisible(code) {
    if (visibleCountryCodes.includes(code)) {
      visibleCountryCodes = visibleCountryCodes.filter(c => c !== code);
    } else {
      visibleCountryCodes = [...visibleCountryCodes, code];
    }
  }

  function selectTopCountries(n) {
    visibleCountryCodes = allCountries.slice(0, n).map(c => c.code);
  }

  async function saveSidebarConfig() {
    isSavingOptions = true;
    try {
      await api.updateConfig({
        sidebar_countries: JSON.stringify(visibleCountryCodes)
      });
      actions.showToast('Sidebar-Einstellungen gespeichert');
      onclose?.();
    } catch (e) {
      actions.showToast('Speichern fehlgeschlagen', 'error');
    }
    isSavingOptions = false;
  }

  function close() {
    onclose?.();
  }

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) close();
  }
</script>

<div class="hifi-modal-overlay" class:visible={open} onclick={handleOverlayClick}>
  <div class="hifi-modal filter-modal">
    <!-- Header -->
    <div class="hifi-modal-header">
      <div class="modal-header-left">
        <span class="hifi-modal-title">SENDER-FILTER</span>
        <div class="tab-bar">
          <button
            class="tab-btn"
            class:active={activeTab === 'filter'}
            onclick={() => activeTab = 'filter'}
            title="Sender nach Sprache, Tags oder Votes ausblenden"
          >FILTER</button>
          <button
            class="tab-btn"
            class:active={activeTab === 'release'}
            onclick={() => activeTab = 'release'}
            title="Ausgeblendete Sender wieder freigeben"
          >FREIGEBEN</button>
          <button
            class="tab-btn"
            class:active={activeTab === 'options'}
            onclick={() => activeTab = 'options'}
            title="Sidebar-Anzeige konfigurieren"
          >OPTIONEN</button>
        </div>
      </div>
      <button class="hifi-modal-close" onclick={close} title="Filter-Dialog schliessen">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- Body -->
    <div class="hifi-modal-body filter-body">

      {#if activeTab === 'filter'}
        <!-- FILTER TAB -->

        <!-- Sprachen -->
        <div class="filter-section">
          <div class="section-header">
            <span class="section-label">SPRACHEN</span>
            <div class="section-actions">
              <button class="mini-btn" onclick={selectAllLanguages} title="Alle Sprachen einschliessen">Alle</button>
              <button class="mini-btn" onclick={selectNoLanguages} title="Alle Sprachen ausschliessen">Keine</button>
            </div>
          </div>

          <input
            type="text"
            class="filter-search"
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
                <span class="toggle-switch" class:on={!excludedLanguages.includes(lang.name)}><span class="toggle-knob"></span></span>
                <span class="lang-name">{lang.name}</span>
                <span class="lang-count">{lang.count}</span>
              </button>
            {/each}
          </div>
        </div>

        <!-- Tags -->
        <div class="filter-section">
          <span class="section-label">TAGS AUSSCHLIESSEN</span>
          <div class="tag-chips">
            {#each excludedTags as tag}
              <span class="tag-chip">
                {tag}
                <button class="tag-remove" onclick={() => removeTag(tag)} title="Tag '{tag}' aus Ausschlussliste entfernen">&times;</button>
              </span>
            {/each}
          </div>
          <div class="tag-input-row">
            <input
              type="text"
              class="filter-search tag-input"
              placeholder="Tag hinzufuegen..."
              bind:value={tagInput}
              onkeydown={handleTagKeydown}
            />
            <button class="mini-btn" onclick={() => addTag(tagInput)} disabled={!tagInput.trim()} title={!tagInput.trim() ? 'Tag-Name eingeben' : 'Tag zur Ausschlussliste hinzufuegen'}>+</button>
          </div>
          <div class="tag-suggestions">
            {#each tagSuggestions.filter(s => !excludedTags.includes(s)) as suggestion}
              <button class="suggestion-chip" onclick={() => addTag(suggestion)} title="Klicken um '{suggestion}' auszuschliessen">{suggestion}</button>
            {/each}
          </div>
        </div>

        <!-- Min Votes -->
        <div class="filter-section">
          <span class="section-label">MIN VOTES</span>
          <input
            type="number"
            class="filter-search votes-input"
            min="0"
            bind:value={minVotes}
            onchange={() => previewCount = null}
          />
        </div>

        <!-- Preview + Push -->
        <div class="filter-actions">
          <button class="action-btn preview-btn" onclick={preview} disabled={isPreviewing} title="Zeigt wie viele Sender mit diesen Filtern ausgeblendet wuerden">
            {isPreviewing ? 'ZAEHLE...' : 'VORSCHAU'}
          </button>
          {#if previewCount !== null}
            <span class="preview-count">{previewCount} Sender wuerden ausgeblendet</span>
          {/if}
        </div>

      {:else if activeTab === 'release'}
        <!-- RELEASE TAB -->

        {#if isLoadingHidden}
          <div class="loading-text">Lade...</div>
        {:else if hiddenData}
          <div class="release-header">
            <span class="release-total">{hiddenData.count} Sender ausgeblendet</span>
            {#if hiddenData.count > 0}
              <button class="action-btn release-all-btn" onclick={releaseAll} disabled={isReleasing} title={isReleasing ? 'Freigabe laeuft...' : 'Alle ausgeblendeten Sender wieder sichtbar machen'}>
                ALLE FREIGEBEN
              </button>
            {/if}
          </div>

          {#if Object.keys(hiddenData.reasons).length > 0}
            <div class="reason-list">
              {#each Object.entries(hiddenData.reasons) as [reason, count]}
                <div class="reason-item">
                  <span class="reason-label">{reason}</span>
                  <span class="reason-count">({count})</span>
                  <button
                    class="mini-btn release-btn"
                    onclick={() => releaseByReason(reason)}
                    disabled={isReleasing}
                    title={isReleasing ? 'Freigabe laeuft...' : 'Diese Gruppe wieder sichtbar machen'}
                  >FREIGEBEN</button>
                </div>
              {/each}
            </div>
          {:else}
            <div class="empty-text">Keine ausgeblendeten Sender</div>
          {/if}
        {/if}

      {:else if activeTab === 'options'}
        <!-- OPTIONS TAB -->

        <div class="filter-section">
          <div class="section-header">
            <span class="section-label">SIDEBAR-LAENDER</span>
            <div class="section-actions">
              <button class="mini-btn" onclick={() => selectTopCountries(10)} title="Die 10 Laender mit den meisten Sendern anzeigen">Top 10</button>
              <button class="mini-btn" onclick={() => selectTopCountries(20)} title="Die 20 Laender mit den meisten Sendern anzeigen">Top 20</button>
              <button class="mini-btn" onclick={() => visibleCountryCodes = allCountries.map(c => c.code)} title="Alle Laender in der Sidebar anzeigen">Alle</button>
            </div>
          </div>

          <input
            type="text"
            class="filter-search"
            placeholder="Land suchen..."
            bind:value={countrySearch}
          />

          <div class="language-list">
            {#each filteredCountries as country}
              <button
                class="lang-item"
                class:excluded={!visibleCountryCodes.includes(country.code)}
                onclick={() => toggleCountryVisible(country.code)}
              >
                <span class="toggle-switch" class:on={visibleCountryCodes.includes(country.code)}><span class="toggle-knob"></span></span>
                <span class="lang-name">{country.name}</span>
                <span class="lang-count">{country.count}</span>
              </button>
            {/each}
          </div>

          <div class="options-info">
            {visibleCountryCodes.length} von {allCountries.length} Laendern sichtbar
          </div>
        </div>
      {/if}
    </div>

    <!-- Footer -->
    {#if activeTab === 'filter'}
      <div class="hifi-modal-footer">
        <button class="action-btn cancel-btn" onclick={close}>ABBRECHEN</button>
        <button
          class="action-btn push-btn"
          onclick={push}
          disabled={isPushing || (excludedLanguages.length === 0 && excludedTags.length === 0 && minVotes === 0)}
          title={isPushing ? 'Sender werden ausgeblendet...' : (excludedLanguages.length === 0 && excludedTags.length === 0 && minVotes === 0) ? 'Mindestens einen Filter setzen (Sprache, Tag oder Votes)' : 'Gefilterte Sender dauerhaft ausblenden (kumulativ)'}
        >
          {isPushing ? 'AUSBLENDEN...' : 'PUSH - AUSBLENDEN'}
        </button>
      </div>
    {:else if activeTab === 'options'}
      <div class="hifi-modal-footer">
        <button class="action-btn cancel-btn" onclick={close}>ABBRECHEN</button>
        <button
          class="action-btn push-btn"
          onclick={saveSidebarConfig}
          disabled={isSavingOptions}
          title={isSavingOptions ? 'Einstellungen werden gespeichert...' : 'Sidebar-Laender Konfiguration speichern'}
        >
          {isSavingOptions ? 'SPEICHERE...' : 'SPEICHERN'}
        </button>
      </div>
    {:else}
      <div class="hifi-modal-footer">
        <button class="action-btn cancel-btn" onclick={close}>SCHLIESSEN</button>
      </div>
    {/if}
  </div>
</div>

<style>
  .filter-modal {
    width: 520px;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
  }

  .modal-header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .tab-bar {
    display: flex;
    gap: 2px;
  }

  .tab-btn {
    padding: 5px 12px;
    background: var(--hifi-bg-tertiary);
    border: none;
    color: var(--hifi-text-secondary);
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.5px;
    cursor: pointer;
    border-radius: var(--hifi-border-radius-sm);
  }

  .tab-btn.active {
    background: var(--hifi-accent);
    color: var(--hifi-text-primary);
  }

  .filter-body {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .filter-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .section-actions {
    display: flex;
    gap: 4px;
  }

  .mini-btn {
    padding: 3px 8px;
    background: var(--hifi-bg-tertiary);
    border: none;
    color: var(--hifi-text-secondary);
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    cursor: pointer;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
  }

  .mini-btn:hover {
    color: var(--hifi-text-primary);
  }

  .mini-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .filter-search {
    padding: 7px 10px;
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    color: var(--hifi-text-primary);
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    outline: none;
    box-shadow: var(--hifi-shadow-inset);
  }

  .filter-search:focus {
    box-shadow: var(--hifi-shadow-inset), 0 0 0 2px var(--hifi-accent);
  }

  .filter-search::placeholder {
    color: var(--hifi-text-secondary);
  }

  .votes-input {
    width: 100px;
  }

  /* Language List */
  .language-list {
    max-height: 240px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }

  .lang-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    cursor: pointer;
    text-align: left;
    border-radius: var(--hifi-border-radius-sm);
  }

  .lang-item:hover {
    background: var(--hifi-row-hover);
  }

  .lang-item.excluded {
    opacity: 0.5;
  }

  .toggle-switch {
    width: 28px;
    height: 14px;
    border-radius: 7px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    position: relative;
    flex-shrink: 0;
    transition: background 0.2s, border-color 0.2s;
  }

  .toggle-switch.on {
    background: var(--hifi-led-green);
    border-color: var(--hifi-led-green);
  }

  .toggle-knob {
    position: absolute;
    top: 1px;
    left: 1px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--hifi-text-secondary);
    transition: transform 0.2s, background 0.2s;
  }

  .toggle-switch.on .toggle-knob {
    transform: translateX(14px);
    background: #fff;
  }

  .lang-name {
    flex: 1;
    text-transform: capitalize;
  }

  .lang-count {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
  }

  /* Tags */
  .tag-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .tag-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
    font-size: 11px;
    color: var(--hifi-text-primary);
  }

  .tag-remove {
    background: none;
    border: none;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    font-size: 14px;
    padding: 0 2px;
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
    gap: 4px;
  }

  .suggestion-chip {
    padding: 2px 8px;
    background: none;
    border: 1px dashed var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-secondary);
    font-family: 'Barlow', sans-serif;
    font-size: 10px;
    cursor: pointer;
  }

  .suggestion-chip:hover {
    border-color: var(--hifi-accent);
    color: var(--hifi-text-primary);
  }

  /* Actions */
  .filter-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .preview-count {
    font-size: 11px;
    color: var(--hifi-accent);
  }

  .action-btn {
    padding: 8px 16px;
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.5px;
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    cursor: pointer;
    box-shadow: var(--hifi-shadow-button);
  }

  .action-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .preview-btn {
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-primary);
  }

  .push-btn {
    background: var(--hifi-accent);
    color: var(--hifi-text-primary);
  }

  .cancel-btn {
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-secondary);
  }

  /* Release Tab */
  .release-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .release-total {
    font-size: 12px;
    font-weight: 500;
    color: var(--hifi-text-primary);
  }

  .release-all-btn {
    background: var(--hifi-led-red);
    color: #fff;
    font-size: 10px;
  }

  .reason-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .reason-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    background: var(--hifi-bg-tertiary);
    border-radius: var(--hifi-border-radius-sm);
  }

  .reason-label {
    flex: 1;
    font-size: 11px;
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-values);
  }

  .reason-count {
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }

  .release-btn {
    color: var(--hifi-led-red);
  }

  .options-info {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    text-align: center;
    padding: 4px;
  }

  .loading-text, .empty-text {
    font-size: 11px;
    color: var(--hifi-text-secondary);
    text-align: center;
    padding: 20px;
  }
</style>
