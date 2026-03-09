// uiSounds.js -- Synthethische UI-Sounds via Web Audio API
// Mechanisch, tief, perkussiv -- wie High-End Audio-Equipment

let ctx = null;
let enabled = true;
let masterVolume = 0.12;

function getCtx() {
  if (!ctx) {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

// -- Sound-Definitionen --

// Hover: Kurzer mechanischer Tick -- wie Relais-Klick
export function hover() {
  if (!enabled) return;
  const ac = getCtx();
  const t = ac.currentTime;
  // Noise-Burst durch hochfrequenten Oszillator, ultrakurz
  const osc = ac.createOscillator();
  const filter = ac.createBiquadFilter();
  const g = ac.createGain();
  filter.type = 'bandpass';
  filter.frequency.value = 600;
  filter.Q.value = 1.5;
  osc.type = 'square';
  osc.frequency.value = 150;
  g.gain.setValueAtTime(masterVolume * 0.7, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.025);
  osc.connect(filter);
  filter.connect(g);
  g.connect(ac.destination);
  osc.start(t);
  osc.stop(t + 0.025);
}

// Hover-Variante: Weicher mechanischer Puls -- für Buttons
export function hoverSoft() {
  if (!enabled) return;
  const ac = getCtx();
  const t = ac.currentTime;
  const osc = ac.createOscillator();
  const filter = ac.createBiquadFilter();
  const g = ac.createGain();
  filter.type = 'lowpass';
  filter.frequency.value = 800;
  filter.Q.value = 0.7;
  osc.type = 'triangle';
  osc.frequency.setValueAtTime(220, t);
  osc.frequency.exponentialRampToValueAtTime(120, t + 0.04);
  g.gain.setValueAtTime(masterVolume * 0.5, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.04);
  osc.connect(filter);
  filter.connect(g);
  g.connect(ac.destination);
  osc.start(t);
  osc.stop(t + 0.04);
}

// Click: Satter mechanischer Schalter-Klick
export function click() {
  if (!enabled) return;
  const ac = getCtx();
  const t = ac.currentTime;
  // Tiefer Impuls + kurzer Attack
  const osc1 = ac.createOscillator();
  const osc2 = ac.createOscillator();
  const filter = ac.createBiquadFilter();
  const g = ac.createGain();
  filter.type = 'lowpass';
  filter.frequency.setValueAtTime(1200, t);
  filter.frequency.exponentialRampToValueAtTime(200, t + 0.04);
  osc1.type = 'square';
  osc1.frequency.value = 80;
  osc2.type = 'triangle';
  osc2.frequency.value = 300;
  const mix = ac.createGain();
  mix.gain.value = 0.5;
  g.gain.setValueAtTime(masterVolume * 0.9, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.05);
  osc1.connect(filter);
  osc2.connect(mix);
  mix.connect(filter);
  filter.connect(g);
  g.connect(ac.destination);
  osc1.start(t);
  osc2.start(t);
  osc1.stop(t + 0.05);
  osc2.stop(t + 0.05);
}

// Select: Tiefer Doppel-Puls -- Bestätigung
export function select() {
  if (!enabled) return;
  const ac = getCtx();
  const t = ac.currentTime;
  // Erster Puls
  const osc1 = ac.createOscillator();
  const g1 = ac.createGain();
  osc1.type = 'sine';
  osc1.frequency.value = 350;
  g1.gain.setValueAtTime(masterVolume * 0.5, t);
  g1.gain.exponentialRampToValueAtTime(0.001, t + 0.04);
  osc1.connect(g1);
  g1.connect(ac.destination);
  osc1.start(t);
  osc1.stop(t + 0.04);
  // Zweiter Puls, leicht höher
  const osc2 = ac.createOscillator();
  const g2 = ac.createGain();
  osc2.type = 'sine';
  osc2.frequency.value = 500;
  g2.gain.setValueAtTime(0.001, t);
  g2.gain.setValueAtTime(masterVolume * 0.5, t + 0.05);
  g2.gain.exponentialRampToValueAtTime(0.001, t + 0.09);
  osc2.connect(g2);
  g2.connect(ac.destination);
  osc2.start(t + 0.05);
  osc2.stop(t + 0.09);
}

// Deselect: Einzelner abfallender Puls
export function deselect() {
  if (!enabled) return;
  const ac = getCtx();
  const t = ac.currentTime;
  const osc = ac.createOscillator();
  const g = ac.createGain();
  osc.type = 'sine';
  osc.frequency.setValueAtTime(400, t);
  osc.frequency.exponentialRampToValueAtTime(180, t + 0.06);
  g.gain.setValueAtTime(masterVolume * 0.5, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.06);
  osc.connect(g);
  g.connect(ac.destination);
  osc.start(t);
  osc.stop(t + 0.06);
}

// Sweep: Gefiltertes Rauschen -- wie Servo/Motorgeräusch
export function sweep() {
  if (!enabled) return;
  const ac = getCtx();
  const t = ac.currentTime;
  const osc = ac.createOscillator();
  const filter = ac.createBiquadFilter();
  const g = ac.createGain();
  filter.type = 'bandpass';
  filter.frequency.setValueAtTime(200, t);
  filter.frequency.exponentialRampToValueAtTime(1200, t + 0.12);
  filter.Q.value = 3;
  osc.type = 'sawtooth';
  osc.frequency.value = 80;
  g.gain.setValueAtTime(masterVolume * 0.4, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.15);
  osc.connect(filter);
  filter.connect(g);
  g.connect(ac.destination);
  osc.start(t);
  osc.stop(t + 0.15);
}

// Deny: Tiefer Brumm-Impuls
export function deny() {
  if (!enabled) return;
  const ac = getCtx();
  const t = ac.currentTime;
  const osc = ac.createOscillator();
  const g = ac.createGain();
  osc.type = 'square';
  osc.frequency.setValueAtTime(100, t);
  osc.frequency.exponentialRampToValueAtTime(50, t + 0.08);
  g.gain.setValueAtTime(masterVolume * 0.6, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.1);
  osc.connect(g);
  g.connect(ac.destination);
  osc.start(t);
  osc.stop(t + 0.1);
}

// -- Steuerung --

export function setEnabled(val) { enabled = val; }
export function isEnabled() { return enabled; }
export function setVolume(vol) { masterVolume = Math.max(0, Math.min(0.3, vol)); }
