/**
 * Neue Fassung erkennen (RAD-20): die geöffnete App prüft alle paar Minuten und beim Zurückkehren auf die Seite, ob es
 * eine neue Fassung gibt (das Skript in der index.html hat einen anderen Namen, er trägt den Hash des Baus). Sie lädt
 * nie von selbst neu: wer Radio hört, wird nicht übergangen. Ein Hinweis mit "Neu laden" erscheint (Meldung.svelte);
 * neu geladen wird nur, wenn jemand ihn auslöst. Der gewählte Sender bzw. die Folge wird dabei übergeben.
 * Nutzer 20.11.2026: "nutzer des radio wird nicht übergangen, sondern bekommt reloadinfo die er selber auslösen kann,
 * nicht muss".
 */

const PRUEF_ABSTAND_MS = 5 * 60 * 1000;
const UEBERGABE = 'radiohub_nach_aktualisierung';
const SKRIPT = /\/assets\/index-[^"'\s]+\.js/;

/** `neu`: eine neue Fassung liegt bereit; `spaeter`: der Hinweis ist für genau diese Fassung weggeklickt */
export const aktualisierung = $state({ neu: false, spaeter: false });

let _appState = null;
let _eigenes = null;
let _bekannt = null;   // Skript der zuletzt erkannten neuen Fassung

/** Auf Wunsch: Zustand übergeben und neu laden */
export function neuLaden() {
  try {
    const s = _appState;
    if (s) sessionStorage.setItem(UEBERGABE, JSON.stringify({ station: s.currentStation, episode: s.currentEpisode }));
  } catch { /* privates Fenster: dann ohne Übergabe */ }
  location.reload();
}

/** Hinweis wegklicken; eine noch neuere Fassung meldet sich wieder */
export function spaeter() {
  aktualisierung.spaeter = true;
}

export async function pruefen() {
  if (!_eigenes) return;
  try {
    const antwort = await fetch(import.meta.env.BASE_URL, { cache: 'no-store' });
    const treffer = (await antwort.text()).match(SKRIPT);
    if (!treffer || treffer[0] === _eigenes || treffer[0] === _bekannt) return;
    _bekannt = treffer[0];
    aktualisierung.neu = true;
    aktualisierung.spaeter = false;
  } catch { /* Server kurz weg: beim nächsten Mal */ }
}

/** Beim Start: eigene Fassung merken, Übergabe der vorigen Fassung übernehmen, Prüfungen anstoßen. */
export function starten(appState) {
  _appState = appState;
  const skript = [...document.querySelectorAll('script[src]')].map((s) => new URL(s.src, location.href).pathname)
    .find((p) => SKRIPT.test(p));
  _eigenes = skript?.match(SKRIPT)?.[0] || null;   // im Entwicklungsserver gibt es kein gebautes Skript: keine Prüfung
  try {
    const uebergabe = JSON.parse(sessionStorage.getItem(UEBERGABE) || 'null');
    sessionStorage.removeItem(UEBERGABE);
    if (uebergabe?.station && !appState.currentStation) appState.currentStation = uebergabe.station;
    if (uebergabe?.episode && !appState.currentEpisode) appState.currentEpisode = uebergabe.episode;
  } catch { /* nichts übergeben */ }
  if (!_eigenes) return;
  setInterval(pruefen, PRUEF_ABSTAND_MS);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') pruefen(); });
}
