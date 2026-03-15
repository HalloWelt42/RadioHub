/**
 * RadioHub Tour Szenarien v1.0
 * Reine Daten -- keine Logik, kein Svelte-Code.
 *
 * Step-Felder:
 *   target:    CSS-Selector des hervorzuhebenden Elements
 *   titleKey:  i18n-Key für den Titel (aus tourLocales)
 *   textKey:   i18n-Key für den Erklärungstext
 *   position:  Tooltip-Position: 'top' | 'bottom' | 'left' | 'right'
 *   waitFor:   Optional -- Bedingung auf appState die erfüllt sein muss
 *              { prop, op, value } -- op: 'truthy'|'falsy'|'equals'|'not_equals'|'gt'|'includes'
 *   preAction: Optional -- Aktion vor dem Step: { type: 'setTab', value: 'radio' }
 */

export const scenarios = {
  'first-steps': {
    title: 'tour.firstSteps',
    description: 'tour.firstStepsDesc',
    steps: [
      {
        target: '.hifi-nav',
        titleKey: 'tour.navTitle',
        textKey: 'tour.navText',
        position: 'bottom'
      },
      {
        target: '.hifi-nav-btn:nth-child(1)',
        titleKey: 'tour.radioTabTitle',
        textKey: 'tour.radioTabText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'radio' }
      },
      {
        target: '.sidebar-filters',
        titleKey: 'tour.filterTitle',
        textKey: 'tour.filterText',
        position: 'right'
      },
      {
        target: '.station-list',
        titleKey: 'tour.stationListTitle',
        textKey: 'tour.stationListText',
        position: 'left'
      },
      {
        target: '.station-row:first-child',
        titleKey: 'tour.selectStationTitle',
        textKey: 'tour.selectStationText',
        position: 'bottom',
        waitFor: { prop: 'currentStation', op: 'truthy' }
      },
      {
        target: '.transport-section',
        titleKey: 'tour.transportTitle',
        textKey: 'tour.transportText',
        position: 'top'
      },
      {
        target: '.volume-section',
        titleKey: 'tour.volumeTitle',
        textKey: 'tour.volumeText',
        position: 'top'
      },
      {
        target: '.display-section',
        titleKey: 'tour.displayTitle',
        textKey: 'tour.displayText',
        position: 'top'
      },
      {
        target: '.source-section',
        titleKey: 'tour.sourceTitle',
        textKey: 'tour.sourceText',
        position: 'top'
      },
      {
        target: '.timer-section',
        titleKey: 'tour.timerTitle',
        textKey: 'tour.timerText',
        position: 'top'
      },
      {
        target: '.hifi-nav-btn:nth-child(1)',
        titleKey: 'tour.firstStepsDoneTitle',
        textKey: 'tour.firstStepsDoneText',
        position: 'bottom'
      }
    ]
  },

  'recording': {
    title: 'tour.recording',
    description: 'tour.recordingDesc',
    steps: [
      {
        target: '.hifi-nav-btn:nth-child(1)',
        titleKey: 'tour.recStartTitle',
        textKey: 'tour.recStartText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'radio' }
      },
      {
        target: '.station-row:first-child',
        titleKey: 'tour.recSelectTitle',
        textKey: 'tour.recSelectText',
        position: 'bottom',
        waitFor: { prop: 'isPlaying', op: 'equals', value: true }
      },
      {
        target: '.rec-btn',
        titleKey: 'tour.recButtonTitle',
        textKey: 'tour.recButtonText',
        position: 'top',
        waitFor: { prop: 'isRecording', op: 'equals', value: true }
      },
      {
        target: '.timer-section',
        titleKey: 'tour.recTimerTitle',
        textKey: 'tour.recTimerText',
        position: 'top'
      },
      {
        target: '.hifi-nav-btn:nth-child(2)',
        titleKey: 'tour.recTabTitle',
        textKey: 'tour.recTabText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'recordings' }
      },
      {
        target: '.rec-btn',
        titleKey: 'tour.recStopTitle',
        textKey: 'tour.recStopText',
        position: 'top',
        waitFor: { prop: 'isRecording', op: 'equals', value: false }
      },
      {
        target: '.hifi-nav-btn:nth-child(2)',
        titleKey: 'tour.recDoneTitle',
        textKey: 'tour.recDoneText',
        position: 'bottom'
      }
    ]
  },

  'podcast': {
    title: 'tour.podcast',
    description: 'tour.podcastDesc',
    steps: [
      {
        target: '.hifi-nav-btn:nth-child(3)',
        titleKey: 'tour.podTabTitle',
        textKey: 'tour.podTabText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'podcasts' }
      },
      {
        target: '.action-btn:first-child',
        titleKey: 'tour.podSearchTitle',
        textKey: 'tour.podSearchText',
        position: 'right'
      },
      {
        target: '.podcast-sidebar',
        titleKey: 'tour.podSidebarTitle',
        textKey: 'tour.podSidebarText',
        position: 'right'
      },
      {
        target: '.hifi-nav-btn:nth-child(3)',
        titleKey: 'tour.podDoneTitle',
        textKey: 'tour.podDoneText',
        position: 'bottom'
      }
    ]
  },

  'settings': {
    title: 'tour.settings',
    description: 'tour.settingsDesc',
    steps: [
      {
        target: '.hifi-nav-btn:nth-child(4)',
        titleKey: 'tour.settingsTabTitle',
        textKey: 'tour.settingsTabText',
        position: 'bottom',
        preAction: { type: 'setTab', value: 'settings' }
      },
      {
        target: '.hifi-header-right .hifi-nav-btn',
        titleKey: 'tour.themeTitle',
        textKey: 'tour.themeText',
        position: 'bottom'
      },
      {
        target: '.hifi-nav-btn:nth-child(4)',
        titleKey: 'tour.settingsDoneTitle',
        textKey: 'tour.settingsDoneText',
        position: 'bottom'
      }
    ]
  }
};
