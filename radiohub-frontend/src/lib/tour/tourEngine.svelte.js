/**
 * RadioHub Tour Engine v1.0
 * Lose gekoppelte State-Maschine für interaktive Guided Tours.
 * Beobachtet appState und erkennt User-Aktionen automatisch.
 */
import { appState } from '../store.svelte.js';
import { scenarios } from './tourScenarios.js';

// === Tour State (reaktiv) ===
export const tourState = $state({
  active: false,
  scenarioId: null,
  stepIndex: 0,
  steps: [],
  completed: _loadProgress(),
  menuOpen: false
});

// === Fortschritt persistieren ===
function _loadProgress() {
  try {
    return JSON.parse(localStorage.getItem('radiohub_tour_progress') || '[]');
  } catch { return []; }
}

function _saveProgress() {
  localStorage.setItem('radiohub_tour_progress', JSON.stringify(tourState.completed));
}

// === Watcher-Interval ===
let _watchInterval = null;

function _startWatcher() {
  _stopWatcher();
  _watchInterval = setInterval(_checkWaitCondition, 300);
}

function _stopWatcher() {
  if (_watchInterval) {
    clearInterval(_watchInterval);
    _watchInterval = null;
  }
}

function _checkWaitCondition() {
  const step = currentStep();
  if (!step?.waitFor) return;

  const { prop, op, value } = step.waitFor;
  const actual = _resolveProperty(prop);
  let satisfied = false;

  switch (op) {
    case 'truthy': satisfied = !!actual; break;
    case 'falsy': satisfied = !actual; break;
    case 'equals': satisfied = actual === value; break;
    case 'not_equals': satisfied = actual !== value; break;
    case 'gt': satisfied = actual > value; break;
    case 'includes': satisfied = typeof actual === 'string' && actual.includes(value); break;
    default: satisfied = false;
  }

  if (satisfied) {
    // Kurze Pause damit der User die Änderung sieht
    setTimeout(() => next(), 600);
  }
}

function _resolveProperty(prop) {
  // Unterstützt verschachtelte Props: "hlsStatus.buffered_seconds"
  const parts = prop.split('.');
  let val = appState;
  for (const p of parts) {
    if (val == null) return undefined;
    val = val[p];
  }
  return val;
}

// === Öffentliche API ===

export function currentStep() {
  if (!tourState.active || tourState.steps.length === 0) return null;
  return tourState.steps[tourState.stepIndex] || null;
}

export function start(scenarioId) {
  const scenario = scenarios[scenarioId];
  if (!scenario) return;

  tourState.scenarioId = scenarioId;
  tourState.steps = scenario.steps;
  tourState.stepIndex = 0;
  tourState.active = true;
  tourState.menuOpen = false;

  // Pre-Aktion: Tab wechseln wenn nötig
  _executePreAction(currentStep());
  _startWatcher();
}

export function stop() {
  _stopWatcher();
  tourState.active = false;
  tourState.scenarioId = null;
  tourState.stepIndex = 0;
  tourState.steps = [];
  tourState.menuOpen = false;
}

export function next() {
  if (!tourState.active) return;

  const nextIdx = tourState.stepIndex + 1;
  if (nextIdx >= tourState.steps.length) {
    // Szenario abgeschlossen
    if (tourState.scenarioId && !tourState.completed.includes(tourState.scenarioId)) {
      tourState.completed = [...tourState.completed, tourState.scenarioId];
      _saveProgress();
    }
    stop();
    return;
  }

  tourState.stepIndex = nextIdx;
  _executePreAction(currentStep());
}

export function prev() {
  if (!tourState.active || tourState.stepIndex <= 0) return;
  tourState.stepIndex--;
  _executePreAction(currentStep());
}

export function skip() {
  stop();
}

export function toggleMenu() {
  tourState.menuOpen = !tourState.menuOpen;
}

export function closeMenu() {
  tourState.menuOpen = false;
}

export function isCompleted(scenarioId) {
  return tourState.completed.includes(scenarioId);
}

export function resetProgress() {
  tourState.completed = [];
  _saveProgress();
}

// === Pre-Actions ===
function _executePreAction(step) {
  if (!step?.preAction) return;
  const { type, value } = step.preAction;
  switch (type) {
    case 'setTab':
      if (appState.activeTab !== value) {
        // Importiert actions nicht direkt -- nutzt den Store-Import
        import('../store.svelte.js').then(({ actions }) => actions.setTab(value));
      }
      break;
  }
}

// === Szenario-Liste für Menü ===
export function getScenarioList() {
  return Object.entries(scenarios).map(([id, scenario]) => ({
    id,
    title: scenario.title,
    description: scenario.description,
    stepCount: scenario.steps.length,
    completed: tourState.completed.includes(id)
  }));
}
