<script>
  /**
   * SearchBarWithHistory - Suchfeld mit History-Dropdown
   * Exaktes Design wie StationsTab-Suchfeld.
   */
  let {
    placeholder = 'Suchen...',
    storageKey = 'radiohub_search_history',
    maxHistory = 10,
    onsearch = () => {}
  } = $props();

  let query = $state('');
  let history = $state(loadHistory());
  let showHistory = $state(false);
  let inputEl;

  function loadHistory() {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || '[]');
    } catch {
      return [];
    }
  }

  function saveHistory() {
    localStorage.setItem(storageKey, JSON.stringify(history));
  }

  function doSearch() {
    const q = query.trim();
    if (!q) return;
    history = [q, ...history.filter(h => h !== q)].slice(0, maxHistory);
    saveHistory();
    showHistory = false;
    onsearch(q);
  }

  function selectHistory(item) {
    query = item;
    showHistory = false;
    doSearch();
  }

  function clearHistory() {
    history = [];
    saveHistory();
    showHistory = false;
  }

  function clearQuery() {
    query = '';
    inputEl?.focus();
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      doSearch();
    } else if (e.key === 'Escape') {
      showHistory = false;
    }
  }

  function handleFocus() {
    if (history.length > 0 && !query) {
      showHistory = true;
    }
  }

  function handleBlur() {
    setTimeout(() => { showHistory = false; }, 200);
  }
</script>

<div class="search-wrapper">
  <div class="search-bar">
    <i class="fa-solid fa-magnifying-glass search-icon"></i>
    <input
      type="text"
      class="search-input"
      {placeholder}
      bind:value={query}
      bind:this={inputEl}
      onkeydown={handleKeydown}
      onfocus={handleFocus}
      onblur={handleBlur}
    />
    {#if query}
      <button class="search-clear" onclick={clearQuery} title="Suche leeren">&#10005;</button>
    {/if}
  </div>

  {#if showHistory && history.length > 0}
    <div class="search-history">
      <div class="search-history-header">
        <span>Letzte Suchen</span>
        <button class="search-history-clear" onclick={clearHistory}>Leeren</button>
      </div>
      {#each history as item}
        <button class="search-history-item" onmousedown={() => selectHistory(item)}>
          <i class="fa-solid fa-clock-rotate-left"></i>
          <span>{item}</span>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .search-wrapper {
    position: relative;
    flex: 1;
  }

  /* Exaktes StationsTab-Suchfeld-Design */
  .search-bar {
    display: flex;
    align-items: center;
    flex: 1;
    height: 34px;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-sm, 4px);
    box-sizing: border-box;
    padding: 0 10px;
    gap: 8px;
    position: relative;
    box-shadow: var(--hifi-shadow-inset);
  }

  .search-bar:focus-within {
    box-shadow: var(--hifi-shadow-inset), 0 0 0 1px rgba(74, 144, 217, 0.3);
  }

  .search-icon {
    font-size: 11px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    background: none;
    border: none;
    padding: 0;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 13px;
    font-weight: 700;
    color: var(--hifi-text-primary);
    outline: none;
    letter-spacing: 0.5px;
  }

  .search-input::placeholder {
    color: var(--hifi-text-secondary);
    opacity: 0.4;
  }

  .search-clear {
    background: none;
    border: none;
    color: var(--hifi-text-secondary);
    font-size: 12px;
    cursor: pointer;
    padding: 2px;
    flex-shrink: 0;
  }

  .search-clear:hover {
    color: var(--hifi-text-primary);
  }

  /* History Dropdown */
  .search-history {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--hifi-bg-panel);
    border-radius: 0 0 var(--hifi-border-radius-sm, 4px) var(--hifi-border-radius-sm, 4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    max-height: 240px;
    overflow-y: auto;
  }

  .search-history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 12px;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--hifi-text-secondary);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .search-history-clear {
    background: none;
    border: none;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    font-size: 9px;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    text-transform: uppercase;
    padding: 2px 4px;
  }

  .search-history-clear:hover {
    color: var(--hifi-accent);
  }

  .search-history-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    cursor: pointer;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.3px;
    text-align: left;
  }

  .search-history-item:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .search-history-item i {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }
</style>
