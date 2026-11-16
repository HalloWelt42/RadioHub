/**
 * Ein Web-Audio-Kontext für die Telefonansicht (Zeitansage, Weckton). Browser erlauben Ton erst in einer Geste, und
 * als Geste zählt beim Finger erst das Loslassen (pointerup, click), nicht das Aufsetzen: `entsperren` also beim
 * Loslassen aufrufen. Läuft der Kontext, hält ihn eine stille Schleife offen, damit die Ansage von selbst (ohne
 * Tippen) Ton bekommt; `ton.laeuft` zeigt, ob gerade Ton möglich ist (sonst muss einmal getippt werden).
 */

let _ctx = null;
let _stille = null;
let _halten = false;   // nur solange die Weckeransicht offen ist

export const ton = $state({ laeuft: false });

export function kontext() {
  if (!_ctx) {
    _ctx = new (window.AudioContext || window.webkitAudioContext)();
    // iOS: Web Audio auch bei Stummschalter wie Wiedergabe behandeln
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch { /* älteres iOS */ }
    _ctx.onstatechange = zustandUebernehmen;
    zustandUebernehmen();
  }
  return _ctx;
}

function zustandUebernehmen() {
  ton.laeuft = _ctx.state === 'running';
  if (ton.laeuft) stilleHalten();
}

/** Eine stille Schleife hält die Tonausgabe offen, solange die Weckeransicht sie braucht. */
function stilleHalten() {
  if (!_halten || _stille || !_ctx || _ctx.state !== 'running') return;
  const quelle = _ctx.createBufferSource();
  quelle.buffer = _ctx.createBuffer(1, _ctx.sampleRate, _ctx.sampleRate);
  quelle.loop = true;
  quelle.connect(_ctx.destination);
  quelle.start();
  _stille = quelle;
}

/** In einer Geste aufrufen: weckt den Kontext, ob "suspended" oder vom Radio "interrupted". */
export function entsperren() {
  _halten = true;
  const c = kontext();
  if (c.state !== 'running' && c.state !== 'closed') c.resume().catch(() => {});
  stilleHalten();
  return c;
}

/** Beim Verlassen der Weckeransicht: die stille Schleife beenden. */
export function loslassen() {
  _halten = false;
  if (!_stille) return;
  try { _stille.stop(); } catch { /* schon aus */ }
  _stille = null;
}
