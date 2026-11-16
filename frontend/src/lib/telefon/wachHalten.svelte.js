/**
 * Bildschirm wach halten (Screen Wake Lock, auch iOS ab 16.4). Die Sperre fällt beim Verlassen der Seite von selbst;
 * sie wird beim Zurückkehren neu geholt. Wunsch des Menschen bleibt im Gerät gespeichert; die Weckeransicht
 * hält zusätzlich wach, solange sie offen ist.
 */

const SCHLUESSEL = 'radiohub_wach_halten';

export const wach = $state({
  gewuenscht: lesen(),
  weckeransicht: false,
  aktiv: false,
  unterstuetzt: typeof navigator !== 'undefined' && 'wakeLock' in navigator
});

let _sperre = null;

function lesen() {
  try { return localStorage.getItem(SCHLUESSEL) === '1'; } catch { return false; }
}

async function anpassen() {
  const soll = (wach.gewuenscht || wach.weckeransicht) && document.visibilityState === 'visible';
  if (!wach.unterstuetzt) return;
  if (soll && !_sperre) {
    try {
      _sperre = await navigator.wakeLock.request('screen');
      wach.aktiv = true;
      _sperre.addEventListener('release', () => { _sperre = null; wach.aktiv = false; });
    } catch {
      wach.aktiv = false; // etwa ohne sicheren Kontext oder im Stromsparmodus
    }
  } else if (!soll && _sperre) {
    await _sperre.release();
  }
}

export function wachHaltenSetzen(an) {
  wach.gewuenscht = an;
  try { localStorage.setItem(SCHLUESSEL, an ? '1' : '0'); } catch { /* privates Fenster */ }
  anpassen();
}

export function weckeransichtOffen(offen) {
  wach.weckeransicht = offen;
  anpassen();
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', anpassen);
  anpassen();
}
