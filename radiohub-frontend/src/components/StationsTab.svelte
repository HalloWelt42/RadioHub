<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  
  // 1000er-Trenner für Zahlen
  function formatNumber(num) {
    return num?.toLocaleString('de-DE') ?? '-';
  }
  
  let searchQuery = $state('');
  let stations = $state([]);
  let isLoading = $state(false);
  let isLoadingMore = $state(false);
  let isRefreshing = $state(false);
  
  // Details erweitert für welche Station (null = keine)
  let expandedUuid = $state(null);
  
  // Aktuell spielender Sender
  let currentPlayingStation = $derived(appState.currentStation);
  
  // Stationen OHNE den aktuellen Sender (der wird separat dargestellt)
  let filteredStations = $derived(() => {
    if (!currentPlayingStation) return stations;
    return stations.filter(s => s.uuid !== currentPlayingStation.uuid);
  });
  
  // Filter-Daten
  let availableCountries = $state([]);
  let availableBitrates = $state([]);
  let availableVotesRanges = $state([]);
  
  // Aktive Filter
  let selectedCountries = $state([]);
  let selectedBitrates = $state([]);
  let selectedVotesRanges = $state([]);
  let showFavsOnly = $state(false);
  
  // Sortierung
  let sortBy = $state('name');
  let sortOrder = $state('asc');
  
  // Pagination
  let offset = $state(0);
  let limit = 50;
  let hasMore = $state(true);
  
  // Filter collapsed
  let countriesExpanded = $state(true);
  let bitratesExpanded = $state(true);
  let votesExpanded = $state(true);
  
  // Search debounce
  let searchTimeout;
  
  $effect(() => {
    loadFilters();
    actions.loadFavorites();
  });
  
  // Sync stations to appState für Navigation
  $effect(() => {
    appState.stations = stations;
  });
  
  // Votes-Ranges logarithmisch berechnen
  function calculateVotesRanges(maxVotes) {
    if (!maxVotes || maxVotes <= 0) return [];
    
    const ranges = [];
    
    // Bereich 0: Exakt 0 Votes
    ranges.push({ label: '0', min: 0, max: 0 });
    
    // 9 weitere Bereiche logarithmisch verteilt
    // log10(1) = 0, log10(maxVotes) = max
    const logMax = Math.log10(maxVotes);
    
    for (let i = 1; i <= 9; i++) {
      // Logarithmische Verteilung
      const logMin = (logMax / 9) * (i - 1);
      const logMaxRange = (logMax / 9) * i;
      
      let min = i === 1 ? 1 : Math.ceil(Math.pow(10, logMin));
      let max = Math.floor(Math.pow(10, logMaxRange));
      
      // Runden auf schöne Zahlen (mehr Nullen bei größeren Werten)
      if (max >= 100000) {
        max = Math.floor(max / 10000) * 10000;
        min = Math.floor(min / 10000) * 10000 || min;
      } else if (max >= 10000) {
        max = Math.floor(max / 1000) * 1000;
        min = Math.floor(min / 1000) * 1000 || min;
      } else if (max >= 1000) {
        max = Math.floor(max / 100) * 100;
        min = Math.floor(min / 100) * 100 || min;
      }
      
      // Label formatieren mit Tausendertrennern
      const formatLabel = (n) => n.toLocaleString('de-DE');
      
      if (i === 9) {
        // Letzter Bereich: > X
        ranges.push({ label: `> ${formatLabel(min)}`, min: min, max: 999999999 });
      } else {
        ranges.push({ label: `${formatLabel(min)} - ${formatLabel(max)}`, min: min, max: max });
      }
    }
    
    return ranges;
  }
  
  async function loadFilters() {
    try {
      const filters = await api.getFilters();
      availableCountries = filters.countries || [];
      
      // Backend gibt Bitrate-Bereiche als Objekte: {label, min, max}
      const defaultBitrates = [
        { label: '< 64 kbps', min: 0, max: 64 },
        { label: '64-128 kbps', min: 64, max: 128 },
        { label: '128-192 kbps', min: 128, max: 192 },
        { label: '192-256 kbps', min: 192, max: 256 },
        { label: '> 256 kbps', min: 256, max: 9999 }
      ];
      
      availableBitrates = filters.bitrates?.length ? filters.bitrates : defaultBitrates;
      
      // Votes-Ranges aus max_votes berechnen (vom Backend oder Default)
      const maxVotes = filters.max_votes || 100000;
      availableVotesRanges = calculateVotesRanges(maxVotes);
      
      search();
    } catch (e) {
      console.error('Filter laden fehlgeschlagen:', e);
      search();
    }
  }
  
  async function search(append = false) {
    if (!append) {
      isLoading = true;
      offset = 0;
      stations = [];
    } else {
      isLoadingMore = true;
    }
    
    try {
      // Bitrate-Bereiche: min/max aus allen ausgewählten Bereichen
      let bitrate_min = undefined;
      let bitrate_max = undefined;
      if (selectedBitrates.length > 0) {
        bitrate_min = Math.min(...selectedBitrates.map(b => b.min));
        bitrate_max = Math.max(...selectedBitrates.map(b => b.max));
        // 9999 bedeutet "unbegrenzt", also nicht als max setzen
        if (bitrate_max >= 9999) bitrate_max = undefined;
      }
      
      // Votes-Bereiche: min/max aus allen ausgewählten Bereichen
      let votes_min = undefined;
      let votes_max = undefined;
      if (selectedVotesRanges.length > 0) {
        votes_min = Math.min(...selectedVotesRanges.map(r => r.min));
        votes_max = Math.max(...selectedVotesRanges.map(r => r.max));
        // 999999999 bedeutet "unbegrenzt"
        if (votes_max >= 999999999) votes_max = undefined;
      }
      
      const params = {
        q: searchQuery || undefined,
        countries: selectedCountries.length > 0 ? selectedCountries : undefined,
        bitrate_min: bitrate_min,
        bitrate_max: bitrate_max,
        votes_min: votes_min,
        votes_max: votes_max,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: limit,
        offset: append ? offset : 0
      };
      
      if (showFavsOnly) {
        params.favs_only = true;
      }
      
      const result = await api.searchStations(params);
      const newStations = result.stations || [];
      
      if (append) {
        stations = [...stations, ...newStations];
      } else {
        stations = newStations;
      }
      
      hasMore = newStations.length === limit;
      offset = stations.length;
    } catch (e) {
      actions.showToast('Suche fehlgeschlagen', 'error');
    } finally {
      isLoading = false;
      isLoadingMore = false;
    }
  }
  
  async function refreshStations() {
    isRefreshing = true;
    try {
      await api.syncCache(true);
      await loadFilters();
      actions.showToast('Stationen aktualisiert', 'success');
    } catch (e) {
      actions.showToast('Refresh fehlgeschlagen', 'error');
    }
    isRefreshing = false;
  }
  
  function handleSearchInput() {
    clearTimeout(searchTimeout);
    if (searchQuery.length >= 2 || searchQuery.length === 0) {
      searchTimeout = setTimeout(() => search(), 300);
    }
  }
  
  function handleScroll(e) {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    if (scrollHeight - scrollTop - clientHeight < 200 && hasMore && !isLoadingMore && !isLoading) {
      search(true);
    }
  }
  
  function playStation(station) {
    actions.playStation(station);
  }
  
  function toggleFavorite(station, e) {
    e.stopPropagation();
    actions.toggleFavorite(station);
  }
  
  function toggleDetails(uuid, e) {
    e?.stopPropagation();
    expandedUuid = expandedUuid === uuid ? null : uuid;
  }
  
  function toggleCountry(code) {
    if (selectedCountries.includes(code)) {
      selectedCountries = selectedCountries.filter(c => c !== code);
    } else {
      selectedCountries = [...selectedCountries, code];
    }
    search();
  }
  
  function toggleBitrate(bitrate) {
    // Vergleich über label, da Objekte nicht direkt verglichen werden können
    const isSelected = selectedBitrates.some(b => b.label === bitrate.label);
    if (isSelected) {
      selectedBitrates = selectedBitrates.filter(b => b.label !== bitrate.label);
    } else {
      selectedBitrates = [...selectedBitrates, bitrate];
    }
    search();
  }
  
  function toggleVotesRange(range) {
    const isSelected = selectedVotesRanges.some(r => r.label === range.label);
    if (isSelected) {
      selectedVotesRanges = selectedVotesRanges.filter(r => r.label !== range.label);
    } else {
      selectedVotesRanges = [...selectedVotesRanges, range];
    }
    search();
  }
  
  function setSort(field) {
    if (sortBy === field) {
      sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      sortBy = field;
      sortOrder = 'asc';
    }
    search();
  }
  
  async function blockStation(station, e) {
    e.stopPropagation();
    try {
      await api.blockStation(station.uuid, station.name);
      actions.showToast(`${station.name} blockiert`, 'info');
      
      // Aus Liste entfernen
      stations = stations.filter(s => s.uuid !== station.uuid);
      
      // Falls aktueller Sender blockiert wurde, stoppen
      if (appState.currentStation?.uuid === station.uuid) {
        actions.stop();
        appState.currentStation = null;
      }
      
      expandedUuid = null;
    } catch (err) {
      actions.showToast('Blockieren fehlgeschlagen', 'error');
    }
  }
  
  function clearFilters() {
    selectedCountries = [];
    selectedBitrates = [];
    selectedVotesRanges = [];
    showFavsOnly = false;
    searchQuery = '';
    search();
  }
  
  let activeFilterCount = $derived(
    selectedCountries.length + selectedBitrates.length + selectedVotesRanges.length + (showFavsOnly ? 1 : 0)
  );
