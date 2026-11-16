/**
 * Selbst-Aktualisierung: die geöffnete App erkennt eine neue Fassung (das Skript in der index.html hat einen anderen
 * Namen, er trägt den Hash des Baus) alle paar Minuten und beim Zurückkehren auf die Seite. Gewechselt wird von
 * selbst, aber nie mitten in der Arbeit: nicht während Wiedergabe, Aufnahme, Ansage, Schlummern, offener Bearbeitung
 * oder Eingabe, sondern im nächsten ruhigen Moment (Wiedergabe beendet oder pausiert, Wechsel der Ansicht).
 * Pfad, Weckeransicht und Wachhalten bleiben von selbst; der gewählte Sender bzw. die Folge wird übergeben.
 */

const PRUEF_ABSTAND_MS = 5 * 60 * 1000;
const UEBERGABE = 'radiohub_nach_aktualisierung';
const SKRIPT = /\/assets\/index-[^"'\s]+\.js/;

export const aktualisierung = $state({ neu: false });

const _sperren = new Set();
let _appState = null;
let _eigenes = null;
let _zeitansage = () => false;

/** Arbeit, die eine Aktualisierung aufhalten soll (etwa 'schlummern', 'wecker-bearbeiten'). */
export function sperren(grund) { _sperren.add(grund); }
export function freigeben(grund) { _sperren.delete(grund); versuchen(); }

function eingabeOffen() {
  const e = document.activeElement;
  return !!e && ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.tagName);
}

export function ruhig(appState = _appState, zeitansageLaeuft = false) {
  if (!appState) return false;
  const spielt = appState.isPlaying && !appState.isPaused;
  return !spielt && !appState.isRecording && !zeitansageLaeuft && _sperren.size === 0 && !eingabeOffen();
}

/** Im ruhigen Moment auf die neue Fassung wechseln (Zustand übergeben, neu laden). */
export function versuchen() {
  if (!aktualisierung.neu || !ruhig(_appState, _zeitansage())) return false;
  try {
    const s = _appState;
    sessionStorage.setItem(UEBERGABE, JSON.stringify({ station: s.currentStation, episode: s.currentEpisode }));
  } catch { /* privates Fenster: dann ohne Übergabe */ }
  location.reload();
  return true;
}

export async function pruefen() {
  if (!_eigenes) return;
  try {
    const antwort = await fetch('/', { cache: 'no-store' });
    const treffer = (await antwort.text()).match(SKRIPT);
    if (treffer && treffer[0] !== _eigenes) {
      aktualisierung.neu = true;
      versuchen();
    }
  } catch { /* Server kurz weg: beim nächsten Mal */ }
}

/** Beim Start: eigene Fassung merken, Übergabe der vorigen Fassung übernehmen, Prüfungen anstoßen. */
export function starten(appState, zeitansageLaeuft = () => false) {
  _appState = appState;
  _zeitansage = zeitansageLaeuft;
  const skript = [...document.querySelectorAll('script[src]')].map((s) => new URL(s.src, location.href).pathname)
    .find((p) => SKRIPT.test(p));
  _eigenes = skript || null;   // im Entwicklungsserver gibt es kein gebautes Skript: dann keine Prüfung
  try {
    const uebergabe = JSON.parse(sessionStorage.getItem(UEBERGABE) || 'null');
    sessionStorage.removeItem(UEBERGABE);
    if (uebergabe?.station && !appState.currentStation) appState.currentStation = uebergabe.station;
    if (uebergabe?.episode && !appState.currentEpisode) appState.currentEpisode = uebergabe.episode;
  } catch { /* nichts übergeben */ }
  if (!_eigenes) return;
  setInterval(pruefen, PRUEF_ABSTAND_MS);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') pruefen(); });
  window.addEventListener('popstate', () => versuchen());
}
