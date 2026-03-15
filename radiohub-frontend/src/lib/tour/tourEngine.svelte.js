/**
 * RadioHub Tour Engine v1.1
 * Lose gekoppelte State-Maschine für interaktive Guided Tours.
 * Beobachtet appState und erkennt User-Aktionen automatisch.
 *
 * Demo-Modus: Wenn public/.demomode existiert, werden waitFor-Bedingungen
 * automatisch per State-Simulation erfüllt. Die Datei wird nicht ins Repo
 * committed -- nur für lokale Entwicklung/Demo.
 */
import { appState } from '../store.svelte.js';
import { scenarios } from './tourScenarios.js';

// === Demo-Modus ===
let _demoMode = false;

async function _detectDemoMode() {
  try {
    const res = await fetch('/.demomode', { method: 'HEAD', cache: 'no-store' });
    _demoMode = res.ok;
  } catch { _demoMode = false; }
}
_detectDemoMode();

export function isDemoMode() { return _demoMode; }

// === Tour State (reaktiv) ===
export const tourState = $state({
  active: false,
  scenarioId: null,
  stepIndex: 0,
  steps: [],
  completed: _loadProgress(),
  menuOpen: false,
  waitAlreadySatisfied: false
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
let _stepSetAt = 0;
let _advancing = false; // Verhindert mehrfaches Triggern
let _demoScheduled = false; // Demo-Simulation geplant
const _MIN_STEP_TIME = 1200;

function _startWatcher() {
  _stopWatcher();
  _stepSetAt = Date.now();
  _advancing = false;
  // Prüfe ob waitFor beim Betreten schon erfüllt ist
  const step = currentStep();
  tourState.waitAlreadySatisfied = step?.waitFor ? _evaluateCondition(step.waitFor) : false;
  _watchInterval = setInterval(_checkWaitCondition, 300);
}

function _stopWatcher() {
  if (_watchInterval) {
    clearInterval(_watchInterval);
    _watchInterval = null;
  }
  _advancing = false;
  _demoScheduled = false;
  tourState.waitAlreadySatisfied = false;
}

function _evaluateCondition(waitFor) {
  const { prop, op, value, selector } = waitFor;
  if (selector) {
    const el = document.querySelector(selector);
    switch (op) {
      case 'exists': return !!el;
      case 'not_exists': return !el;
      case 'count_gt': return document.querySelectorAll(selector).length > (value || 0);
      default: return !!el;
    }
  } else {
    const actual = _resolveProperty(prop);
    switch (op) {
      case 'truthy': return !!actual;
      case 'falsy': return !actual;
      case 'equals': return actual === value;
      case 'not_equals': return actual !== value;
      case 'gt': return actual > value;
      case 'includes': return typeof actual === 'string' && actual.includes(value);
      default: return false;
    }
  }
}

function _checkWaitCondition() {
  if (_advancing) return;
  const step = currentStep();
  if (!step?.waitFor) return;

  // Mindest-Anzeigezeit abwarten
  if (Date.now() - _stepSetAt < _MIN_STEP_TIME) return;

  const satisfied = _evaluateCondition(step.waitFor);

  // Demo-Modus: waitFor nach Verzögerung automatisch simulieren
  if (_demoMode && !satisfied && !_demoScheduled && step.demoSimulate) {
    _demoScheduled = true;
    const demoDelay = step.demoDelay || 2000;
    setTimeout(() => {
      _demoScheduled = false;
      if (!tourState.active) return;
      _executeDemoSimulate(step.demoSimulate);
    }, demoDelay);
  }

  // Nur auto-advance wenn Bedingung NICHT schon beim Betreten erfüllt war
  // (sonst zeigt der Step den Weiter-Button und der User klickt manuell)
  if (satisfied && !tourState.waitAlreadySatisfied) {
    _advancing = true;
    setTimeout(() => { _advancing = false; next(); }, 600);
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
  _stepSetAt = Date.now();
  _advancing = false;
  _executePreAction(currentStep());
  // Prüfe ob waitFor des neuen Steps schon erfüllt ist
  const newStep = currentStep();
  tourState.waitAlreadySatisfied = newStep?.waitFor ? _evaluateCondition(newStep.waitFor) : false;
}

export function prev() {
  if (!tourState.active || tourState.stepIndex <= 0) return;
  tourState.stepIndex--;
  _stepSetAt = Date.now();
  _advancing = false;
  _executePreAction(currentStep());
  const step = currentStep();
  tourState.waitAlreadySatisfied = step?.waitFor ? _evaluateCondition(step.waitFor) : false;
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

// === Demo-Simulation ===
function _executeDemoSimulate(simulate) {
  // simulate: Array von { prop: 'isPlaying', value: true }
  const actions = Array.isArray(simulate) ? simulate : [simulate];
  for (const { prop, value } of actions) {
    _setProperty(prop, value);
  }
}

function _setProperty(prop, value) {
  const parts = prop.split('.');
  let obj = appState;
  for (let i = 0; i < parts.length - 1; i++) {
    if (obj[parts[i]] == null) return;
    obj = obj[parts[i]];
  }
  obj[parts[parts.length - 1]] = value;
}

// === Pre-Actions ===
function _executePreAction(step) {
  if (!step?.preAction) return;

  // Array-Support: mehrere preActions sequentiell abarbeiten
  if (Array.isArray(step.preAction)) {
    step.preAction.forEach(action => _executeSingleAction(action));
    return;
  }
  _executeSingleAction(step.preAction);
}

function _executeSingleAction(action) {
  const { type, value, selector, delay } = action;
  switch (type) {
    case 'setTab':
      if (appState.activeTab !== value) {
        import('../store.svelte.js').then(({ actions }) => actions.setTab(value));
      }
      break;
    case 'click':
      // Element per CSS-Selector klicken
      if (selector) {
        const wait = delay || 300;
        setTimeout(() => {
          const el = document.querySelector(selector);
          if (el) el.click();
        }, wait);
      }
      break;
    case 'fillInput':
      // Eingabefeld füllen (mit Svelte-kompatiblem Event)
      if (selector && value !== undefined) {
        const wait = delay || 300;
        setTimeout(() => {
          const el = document.querySelector(selector);
          if (el) {
            // Für Svelte bind:value muss der native Setter genutzt werden
            const nativeSet = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
            if (nativeSet) {
              nativeSet.call(el, value);
              el.dispatchEvent(new Event('input', { bubbles: true }));
            } else {
              el.value = value;
              el.dispatchEvent(new Event('input', { bubbles: true }));
            }
          }
        }, wait);
      }
      break;
    case 'clickSource':
      // Source-Sprung: Klick auf die Quellenanzeige
      if (selector) {
        const wait = delay || 300;
        setTimeout(() => {
          const el = document.querySelector(selector);
          if (el) el.click();
        }, wait);
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