</script>

<div class="stations-tab">
  <!-- Filter Panel (Links) -->
  <aside class="filter-panel">
    <!-- Search ohne Label -->
    <div class="filter-section">
      <input 
        type="text" 
        class="search-input"
        placeholder="Suchen..." 
        bind:value={searchQuery}
        oninput={handleSearchInput}
      />
    </div>
    
    <!-- Favorites Toggle -->
    <button class="filter-item" onclick={() => { showFavsOnly = !showFavsOnly; search(); }}>
      <HiFiLed color={showFavsOnly ? 'yellow' : 'off'} size="small" />
      <span>FAVORITES ONLY</span>
    </button>
    
    <!-- Countries -->
    <div class="filter-section">
      <button class="filter-header" onclick={() => countriesExpanded = !countriesExpanded}>
        <span class="filter-label">COUNTRY</span>
        <span class="filter-toggle">{countriesExpanded ? '▼' : '▶'}</span>
        {#if selectedCountries.length > 0}
          <span class="filter-badge">{selectedCountries.length}</span>
        {/if}
      </button>
      {#if countriesExpanded}
        <div class="filter-options">
          {#each availableCountries.slice(0, 25) as country}
            <button class="filter-item" onclick={() => toggleCountry(country.code)}>
              <HiFiLed color={selectedCountries.includes(country.code) ? 'yellow' : 'off'} size="small" />
              <span class="filter-item-label">{country.name}</span>
              <span class="filter-item-count">{formatNumber(country.count)}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
    
    <!-- Bitrates -->
    <div class="filter-section">
      <button class="filter-header" onclick={() => bitratesExpanded = !bitratesExpanded}>
        <span class="filter-label">BITRATE</span>
        <span class="filter-toggle">{bitratesExpanded ? '▼' : '▶'}</span>
        {#if selectedBitrates.length > 0}
          <span class="filter-badge">{selectedBitrates.length}</span>
        {/if}
      </button>
      {#if bitratesExpanded}
        <div class="filter-options">
          {#each availableBitrates as bitrate}
            <button class="filter-item" onclick={() => toggleBitrate(bitrate)}>
              <HiFiLed color={selectedBitrates.some(b => b.label === bitrate.label) ? 'yellow' : 'off'} size="small" />
              <span>{bitrate.label}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
    
    <!-- Votes -->
    <div class="filter-section">
      <button class="filter-header" onclick={() => votesExpanded = !votesExpanded}>
        <span class="filter-label">VOTES</span>
        <span class="filter-toggle">{votesExpanded ? '▼' : '▶'}</span>
        {#if selectedVotesRanges.length > 0}
          <span class="filter-badge">{selectedVotesRanges.length}</span>
        {/if}
      </button>
      {#if votesExpanded}
        <div class="filter-options">
          {#each availableVotesRanges as range}
            <button class="filter-item" onclick={() => toggleVotesRange(range)}>
              <HiFiLed color={selectedVotesRanges.some(r => r.label === range.label) ? 'yellow' : 'off'} size="small" />
              <span>{range.label}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
    
    <!-- Clear -->
    {#if activeFilterCount > 0}
      <button class="clear-btn" onclick={clearFilters}>
        CLEAR ({activeFilterCount})
      </button>
    {/if}
  </aside>
  
  <!-- Station List (Rechts) -->
  <main class="station-list-container">
    <!-- Header -->
    <div class="list-header">
      <div class="station-count-display">
        <span class="count-zeros">{String(stations.length).padStart(7, '0').slice(0, -String(stations.length).length)}</span><span class="count-value">{formatNumber(stations.length)}</span>
        <span class="count-label">STATIONS</span>
      </div>
      
      <!-- Sort Buttons -->
      <div class="sort-controls">
        <button class="sort-btn" class:active={sortBy === 'name'} onclick={() => setSort('name')}>NAME</button>
        <button class="sort-btn" class:active={sortBy === 'country'} onclick={() => setSort('country')}>COUNTRY</button>
        <button class="sort-btn" class:active={sortBy === 'bitrate'} onclick={() => setSort('bitrate')}>BITRATE</button>
        <button class="sort-btn" class:active={sortBy === 'votes'} onclick={() => setSort('votes')}>VOTES</button>
      </div>
      
      <!-- Refresh mit Spinner-Platz -->
      <button class="sort-btn refresh-btn" onclick={refreshStations} disabled={isRefreshing}>
        <span class="refresh-spinner-slot">
          {#if isRefreshing}
            <div class="btn-spinner"></div>
          {/if}
        </span>
        <span>REFRESH ALL STATIONS</span>
      </button>
    </div>
    
    <!-- FIXIERTER AKTUELLER SENDER (außerhalb der scrollbaren Liste) -->
    {#if currentPlayingStation && !isLoading}
      {@const isFav = actions.isFavorite(currentPlayingStation.uuid)}
      {@const bitrateVal = typeof currentPlayingStation.bitrate === 'object' ? currentPlayingStation.bitrate?.value : currentPlayingStation.bitrate}
      {@const votesVal = currentPlayingStation.votes ?? 0}
      <div class="current-station-wrapper">
        <div 
          class="station-row playing sticky"
          onclick={() => toggleDetails(currentPlayingStation.uuid)}
        >
          <div class="station-led">
            <HiFiLed color="green" size="small" />
          </div>
          <div class="station-name">{currentPlayingStation.name}</div>
          <div class="station-country">{currentPlayingStation.country || '-'}</div>
          <div class="station-bitrate">{bitrateVal ? formatNumber(bitrateVal) : '-'} kbps</div>
          <div class="station-stats">{formatNumber(votesVal)}</div>
          <button 
            class="station-fav"
            onclick={(e) => toggleFavorite(currentPlayingStation, e)}
          >
            <HiFiLed color={isFav ? 'yellow' : 'off'} size="small" />
          </button>
          <span class="expand-icon">{expandedUuid === currentPlayingStation.uuid ? '▼' : '▶'}</span>
        </div>
        
        <!-- Details aufklappbar -->
        {#if expandedUuid === currentPlayingStation.uuid}
          <div class="station-details">
            <div class="details-content">
              <div class="details-grid">
                {#if currentPlayingStation.homepage}
                  <div class="detail-row">
                    <span class="detail-label">HOMEPAGE</span>
                    <a href={currentPlayingStation.homepage} target="_blank" class="detail-value link">{currentPlayingStation.homepage}</a>
                  </div>
                {/if}
                {#if currentPlayingStation.tags}
                  <div class="detail-row">
                    <span class="detail-label">TAGS</span>
                    <span class="detail-value">{currentPlayingStation.tags}</span>
                  </div>
                {/if}
                {#if currentPlayingStation.language}
                  <div class="detail-row">
                    <span class="detail-label">LANGUAGE</span>
                    <span class="detail-value">{currentPlayingStation.language}</span>
                  </div>
                {/if}
                {#if currentPlayingStation.codec}
                  <div class="detail-row">
                    <span class="detail-label">CODEC</span>
                    <span class="detail-value">{currentPlayingStation.codec}</span>
                  </div>
                {/if}
                {#if currentPlayingStation.votes !== undefined}
                  <div class="detail-row">
                    <span class="detail-label">VOTES</span>
                    <span class="detail-value">{formatNumber(currentPlayingStation.votes)}</span>
                  </div>
                {/if}
                {#if currentPlayingStation.clickcount !== undefined}
                  <div class="detail-row">
                    <span class="detail-label">CLICKS</span>
                    <span class="detail-value">{formatNumber(currentPlayingStation.clickcount)}</span>
                  </div>
                {/if}
                {#if currentPlayingStation.url_resolved}
                  <div class="detail-row">
                    <span class="detail-label">STREAM URL</span>
                    <span class="detail-value url">{currentPlayingStation.url_resolved}</span>
                  </div>
                {/if}
              </div>
              <div class="details-actions">
                <button class="block-btn" onclick={(e) => blockStation(currentPlayingStation, e)}>
                  BLOCK
                </button>
              </div>
            </div>
          </div>
        {/if}
      </div>
    {/if}
    
    <!-- List (scrollbar, ohne aktuellen Sender) -->
    <div class="station-list" onscroll={handleScroll}>
      {#if isLoading}
        <div class="loading">
          <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
        </div>
      {:else if stations.length === 0}
        <div class="empty">
          <div class="empty-display">NO STATIONS FOUND</div>
        </div>
      {:else}
        <!-- RESTLICHE STATIONEN -->
        {#each filteredStations() as station}
          {@const isPlaying = appState.currentStation?.uuid === station.uuid && appState.isPlaying}
          {@const isFav = actions.isFavorite(station.uuid)}
          {@const bitrateVal = typeof station.bitrate === 'object' ? station.bitrate?.value : station.bitrate}
          {@const votesVal = station.votes ?? 0}
          <div 
            class="station-row" 
            class:playing={isPlaying}
            onclick={() => playStation(station)}
          >
            <div class="station-led">
              <HiFiLed color={isPlaying ? 'green' : 'off'} size="small" />
            </div>
            <div class="station-name">{station.name}</div>
            <div class="station-country">{station.country || '-'}</div>
            <div class="station-bitrate">{bitrateVal ? formatNumber(bitrateVal) : '-'} kbps</div>
            <div class="station-stats">{formatNumber(votesVal)}</div>
            <button 
              class="station-fav"
              onclick={(e) => toggleFavorite(station, e)}
            >
              <HiFiLed color={isFav ? 'yellow' : 'off'} size="small" />
            </button>
          </div>
        {/each}
        
        {#if isLoadingMore}
          <div class="loading-more">
            <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
          </div>
        {/if}
      {/if}
    </div>
  </main>
</div>

<style>
  .stations-tab {
    display: flex;
    height: 100%;
    gap: 1px;
    background: var(--hifi-border-dark);
    font-family: 'Roboto', sans-serif;
  }
  
  /* Filter Panel */
  .filter-panel {
    width: 220px;
    background: var(--hifi-bg-panel);
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .filter-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  
  .search-input {
    padding: 10px 14px;
    font-family: 'Roboto', sans-serif;
    font-size: 12px;
    font-weight: 400;
    color: var(--hifi-text-primary);
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    outline: none;
    box-shadow: var(--hifi-shadow-inset);
  }
  
  .search-input:focus {
    box-shadow: var(--hifi-shadow-inset), 0 0 0 2px var(--hifi-accent);
  }
  
  .search-input::placeholder {
    color: var(--hifi-text-secondary);
  }
  
  .filter-header {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: var(--hifi-text-secondary);
    cursor: pointer;
    padding: 4px 0;
    font-family: 'Roboto', sans-serif;
  }
  
  .filter-label {
    font-size: 10px;
    font-weight: 400;
    letter-spacing: 1px;
  }
  
  .filter-toggle {
    font-size: 8px;
  }
  
  .filter-badge {
    margin-left: auto;
    background: transparent;
    color: var(--hifi-accent);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
  }
  
  .filter-options {
    display: flex;
    flex-direction: column;
    max-height: 180px;
    overflow-y: auto;
  }
  
  .filter-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-family: 'Roboto', sans-serif;
    font-size: 11px;
    font-weight: 400;
    cursor: pointer;
    text-align: left;
    border-radius: var(--hifi-border-radius-sm);
  }
  
  .filter-item:hover {
    background: var(--hifi-row-hover);
  }
  
  .filter-item-label {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .filter-item-count {
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }
  
  .clear-btn {
    width: 100%;
    padding: 8px 16px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-primary);
    font-family: 'Roboto', sans-serif;
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    cursor: pointer;
    margin-top: 8px;
  }
  
  .clear-btn:hover {
    background: var(--hifi-bg-secondary);
  }
  
  /* Station List */
  .station-list-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: var(--hifi-bg-secondary);
    min-width: 0;
  }
  
  .list-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 16px;
    background: var(--hifi-bg-panel);
    border-bottom: 1px solid var(--hifi-border-dark);
  }
  
  .station-count-display {
    display: flex;
    align-items: baseline;
    gap: 6px;
    background: var(--hifi-display-bg);
    border: 1px solid var(--hifi-display-border);
    border-radius: var(--hifi-border-radius-sm);
    padding: 6px 12px;
    min-width: 140px;
  }
  
  .count-zeros {
    font-family: var(--hifi-font-display);
    font-size: 14px;
    color: var(--hifi-display-text);
    opacity: 0.2;
  }
  
  .count-value {
    font-family: var(--hifi-font-display);
    font-size: 14px;
    color: var(--hifi-display-text);
    text-shadow: 0 0 6px var(--hifi-display-text);
  }
  
  .count-label {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    color: var(--hifi-display-text);
    opacity: 0.6;
  }
  
  .sort-controls {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
  }
  
  .sort-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    cursor: pointer;
    box-shadow: var(--hifi-shadow-button);
  }
  
  .sort-btn:hover:not(:disabled) {
    box-shadow: 2px 2px 4px var(--hifi-shadow-dark), -2px -2px 4px var(--hifi-shadow-light);
  }
  
  .sort-btn:active:not(:disabled) {
    box-shadow: var(--hifi-shadow-inset);
  }
  
  /* Aktive Sort-Buttons: Blau mit leichtem Hover-Effekt */
  .sort-btn.active {
    background: var(--hifi-accent);
    color: white;
    box-shadow: 2px 2px 4px var(--hifi-shadow-dark), -2px -2px 4px var(--hifi-shadow-light);
  }
  
  .sort-btn:disabled {
    opacity: 0.7;
    cursor: wait;
  }
  
  .refresh-btn {
    margin-left: auto;
  }
  
  .refresh-spinner-slot {
    width: 14px;
    height: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .btn-spinner {
    width: 12px;
    height: 12px;
    border: 2px solid var(--hifi-text-secondary);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .station-list {
    flex: 1;
    overflow-y: auto;
  }
  
  .station-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    cursor: pointer;
    border-bottom: 1px solid var(--hifi-border-dark);
    transition: background 0.1s ease;
  }
  
  .station-row:hover {
    background: var(--hifi-row-hover);
  }
  
  .station-row.playing {
    background: var(--hifi-row-selected);
  }
  
  .station-led {
    flex-shrink: 0;
  }
  
  /* Sendernamen: Roboto */
  .station-name {
    flex: 1;
    font-family: 'Roboto', sans-serif;
    font-size: 14px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .station-country {
    width: 224px;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    text-align: left;
    padding: 0 16px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .station-bitrate {
    width: 90px;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    text-align: right;
    padding-right: 8px;
  }
  
  .station-stats {
    width: 70px;
    font-family: 'Roboto', sans-serif;
    font-size: 10px;
    color: var(--hifi-text-secondary);
    text-align: right;
    padding-right: 8px;
  }
  
  .station-fav {
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px;
  }
  
  .loading, .empty {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 60px;
  }
  
  .empty-display {
    background: var(--hifi-display-bg);
    border: 1px solid var(--hifi-display-border);
    border-radius: var(--hifi-border-radius-sm);
    padding: 16px 24px;
    font-family: var(--hifi-font-display);
    color: var(--hifi-display-text);
    text-shadow: 0 0 8px var(--hifi-display-text);
  }
  
  .loading-more {
    display: flex;
    justify-content: center;
    padding: 20px;
  }
  
  /* Aktueller Sender - fixiert oberhalb der Liste */
  .current-station-wrapper {
    flex-shrink: 0;
    background: var(--hifi-bg-panel);
    border-bottom: 2px solid var(--hifi-accent);
  }
  
  .station-row.sticky {
    background: var(--hifi-row-selected);
    border-bottom: none;
  }
  
  .station-row.sticky:hover {
    background: var(--hifi-row-selected);
  }
  
  .expand-icon {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    margin-left: 8px;
    width: 16px;
  }
  
  /* Station Details */
  .station-details {
    background: var(--hifi-bg-tertiary);
    padding: 12px 16px;
    border-top: 1px solid var(--hifi-border-dark);
  }
  
  .details-content {
    display: flex;
    gap: 16px;
  }
  
  .details-grid {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
  }
  
  .details-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
  }
  
  .block-btn {
    padding: 8px 16px;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-led-red);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    cursor: pointer;
    box-shadow: var(--hifi-shadow-button);
  }
  
  .block-btn:hover {
    background: var(--hifi-led-red);
    color: white;
  }
  
  .detail-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }
  
  .detail-label {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 400;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    min-width: 80px;
    flex-shrink: 0;
  }
  
  .detail-value {
    font-family: 'Roboto', sans-serif;
    font-size: 12px;
    color: var(--hifi-text-primary);
    word-break: break-word;
  }
  
  .detail-value.link {
    color: var(--hifi-accent);
    text-decoration: none;
  }
  
  .detail-value.link:hover {
    text-decoration: underline;
  }
  
  .detail-value.url {
    font-family: var(--hifi-font-display);
    font-size: 10px;
    color: var(--hifi-text-secondary);
    word-break: break-all;
  }
</style>
