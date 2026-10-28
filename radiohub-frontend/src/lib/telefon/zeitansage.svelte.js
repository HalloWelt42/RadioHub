/**
 * Zeitansage aus Bausteinen ("Es ist" + "fünf Uhr" + "vierunddreißig"), die das Backend aus der Ablage liefert.
 * Die Bausteine werden einmal geladen und als dekodierte Puffer gehalten; abgespielt wird über Web Audio, so
 * schließen sie ohne Lücke aneinander an. Läuft etwas, wird es sanft leise gezogen (wo der Browser die Lautstärke
 * nicht stellen lässt, etwa iOS, stumm geschaltet), nach der Ansage 2 Sekunden Pause, dann wieder die alte Lautstärke.
 * Nur die Weckeransicht ruft die Ansage auf; verlässt man sie, bricht `abbrechen` sauber ab.
 */
import { api } from '../api.js';

const SCHLUESSEL_AN = 'radiohub_zeitansage';
const SCHLUESSEL_NACHTS = 'radiohub_zeitansage_nachts';
const BLENDEN_MS = 600;
const PAUSE_NACH_ANSAGE_MS = 2000;
const LUECKE_S = 0.06;          // Atempause zwischen den Bausteinen
const NACHTS_LEISE = 0.35;

function lesen(schluessel, vorgabe) {
  try { return localStorage.getItem(schluessel) ?? vorgabe; } catch { return vorgabe; }
}

function schreiben(schluessel, wert) {
  try { localStorage.setItem(schluessel, wert); } catch { /* privates Fenster */ }
}

export const zeit = $state({
  an: lesen(SCHLUESSEL_AN, '1') === '1',
  nachts: lesen(SCHLUESSEL_NACHTS, 'leise'),   // 'normal' | 'leise' | 'aus'
  bereit: false,
  fehlend: 0,
  laeuft: false
});

let _ctx = null;
let _radio = null;
let _laden = null;
let _lauf = null;
let _quellen = [];
const _puffer = new Map();

export function zeitansageSchalten(an) {
  zeit.an = an;
  schreiben(SCHLUESSEL_AN, an ? '1' : '0');
  if (!an) abbrechen();
}

export function nachtsSetzen(wert) {
  zeit.nachts = wert;
  schreiben(SCHLUESSEL_NACHTS, wert);
}

/** Das Audio-Element der Wiedergabe, das während der Ansage leise gezogen wird. */
export function radioSetzen(element) {
  _radio = element;
}

function kontext() {
  if (!_ctx) {
    _ctx = new (window.AudioContext || window.webkitAudioContext)();
    // iOS: Web Audio auch bei Stummschalter wie Wiedergabe behandeln
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch { /* älteres iOS */ }
  }
  return _ctx;
}

/** Bei jeder Berührung der Weckeransicht: Browser erlauben Ton erst nach einer Geste. */
export function entsperren() {
  const c = kontext();
  if (c.state === 'suspended') c.resume().catch(() => {});
}

export async function stand() {
  return api.fetch('/api/zeitansage');
}

/** Alle Bausteine einmal laden und dekodieren; ohne vollständigen Satz bleibt die Ansage aus. */
export function bausteineLaden() {
  if (zeit.bereit) return Promise.resolve();
  if (_laden) return _laden;
  _laden = (async () => {
    const s = await stand();
    zeit.fehlend = s.fehlend.length;
    if (s.fehlend.length) return;
    const c = kontext();
    await Promise.all(s.bausteine.map(async (name) => {
      if (_puffer.has(name)) return;
      const antwort = await fetch(`/api/zeitansage/ton/${name}`);
      if (!antwort.ok) throw new Error(`Baustein ${name}: ${antwort.status}`);
      _puffer.set(name, await c.decodeAudioData(await antwort.arrayBuffer()));
    }));
    zeit.bereit = true;
  })().catch(() => { zeit.bereit = false; }).finally(() => { _laden = null; });
  return _laden;
}

export function bausteineFuer(datum) {
  const zwei = (n) => String(n).padStart(2, '0');
  const m = datum.getMinutes();
  return ['es-ist', `stunde-${zwei(datum.getHours())}`, ...(m ? [`minute-${zwei(m)}`] : [])];
}

function warten(ms, lauf) {
  return new Promise((fertig) => {
    const ende = Date.now() + ms;
    const takt = setInterval(() => {
      if (lauf.aus || Date.now() >= ende) { clearInterval(takt); fertig(); }
    }, 50);
  });
}

async function blenden(element, ziel, ms, lauf) {
  const start = element.volume;
  const schritte = Math.max(1, Math.round(ms / 40));
  for (let i = 1; i <= schritte; i++) {
    if (lauf?.aus) break;
    element.volume = Math.min(1, Math.max(0, start + (ziel - start) * (i / schritte)));
    await new Promise((r) => setTimeout(r, 40));
  }
}

/** Die Uhrzeit ansagen; `nacht` (Nachtrot) wendet die Einstellung für nachts an. */
export async function ansagen({ nacht = false, jetzt = new Date() } = {}) {
  if (zeit.laeuft || (nacht && zeit.nachts === 'aus')) return;
  await bausteineLaden();
  if (!zeit.bereit) return;
  const c = kontext();
  if (c.state === 'suspended') { try { await c.resume(); } catch { return; } }

  const lauf = { aus: false };
  _lauf = lauf;
  zeit.laeuft = true;
  const radio = _radio && !_radio.paused && _radio.src ? _radio : null;
  const alt = radio ? radio.volume : 1;
  try {
    if (radio) {
      await blenden(radio, 0, BLENDEN_MS, lauf);
      if (radio.volume > 0.01) radio.muted = true;   // Lautstärke nicht stellbar (iOS): stumm statt leise
    }
    if (lauf.aus) return;
    const laut = c.createGain();
    laut.gain.value = nacht && zeit.nachts === 'leise' ? NACHTS_LEISE : 1;
    laut.connect(c.destination);
    let t = c.currentTime + 0.05;
    _quellen = bausteineFuer(jetzt).map((name) => {
      const quelle = c.createBufferSource();
      quelle.buffer = _puffer.get(name);
      quelle.connect(laut);
      quelle.start(t);
      t += quelle.buffer.duration + LUECKE_S;
      return quelle;
    });
    await warten((t - c.currentTime) * 1000, lauf);
    if (radio) await warten(PAUSE_NACH_ANSAGE_MS, lauf);
  } finally {
    for (const q of _quellen) { try { q.stop(); } catch { /* schon zu Ende */ } }
    _quellen = [];
    if (radio) {
      radio.muted = false;
      await blenden(radio, alt, lauf.aus ? 150 : BLENDEN_MS, null);
      radio.volume = alt;
    }
    zeit.laeuft = false;
    if (_lauf === lauf) _lauf = null;
  }
}

/** Laufende Ansage sofort beenden; das Radio geht auf die alte Lautstärke zurück. */
export function abbrechen() {
  if (_lauf) _lauf.aus = true;
  for (const q of _quellen) { try { q.stop(); } catch { /* schon zu Ende */ } }
}
