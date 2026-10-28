/**
 * Ein Web-Audio-Kontext für die Telefonansicht (Zeitansage, Weckton). Browser erlauben Ton erst nach einer Geste:
 * `entsperren` bei jeder Berührung der Weckeransicht aufrufen.
 */

let _ctx = null;

export function kontext() {
  if (!_ctx) {
    _ctx = new (window.AudioContext || window.webkitAudioContext)();
    // iOS: Web Audio auch bei Stummschalter wie Wiedergabe behandeln
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch { /* älteres iOS */ }
  }
  return _ctx;
}

export function entsperren() {
  const c = kontext();
  if (c.state === 'suspended') c.resume().catch(() => {});
}
