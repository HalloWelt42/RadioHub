/**
 * RadioHub Router v2.0
 * Echte Pfade über die History-Schnittstelle, ohne externe Abhängigkeiten.
 *
 * Routen-Schema: /bereich/segment1/segment2
 * Beispiele:
 *   /radio, /radio/<sender-uuid>, /radio/search/<suche>
 *   /podcasts, /podcasts/<abo>, /podcasts/<abo>/<folge>
 *   /aufnahmen, /einstellungen/radio/filter, /wecker
 *
 * Alte Adressen (#/tuner, #/podcast/3 ...) aus Lesezeichen werden beim Start auf den neuen Pfad umgeleitet.
 * Der Server liefert für unbekannte Pfade index.html (Dateien mit Endung nicht).
 */

// Mapping: Store Tab-ID -> Route-Prefix
const TAB_TO_ROUTE = {
  radio: 'radio',
  recordings: 'aufnahmen',
  podcasts: 'podcasts',
  settings: 'einstellungen',
  wecker: 'wecker'
};

// Mapping: Route-Prefix -> Store Tab-ID
const ROUTE_TO_TAB = Object.fromEntries(Object.entries(TAB_TO_ROUTE).map(([tab, route]) => [route, tab]));

// Frühere Präfixe der Hash-Adressen
const ALTE_PRAEFIXE = { tuner: 'radio', recorder: 'aufnahmen', podcast: 'podcasts', setup: 'einstellungen' };

const STARTPFAD = '/radio';

// Default-Suffixe für Tabs mit Sub-Navigation
const ROUTE_DEFAULTS = {
  einstellungen: {
    _default: ['allgemein', 'einstellungen'],
    allgemein: ['einstellungen'],
    radio: ['filter']
  }
};

let _onNavigate = null;
let _currentPath = null;
let _initialized = false;

/**
 * Parst einen Pfad in strukturierte Route-Info.
 * @param {string} pfad - z.B. "/einstellungen/radio/filter"
 * @returns {{ tab: string, segments: string[], path: string }}
 */
export function parsePath(pfad) {
  const segments = (pfad || '').split('?')[0].split('/').filter(Boolean).map((s) => {
    try { return decodeURIComponent(s); } catch { return s; }
  });
  const tab = segments.length ? ROUTE_TO_TAB[segments[0].toLowerCase()] : null;
  if (!tab) {
    return { tab: 'radio', segments: [], path: STARTPFAD };
  }
  return {
    tab,
    segments: segments.slice(1),
    path: '/' + [segments[0].toLowerCase(), ...segments.slice(1).map(encodeURIComponent)].join('/')
  };
}

/**
 * Wandelt eine alte Hash-Adresse (#/tuner/...) in den neuen Pfad; null, wenn es keine ist.
 * @param {string} hash
 * @returns {string|null}
 */
export function pfadAusAlterAdresse(hash) {
  const roh = (hash || '').replace(/^#\/?/, '');
  if (!roh) return null;
  const teile = roh.split('/').filter(Boolean);
  if (!teile.length) return null;
  const erster = teile[0].toLowerCase();
  teile[0] = ALTE_PRAEFIXE[erster] || erster;
  return '/' + teile.join('/');
}

/**
 * Baut einen Pfad aus Segmenten.
 * @param {string} routePrefix - z.B. 'einstellungen'
 * @param {...string} rest - z.B. 'radio', 'filter'
 * @returns {string} - z.B. '/einstellungen/radio/filter'
 */
export function buildPath(routePrefix, ...rest) {
  const parts = [routePrefix, ...rest].filter(Boolean);
  return '/' + parts.join('/');
}

/**
 * Gibt den Default-Pfad für einen Tab zurück.
 * @param {string} tabId - Store Tab-ID (z.B. 'settings')
 * @returns {string} - z.B. '/einstellungen/allgemein/einstellungen'
 */
export function getDefaultPath(tabId) {
  const prefix = TAB_TO_ROUTE[tabId];
  if (!prefix) return STARTPFAD;

  const defaults = ROUTE_DEFAULTS[prefix];
  if (defaults && defaults._default) {
    return buildPath(prefix, ...defaults._default);
  }
  return buildPath(prefix);
}

/**
 * Gibt den Default-Suffix für ein Einstellungs-Sub-Tab zurück.
 * @param {string} subTab - z.B. 'allgemein', 'radio'
 * @returns {string[]} - z.B. ['einstellungen']
 */
export function getSubDefault(subTab) {
  const defaults = ROUTE_DEFAULTS.einstellungen;
  return (defaults && defaults[subTab]) || [];
}

/**
 * Navigiert zu einem Pfad (neuer Eintrag im Verlauf oder ersetzt den aktuellen).
 * @param {string} path - z.B. '/einstellungen/radio/filter'
 * @param {{ replace?: boolean }} options
 */
export function navigate(path, { replace = false } = {}) {
  if (_currentPath === path) return;
  _currentPath = path;
  if (replace) {
    history.replaceState(null, '', path);
  } else {
    history.pushState(null, '', path);
  }
}

/**
 * Handler für popstate (Browser Zurück/Vor).
 */
function handlePopState() {
  const info = parsePath(window.location.pathname);
  _currentPath = info.path;
  if (_onNavigate) {
    _onNavigate(info);
  }
}

/**
 * Initialisiert den Router; leitet alte Hash-Adressen und die Wurzel auf echte Pfade um.
 * @param {function} onNavigate - Callback bei Route-Änderung durch Browser
 * @returns {{ tab: string, segments: string[], path: string }}
 */
export function init(onNavigate) {
  if (_initialized) {
    window.removeEventListener('popstate', handlePopState);
  }
  _onNavigate = onNavigate;
  window.addEventListener('popstate', handlePopState);
  _initialized = true;

  const alt = pfadAusAlterAdresse(window.location.hash);
  const info = parsePath(alt || window.location.pathname);
  if (alt || window.location.pathname !== info.path) {
    history.replaceState(null, '', info.path);
  }
  _currentPath = info.path;
  return info;
}

/**
 * Entfernt den Router-Listener.
 */
export function destroy() {
  window.removeEventListener('popstate', handlePopState);
  _onNavigate = null;
  _currentPath = null;
  _initialized = false;
}

/**
 * Gibt den aktuellen geparsten Zustand zurück.
 */
export function current() {
  return parsePath(window.location.pathname);
}

export { TAB_TO_ROUTE, ROUTE_TO_TAB };
