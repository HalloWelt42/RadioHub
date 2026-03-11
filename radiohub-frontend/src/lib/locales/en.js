/**
 * RadioHub - English Translations
 */
export default {
  // === Navigation ===
  nav: {
    tuner: 'TUNER',
    recorder: 'RECORDER',
    podcast: 'PODCAST',
    setup: 'SETUP'
  },

  // === Setup Tabs ===
  setup: {
    allgemein: 'GENERAL',
    radio: 'RADIO',
    podcast: 'PODCAST',
    aufnahmen: 'RECORDINGS',
    speicher: 'STORAGE',
    dienste: 'SERVICES',
    system: 'SYSTEM',
    // Sub-Tabs
    filter: 'FILTER',
    sender: 'STATIONS',
    kategorien: 'CATEGORIES'
  },

  // === Setup Allgemein ===
  allgemein: {
    displayTheme: 'DISPLAY THEME',
    dark: 'DARK',
    light: 'LIGHT',
    uiSounds: 'UI SOUNDS',
    clickSounds: 'CLICK-SOUNDS',
    timeshiftBuffer: 'TIMESHIFT BUFFER',
    minBitrate: 'MIN BITRATE',
    maxBitrate: 'MAX BITRATE',
    timeshiftHint: 'Output bitrate is automatically adjusted to input (never higher than source)',
    hlsRec: 'HLS-REC',
    bufferAufnahme: 'BUFFER RECORDING',
    lookback: 'LOOKBACK',
    lookbackHint: 'How many minutes should the HLS recording look back into the past?',
    language: 'LANGUAGE'
  },

  // === Setup Podcast ===
  podcast: {
    autoRefresh: 'AUTO-REFRESH',
    aktiv: 'ON',
    aus: 'OFF',
    refreshIntervall: 'REFRESH INTERVAL',
    intervall: 'INTERVAL',
    refreshHint: 'Podcast feeds are automatically checked for new episodes',
    refreshHintDynamic: 'Subscribed feeds are updated every {hours} hours'
  },

  // === Setup Aufnahmen ===
  aufnahmen: {
    aufnahmeFormat: 'RECORDING FORMAT',
    bitrate: 'BITRATE',
    ordner: 'RECORDING FOLDERS',
    neuerOrdner: '+ NEW FOLDER',
    ordnername: 'FOLDER NAME',
    neueAufnahmenIn: 'New recordings go to:',
    standardOrdner: 'New recordings go to the default folder (Root)',
    aktivieren: 'ACTIVATE',
    root: 'ROOT',
    aufnahmen: 'Recordings'
  },

  // === Setup Filter ===
  filter: {
    suchfilter: 'SEARCH FILTER',
    laender: 'COUNTRIES',
    sprachenAusschliessen: 'EXCLUDE LANGUAGES',
    tagsAusschliessen: 'EXCLUDE TAGS',
    minVotes: 'MIN VOTES',
    permanentAusblenden: 'PERMANENTLY HIDE',
    permanentHint: 'Permanently remove stations matching the above criteria',
    vorschau: 'PREVIEW',
    zaehle: 'COUNTING...',
    ausblenden: 'HIDE',
    blendeAus: 'HIDING...',
    betroffen: 'affected',
    alle: 'All',
    keine: 'None',
    seltene: 'RARE',
    spracheSuchen: 'Search language...',
    landSuchen: 'Search country...',
    sichtbareLaender: 'VISIBLE COUNTRIES',
    tagHinzufuegen: 'Add tag...',
    aktiv: 'Active:'
  },

  // === Setup Sender ===
  senderSetup: {
    adBlocker: 'AD-BLOCKER',
    ausgeblendet: 'HIDDEN',
    werbeerkennung: 'AD DETECTION',
    werbeHint: 'Check stations for ads and decide',
    alleScannen: 'SCAN ALL',
    nochNichtGeprueft: 'not yet checked',
    geprueft: 'CHECKED',
    sauber: 'CLEAN',
    verdaechtig: 'SUSPECT',
    ausgeblendetLabel: 'HIDDEN',
    alleAusblenden: 'HIDE ALL',
    alleOk: 'ALL OK',
    ok: 'OK',
    freigeben: 'RELEASE',
    manuell: 'MANUAL',
    filterLabel: 'FILTER',
    werbung: 'AD',
    ein: 'ON',
    ausLabel: 'OFF'
  },

  // === Setup Kategorien ===
  kategorien: {
    kategorien: 'CATEGORIES',
    podcastKategorien: 'PODCAST CATEGORIES',
    aufnahmeKategorien: 'RECORDING CATEGORIES',
    neueKategorie: '+ NEW CATEGORY',
    kategorieBearbeiten: 'EDIT CATEGORY',
    nochKeine: 'No categories created yet',
    hintRadio: 'Categories filter stations in the sidebar',
    hintPodcast: 'Categories filter podcasts in the sidebar',
    hintRecording: 'Categories filter recordings in the sidebar'
  },

  // === Setup System ===
  system: {
    stationCache: 'STATION CACHE',
    stations: 'STATIONS',
    countries: 'COUNTRIES',
    syncNow: 'SYNC NOW',
    syncing: 'SYNCING...',
    systemInfo: 'SYSTEM INFO'
  },

  // === Player ===
  player: {
    play: 'Play',
    pause: 'Pause',
    stop: 'Stop playback',
    recStart: 'Start recording',
    recStop: 'Stop recording',
    recLaeuft: 'Recording in progress',
    skipBack: '10 seconds back',
    skipForward: '10 seconds forward',
    goLive: 'Jump to live position',
    bereitsLive: 'Already live',
    liveNurHls: 'Live only available in HLS mode',
    keinSender: 'No station selected',
    recLaeuftStoppen: 'Recording in progress -- stop REC first',
    spulenNicht: 'Seeking not available',
    prevSender: 'Previous station',
    nextSender: 'Next station',
    prevEpisode: 'Previous episode',
    nextEpisode: 'Next episode',
    prevTitel: 'Previous track',
    nextTitel: 'Next track',
    keinPrev: 'No previous station',
    keinNext: 'No next station',
    directMode: 'Switch to original stream (Direct)',
    hlsMode: 'Switch to HLS stream (time-shifted)',
    moduswechselNicht: 'Mode switch not available',
    recModuswechsel: 'Recording in progress -- no mode switch',
    fehlerSchliessen: 'Close error message'
  },

  // === Stations ===
  stations: {
    senderSuchen: 'Search stations...',
    podcastsSuchen: 'Search podcasts...',
    alleSender: 'Show all stations',
    nurFavoriten: 'Show favorites only',
    filterZuruecksetzen: 'Reset all filters',
    setupFilter: 'Setup: Open filters',
    neuLaden: 'Reload station list from server',
    zuFavoriten: 'Add to favorites',
    ausFavoriten: 'Remove from favorites',
    alsWerbung: 'Mark as advertisement',
    senderAusblenden: 'Hide station'
  },

  // === Common Buttons ===
  common: {
    speichern: 'SAVE',
    abbrechen: 'CANCEL',
    loeschen: 'DELETE',
    bearbeiten: 'EDIT',
    aktualisieren: 'UPDATE',
    name: 'NAME',
    laden: 'Loading...'
  },

  // === Toast Messages ===
  toast: {
    speichernFehler: 'Save failed',
    ladenFehler: 'Load failed',
    loeschenFehler: 'Delete failed',
    backendOffline: 'Backend not reachable',
    recGestartet: 'Recording started',
    recGespeichert: 'Recording saved',
    recFehler: 'Recording failed',
    stopFehler: 'Stop failed',
    favHinzu: 'Favorite added',
    favEntfernt: 'Favorite removed',
    katErstellt: 'Category created',
    katAktualisiert: 'Category updated',
    katGeloescht: 'Category deleted',
    ordnerErstellt: 'Folder created',
    ordnerUmbenannt: 'Folder renamed',
    ordnerGeloescht: 'Folder deleted',
    ordnerAktiviert: 'Recording folder activated',
    standardOrdner: 'Default folder active (Root)',
    aufnahmeGeloescht: 'Recording deleted',
    aufnahmeVerschoben: 'Recording moved',
    segmentGeloescht: 'Segment deleted',
    dateiGeloescht: 'File deleted',
    senderGeladen: 'Stations loaded',
    feedAktualisiert: 'Feed updated',
    abonniert: 'subscribed',
    endpunktAktualisiert: 'Endpoint updated',
    standardWiederhergestellt: 'Default restored',
    scanBeendet: 'Scan complete',
    senderFreigegeben: 'Station released',
    senderAusgeblendet: 'Station hidden'
  }
};
