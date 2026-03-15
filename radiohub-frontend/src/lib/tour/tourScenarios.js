/**
 * RadioHub Tour Szenarien v2.0
 * 7 kurze, fokussierte Touren -- max 7 Steps, viele interaktive Schritte.
 * Reine Daten -- keine Logik, kein Svelte-Code.
 *
 * Step-Felder:
 *   target:    CSS-Selector des hervorzuhebenden Elements
 *   titleKey:  i18n-Key für den Titel (aus tourLocales)
 *   textKey:   i18n-Key für den Erklärungstext
 *   position:  Tooltip-Position: 'top' | 'bottom' | 'left' | 'right'
 *   waitFor:   Optional -- Bedingung die erfüllt sein muss
 *              { prop, op, value } auf appState ODER { selector, op } auf DOM
 *   preAction: Optional -- Aktion(en) vor dem Step (einzeln oder Array)
 *              { type: 'setTab'|'click'|'fillInput'|'clickSource', ... }
 */

export const scenarios = {
  // =====================================================
  // 1. WILLKOMMEN -- Sender laden, auswählen, abspielen
  // =====================================================
  'welcome': {
    title: 'tour.welcome',
    description: 'tour.welcomeDesc',
    steps: [
      {
        target: '.hifi-nav',
        titleKey: 'tour.w.navTitle',
        textKey: 'tour.w.navText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'radio' }
      },
      {
        target: '.refresh-btn',
        titleKey: 'tour.w.loadTitle',
        textKey: 'tour.w.loadText',
        position: 'bottom',
        waitFor: { selector: '.station-row', op: 'exists' }
      },
      {
        target: '.filter-panel',
        titleKey: 'tour.w.filterTitle',
        textKey: 'tour.w.filterText',
        position: 'right'
      },
      {
        target: '.station-list',
        titleKey: 'tour.w.selectTitle',
        textKey: 'tour.w.selectText',
        position: 'left',
        waitFor: { selector: '.station-wrapper.selected', op: 'exists' }
      },
      {
        target: '.display-section',
        titleKey: 'tour.w.displayTitle',
        textKey: 'tour.w.displayText',
        position: 'top',
        waitFor: { prop: 'isPlaying', op: 'equals', value: true }
      },
      {
        target: '.search-bar',
        titleKey: 'tour.w.doneTitle',
        textKey: 'tour.w.doneText',
        position: 'bottom'
      }
    ]
  },

  // =====================================================
  // 2. FAVORITEN -- Markieren, filtern, nutzen
  // =====================================================
  'favorites': {
    title: 'tour.favorites',
    description: 'tour.favoritesDesc',
    steps: [
      {
        target: '.col-fav',
        titleKey: 'tour.fav.headerTitle',
        textKey: 'tour.fav.headerText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'radio' }
      },
      {
        target: '.station-list',
        titleKey: 'tour.fav.addTitle',
        textKey: 'tour.fav.addText',
        position: 'left',
        waitFor: { prop: 'favorites.length', op: 'gt', value: 0 }
      },
      {
        target: '.station-fav',
        titleKey: 'tour.fav.ledTitle',
        textKey: 'tour.fav.ledText',
        position: 'left'
      },
      {
        target: '.action-row .action-btn:first-child',
        titleKey: 'tour.fav.filterTitle',
        textKey: 'tour.fav.filterText',
        position: 'right'
      },
      {
        target: '.station-list',
        titleKey: 'tour.fav.showTitle',
        textKey: 'tour.fav.showText',
        position: 'left',
        preAction: { type: 'click', selector: '.action-row .action-btn:first-child', delay: 400 }
      },
      {
        target: '.action-row .action-btn:first-child',
        titleKey: 'tour.fav.doneTitle',
        textKey: 'tour.fav.doneText',
        position: 'right'
      }
    ]
  },

  // =====================================================
  // 3. PLAYER-FUNKTIONEN -- Timeshift, GoLive, Modi, Bitrate
  // =====================================================
  'player-features': {
    title: 'tour.playerFeatures',
    description: 'tour.playerFeaturesDesc',
    steps: [
      {
        target: '.transport-controls button:nth-child(9)',
        titleKey: 'tour.pf.modeTitle',
        textKey: 'tour.pf.modeText',
        position: 'top',
        preAction: { type: 'setTab', value: 'radio' }
      },
      {
        target: '.transport-fader-container',
        titleKey: 'tour.pf.seekTitle',
        textKey: 'tour.pf.seekText',
        position: 'top'
      },
      {
        target: '.transport-controls button:nth-child(8)',
        titleKey: 'tour.pf.liveTitle',
        textKey: 'tour.pf.liveText',
        position: 'top'
      },
      {
        target: '.bitrate-bar',
        titleKey: 'tour.pf.bitrateTitle',
        textKey: 'tour.pf.bitrateText',
        position: 'top'
      },
      {
        target: '.transport-controls button:nth-child(10)',
        titleKey: 'tour.pf.playModeTitle',
        textKey: 'tour.pf.playModeText',
        position: 'top'
      },
      {
        target: '.timer-section',
        titleKey: 'tour.pf.timerTitle',
        textKey: 'tour.pf.timerText',
        position: 'top'
      },
      {
        target: '.source-section',
        titleKey: 'tour.pf.sourceTitle',
        textKey: 'tour.pf.sourceText',
        position: 'top'
      }
    ]
  },

  // =====================================================
  // 4. AUFNAHME -- Aufnehmen, Sessions, Segmente
  // =====================================================
  'recording': {
    title: 'tour.recording',
    description: 'tour.recordingDesc',
    steps: [
      {
        target: '.station-list',
        titleKey: 'tour.rec.prepTitle',
        textKey: 'tour.rec.prepText',
        position: 'left',
        preAction: { type: 'setTab', value: 'radio' },
        waitFor: { prop: 'isPlaying', op: 'equals', value: true }
      },
      {
        target: '.transport-btn.rec',
        titleKey: 'tour.rec.startTitle',
        textKey: 'tour.rec.startText',
        position: 'top',
        waitFor: { prop: 'isRecording', op: 'equals', value: true }
      },
      {
        target: '.timer-section',
        titleKey: 'tour.rec.runningTitle',
        textKey: 'tour.rec.runningText',
        position: 'top'
      },
      {
        target: '.transport-btn.stop',
        titleKey: 'tour.rec.stopTitle',
        textKey: 'tour.rec.stopText',
        position: 'top',
        waitFor: { prop: 'isRecording', op: 'equals', value: false }
      },
      {
        target: '.recording-sidebar',
        titleKey: 'tour.rec.sessionsTitle',
        textKey: 'tour.rec.sessionsText',
        position: 'right',
        preAction: { type: 'setTab', value: 'recordings' }
      },
      {
        target: '.session-item:first-child',
        titleKey: 'tour.rec.detailTitle',
        textKey: 'tour.rec.detailText',
        position: 'right',
        waitFor: { selector: '.segment-entry', op: 'exists' }
      },
      {
        target: '.recording-sidebar',
        titleKey: 'tour.rec.doneTitle',
        textKey: 'tour.rec.doneText',
        position: 'right'
      }
    ]
  },

  // =====================================================
  // 5. PODCAST -- Suchen, abonnieren, abspielen
  // =====================================================
  'podcast': {
    title: 'tour.podcast',
    description: 'tour.podcastDesc',
    steps: [
      {
        target: '.hifi-nav-btn:nth-child(3)',
        titleKey: 'tour.pod.tabTitle',
        textKey: 'tour.pod.tabText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'podcasts' }
      },
      {
        target: '.action-btn:first-child',
        titleKey: 'tour.pod.searchTitle',
        textKey: 'tour.pod.searchText',
        position: 'right',
        preAction: { type: 'click', selector: '.action-btn:first-child', delay: 400 }
      },
      {
        target: '.scope-badges',
        titleKey: 'tour.pod.scopeTitle',
        textKey: 'tour.pod.scopeText',
        position: 'right',
        preAction: { type: 'click', selector: '.scope-badge:nth-child(3)', delay: 400 }
      },
      {
        target: '.search-input',
        titleKey: 'tour.pod.inputTitle',
        textKey: 'tour.pod.inputText',
        position: 'right',
        preAction: { type: 'fillInput', selector: '.search-input', value: 'Geld für die Welt', delay: 500 },
        waitFor: { selector: '.result-item', op: 'exists' }
      },
      {
        target: '.search-results',
        titleKey: 'tour.pod.subscribeTitle',
        textKey: 'tour.pod.subscribeText',
        position: 'right',
        waitFor: { selector: '.sub-item', op: 'exists' }
      },
      {
        target: '.podcast-sidebar',
        titleKey: 'tour.pod.sidebarTitle',
        textKey: 'tour.pod.sidebarText',
        position: 'right',
        preAction: { type: 'click', selector: '.action-btn:first-child', delay: 300 }
      },
      {
        target: '.episode-row:first-child',
        titleKey: 'tour.pod.playTitle',
        textKey: 'tour.pod.playText',
        position: 'left',
        preAction: { type: 'click', selector: '.sub-item:first-child', delay: 400 },
        waitFor: { selector: '.episode-row', op: 'exists' }
      }
    ]
  },

  // =====================================================
  // 6. QUELL-SPRUNG -- Über Tab-Grenzen zurücknavigieren
  // =====================================================
  'source-jump': {
    title: 'tour.sourceJump',
    description: 'tour.sourceJumpDesc',
    steps: [
      {
        target: '.source-section',
        titleKey: 'tour.sj.introTitle',
        textKey: 'tour.sj.introText',
        position: 'top',
        waitFor: { prop: 'isPlaying', op: 'equals', value: true }
      },
      {
        target: '.source-mode',
        titleKey: 'tour.sj.modeTitle',
        textKey: 'tour.sj.modeText',
        position: 'top'
      },
      {
        target: '.hifi-nav-btn:nth-child(4)',
        titleKey: 'tour.sj.switchTitle',
        textKey: 'tour.sj.switchText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'settings' }
      },
      {
        target: '.source-section',
        titleKey: 'tour.sj.awayTitle',
        textKey: 'tour.sj.awayText',
        position: 'top'
      },
      {
        target: '.source-section',
        titleKey: 'tour.sj.jumpTitle',
        textKey: 'tour.sj.jumpText',
        position: 'top',
        waitFor: { prop: 'activeTab', op: 'not_equals', value: 'settings' }
      },
      {
        target: '.hifi-nav',
        titleKey: 'tour.sj.doneTitle',
        textKey: 'tour.sj.doneText',
        position: 'bottom'
      }
    ]
  },

  // =====================================================
  // 7. EINSTELLUNGEN -- Filter, Block-Zone, Dienste
  // =====================================================
  'settings': {
    title: 'tour.settings',
    description: 'tour.settingsDesc',
    steps: [
      {
        target: '.hifi-nav-btn:nth-child(4)',
        titleKey: 'tour.set.tabTitle',
        textKey: 'tour.set.tabText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'settings' }
      },
      {
        target: '.setup-sidebar',
        titleKey: 'tour.set.sidebarTitle',
        textKey: 'tour.set.sidebarText',
        position: 'right'
      },
      {
        target: '.hifi-panel:nth-child(1)',
        titleKey: 'tour.set.themeTitle',
        textKey: 'tour.set.themeText',
        position: 'right'
      },
      {
        target: '.setup-nav-btn:nth-child(2)',
        titleKey: 'tour.set.radioTitle',
        textKey: 'tour.set.radioText',
        position: 'right',
        preAction: { type: 'click', selector: '.setup-nav-btn:nth-child(2)', delay: 300 }
      },
      {
        target: '.filter-section',
        titleKey: 'tour.set.filterTitle',
        textKey: 'tour.set.filterText',
        position: 'left'
      },
      {
        target: '.setup-nav-btn:nth-child(6)',
        titleKey: 'tour.set.servicesTitle',
        textKey: 'tour.set.servicesText',
        position: 'right',
        preAction: { type: 'click', selector: '.setup-nav-btn:nth-child(6)', delay: 300 }
      }
    ]
  }
};
