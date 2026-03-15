/**
 * RadioHub Update Checker v1.0
 * Prüft ob im GitHub-Repo eine neuere Version vorliegt.
 * Vergleicht package.json Version aus dem main-Branch mit der lokalen Build-Version.
 */

const REPO_URL = 'https://github.com/HalloWelt42/RadioHub';
const VERSION_URL = 'https://raw.githubusercontent.com/HalloWelt42/RadioHub/main/radiohub-frontend/package.json';
const CHECK_INTERVAL = 6 * 60 * 60 * 1000; // 6 Stunden
const LOCAL_VERSION = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.0.0';

export const updateState = $state({
  available: false,
  remoteVersion: null,
  localVersion: LOCAL_VERSION,
  repoUrl: REPO_URL,
  lastCheck: null,
  error: null
});

/**
 * Semver-Vergleich: gibt true zurück wenn remote > local
 */
function _isNewer(remote, local) {
  const r = remote.replace(/^v/, '').split('.').map(Number);
  const l = local.replace(/^v/, '').split('.').map(Number);
  for (let i = 0; i < 3; i++) {
    const rv = r[i] || 0;
    const lv = l[i] || 0;
    if (rv > lv) return true;
    if (rv < lv) return false;
  }
  return false;
}

/**
 * Versions-Check gegen GitHub durchführen
 */
async function _checkForUpdate() {
  try {
    const res = await fetch(VERSION_URL, { cache: 'no-store' });
    if (!res.ok) {
      updateState.error = `HTTP ${res.status}`;
      return;
    }
    const pkg = await res.json();
    const remote = pkg.version || '0.0.0';
    updateState.remoteVersion = remote;
    updateState.available = _isNewer(remote, LOCAL_VERSION);
    updateState.lastCheck = Date.now();
    updateState.error = null;
  } catch (err) {
    updateState.error = err.message;
  }
}

/**
 * Update-Check starten (beim App-Start aufrufen).
 * Prüft sofort und dann alle 6 Stunden.
 */
let _interval = null;

export function startUpdateChecker() {
  if (_interval) return;
  // Verzögerter Start um den App-Start nicht zu blockieren
  setTimeout(() => {
    _checkForUpdate();
    _interval = setInterval(_checkForUpdate, CHECK_INTERVAL);
  }, 5000);
}

export function stopUpdateChecker() {
  if (_interval) {
    clearInterval(_interval);
    _interval = null;
  }
}
