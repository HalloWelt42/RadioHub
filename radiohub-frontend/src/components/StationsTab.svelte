<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  import * as sfx from '../lib/uiSounds.js';
  import { translateCountry } from '../lib/countryNames.js';
  import { formatNumber, formatK } from '../lib/formatters.js';
  import { t } from '../lib/i18n.svelte.js';


  let searchQuery = $state('');
  let stations = $state([]);
  let isLoading = $state(false);
  let isLoadingMore = $state(false);
  let isRefreshing = $state(false);

  // Suchhistorie (localStorage)
  let searchHistory = $state(JSON.parse(localStorage.getItem('radiohub_search_history') || '[]'));
  let showSearchHistory = $state(false);
  
  // Ausgewählter Sender (Details sichtbar)
  let selectedUuid = $state(null);

  // Auto-Scroll: nach 90s Inaktivität zur spielenden Station scrollen
  let _inactivityTimer = null;
  const INACTIVITY_SCROLL_DELAY = 90_000; // 90 Sekunden

  function _resetInactivityTimer() {
    clearTimeout(_inactivityTimer);
    _inactivityTimer = setTimeout(_scrollToPlayingStation, INACTIVITY_SCROLL_DELAY);
  }

  function _scrollToPlayingStation() {
    if (appState.activeTab !== 'radio') return;
    if (!appState.currentStation) return;
    const playingEl = document.querySelector('.station-wrapper.playing');
    if (playingEl) {
      playingEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
      // Auch selectedUuid auf spielenden Sender setzen
      selectedUuid = appState.currentStation.uuid;
    }
  }

  // Inaktivitäts-Timer bei User-Interaktion zurücksetzen
  function _handleUserActivity() {
    _resetInactivityTimer();
  }

  // selectedUuid folgt dem aktuell spielenden Sender nur bei externer Navigation
  // (z.B. Prev/Next Buttons), nicht bei eigenem selectStation()-Klick
  let _lastPlayTriggeredUuid = null;
  $effect(() => {
    const playingUuid = appState.currentStation?.uuid ?? null;
    if (playingUuid && playingUuid !== _lastPlayTriggeredUuid) {
      // Externer Senderwechsel (Prev/Next) -> selectedUuid nachziehen
      selectedUuid = playingUuid;
    }
    if (!playingUuid) {
      _lastPlayTriggeredUuid = null;
    }
  });

  // Filter-Daten
  let availableCountries = $state([]);
  let availableBitrates = $state([]);
  let availableVotesRanges = $state([]);
  
  // Sichtbare Länder (in Setup konfiguriert, in Config persistiert)
  let visibleCountries = $state([]);

  // Setup-Suchfilter (excludedLanguages, excludedTags, minVotes) - aus Config geladen
  let excludedLanguages = $state([]);
  let excludedTags = $state([]);
  let filterMinVotes = $state(0);

  // Aktive Filter (in Sidebar angeklickt = Suchfilter)
  let selectedCountries = $state([]);
  let selectedBitrates = $state([]);
  let selectedVotesRanges = $state([]);
  let showFavsOnly = $state(localStorage.getItem('radiohub_favs_only') === 'true');

  // Kategorien
  let categories = $state([]);
  let selectedCategories = $state([]);
  let categoryAssignments = $state({}); // Map<uuid, [categoryId, ...]>

  // Sortierung
  let sortBy = $state('name');
  let sortOrder = $state('asc');

  // Ad-Status Map für Hover-Anzeige
  let adStatusMap = $state({});

  // visibleCountries persistieren (Backend-Config)
  let _countriesInitialized = false;
  $effect(() => {
    if (!_countriesInitialized) return;
    api.updateConfig({ sidebar_countries: visibleCountries });
  });

  // Pagination
  let offset = $state(0);
  let limit = 50;
  let hasMore = $state(true);

  // Sidebar-Länder: nur die im Overlay konfigurierten, mit Daten aus availableCountries
  let sidebarCountries = $derived(() => {
    if (visibleCountries.length === 0) return [];
    const visSet = new Set(visibleCountries);
    return availableCountries.filter(c => visSet.has(c.code));
  });

  // Search debounce
  let searchTimeout;
  
  $effect(() => {
    loadFilters();
    actions.loadFavorites();
    _resetInactivityTimer();
    return () => clearTimeout(_inactivityTimer);
  });

  // Bei Tab-Wechsel zurück auf Radio: Config + Kategorien neu laden
  let _prevTab = appState.activeTab;
  $effect(() => {
    const tab = appState.activeTab;
    if (tab === 'radio' && _prevTab !== 'radio' && _countriesInitialized) {
      reloadConfig();
    }
    _prevTab = tab;
  });

  async function reloadConfig() {
    try {
      const [config, cats, filters] = await Promise.all([
        api.getConfig(),
        api.getCategories().catch(() => []),
        api.getFilters()
      ]);
      categories = Array.isArray(cats) ? cats : (cats?.categories || []);

      // Länder + Filter-Config aktualisieren
      if (config.sidebar_countries) {
        const saved = typeof config.sidebar_countries === 'string'
          ? JSON.parse(config.sidebar_countries) : config.sidebar_countries;
        if (Array.isArray(saved)) visibleCountries = saved;
      }
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
      filterMinVotes = Number(config.filter_min_votes) || 0;

      availableCountries = filters.countries || [];
      search();
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
  }

  // Sync stations to appState für Navigation
  $effect(() => {
    appState.stations = stations;
  });

  // Ad-Status für sichtbare Sender laden
  let _adStatusLoading = false;
  $effect(() => {
    const uuids = stations.map(s => s.uuid);
    if (uuids.length === 0 || _adStatusLoading) return;
    _adStatusLoading = true;
    api.getAdBatchStatus(uuids).then(result => {
      adStatusMap = result || {};
    }).catch(() => {}).finally(() => {
      _adStatusLoading = false;
    });
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
      const [filters, config, cats] = await Promise.all([
        api.getFilters(),
        api.getConfig(),
        api.getCategories().catch(() => [])
      ]);

      let allCountries = filters.countries || [];
      availableCountries = allCountries;
      categories = Array.isArray(cats) ? cats : (cats?.categories || []);

      // Gespeicherte sichtbare Länder aus Config laden
      if (config.sidebar_countries && !_countriesInitialized) {
        try {
          const saved = typeof config.sidebar_countries === 'string'
            ? JSON.parse(config.sidebar_countries)
            : config.sidebar_countries;
          if (Array.isArray(saved)) visibleCountries = saved;
        } catch { /* ignore */ }
      }

      // Setup-Suchfilter aus Config laden
      if (!_countriesInitialized) {
        if (config.filter_excluded_languages) {
          try {
            const saved = typeof config.filter_excluded_languages === 'string'
              ? JSON.parse(config.filter_excluded_languages)
              : config.filter_excluded_languages;
            if (Array.isArray(saved)) excludedLanguages = saved;
          } catch { /* ignore */ }
        }
        if (config.filter_excluded_tags) {
          try {
            const saved = typeof config.filter_excluded_tags === 'string'
              ? JSON.parse(config.filter_excluded_tags)
              : config.filter_excluded_tags;
            if (Array.isArray(saved)) excludedTags = saved;
          } catch { /* ignore */ }
        }
        if (config.filter_min_votes != null) {
          filterMinVotes = Number(config.filter_min_votes) || 0;
        }
      }
      _countriesInitialized = true;

      availableBitrates = BITRATE_RANGES;
      availableVotesRanges = VOTES_RANGES;

      await search();
      // Deep-Link: UUID aus Route auslesen und Sender anwählen
      _handleDeepLink();
    } catch (e) {
      // Netzwerkfehler bei Seitenlade ignorieren
      await search();
      _handleDeepLink();
    }
  }

  // Deep-Link: Sender per UUID oder Suche aus URL
  let _deepLinkHandled = false;
  async function _handleDeepLink() {
    if (_deepLinkHandled) return;
    const seg = appState.routeSegments;
    if (!seg || seg.length === 0) return;

    // Such-Deep-Link: /tuner/search/[query]
    if (seg[0] === 'search' && seg[1]) {
      _deepLinkHandled = true;
      searchQuery = decodeURIComponent(seg[1]);
      await search();
      return;
    }

    // UUID-Format prüfen (32 hex mit Bindestrichen)
    const uuid = seg[0];
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(uuid)) return;

    _deepLinkHandled = true;

    // Sender in bereits geladener Liste suchen
    let found = stations.find(s => s.uuid === uuid);

    // Falls nicht in Liste: per API einzeln laden und vorne einfügen
    if (!found) {
      try {
        const station = await api.getStation(uuid);
        if (station && !station.error) {
          stations = [station, ...stations];
          found = station;
        }
      } catch { /* Sender nicht gefunden */ }
    }

    if (found) {
      selectedUuid = found.uuid;
      // Nach kurzem Delay scrollen damit DOM gerendert ist
      requestAnimationFrame(() => {
        const el = document.querySelector(`.station-wrapper[data-uuid="${found.uuid}"]`);
        if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      });
    }
  }
  
  async function search(append = false) {
    if (!append) {
      isLoading = true;
      offset = 0;
      stations = [];
      if (searchQuery && searchQuery.length >= 2) {
        saveSearchHistory(searchQuery);
        actions.navigateTo('/tuner/search/' + encodeURIComponent(searchQuery), { replace: true });
      } else if (!searchQuery) {
        actions.navigateTo('/tuner', { replace: true });
      }
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
      
      // filterMinVotes als Floor für votes_min (max aus Sidebar-Range und Overlay-Wert)
      if (filterMinVotes > 0) {
        votes_min = Math.max(votes_min ?? 0, filterMinVotes);
      }

      const params = {
        q: searchQuery || undefined,
        countries: selectedCountries.length > 0 ? selectedCountries : undefined,
        category_ids: selectedCategories.length > 0 ? selectedCategories : undefined,
        exclude_languages: excludedLanguages.length > 0 ? excludedLanguages : undefined,
        exclude_tags: excludedTags.length > 0 ? excludedTags : undefined,
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
        // Deduplizierung: nur Sender hinzufügen die noch nicht in der Liste sind
        const existingUuids = new Set(stations.map(s => s.uuid));
        const uniqueNew = newStations.filter(s => !existingUuids.has(s.uuid));
        stations = [...stations, ...uniqueNew];
      } else {
        stations = newStations;
      }

      hasMore = newStations.length === limit;
      offset = append ? offset + newStations.length : newStations.length;

      // Erste Station vorauswählen wenn keine Auswahl aktiv
      if (!append && !selectedUuid && stations.length > 0) {
        // Spielenden Sender bevorzugen, sonst erste Station
        const playingUuid = appState.currentStation?.uuid;
        if (playingUuid && stations.some(s => s.uuid === playingUuid)) {
          selectedUuid = playingUuid;
        } else {
          selectedUuid = stations[0].uuid;
        }
      }

      // Kategorie-Zuordnungen für geladene Sender holen
      if (categories.length > 0 && newStations.length > 0) {
        loadCategoryAssignments(newStations);
      }

    } catch (e) {
      actions.showToast(t('toast.ladenFehler'), 'error');
    } finally {
      isLoading = false;
      isLoadingMore = false;
    }
  }

  // Einzelne Station proben bei Play - echte Werte ermitteln und in Liste mergen
  let probeTimer;
  async function probeOnPlay(station) {
    try {
      await api.verifyBitrate([station.uuid]);
    } catch { return; }

    // Fire-and-forget: Ad-Check im Hintergrund
    const streamUrl = station.url_resolved || station.url;
    if (streamUrl) {
      api.checkAds(station.uuid, streamUrl, station.name).catch(() => {});
    }

    // Nach Verzögerung erkannten Wert abholen
    clearTimeout(probeTimer);
    probeTimer = setTimeout(async () => {
      try {
        const result = await api.getDetectedBitrates([station.uuid]);
        const det = (result.bitrates || {})[station.uuid];
        if (!det) return;
        stations = stations.map(s => {
          if (s.uuid !== station.uuid) return s;
          const updates = {};
          if (det.bitrate > 0) updates.bitrate = det.bitrate;
          if (det.codec) updates.codec = det.codec.toUpperCase();
          if (det.icy) updates.icy = true;
          if (det.icy_quality) updates.icy_quality = det.icy_quality;
          return { ...s, ...updates };
        });
      } catch { /* ignore */ }
    }, 10000);
  }
  
  async function refreshStations() {
    isRefreshing = true;
    try {
      // Filter/Sortierung zurücksetzen
      searchQuery = '';
      selectedCountries = [];
      selectedBitrates = [];
      selectedVotesRanges = [];
      selectedCategories = [];
      showFavsOnly = false;
      localStorage.removeItem('radiohub_favs_only');
      sortBy = 'name';
      sortOrder = 'asc';

      await api.syncCache(true);
      await loadFilters();
      actions.showToast(t('toast.senderGeladen'), 'success');
    } catch (e) {
      actions.showToast(t('toast.ladenFehler'), 'error');
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

  // Tastatur-Navigation in Stationsliste
  let focusedIndex = $state(-1);

  function handleListKeydown(e) {
    if (!stations.length) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        e.stopPropagation();
        focusedIndex = Math.min(focusedIndex + 1, stations.length - 1);
        scrollToFocused();
        break;
      case 'ArrowUp':
        e.preventDefault();
        e.stopPropagation();
        focusedIndex = Math.max(focusedIndex - 1, 0);
        scrollToFocused();
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (focusedIndex >= 0 && focusedIndex < stations.length) {
          const station = stations[focusedIndex];
          selectedUuid = station.uuid;
          _lastPlayTriggeredUuid = station.uuid;
          actions.playStation(station);
          probeOnPlay(station);
          actions.navigateTo('/tuner/' + station.uuid);
        }
        break;
      case 'Escape':
        e.preventDefault();
        selectedUuid = null;
        actions.navigateTo('/tuner');
        break;
    }
  }

  function scrollToFocused() {
    requestAnimationFrame(() => {
      const list = document.querySelector('.station-list');
      const row = list?.querySelectorAll('.station-wrapper')[focusedIndex];
      if (row) row.scrollIntoView({ block: 'nearest' });
    });
  }

  function toggleExpand(station) {
    // Nur auf/zuklappen, kein Play
    if (selectedUuid === station.uuid) {
      selectedUuid = null;
      actions.navigateTo('/tuner');
    } else {
      selectedUuid = station.uuid;
      actions.navigateTo('/tuner/' + station.uuid);
    }
  }

  function playAndExpand(station, e) {
    e.stopPropagation();
    selectedUuid = station.uuid;
    _lastPlayTriggeredUuid = station.uuid;
    actions.playStation(station);
    probeOnPlay(station);
    actions.navigateTo('/tuner/' + station.uuid);
  }
  
  function toggleFavorite(station, e) {
    e.stopPropagation();
    actions.toggleFavorite(station);
  }

  async function toggleIcyQuality(station, e) {
    e.stopPropagation();
    // Zyklus: null -> good -> poor -> null
    const current = station.icy_quality || null;
    const next = current === null ? 'good' : current === 'good' ? 'poor' : null;
    try {
      await api.setIcyQuality(station.uuid, next);
      station.icy_quality = next;
    } catch (err) {
      actions.showToast(`ICY-Bewertung fehlgeschlagen: ${err.message}`, 'error');
    }
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
      // Index des blockierten Senders merken
      const idx = stations.findIndex(s => s.uuid === station.uuid);

      await api.blockStation(station.uuid, station.name);
      actions.showToast(t('toast.senderAusgeblendet'), 'info');

      // Aus Liste entfernen
      stations = stations.filter(s => s.uuid !== station.uuid);

      // Zum nächsten Sender springen
      if (stations.length > 0) {
        const nextIdx = Math.min(idx, stations.length - 1);
        const nextStation = stations[nextIdx];
        selectedUuid = nextStation.uuid;
        _lastPlayTriggeredUuid = nextStation.uuid;
        actions.playStation(nextStation);
        probeOnPlay(nextStation);
      } else {
        selectedUuid = null;
        actions.stop();
        appState.currentStation = null;
      }

    } catch (err) {
      actions.showToast(t('common.fehler'), 'error');
    }
  }

  async function reportAd(station, e) {
    e.stopPropagation();
    try {
      const streamUrl = station.url_resolved || station.url;
      await api.reportAdMarkOnly(station.uuid, streamUrl, station.name);
      adStatusMap = { ...adStatusMap, [station.uuid]: { status: 'confirmed_ad', confidence: 1.0, user_action: null } };
      actions.showToast(t('stations.alsWerbung'), 'info');
    } catch (err) {
      actions.showToast(t('common.fehler'), 'error');
    }
  }

  function toggleCategory(catId) {
    if (selectedCategories.includes(catId)) {
      selectedCategories = selectedCategories.filter(c => c !== catId);
    } else {
      selectedCategories = [...selectedCategories, catId];
    }
    search();
  }


  function openSetupFilter() {
    actions.navigateTo('/setup/radio/filter');
  }

  async function loadCategoryAssignments(stationList) {
    if (!stationList.length || !categories.length) return;
    try {
      const uuids = stationList.map(s => s.uuid);
      const result = await api.getStationAssignments(uuids);
      const data = result?.assignments || {};
      categoryAssignments = { ...categoryAssignments, ...data };
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
  }

  async function toggleCategoryAssignment(stationUuid, categoryId, e) {
    e.stopPropagation();
    const isAssigned = (categoryAssignments[stationUuid] || []).includes(categoryId);

    // Optimistisches Update
    if (isAssigned) {
      categoryAssignments[stationUuid] = (categoryAssignments[stationUuid] || []).filter(id => id !== categoryId);
    } else {
      categoryAssignments[stationUuid] = [...(categoryAssignments[stationUuid] || []), categoryId];
    }
    categoryAssignments = { ...categoryAssignments };

    try {
      if (isAssigned) {
        await api.unassignStation(categoryId, stationUuid);
      } else {
        await api.assignStation(categoryId, stationUuid);
      }
    } catch {
      // Rollback: gezielt nur diese categoryId korrigieren
      const live = categoryAssignments[stationUuid] || [];
      if (isAssigned) {
        // War vorher drin, API-Remove fehlgeschlagen -> wieder hinzufügen
        if (!live.includes(categoryId)) {
          categoryAssignments[stationUuid] = [...live, categoryId];
        }
      } else {
        // War vorher nicht drin, API-Add fehlgeschlagen -> wieder entfernen
        categoryAssignments[stationUuid] = live.filter(id => id !== categoryId);
      }
      categoryAssignments = { ...categoryAssignments };
      actions.showToast(t('common.fehler'), 'error');
    }
  }

  function clearFilters() {
    selectedCountries = [];
    selectedBitrates = [];
    selectedVotesRanges = [];
    selectedCategories = [];
    showFavsOnly = false;
    localStorage.removeItem('radiohub_favs_only');
    searchQuery = '';
    search();
  }

  let activeFilterCount = $derived(
    selectedCountries.length + selectedBitrates.length + selectedVotesRanges.length
    + selectedCategories.length
    + excludedLanguages.length + excludedTags.length
    + (filterMinVotes > 0 ? 1 : 0)
    + (showFavsOnly ? 1 : 0)
  );
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="stations-tab" onclick={_handleUserActivity} onscroll={_handleUserActivity} onkeydown={_handleUserActivity} onmousemove={_handleUserActivity}>
  <!-- Filter Panel (Links) -->
  <aside class="filter-panel">
    <!-- Action Row: Favs + Clear + Filter -->
    <div class="action-row">
      <button class="action-btn" onclick={() => { showFavsOnly = !showFavsOnly; localStorage.setItem('radiohub_favs_only', showFavsOnly); search(); sfx.click(); }} onmouseenter={sfx.hoverSoft} title={showFavsOnly ? t('stations.alleSender') : t('stations.nurFavoriten')}>
        <HiFiLed color={showFavsOnly ? 'yellow' : 'off'} size="small" />
        <span>{t('stationDetail.favoriten')}</span>
      </button>
      {#if activeFilterCount > 0}
        <button class="action-btn square" onclick={() => { clearFilters(); sfx.click(); }} onmouseenter={sfx.hoverSoft} title={t('stations.filterZuruecksetzen')}>&#10005;</button>
      {/if}
      <button class="action-btn square" onclick={() => { openSetupFilter(); sfx.click(); }} onmouseenter={sfx.hoverSoft} title={t('stations.setupFilter')}>
        <i class="fa-solid fa-sliders"></i>
      </button>
    </div>

    <div class="sidebar-divider"></div>

    <!-- Countries: nimmt Restplatz, scrollt intern -->
    <div class="section-flex">
      <div class="section-header">
        <span class="section-label">{t('stationDetail.country')}</span>
        {#if selectedCountries.length > 0}
          <span class="section-count">{selectedCountries.length}/{visibleCountries.length}</span>
        {:else if visibleCountries.length > 0}
          <span class="section-count dim">{visibleCountries.length}</span>
        {/if}
      </div>
      {#if sidebarCountries().length > 0}
        <div class="filter-list">
          {#each sidebarCountries() as country}
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
      {:else}
        <div class="empty-hint" onclick={() => { openSetupFilter(); sfx.click(); }} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openSetupFilter(); sfx.click(); } }}>
          {t('stations.laenderKonfigurieren')}
        </div>
      {/if}
    </div>

    <div class="sidebar-divider"></div>

    <!-- Kategorien -->
    <div class="section-fixed">
      <div class="section-header">
        <span class="section-label">{t('stations.kategorienLabel')}</span>
        {#if selectedCategories.length > 0}
          <span class="section-count">{selectedCategories.length}/{categories.length}</span>
        {:else if categories.length > 0}
          <span class="section-count dim">{categories.length}</span>
        {/if}
      </div>
      {#if categories.length > 0}
        <div class="filter-list compact">
          {#each categories as cat (cat.id)}
            {@const isSelected = selectedCategories.includes(cat.id)}
            {@const hasSel = selectedCategories.length > 0}
            <button class="filter-item" class:selected={isSelected} class:dimmed={hasSel && !isSelected} onclick={() => toggleCategory(cat.id)} title={cat.name}>
              <HiFiLed color={isSelected ? 'yellow' : 'off'} size="small" />
              <span class="filter-item-label">{cat.name}</span>
            </button>
          {/each}
        </div>
      {:else}
        <div class="empty-hint" onclick={() => { actions.navigateTo('/setup/radio/kategorien'); sfx.click(); }} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); actions.navigateTo('/setup/radio/kategorien'); sfx.click(); } }}>
          {t('stations.kategorienErstellen')}
        </div>
      {/if}
    </div>

    <div class="sidebar-divider"></div>

    <!-- Bitrate: 2-spaltig -->
    <div class="section-fixed">
      <div class="section-header">
        <span class="section-label">{t('stationDetail.bitrate')}</span>
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
        <span class="section-label">{t('stationDetail.votes')}</span>
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
        <span class="count-label">{t('stationDetail.stations')}</span>
      </div>

      <!-- Suchfeld -->
      <div class="search-bar">
        <i class="fa-solid fa-magnifying-glass search-icon"></i>
        <input
          type="text"
          class="search-input"
          placeholder={t('stations.senderSuchen')}
          bind:value={searchQuery}
          oninput={handleSearchInput}
          onfocus={() => { if (searchHistory.length > 0 && !searchQuery) showSearchHistory = true; }}
          onblur={() => { setTimeout(() => showSearchHistory = false, 200); }}
        />
        {#if searchQuery}
          <button class="search-clear" onclick={() => { searchQuery = ''; search(); }} title={t('common.loeschen')}>&#10005;</button>
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
              {t('stationDetail.historieLoschen')}
            </button>
          </div>
        {/if}
      </div>

      <!-- Refresh mit Kreispfeil-Icon -->
      <button class="refresh-btn" onclick={() => { refreshStations(); sfx.click(); }} onmouseenter={sfx.hoverSoft} disabled={isRefreshing} title={isRefreshing ? t('common.laden') : t('stations.neuLaden')}>
        <i class="fa-solid fa-arrows-rotate refresh-icon" class:spinning={isRefreshing}></i>
        <span>{t('stationDetail.refresh')}</span>
      </button>
    </div>

    <!-- Liste (scrollbar, alle Sender) -->
    <div class="station-list" onscroll={handleScroll} onkeydown={handleListKeydown} tabindex="0" role="listbox">
      <!-- Spaltenköpfe (sticky) -->
      <div class="column-headers">
        <div class="col-led"></div>
        <div class="col-name" class:col-active={sortBy === 'name'} onclick={() => setSort('name')} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSort('name'); } }}>{t('stationDetail.name')} {#if sortBy === 'name'}<i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>{/if}</div>
        <div class="col-badges"></div>
        <div class="col-country" class:col-active={sortBy === 'country'} onclick={() => setSort('country')} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSort('country'); } }}>{t('stationDetail.country')} {#if sortBy === 'country'}<i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>{/if}</div>
        <div class="col-bitrate" class:col-active={sortBy === 'bitrate'} onclick={() => setSort('bitrate')} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSort('bitrate'); } }}>KBPS {#if sortBy === 'bitrate'}<i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>{/if}</div>
        <div class="col-votes" class:col-active={sortBy === 'votes'} onclick={() => setSort('votes')} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSort('votes'); } }}>{t('stationDetail.votes')} {#if sortBy === 'votes'}<i class="fa-solid {sortOrder === 'asc' ? 'fa-caret-up' : 'fa-caret-down'}"></i>{/if}</div>
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
        {#each stations as station, idx (station.uuid)}
          {@const isPlaying = appState.currentStation?.uuid === station.uuid}
          {@const isSelected = selectedUuid === station.uuid}
          {@const isFocused = focusedIndex === idx}
          {@const isExpanded = isSelected}
          {@const isFav = actions.isFavorite(station.uuid)}
          {@const bitrateVal = typeof station.bitrate === 'object' ? station.bitrate?.value : station.bitrate}
          {@const votesVal = station.votes ?? 0}

          <div class="station-wrapper" data-uuid={station.uuid} class:playing={isPlaying} class:selected={isSelected && !isPlaying} class:focused={isFocused && !isPlaying && !isSelected}>
            <div
              class="station-row"
              class:playing={isPlaying}
              class:selected={isSelected && !isPlaying}
              class:focused={isFocused && !isPlaying && !isSelected}
              onclick={() => { toggleExpand(station); sfx.click(); }}
              onmouseenter={sfx.hover}
              role="button"
              tabindex="0"
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(station); sfx.click(); } }}
            >
              <div class="station-led" onclick={(e) => playAndExpand(station, e)} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); playAndExpand(station, e); } }}>
                <HiFiLed color={isPlaying ? 'blue' : isFocused ? 'yellow' : 'off'} size="small" />
              </div>
              <div class="station-name" onclick={(e) => playAndExpand(station, e)} role="button" tabindex="0" onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); playAndExpand(station, e); } }}>
                <i class="fa-solid fa-play hover-play-icon"></i>
                {#if station.favicon}<img class="station-favicon" src={'/api/favicon/' + station.uuid} alt="" loading="lazy" onerror={(e) => { e.target.style.display = 'none'; }} />{:else}<i class="fa-solid fa-music station-favicon-fallback"></i>{/if}
                <span class="station-name-text">{station.name}</span>
              </div>
              <div class="station-badges">
                {#if station.icy}
                  <button
                    class="info-badge icy-badge"
                    class:icy-good={station.icy_quality === 'good'}
                    class:icy-poor={station.icy_quality === 'poor'}
                    onclick={(e) => toggleIcyQuality(station, e)}
                    title={station.icy_quality === 'good' ? 'ICY: Genaue Schnitte (Klick: wechseln)' : station.icy_quality === 'poor' ? 'ICY: Ungenaue Schnitte (Klick: wechseln)' : 'ICY Metadata (Klick: Qualität bewerten)'}
                  >ICY</button>
                {/if}
                {#if adStatusMap[station.uuid]}
                  {@const ad = adStatusMap[station.uuid]}
                  {#if ad.user_action === 'blocked'}
                    <span class="info-badge ad-badge-blocked" title="Werbung: Als Werbung markiert">AD</span>
                  {:else if ad.user_action === 'allowed'}
                    <span class="info-badge ad-badge-ok" title="Werbung: Manuell freigegeben">OK</span>
                  {:else if ad.confidence > 0}
                    <span class="info-badge ad-badge-suspect" title="Werbung: {Math.round(ad.confidence * 100)}% Verdacht nach Prüfung">{Math.round(ad.confidence * 100)}% AD</span>
                  {:else}
                    <span class="info-badge ad-badge-clean" title="Werbung: 0% - Kein Verdacht nach Prüfung">0% AD</span>
                  {/if}
                {/if}
              </div>
              <div class="station-country">{translateCountry(station.country) || '-'}</div>
              <div class="station-bitrate">{bitrateVal ? formatNumber(bitrateVal) : '--'}{station.codec ? ' / ' + station.codec : ''}</div>
              <div class="station-stats">{formatK(votesVal)}</div>
              <button
                class="station-fav"
                onclick={(e) => toggleFavorite(station, e)}
                title={isFav ? t('stations.ausFavoriten') : t('stations.zuFavoriten')}
              >
                <HiFiLed color={isFav ? 'yellow' : 'off'} size="small" />
              </button>
            </div>

            {#if isExpanded}
              <div class="station-details">
                <div class="details-content">
                  <div class="details-favicon">
                    {#if station.favicon}<img src={'/api/favicon/' + station.uuid} alt="" onerror={(e) => { e.target.style.display = 'none'; }} />{:else}<i class="fa-solid fa-music details-favicon-fallback"></i>{/if}
                  </div>
                  <div class="details-grid">
                    {#if isPlaying && appState.streamTitle}
                      <div class="detail-row icy-now-playing">
                        <span class="detail-label">{t('stationDetail.nowPlaying')}</span>
                        <span class="detail-value icy-title">{appState.streamTitle}</span>
                      </div>
                    {/if}
                    {#if station.homepage}
                      <div class="detail-row">
                        <span class="detail-label">{t('stationDetail.homepage')}</span>
                        <a href={station.homepage} target="_blank" class="detail-value link">{station.homepage}</a>
                      </div>
                    {/if}
                    {#if station.tags}
                      <div class="detail-row">
                        <span class="detail-label">{t('stationDetail.tags')}</span>
                        <span class="detail-value">{station.tags}</span>
                      </div>
                    {/if}
                    {#if station.language}
                      <div class="detail-row">
                        <span class="detail-label">{t('stationDetail.language')}</span>
                        <span class="detail-value">{station.language}</span>
                      </div>
                    {/if}
                    {#if station.codec}
                      <div class="detail-row">
                        <span class="detail-label">{t('stationDetail.codec')}</span>
                        <span class="detail-value">{station.codec}</span>
                      </div>
                    {/if}
                    {#if station.votes !== undefined}
                      <div class="detail-row">
                        <span class="detail-label">{t('stationDetail.votes')}</span>
                        <span class="detail-value">{formatNumber(station.votes)}</span>
                      </div>
                    {/if}
                    {#if station.clickcount !== undefined}
                      <div class="detail-row">
                        <span class="detail-label">{t('stationDetail.clicks')}</span>
                        <span class="detail-value">{formatNumber(station.clickcount)}</span>
                      </div>
                    {/if}
                    {#if station.url_resolved}
                      <div class="detail-row">
                        <span class="detail-label">{t('stationDetail.streamUrl')}</span>
                        <span class="detail-value url">{station.url_resolved}</span>
                      </div>
                    {/if}
                  </div>
                  <div class="details-actions">
                    <div class="details-actions-btns">
                      <button class="ad-hover-btn" onclick={(e) => reportAd(station, e)} title={t('stations.alsWerbung')}>{t('stationDetail.werbung')}</button>
                      <button class="ad-hover-btn ad-hover-hide" onclick={(e) => blockStation(station, e)} title={t('stations.senderAusblenden')}>{t('stationDetail.ausblenden')}</button>
                    </div>
                    {#if categories.length > 0}
                      <div class="category-assign-list" class:scrollable={categories.length > 4}>
                        {#each categories as cat (cat.id)}
                          {@const isAssigned = (categoryAssignments[station.uuid] || []).includes(cat.id)}
                          <button
                            class="category-assign-item"
                            class:assigned={isAssigned}
                            onclick={(e) => toggleCategoryAssignment(station.uuid, cat.id, e)}
                            title={isAssigned ? cat.name + ' entfernen' : cat.name + ' zuordnen'}
                          >
                            <HiFiLed color={isAssigned ? 'green' : 'off'} size="small" />
                            <span class="category-assign-label">{cat.name}</span>
                          </button>
                        {/each}
                      </div>
                    {/if}
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
    font-weight: 700;
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

  .section-count.dim {
    color: var(--hifi-text-secondary);
    font-weight: 500;
  }

  .empty-hint {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    opacity: 0.6;
    padding: 8px 4px;
    cursor: pointer;
    text-align: center;
  }

  .empty-hint:hover {
    opacity: 1;
    color: var(--hifi-accent);
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

  .filter-list.compact {
    flex: none;
    max-height: 120px;
  }

  /* Bitrate/Votes: feste Höhe */
  .section-fixed {
    flex-shrink: 0;
  }

  /* 2-spaltig Grid für Bitrate/Votes */
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
    font-weight: 700;
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

  /* Ausgewählt: blau */
  .filter-item.selected {
    color: var(--hifi-accent);
  }

  .filter-item.selected .country-code,
  .filter-item.selected .filter-item-count {
    color: var(--hifi-accent);
  }

  /* Nicht ausgewählt wenn Gruppe aktiv: hellgrau/gedimmt */
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
    font-weight: 700;
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
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    padding: 0 10px;
    height: 34px;
    box-sizing: border-box;
    width: 160px;
    flex-shrink: 0;
    box-shadow: var(--hifi-shadow-button);
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
    font-weight: 700;
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
  
  .refresh-icon {
    font-size: 12px;
    color: var(--hifi-accent);
    transition: color 0.15s;
  }

  .refresh-icon.spinning {
    animation: spin 1s linear infinite;
    color: var(--hifi-display-blue);
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  /* Suchleiste (im Header, gleiche Höhe wie Stations-Display) */
  .search-bar {
    display: flex;
    align-items: center;
    flex: 1;
    height: 34px;
    background: var(--hifi-bg-panel);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-sizing: border-box;
    padding: 0 10px;
    gap: 8px;
    position: relative;
    box-shadow: var(--hifi-shadow-inset);
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

  .station-list {
    flex: 1;
    overflow-y: auto;
    background: var(--hifi-bg-panel);
  }

  /* Spaltenköpfe */
  .column-headers {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 24px 6px 16px;
    background: var(--hifi-bg-tertiary);
    border-bottom: none;
    position: sticky;
    top: -1px;
    padding-top: 7px;
    z-index: 20;
    box-shadow: 0 2px 0 0 var(--hifi-bg-tertiary);
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

  .col-badges {
    width: 72px;
    flex-shrink: 0;
  }

  .col-country {
    width: 160px;
    padding: 0 8px;
  }

  .col-bitrate {
    width: 90px;
    text-align: right;
    padding-right: 8px;
  }

  .col-votes {
    width: 60px;
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
    padding: 6px 24px 6px 16px;
    cursor: pointer;
    border-bottom: 1px solid var(--hifi-border-dark);
    transition: background 0.1s ease;
    position: relative;
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
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0;
  }

  .hover-play-icon {
    font-size: 10px;
    color: var(--hifi-display-amber);
    width: 0;
    opacity: 0;
    transition: width 0.15s, opacity 0.15s, margin-right 0.15s;
    flex-shrink: 0;
    margin-right: 0;
  }

  .station-name:hover .hover-play-icon,
  .station-led:hover + .station-name .hover-play-icon {
    width: 12px;
    opacity: 1;
    margin-right: 4px;
  }

  .station-favicon {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    object-fit: contain;
    flex-shrink: 0;
    margin-right: 2px;
    filter: grayscale(60%);
  }

  :global(.station-favicon-fallback) {
    width: 18px;
    min-width: 18px;
    height: 18px;
    min-height: 18px;
    box-sizing: border-box;
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    color: var(--hifi-text-muted);
    flex-shrink: 0;
    margin-right: 2px;
  }

  .station-name-text {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .station-badges {
    width: 72px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 3px;
  }

  .info-badge {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    line-height: 1;
    padding: 2px 4px;
    border-radius: 2px;
    display: inline-flex;
    align-items: center;
    cursor: default;
    white-space: nowrap;
  }

  .icy-badge {
    color: #5ba8d9;
    background: rgba(91, 168, 217, 0.15);
    border: 1px solid rgba(91, 168, 217, 0.3);
    cursor: pointer;
  }

  .icy-badge:hover {
    background: rgba(91, 168, 217, 0.25);
  }

  .icy-badge.icy-good {
    color: #4caf50;
    background: rgba(76, 175, 80, 0.15);
    border-color: rgba(76, 175, 80, 0.3);
  }

  .icy-badge.icy-poor {
    color: #e09040;
    background: rgba(224, 144, 64, 0.15);
    border-color: rgba(224, 144, 64, 0.3);
  }

  .station-country {
    width: 160px;
    font-size: 11px;
    color: var(--hifi-text-secondary);
    text-align: left;
    padding: 0 8px;
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
    width: 60px;
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

  .details-actions {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;
    margin-left: auto;
  }

  .category-assign-list {
    display: flex;
    flex-direction: column;
    flex: 1;
  }

  .category-assign-list.scrollable {
    max-height: 96px;
    overflow-y: auto;
  }

  .category-assign-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 6px;
    background: none;
    border: none;
    color: var(--hifi-text-secondary);
    font-family: 'Barlow', sans-serif;
    font-size: 11px;
    font-weight: 400;
    cursor: pointer;
    text-align: left;
    border-radius: var(--hifi-border-radius-sm);
  }

  .category-assign-item:hover {
    background: var(--hifi-row-hover);
    color: var(--hifi-text-primary);
  }

  .category-assign-item.assigned {
    color: var(--hifi-text-primary);
  }

  .category-assign-label {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .details-actions-btns {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex-shrink: 0;
  }

  .ad-badge-clean {
    color: var(--hifi-text-green, #4caf50);
    background: rgba(76, 175, 80, 0.12);
    border: 1px solid rgba(76, 175, 80, 0.25);
  }

  .ad-badge-suspect {
    color: var(--hifi-text-amber, #e5a00d);
    background: rgba(229, 160, 13, 0.12);
    border: 1px solid rgba(229, 160, 13, 0.25);
  }

  .ad-badge-blocked {
    color: var(--hifi-led-red, #e53935);
    background: rgba(229, 57, 53, 0.12);
    border: 1px solid rgba(229, 57, 53, 0.25);
  }

  .ad-badge-ok {
    color: var(--hifi-text-green, #4caf50);
    background: rgba(76, 175, 80, 0.12);
    border: 1px solid rgba(76, 175, 80, 0.25);
  }

  .ad-hover-btn {
    font-family: var(--hifi-font-family);
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    padding: 2px 6px;
    border: 1px solid var(--hifi-border-dark);
    border-radius: 3px;
    cursor: pointer;
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-secondary);
    transition: background 0.1s, color 0.1s;
  }

  .ad-hover-btn:hover {
    background: var(--hifi-led-amber, #e5a00d);
    color: #000;
    border-color: var(--hifi-led-amber, #e5a00d);
  }

  .ad-hover-hide {
    color: var(--hifi-led-red, #e53935);
  }

  .ad-hover-hide:hover {
    background: var(--hifi-led-red, #e53935);
    color: #fff;
    border-color: var(--hifi-led-red, #e53935);
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
  
  /* Fokussierter Sender (Tastatur-Navigation): gelber Schein */
  .station-wrapper.focused {
    background: var(--hifi-bg-panel);
  }

  .station-row.focused {
    background: rgba(255, 204, 0, 0.06);
    box-shadow: inset 0 0 16px rgba(255, 204, 0, 0.04);
  }

  .station-row.focused:hover {
    background: rgba(255, 204, 0, 0.10);
  }

  .station-row.focused .station-name {
    color: var(--hifi-led-yellow);
  }

  /* Ausgewählter Sender: blauer Schein */
  .station-wrapper.selected {
    background: var(--hifi-bg-panel);
    border-top: 2px solid rgba(51, 153, 255, 0.2);
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

  /* Spielender Sender: Wrapper-Styling, komplett sticky unterhalb Spaltenköpfe */
  .station-wrapper.playing {
    position: sticky;
    top: 28px;
    bottom: 0;
    z-index: 10;
    background: var(--hifi-bg-panel);
    border-top: 2px solid rgba(51, 153, 255, 0.3);
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
    padding: 6px 16px 6px 16px;
    border-top: 1px solid var(--hifi-border-dark);
  }

  .details-content {
    display: flex;
    gap: 10px;
  }

  .details-favicon {
    flex-shrink: 0;
    width: 96px;
    height: 96px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .details-favicon img {
    width: 100%;
    height: 100%;
    border-radius: 8px;
    object-fit: contain;
    image-rendering: auto;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
  }

  :global(.details-favicon-fallback) {
    width: 96px;
    min-width: 96px;
    height: 96px;
    min-height: 96px;
    box-sizing: border-box;
    display: flex !important;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    color: var(--hifi-text-muted);
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
  }

  .details-grid {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex: 1;
  }
  
  .detail-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }
  
  .detail-label {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
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

  /* Sort-Icons in Spaltenköpfen */
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
    font-weight: 700;
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
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
    text-align: center;
    text-transform: uppercase;
  }

  .history-clear:hover {
    color: var(--hifi-text-primary);
    background: var(--hifi-row-hover);
  }

  /* === ICY Now Playing === */
  .icy-now-playing {
    border-bottom: 1px solid var(--hifi-border-dark);
    padding-bottom: 4px;
    margin-bottom: 2px;
  }

  .icy-title {
    color: var(--hifi-accent);
    font-weight: 600;
  }
</style>
