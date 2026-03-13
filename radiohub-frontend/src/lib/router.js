/**
 * RadioHub Hash-Router v1.0
 * Leichtgewichtiges Hash-Routing ohne externe Abhängigkeiten.
 *
 * Routen-Schema: #/segment1/segment2/segment3
 * Beispiele:
 *   #/tuner
 *   #/setup/radio/filter
 *   #/podcast/search
 */

// Mapping: Store Tab-ID -> Route-Prefix
const TAB_TO_ROUTE = {
  radio: 'tuner',
  recordings: 'recorder',
  podcasts: 'podcast',
  settings: 'setup'
};

// Mapping: Route-Prefix -> Store Tab-ID
const ROUTE_TO_TAB = {
  tuner: 'radio',
  recorder: 'recordings',
  podcast: 'podcasts',
  setup: 'settings'
};

// Default-Suffixe für Tabs mit Sub-Navigation
const ROUTE_DEFAULTS = {
  setup: {
    _default: ['allgemein', 'einstellungen'],
    allgemein: ['einstellungen'],
    radio: ['filter']
  }
};

let _onNavigate = null;
let _suppressHashChange = false;
let _currentPath = null;
let _initialized = false;

/**
 * Parst einen Hash-String in strukturierte Route-Info.
 * @param {string} hash - z.B. "#/setup/radio/filter"
 * @returns {{ tab: string, segments: string[], path: string }}
 */
export function parseHash(hash) {
  const raw = (hash || '').replace(/^#\/?/, '');
  const segments = raw.split('/').filter(Boolean);

  if (segments.length === 0) {
    return { tab: 'radio', segments: [], path: '/tuner' };
  }

  const routePrefix = segments[0].toLowerCase();
  const tab = ROUTE_TO_TAB[routePrefix];

  if (!tab) {
    return { tab: 'radio', segments: [], path: '/tuner' };
  }

  return {
    tab,
    segments: segments.slice(1),
    path: '/' + segments.join('/')
  };
}

/**
 * Baut einen Hash-Pfad aus Segmenten.
 * @param {string} routePrefix - z.B. 'setup'
 * @param {...string} rest - z.B. 'radio', 'filter'
 * @returns {string} - z.B. '/setup/radio/filter'
 */
export function buildPath(routePrefix, ...rest) {
  const parts = [routePrefix, ...rest].filter(Boolean);
  return '/' + parts.join('/');
}

/**
 * Gibt den Default-Pfad für einen Tab zurück.
 * @param {string} tabId - Store Tab-ID (z.B. 'settings')
 * @returns {string} - z.B. '/setup/allgemein/einstellungen'
 */
export function getDefaultPath(tabId) {
  const prefix = TAB_TO_ROUTE[tabId];
  if (!prefix) return '/tuner';

  const defaults = ROUTE_DEFAULTS[prefix];
  if (defaults && defaults._default) {
    return buildPath(prefix, ...defaults._default);
  }
  return buildPath(prefix);
}

/**
 * Gibt den Default-Suffix für ein Setup-Sub-Tab zurück.
 * @param {string} subTab - z.B. 'allgemein', 'radio'
 * @returns {string[]} - z.B. ['einstellungen']
 */
export function getSubDefault(subTab) {
  const defaults = ROUTE_DEFAULTS.setup;
  return (defaults && defaults[subTab]) || [];
}

/**
 * Navigiert zu einem Pfad und aktualisiert den Hash.
 * @param {string} path - z.B. '/setup/radio/filter'
 * @param {{ replace?: boolean }} options
 */
export function navigate(path, { replace = false } = {}) {
  if (_currentPath === path) return;
  _currentPath = path;
  _suppressHashChange = true;

  if (replace) {
    const url = new URL(window.location.href);
    url.hash = path;
    history.replaceState(null, '', url.toString());
  } else {
    window.location.hash = path;
  }

  queueMicrotask(() => { _suppressHashChange = false; });
}

/**
 * Handler für hashchange (Browser Back/Forward, manuelle Eingabe).
 */
function handleHashChange() {
  if (_suppressHashChange) return;

  const info = parseHash(window.location.hash);
  _currentPath = info.path;

  if (_onNavigate) {
    _onNavigate(info);
  }
}

/**
 * Initialisiert den Router.
 * @param {function} onNavigate - Callback bei Route-Änderung durch Browser
 * @returns {{ tab: string, segments: string[], path: string }}
 */
export function init(onNavigate) {
  // Bei HMR: alten Listener entfernen
  if (_initialized) {
    window.removeEventListener('hashchange', handleHashChange);
  }

  _onNavigate = onNavigate;
  window.addEventListener('hashchange', handleHashChange);
  _initialized = true;

  // Initialen Hash parsen
  const info = parseHash(window.location.hash);
  _currentPath = info.path;

  return info;
}

/**
 * Entfernt den Router-Listener.
 */
export function destroy() {
  window.removeEventListener('hashchange', handleHashChange);
  _onNavigate = null;
  _currentPath = null;
  _initialized = false;
}

/**
 * Gibt den aktuellen geparsten Zustand zurück.
 */
export function current() {
  return parseHash(window.location.hash);
}

export { TAB_TO_ROUTE, ROUTE_TO_TAB };
