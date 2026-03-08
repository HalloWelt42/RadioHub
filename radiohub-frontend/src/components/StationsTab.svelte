<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import FilterOverlay from './FilterOverlay.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  
  // 1000er-Trenner für Zahlen
  function formatNumber(num) {
    return num?.toLocaleString('de-DE') ?? '-';
  }

  // k-Format: 1234 -> "1.2k", 12345 -> "12.3k", 999 -> "999"
  function formatK(num) {
    if (num == null) return '-';
    if (num < 1000) return String(num);
    const k = num / 1000;
    return k >= 100 ? Math.round(k) + 'k' : k.toFixed(1).replace('.', ',') + 'k';
  }

  // Laendernamen-Mapping (Korrektur der radio-browser.info Namen)
  const COUNTRY_NAMES = {
    'The United States Of America': 'USA',
    'United States of America': 'USA',
    'The Russian Federation': 'Russland',
    'Russian Federation': 'Russland',
    'Germany': 'Deutschland',
    'France': 'Frankreich',
    'Australia': 'Australien',
    'Austria': 'Oesterreich',
    'Switzerland': 'Schweiz',
    'Netherlands': 'Niederlande',
    'The Netherlands': 'Niederlande',
    'Belgium': 'Belgien',
    'Brazil': 'Brasilien',
    'Spain': 'Spanien',
    'Italy': 'Italien',
    'Japan': 'Japan',
    'China': 'China',
    'India': 'Indien',
    'Canada': 'Kanada',
    'Mexico': 'Mexiko',
    'Poland': 'Polen',
    'Sweden': 'Schweden',
    'Norway': 'Norwegen',
    'Denmark': 'Daenemark',
    'Finland': 'Finnland',
    'Czech Republic': 'Tschechien',
    'Czechia': 'Tschechien',
    'Hungary': 'Ungarn',
    'Romania': 'Rumaenien',
    'Turkey': 'Tuerkei',
    'Greece': 'Griechenland',
    'Portugal': 'Portugal',
    'Argentina': 'Argentinien',
    'Colombia': 'Kolumbien',
    'Chile': 'Chile',
    'Peru': 'Peru',
    'Indonesia': 'Indonesien',
    'South Korea': 'Suedkorea',
    'Thailand': 'Thailand',
    'Ukraine': 'Ukraine',
    'Ireland': 'Irland',
    'New Zealand': 'Neuseeland',
    'South Africa': 'Suedafrika',
    'Croatia': 'Kroatien',
    'Serbia': 'Serbien',
    'Bulgaria': 'Bulgarien',
    'Slovakia': 'Slowakei',
    'Slovenia': 'Slowenien',
    'Lithuania': 'Litauen',
    'Latvia': 'Lettland',
    'Estonia': 'Estland',
    'Luxembourg': 'Luxemburg',
    'United Kingdom': 'Grossbritannien',
    'The United Kingdom Of Great Britain And Northern Ireland': 'Grossbritannien',
  };

  function translateCountry(name) {
    return COUNTRY_NAMES[name] || name;
  }
  
  let searchQuery = $state('');
  let stations = $state([]);
  let isLoading = $state(false);
  let isLoadingMore = $state(false);
  let isRefreshing = $state(false);

  // Suchhistorie (localStorage)
  let searchHistory = $state(JSON.parse(localStorage.getItem('radiohub_search_history') || '[]'));
  let showSearchHistory = $state(false);
  
  // Aktuell spielender Sender
  let currentPlayingStation = $derived(appState.currentStation);

  // Ausgewaehlter Sender (Details sichtbar)
  let selectedUuid = $state(null);

  // selectedUuid folgt dem aktuell spielenden Sender (z.B. bei Prev/Next Navigation)
  $effect(() => {
    const playingUuid = appState.currentStation?.uuid ?? null;
    if (playingUuid) {
      selectedUuid = playingUuid;
    }
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
  let showFilterOverlay = $state(false);
  
  // Sortierung
  let sortBy = $state('name');
  let sortOrder = $state('asc');
  
  // Pagination
  let offset = $state(0);
  let limit = 50;
  let hasMore = $state(true);
  
  // Aktive Filter-Chips (abgeleitete Liste aller aktiven Filter)
  let activeChips = $derived(() => {
    const chips = [];
    for (const code of selectedCountries) {
      const c = availableCountries.find(x => x.code === code);
      chips.push({ type: 'country', code, label: code });
    }
    for (const b of selectedBitrates) {
      chips.push({ type: 'bitrate', label: b.label, ref: b });
    }
    for (const v of selectedVotesRanges) {
      chips.push({ type: 'votes', label: v.label, ref: v });
    }
    return chips;
  });
  
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
  
  // Votes-Ranges: 6 Bereiche, k-Format
  const VOTES_RANGES = [
    { label: '0', min: 0, max: 0 },
    { label: '1 - 100', min: 1, max: 100 },
    { label: '101 - 1k', min: 101, max: 1000 },
    { label: '1k - 10k', min: 1001, max: 10000 },
    { label: '10k - 100k', min: 10001, max: 100000 },
    { label: '> 100k', min: 100001, max: 999999999 }
  ];

  // Bitrate-Bereiche: 6 Stufen
  const BITRATE_RANGES = [
    { label: '< 64', min: 0, max: 64 },
    { label: '64 - 128', min: 64, max: 128 },
    { label: '128 - 192', min: 128, max: 192 },
    { label: '192 - 256', min: 192, max: 256 },
    { label: '256 - 320', min: 256, max: 320 },
    { label: '> 320', min: 320, max: 9999 }
  ];
  
  async function loadFilters() {
    try {
      const [filters, config] = await Promise.all([
        api.getFilters(),
        api.getConfig()
      ]);

      let allCountries = filters.countries || [];

      // Sidebar-Config: nur konfigurierte Laender anzeigen
      if (config.sidebar_countries) {
        try {
          const visible = JSON.parse(config.sidebar_countries);
          availableCountries = allCountries.filter(c => visible.includes(c.code));
        } catch {
          availableCountries = allCountries.slice(0, 10);
        }
      } else {
        // Default: Top 10
        availableCountries = allCountries.slice(0, 10);
      }

      // Feste Bereiche aus Konstanten
      availableBitrates = BITRATE_RANGES;
      availableVotesRanges = VOTES_RANGES;

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
      if (searchQuery && searchQuery.length >= 2) saveSearchHistory(searchQuery);
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

  // Einzelne Station proben bei Play -- echte Werte ermitteln und in Liste mergen
  let probeTimer;
  async function probeOnPlay(station) {
    try {
      await api.verifyBitrate([station.uuid]);
    } catch { return; }

    // Nach Verzoegerung erkannten Wert abholen
    clearTimeout(probeTimer);
    probeTimer = setTimeout(async () => {
      try {
        const result = await api.getDetectedBitrates([station.uuid]);
        const det = (result.bitrates || {})[station.uuid];
        if (!det || det.bitrate <= 0) return;
        stations = stations.map(s => {
          if (s.uuid !== station.uuid) return s;
          const updates = { bitrate: det.bitrate };
          if (det.codec) updates.codec = det.codec.toUpperCase();
          return { ...s, ...updates };
        });
      } catch { /* ignore */ }
    }, 12000);
  }
  
  async function refreshStations() {
    isRefreshing = true;
    try {
      // Filter/Sortierung zuruecksetzen
      searchQuery = '';
      selectedCountries = [];
      selectedBitrates = [];
      selectedVotesRanges = [];
      showFavsOnly = false;
      sortBy = 'name';
      sortOrder = 'asc';

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
    showSearchHistory = false;
    if (searchQuery.length >= 2 || searchQuery.length === 0) {
      searchTimeout = setTimeout(() => search(), 300);
    }
  }

  function saveSearchHistory(query) {
    if (!query || query.length < 2) return;
    searchHistory = [query, ...searchHistory.filter(h => h !== query)].slice(0, 10);
    localStorage.setItem('radiohub_search_history', JSON.stringify(searchHistory));
  }

  function selectFromHistory(query) {
    searchQuery = query;
    showSearchHistory = false;
    search();
  }

  function clearSearchHistory() {
    searchHistory = [];
    showSearchHistory = false;
    localStorage.removeItem('radiohub_search_history');
  }
  
  function handleScroll(e) {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    if (scrollHeight - scrollTop - clientHeight < 200 && hasMore && !isLoadingMore && !isLoading) {
      search(true);
    }
  }
  
  function selectStation(station) {
    // Klick spielt ab und klappt Details auf, zweiter Klick klappt zu
    if (selectedUuid === station.uuid) {
      selectedUuid = null;
    } else {
      selectedUuid = station.uuid;
      actions.playStation(station);
      probeOnPlay(station);
    }
  }
  
  function toggleFavorite(station, e) {
    e.stopPropagation();
    actions.toggleFavorite(station);
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
      
    } catch (err) {
      actions.showToast('Blockieren fehlgeschlagen', 'error');
    }
  }
  
  function removeChip(chip) {
    if (chip.type === 'country') {
      selectedCountries = selectedCountries.filter(c => c !== chip.code);
    } else if (chip.type === 'bitrate') {
      selectedBitrates = selectedBitrates.filter(b => b.label !== chip.ref.label);
    } else if (chip.type === 'votes') {
      selectedVotesRanges = selectedVotesRanges.filter(r => r.label !== chip.ref.label);
    }
    search();
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
    <!-- Action Row: Favs + Clear + Filter -->
    <div class="action-row">
      <button class="action-btn" onclick={() => { showFavsOnly = !showFavsOnly; search(); }} title={showFavsOnly ? 'Alle Sender anzeigen' : 'Nur Favoriten anzeigen'}>
        <HiFiLed color={showFavsOnly ? 'yellow' : 'off'} size="small" />
        <span>FAVORITEN</span>
      </button>
      {#if activeFilterCount > 0}
        <button class="action-btn square" onclick={clearFilters} title="Alle Filter zuruecksetzen">&#10005;</button>
      {/if}
      <button class="action-btn square" onclick={() => showFilterOverlay = true} title="Sender-Filter oeffnen">
        <i class="fa-solid fa-sliders"></i>
      </button>
    </div>

    <!-- Active Filter Chips -->
    {#if activeChips().length > 0}
      <div class="sidebar-divider"></div>
      <div class="active-chips">
        {#each activeChips() as chip}
          <button class="filter-chip" onclick={() => removeChip(chip)} title="Filter entfernen: {chip.label}">{chip.label}</button>
        {/each}
      </div>
    {/if}

    <div class="sidebar-divider"></div>

    <!-- Countries: nimmt Restplatz, scrollt intern -->
    <div class="section-flex">
      <div class="section-header">
        <span class="section-label">COUNTRY</span>
        {#if selectedCountries.length > 0}
          <span class="section-count">{selectedCountries.length}</span>
        {/if}
      </div>
      <div class="filter-list">
        {#each availableCountries.slice(0, 25) as country}
          {@const isSelected = selectedCountries.includes(country.code)}
          {@const hasSel = selectedCountries.length > 0}
          <button class="filter-item" class:selected={isSelected} class:dimmed={hasSel && !isSelected} onclick={() => toggleCountry(country.code)} title={isSelected ? 'Filter entfernen: ' + translateCountry(country.name) : 'Filtern nach: ' + translateCountry(country.name)}>
            <HiFiLed color={isSelected ? 'yellow' : 'off'} size="small" />
            <span class="country-code">{country.code}</span>
            <span class="filter-item-label">{translateCountry(country.name)}</span>
            <span class="filter-item-count">{formatNumber(country.count)}</span>
          </button>
        {/each}
      </div>
    </div>

    <div class="sidebar-divider"></div>

    <!-- Bitrate: 2-spaltig -->
    <div class="section-fixed">
      <div class="section-header">
        <span class="section-label">BITRATE</span>
        {#if selectedBitrates.length > 0}
          <span class="section-count">{selectedBitrates.length}</span>
        {/if}
      </div>
      <div class="filter-grid">
        {#each availableBitrates as bitrate}
          {@const isSelected = selectedBitrates.some(b => b.label === bitrate.label)}
          {@const hasSel = selectedBitrates.length > 0}
          <button class="filter-item" class:selected={isSelected} class:dimmed={hasSel && !isSelected} onclick={() => toggleBitrate(bitrate)} title={isSelected ? 'Filter entfernen: ' + bitrate.label + ' kbps' : 'Filtern nach: ' + bitrate.label + ' kbps'}>
            <HiFiLed color={isSelected ? 'yellow' : 'off'} size="small" />
            <span class="grid-label">{bitrate.label}</span>
          </button>
        {/each}
      </div>
    </div>

    <div class="sidebar-divider"></div>

    <!-- Votes: 2-spaltig -->
    <div class="section-fixed">
      <div class="section-header">
        <span class="section-label">VOTES</span>
        {#if selectedVotesRanges.length > 0}
          <span class="section-count">{selectedVotesRanges.length}</span>
        {/if}
      </div>
      <div class="filter-grid">
        {#each availableVotesRanges as range}
          {@const isSelected = selectedVotesRanges.some(r => r.label === range.label)}
          {@const hasSel = selectedVotesRanges.length > 0}
          <button class="filter-item" class:selected={isSelected} class:dimmed={hasSel && !isSelected} onclick={() => toggleVotesRange(range)} title={isSelected ? 'Filter entfernen: ' + range.label + ' Votes' : 'Filtern nach: ' + range.label + ' Votes'}>
            <HiFiLed color={isSelected ? 'yellow' : 'off'} size="small" />
            <span class="grid-label">{range.label}</span>
          </button>
        {/each}
      </div>
    </div>
  </aside>
  
  <!-- Station List (Rechts) -->
  <main class="station-list-container">
    <!-- Header mit Suche -->
    <div class="list-header">
      <div class="station-count-display">
        <span class="count-zeros">{'0'.repeat(Math.max(0, 7 - String(stations.length).length))}</span><span class="count-value">{formatNumber(stations.length)}</span>
        <span class="count-label">STATIONS</span>
      </div>

      <!-- Suchfeld -->
      <div class="search-bar">
        <i class="fa-solid fa-magnifying-glass search-icon"></i>
        <input
          type="text"
          class="search-input"
          placeholder="Sender suchen..."
          bind:value={searchQuery}
          oninput={handleSearchInput}
          onfocus={() => { if (searchHistory.length > 0 && !searchQuery) showSearchHistory = true; }}
          onblur={() => { setTimeout(() => showSearchHistory = false, 200); }}
        />
        {#if searchQuery}
          <button class="search-clear" onclick={() => { searchQuery = ''; search(); }}>&#10005;</button>
        {/if}
        {#if showSearchHistory && searchHistory.length > 0}
          <div class="search-history">
            {#each searchHistory as item}
              <button class="history-item" onmousedown={() => selectFromHistory(item)}>
                <i class="fa-solid fa-clock-rotate-left"></i>
                <span>{item}</span>
              </button>
            {/each}
            <button class="history-clear" onmousedown={clearSearchHistory}>
              Historie loeschen
            </button>
          </div>
        {/if}
      </div>

      <!-- Refresh mit Spinner-Platz -->
      <button class="refresh-btn" onclick={refreshStations} disabled={isRefreshing} title={isRefreshing ? 'Senderliste wird aktualisiert...' : 'Komplette Senderliste vom Server neu laden'}>
        <span class="refresh-spinner-slot">
          {#if isRefreshing}
            <div class="btn-spinner"></div>
          {/if}
        </span>
        <span>REFRESH</span>
      </button>
    </div>

    <!-- Liste (scrollbar, alle Sender) -->
    <div class="station-list" onscroll={handleScroll}>
      <!-- Spaltenkoepfe (sticky) -->
      <div class="column-headers">
        <div class="col-led"></div>
        <div class="col-name" class:col-active={sortBy === 'name'} onclick={() => setSort('name')}>NAME {#if sortBy === 'name'}<i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>{/if}</div>
        <div class="col-country" class:col-active={sortBy === 'country'} onclick={() => setSort('country')}>COUNTRY {#if sortBy === 'country'}<i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>{/if}</div>
        <div class="col-bitrate" class:col-active={sortBy === 'bitrate'} onclick={() => setSort('bitrate')}>KBPS / CODEC {#if sortBy === 'bitrate'}<i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>{/if}</div>
        <div class="col-votes" class:col-active={sortBy === 'votes'} onclick={() => setSort('votes')}>VOTES / ZUHOERER {#if sortBy === 'votes'}<i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>{/if}</div>
        <div class="col-fav"></div>
      </div>

      {#if isLoading}
        <div class="loading">
          <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
        </div>
      {:else if stations.length === 0}
        <div class="empty">
          <div class="empty-display">NO STATIONS FOUND</div>
        </div>
      {:else}
        {#each stations as station}
          {@const isPlaying = appState.currentStation?.uuid === station.uuid}
          {@const isSelected = selectedUuid === station.uuid}
          {@const isExpanded = isPlaying || isSelected}
          {@const isFav = actions.isFavorite(station.uuid)}
          {@const bitrateVal = typeof station.bitrate === 'object' ? station.bitrate?.value : station.bitrate}
          {@const votesVal = station.votes ?? 0}

          <div class="station-wrapper" class:playing={isPlaying} class:selected={isSelected && !isPlaying}>
            <div
              class="station-row"
              class:playing={isPlaying}
              class:selected={isSelected && !isPlaying}
              onclick={() => selectStation(station)}
            >
              <div class="station-led">
                <HiFiLed color={isPlaying ? 'blue' : isSelected ? 'blue' : 'off'} size="small" />
              </div>
              <div class="station-name">{station.name}</div>
              <div class="station-country">{translateCountry(station.country) || '-'}</div>
              <div class="station-bitrate">{bitrateVal ? formatNumber(bitrateVal) : '--'}{station.codec ? ' / ' + station.codec : ''}</div>
              <div class="station-stats">{formatNumber(votesVal)}{station.clickcount ? ' / ' + formatK(station.clickcount) : ''}</div>
              <button
                class="station-fav"
                onclick={(e) => toggleFavorite(station, e)}
                title={isFav ? 'Aus Favoriten entfernen' : 'Zu Favoriten hinzufuegen'}
              >
                <HiFiLed color={isFav ? 'yellow' : 'off'} size="small" />
              </button>
            </div>

            {#if isExpanded}
              <div class="station-details">
                <div class="details-content">
                  <div class="details-grid">
                    {#if station.homepage}
                      <div class="detail-row">
                        <span class="detail-label">HOMEPAGE</span>
                        <a href={station.homepage} target="_blank" class="detail-value link">{station.homepage}</a>
                      </div>
                    {/if}
                    {#if station.tags}
                      <div class="detail-row">
                        <span class="detail-label">TAGS</span>
                        <span class="detail-value">{station.tags}</span>
                      </div>
                    {/if}
                    {#if station.language}
                      <div class="detail-row">
                        <span class="detail-label">LANGUAGE</span>
                        <span class="detail-value">{station.language}</span>
                      </div>
                    {/if}
                    {#if station.codec}
                      <div class="detail-row">
                        <span class="detail-label">CODEC</span>
                        <span class="detail-value">{station.codec}</span>
                      </div>
                    {/if}
                    {#if station.votes !== undefined}
                      <div class="detail-row">
                        <span class="detail-label">VOTES</span>
                        <span class="detail-value">{formatNumber(station.votes)}</span>
                      </div>
                    {/if}
                    {#if station.clickcount !== undefined}
                      <div class="detail-row">
                        <span class="detail-label">CLICKS</span>
                        <span class="detail-value">{formatNumber(station.clickcount)}</span>
                      </div>
                    {/if}
                    {#if station.url_resolved}
                      <div class="detail-row">
                        <span class="detail-label">STREAM URL</span>
                        <span class="detail-value url">{station.url_resolved}</span>
                      </div>
                    {/if}
                  </div>
                  <div class="details-actions">
                    <button class="block-btn" onclick={(e) => blockStation(station, e)} title="Sender dauerhaft aus der Liste entfernen">
                      BLOCK
                    </button>
                  </div>
                </div>
              </div>
            {/if}
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

  {#if showFilterOverlay}
    <FilterOverlay
      open={true}
      onclose={() => { showFilterOverlay = false; loadFilters(); }}
    />
  {/if}
</div>

<style>
  .stations-tab {
    display: flex;
    height: 100%;
    gap: 1px;
    background: var(--hifi-border-dark);
    font-family: 'Barlow', sans-serif;
  }
  
  /* Filter Panel */
  .filter-panel {
    width: 224px;
    background: var(--hifi-bg-panel);
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    overflow: hidden;
  }

  /* Action Row */
  .action-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .action-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 34px;
    padding: 0;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    cursor: pointer;
    box-shadow: var(--hifi-shadow-button);
  }

  .action-btn:hover {
    background: var(--hifi-bg-secondary);
  }

  .action-btn.square {
    flex: 0 0 34px;
    width: 34px;
    height: 34px;
    padding: 0;
    font-size: 14px;
    color: var(--hifi-accent);
  }

  .action-btn.square i {
    font-size: 12px;
  }

  /* Divider */
  .sidebar-divider {
    height: 1px;
    background: var(--hifi-border-dark);
  }

  /* Active Filter Chips */
  .active-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .filter-chip {
    display: inline-flex;
    align-items: center;
    padding: 3px 8px;
    background: rgba(74,144,217,0.15);
    border: 1px solid rgba(74,144,217,0.3);
    border-radius: 4px;
    font-size: 10px;
    color: var(--hifi-accent);
    cursor: pointer;
    font-family: var(--hifi-font-values);
    font-weight: 600;
    letter-spacing: 1px;
  }

  .filter-chip:hover {
    background: rgba(74,144,217,0.25);
  }

  /* Section Headers */
  .section-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 0;
  }

  .section-label {
    font-size: 10px;
    font-weight: 400;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
  }

  .section-count {
    margin-left: auto;
    font-family: var(--hifi-font-values);
    font-size: 10px;
    color: var(--hifi-accent);
    font-weight: 700;
  }

  /* Country: flex-Restplatz, scrollt intern */
  .section-flex {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .filter-list {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    margin-top: 4px;
  }

  /* Bitrate/Votes: feste Hoehe */
  .section-fixed {
    flex-shrink: 0;
  }

  /* 2-spaltig Grid fuer Bitrate/Votes */
  .filter-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2px;
    margin-top: 4px;
  }

  .filter-grid .filter-item {
    padding: 4px 6px;
    gap: 6px;
  }

  .grid-label {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 500;
  }

  .filter-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 6px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 400;
    cursor: pointer;
    text-align: left;
    border-radius: var(--hifi-border-radius-sm);
  }

  .filter-item:hover {
    background: var(--hifi-row-hover);
  }

  /* Ausgewaehlt: blau */
  .filter-item.selected {
    color: var(--hifi-accent);
  }

  .filter-item.selected .country-code,
  .filter-item.selected .filter-item-count {
    color: var(--hifi-accent);
  }

  /* Nicht ausgewaehlt wenn Gruppe aktiv: hellgrau/gedimmt */
  .filter-item.dimmed {
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .filter-item.dimmed .country-code,
  .filter-item.dimmed .filter-item-count {
    color: var(--hifi-text-secondary);
  }

  /* Country Code */
  .country-code {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    width: 22px;
    text-align: center;
    letter-spacing: 0.5px;
  }

  .filter-item-label {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .filter-item-count {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 500;
    color: var(--hifi-text-secondary);
    text-align: right;
    min-width: 46px;
    letter-spacing: 0.3px;
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
    padding: 12px 16px;
    background: var(--hifi-bg-panel);
    border-bottom: 1px solid var(--hifi-border-dark);
  }
  
  .station-count-display {
    display: flex;
    align-items: center;
    gap: 0;
    background: var(--hifi-display-bg);
    border: 1px solid var(--hifi-display-border);
    border-radius: var(--hifi-border-radius-sm);
    padding: 0 10px;
    height: 34px;
    box-sizing: border-box;
    width: 160px;
    flex-shrink: 0;
  }

  .count-zeros {
    font-family: var(--hifi-font-values);
    font-size: 13px;
    font-weight: 700;
    color: var(--hifi-display-text);
    opacity: 0.15;
  }

  .count-value {
    font-family: var(--hifi-font-values);
    font-size: 13px;
    font-weight: 700;
    color: var(--hifi-display-text);
    text-shadow: 0 0 6px var(--hifi-display-text);
  }

  .count-label {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-display-text);
    opacity: 0.5;
    margin-left: 8px;
  }
  
  .refresh-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 34px;
    padding: 0 14px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    cursor: pointer;
    box-shadow: var(--hifi-shadow-button);
    flex-shrink: 0;
  }

  .refresh-btn:hover:not(:disabled) {
    box-shadow: 2px 2px 4px var(--hifi-shadow-dark), -2px -2px 4px var(--hifi-shadow-light);
  }

  .refresh-btn:disabled {
    opacity: 0.7;
    cursor: wait;
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
  
  /* Suchleiste (im Header, gleiche Hoehe wie Stations-Display) */
  .search-bar {
    display: flex;
    align-items: center;
    flex: 1;
    height: 34px;
    background: var(--hifi-display-bg);
    border: 1px solid var(--hifi-display-border);
    border-radius: var(--hifi-border-radius-sm);
    box-sizing: border-box;
    padding: 0 10px;
    gap: 8px;
    position: relative;
  }

  .search-bar:focus-within {
    border-color: var(--hifi-accent);
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
    font-family: var(--hifi-font-values);
    font-size: 13px;
    font-weight: 700;
    color: var(--hifi-display-text);
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

  .station-list {
    flex: 1;
    overflow-y: auto;
  }

  /* Spaltenkoepfe */
  .column-headers {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 16px;
    background: var(--hifi-bg-tertiary);
    border-bottom: 1px solid var(--hifi-border-dark);
    position: sticky;
    top: 0;
    z-index: 20;
    font-family: var(--hifi-font-segment);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }

  .column-headers > div {
    cursor: pointer;
  }

  .column-headers > div:hover {
    color: var(--hifi-text-primary);
  }

  .col-active {
    color: var(--hifi-accent) !important;
  }

  .col-led {
    width: 12px;
    flex-shrink: 0;
  }

  .col-name {
    flex: 1;
  }

  .col-country {
    width: 224px;
    padding: 0 16px;
  }

  .col-bitrate {
    width: 120px;
    text-align: right;
    padding-right: 8px;
  }

  .col-votes {
    width: 140px;
    text-align: right;
    padding-right: 8px;
  }

  .col-fav {
    width: 20px;
    cursor: default !important;
  }

  .station-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 16px;
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
  
  /* Sendernamen: Barlow */
  .station-name {
    flex: 1;
    font-family: 'Barlow', sans-serif;
    font-size: 18px;
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
    width: 120px;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    text-align: right;
    padding-right: 8px;
  }

  .station-stats {
    width: 140px;
    font-family: 'Barlow', sans-serif;
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
  
  /* Ausgewaehlter Sender: blauer Schein */
  .station-wrapper.selected {
    background: var(--hifi-bg-panel);
    border-bottom: 2px solid rgba(51, 153, 255, 0.2);
  }

  .station-row.selected {
    background: rgba(51, 153, 255, 0.08);
    box-shadow: inset 0 0 20px rgba(51, 153, 255, 0.06);
  }

  .station-row.selected:hover {
    background: rgba(51, 153, 255, 0.12);
  }

  .station-row.selected .station-name {
    color: var(--hifi-display-blue);
  }

  /* Spielender Sender: Wrapper-Styling, komplett sticky unterhalb Spaltenkoepfe */
  .station-wrapper.playing {
    position: sticky;
    top: 28px;
    bottom: 0;
    z-index: 10;
    background: var(--hifi-bg-panel);
    border-bottom: 2px solid rgba(51, 153, 255, 0.3);
  }

  .station-wrapper.playing .station-row {
    background: var(--hifi-bg-panel);
    border-bottom: none;
  }

  .station-wrapper.playing .station-row:hover {
    background: var(--hifi-bg-panel);
  }

  .station-wrapper.playing .station-name {
    color: #fff;
    font-weight: 600;
  }
  
  /* Station Details (kompakt) */
  .station-details {
    background: var(--hifi-bg-tertiary);
    padding: 6px 16px 6px 40px;
    border-top: 1px solid var(--hifi-border-dark);
  }

  .details-content {
    display: flex;
    gap: 12px;
  }

  .details-grid {
    display: flex;
    flex-direction: column;
    gap: 3px;
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
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
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
    font-family: 'Barlow', sans-serif;
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

  /* Sort-Icons in Spaltenkoepfen */
  .column-headers i {
    margin-left: 4px;
    font-size: 10px;
  }

  /* Suchhistorie Dropdown */
  .search-history {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-display-border);
    border-top: none;
    border-radius: 0 0 var(--hifi-border-radius-sm) var(--hifi-border-radius-sm);
    z-index: 30;
    max-height: 200px;
    overflow-y: auto;
  }

  .history-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 6px 10px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-values);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    cursor: pointer;
    text-align: left;
  }

  .history-item:hover {
    background: var(--hifi-row-hover);
  }

  .history-item i {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .history-clear {
    display: block;
    width: 100%;
    padding: 6px 10px;
    background: none;
    border: none;
    border-top: 1px solid var(--hifi-border-dark);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    cursor: pointer;
    text-align: center;
    text-transform: uppercase;
  }

  .history-clear:hover {
    color: var(--hifi-text-primary);
    background: var(--hifi-row-hover);
  }
</style>
