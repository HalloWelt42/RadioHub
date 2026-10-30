/**
 * Weckton aus dem Gerät, ohne Netz: ein im Speicher erzeugter Puffer (Doppelpiep, Pause), der in Schleife läuft,
 * solange der Sender beim Wecken nicht zu hören ist.
 */
import { kontext } from './tonkontext.svelte.js';

let _puffer = null;
let _quelle = null;

/** Einmal erzeugen (beim Öffnen der Weckeransicht), damit im Ernstfall nichts mehr geladen werden muss. */
export function wecktonVorbereiten() {
  if (_puffer) return _puffer;
  const c = kontext();
  const rate = c.sampleRate;
  const laenge = Math.round(rate * 1.6);
  _puffer = c.createBuffer(1, laenge, rate);
  const daten = _puffer.getChannelData(0);
  const pieps = [[0, 0.18], [0.28, 0.46]];          // zwei kurze Pieptöne, dann Ruhe
  for (const [von, bis] of pieps) {
    for (let i = Math.round(von * rate); i < Math.round(bis * rate); i++) {
      const t = i / rate - von;
      const huelle = Math.min(1, t / 0.01, (bis - von - t) / 0.01);   // weiche Kanten, kein Knacken
      daten[i] = 0.6 * huelle * Math.sin(2 * Math.PI * 1000 * (i / rate));
    }
  }
  return _puffer;
}

export function wecktonAn() {
  if (_quelle) return;
  const c = kontext();
  if (c.state === 'suspended') c.resume().catch(() => {});
  const quelle = c.createBufferSource();
  quelle.buffer = wecktonVorbereiten();
  quelle.loop = true;
  quelle.connect(c.destination);
  quelle.start();
  _quelle = quelle;
}

export function wecktonAus() {
  if (!_quelle) return;
  try { _quelle.stop(); } catch { /* schon aus */ }
  _quelle = null;
}
