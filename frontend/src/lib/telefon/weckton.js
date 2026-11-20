/**
 * Weckton aus dem Gerät, ohne Netz (RAD-15): spielt einen der Wecktöne aus `wecktoene.js` in Schleife, solange er weckt.
 * Beim Klingeln wählt die Weckansicht den Ton und die Lautstärke des Weckers (`wecktonWaehlen`); wer den Ton dann
 * einschaltet, die Person oder der Wächter bei stummem Radio, ruft nur `wecktonAn()`. Die Weckerliste spielt mit
 * `wecktonAn(id, laut)` eine Hörprobe. Es läuft immer höchstens ein Ton.
 */
import { kontext } from './tonkontext.svelte.js';
import { VORGABE, WECKTOENE, wecktonDaten } from './wecktoene.js';

const _puffer = new Map();
let _gewaehlt = { id: VORGABE, laut: 1 };
let _laeuft = null;   // { quelle, verstaerker, id }

function puffer(id) {
  const kennung = WECKTOENE.includes(id) ? id : VORGABE;
  if (!_puffer.has(kennung)) {
    const c = kontext();
    const daten = wecktonDaten(kennung, c.sampleRate);
    const p = c.createBuffer(1, daten.length, c.sampleRate);
    p.copyToChannel(daten, 0);
    _puffer.set(kennung, p);
  }
  return _puffer.get(kennung);
}

/** Vorab erzeugen (beim Öffnen der Weckansicht), damit beim Klingeln nichts mehr gerechnet werden muss; die Vorgabe immer */
export function wecktonVorbereiten(ids = []) {
  for (const id of new Set([VORGABE, ...ids])) puffer(id);
}

/** Ton und Lautstärke (0 bis 1) für das nächste `wecktonAn()`; ein laufender Ton wechselt sofort */
export function wecktonWaehlen(id, laut = 1) {
  _gewaehlt = { id: WECKTOENE.includes(id) ? id : VORGABE, laut };
  puffer(_gewaehlt.id);
  if (_laeuft) wecktonAn();
}

export function wecktonAn(id = _gewaehlt.id, laut = _gewaehlt.laut) {
  const c = kontext();
  if (c.state === 'suspended') c.resume().catch(() => {});
  if (_laeuft?.id === id) {
    _laeuft.verstaerker.gain.setTargetAtTime(laut, c.currentTime, 0.05);
    return;
  }
  wecktonAus();
  const verstaerker = c.createGain();
  verstaerker.gain.value = laut;
  verstaerker.connect(c.destination);
  const quelle = c.createBufferSource();
  quelle.buffer = puffer(id);
  quelle.loop = true;
  quelle.connect(verstaerker);
  quelle.start();
  _laeuft = { quelle, verstaerker, id };
}

export function wecktonAus() {
  if (!_laeuft) return;
  try { _laeuft.quelle.stop(); } catch { /* schon aus */ }
  _laeuft.verstaerker.disconnect();
  _laeuft = null;
}
