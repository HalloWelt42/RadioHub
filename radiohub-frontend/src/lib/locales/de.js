/**
 * RadioHub - Deutsche Übersetzungen
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
    allgemein: 'ALLGEMEIN',
    radio: 'RADIO',
    podcast: 'PODCAST',
    aufnahmen: 'AUFNAHMEN',
    speicher: 'SPEICHER',
    dienste: 'DIENSTE',
    system: 'SYSTEM',
    // Sub-Tabs
    filter: 'FILTER',
    sender: 'SENDER',
    kategorien: 'KATEGORIEN'
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
    timeshiftHint: 'Output-Bitrate wird automatisch an Input angepasst (nicht höher als Quelle)',
    hlsRec: 'HLS-REC',
    bufferAufnahme: 'BUFFER-AUFNAHME',
    lookback: 'LOOKBACK',
    lookbackHint: 'Wie viele Minuten soll die HLS-Aufnahme in die Vergangenheit zurückgreifen?',
    language: 'SPRACHE'
  },

  // === Setup Podcast ===
  podcast: {
    autoRefresh: 'AUTO-REFRESH',
    aktiv: 'AKTIV',
    aus: 'AUS',
    refreshIntervall: 'REFRESH-INTERVALL',
    intervall: 'INTERVALL',
    refreshHint: 'Podcast-Feeds werden automatisch auf neue Episoden geprüft',
    refreshHintDynamic: 'Alle {hours} Stunden werden abonnierte Feeds aktualisiert'
  },

  // === Setup Aufnahmen ===
  aufnahmen: {
    aufnahmeFormat: 'AUFNAHME-FORMAT',
    bitrate: 'BITRATE',
    ordner: 'AUFNAHME-ORDNER',
    neuerOrdner: '+ NEUER ORDNER',
    ordnername: 'ORDNERNAME',
    neueAufnahmenIn: 'Neue Aufnahmen gehen in:',
    standardOrdner: 'Neue Aufnahmen gehen in den Standard-Ordner (Root)',
    aktivieren: 'AKTIVIEREN',
    root: 'ROOT',
    aufnahmen: 'Aufnahmen'
  },

  // === Setup Filter ===
  filter: {
    suchfilter: 'SUCHFILTER',
    laender: 'LÄNDER',
    sprachenAusschliessen: 'SPRACHEN AUSSCHLIEßEN',
    tagsAusschliessen: 'TAGS AUSSCHLIEßEN',
    minVotes: 'MIN VOTES',
    permanentAusblenden: 'PERMANENT AUSBLENDEN',
    permanentHint: 'Sender mit obigen Kriterien dauerhaft entfernen',
    vorschau: 'VORSCHAU',
    zaehle: 'ZÄHLE...',
    ausblenden: 'AUSBLENDEN',
    blendeAus: 'BLENDE AUS...',
    betroffen: 'betroffen',
    alle: 'Alle',
    keine: 'Keine',
    seltene: 'SELTENE',
    spracheSuchen: 'Sprache suchen...',
    landSuchen: 'Land suchen...',
    sichtbareLaender: 'SICHTBARE LÄNDER',
    tagHinzufuegen: 'Tag hinzufügen...',
    aktiv: 'Aktiv:'
  },

  // === Setup Sender ===
  senderSetup: {
    adBlocker: 'AD-BLOCKER',
    ausgeblendet: 'AUSGEBLENDET',
    werbeerkennung: 'WERBEERKENNUNG',
    werbeHint: 'Sender auf Werbung prüfen und entscheiden',
    alleScannen: 'ALLE SCANNEN',
    nochNichtGeprueft: 'noch nicht geprüft',
    geprueft: 'GEPRÜFT',
    sauber: 'SAUBER',
    verdaechtig: 'VERDÄCHTIG',
    ausgeblendetLabel: 'AUSGEBLENDET',
    alleAusblenden: 'ALLE AUSBLENDEN',
    alleOk: 'ALLE OK',
    ok: 'OK',
    freigeben: 'FREIGEBEN',
    manuell: 'MANUELL',
    filterLabel: 'FILTER',
    werbung: 'WERBUNG',
    ein: 'EIN',
    ausLabel: 'AUS'
  },

  // === Setup Kategorien ===
  kategorien: {
    kategorien: 'KATEGORIEN',
    podcastKategorien: 'PODCAST-KATEGORIEN',
    aufnahmeKategorien: 'AUFNAHME-KATEGORIEN',
    neueKategorie: '+ NEUE KATEGORIE',
    kategorieBearbeiten: 'KATEGORIE BEARBEITEN',
    nochKeine: 'Noch keine Kategorien erstellt',
    hintRadio: 'Kategorien filtern Sender in der Seitenleiste',
    hintPodcast: 'Kategorien filtern Podcasts in der Seitenleiste',
    hintRecording: 'Kategorien filtern Aufnahmen in der Seitenleiste'
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
    play: 'Abspielen',
    pause: 'Pause',
    stop: 'Wiedergabe stoppen',
    recStart: 'Aufnahme starten',
    recStop: 'Aufnahme stoppen',
    recLaeuft: 'Aufnahme läuft',
    skipBack: '10 Sekunden zurück',
    skipForward: '10 Sekunden vor',
    goLive: 'Zur Live-Position springen',
    bereitsLive: 'Bereits live',
    liveNurHls: 'Live nur im HLS-Modus verfügbar',
    keinSender: 'Kein Sender ausgewählt',
    recLaeuftStoppen: 'Aufnahme läuft -- erst REC stoppen',
    spulenNicht: 'Spulen nicht verfügbar',
    prevSender: 'Vorheriger Sender',
    nextSender: 'Nächster Sender',
    prevEpisode: 'Vorherige Episode',
    nextEpisode: 'Nächste Episode',
    prevTitel: 'Vorheriger Titel',
    nextTitel: 'Nächster Titel',
    keinPrev: 'Kein vorheriger Sender',
    keinNext: 'Kein nächster Sender',
    directMode: 'Zu Original-Stream wechseln (Direct)',
    hlsMode: 'Zu HLS-Stream wechseln (zeitversetzt)',
    moduswechselNicht: 'Moduswechsel nicht verfügbar',
    recModuswechsel: 'Aufnahme läuft -- kein Moduswechsel',
    fehlerSchliessen: 'Fehlermeldung schließen'
  },

  // === Stations ===
  stations: {
    senderSuchen: 'Sender suchen...',
    podcastsSuchen: 'Podcasts suchen...',
    alleSender: 'Alle Sender anzeigen',
    nurFavoriten: 'Nur Favoriten anzeigen',
    filterZuruecksetzen: 'Alle Filter zurücksetzen',
    setupFilter: 'Setup: Filter öffnen',
    neuLaden: 'Senderliste vom Server neu laden',
    zuFavoriten: 'Zu Favoriten hinzufügen',
    ausFavoriten: 'Aus Favoriten entfernen',
    alsWerbung: 'Als Werbung markieren',
    senderAusblenden: 'Sender ausblenden'
  },

  // === Gemeinsame Buttons ===
  common: {
    speichern: 'SPEICHERN',
    abbrechen: 'ABBRECHEN',
    loeschen: 'LÖSCHEN',
    bearbeiten: 'BEARBEITEN',
    aktualisieren: 'AKTUALISIEREN',
    name: 'NAME',
    laden: 'Laden...'
  },

  // === Toast-Meldungen ===
  toast: {
    speichernFehler: 'Speichern fehlgeschlagen',
    ladenFehler: 'Laden fehlgeschlagen',
    loeschenFehler: 'Löschen fehlgeschlagen',
    backendOffline: 'Backend nicht erreichbar',
    recGestartet: 'Aufnahme gestartet',
    recGespeichert: 'Aufnahme gespeichert',
    recFehler: 'Aufnahme fehlgeschlagen',
    stopFehler: 'Stoppen fehlgeschlagen',
    favHinzu: 'Favorit hinzugefügt',
    favEntfernt: 'Favorit entfernt',
    katErstellt: 'Kategorie erstellt',
    katAktualisiert: 'Kategorie aktualisiert',
    katGeloescht: 'Kategorie gelöscht',
    ordnerErstellt: 'Ordner erstellt',
    ordnerUmbenannt: 'Ordner umbenannt',
    ordnerGeloescht: 'Ordner gelöscht',
    ordnerAktiviert: 'Aufnahmeordner aktiviert',
    standardOrdner: 'Standard-Ordner aktiv (Root)',
    aufnahmeGeloescht: 'Aufnahme gelöscht',
    aufnahmeVerschoben: 'Aufnahme verschoben',
    segmentGeloescht: 'Segment gelöscht',
    dateiGeloescht: 'Datei gelöscht',
    senderGeladen: 'Sender geladen',
    feedAktualisiert: 'Feed aktualisiert',
    abonniert: 'abonniert',
    endpunktAktualisiert: 'Endpunkt aktualisiert',
    standardWiederhergestellt: 'Standard wiederhergestellt',
    scanBeendet: 'Scan beendet',
    senderFreigegeben: 'Sender freigegeben',
    senderAusgeblendet: 'Sender ausgeblendet'
  }
};
