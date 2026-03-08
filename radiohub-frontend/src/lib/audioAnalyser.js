/**
 * AudioAnalyser Singleton
 *
 * Verwaltet einen einzigen AnalyserNode fuer das Audio-Element.
 * Mehrere VU-Meter koennen getRMS() aufrufen ohne Konflikte.
 *
 * createMediaElementSource() kann pro Audio-Element nur EINMAL
 * aufgerufen werden. Darum: Singleton.
 */

let _audioContext = null;
let _analyser = null;
let _sourceNode = null;
let _dataArray = null;
let _connectedElement = null;

/**
 * Verbindet das Audio-Element mit dem AnalyserNode.
 * Wird ignoriert wenn bereits verbunden (gleicher Element).
 */
export function connect(audioElement) {
  if (!audioElement) return;
  if (_connectedElement === audioElement && _analyser) return;

  try {
    if (!_audioContext) {
      _audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }

    // Nur einmal pro Element verbinden
    if (!_sourceNode) {
      _sourceNode = _audioContext.createMediaElementSource(audioElement);
    }

    if (!_analyser) {
      _analyser = _audioContext.createAnalyser();
      _analyser.fftSize = 256;
      _analyser.smoothingTimeConstant = 0.4;
      _dataArray = new Uint8Array(_analyser.frequencyBinCount);
      _sourceNode.connect(_analyser);
      _analyser.connect(_audioContext.destination);
    }

    _connectedElement = audioElement;
  } catch (e) {
    // Bereits verbunden oder nicht unterstuetzt -- kein Spam
    if (!_analyser) {
      console.warn('AudioAnalyser: Setup fehlgeschlagen:', e.message);
    }
  }
}

/**
 * Liest den aktuellen RMS-Pegel.
 * Gibt 0-1 zurueck, oder null wenn keine echten Daten (CORS-Block).
 */
export function getRMS() {
  if (!_analyser || !_dataArray) return null;

  // AudioContext resumieren falls suspended (Autoplay-Policy)
  if (_audioContext?.state === 'suspended') {
    _audioContext.resume();
  }

  _analyser.getByteTimeDomainData(_dataArray);

  // RMS berechnen (Root Mean Square)
  let sum = 0;
  for (let i = 0; i < _dataArray.length; i++) {
    const val = (_dataArray[i] - 128) / 128;
    sum += val * val;
  }
  const rms = Math.sqrt(sum / _dataArray.length);

  // Pruefen ob echte Daten kommen (alles ~128 = Stille oder CORS-Block)
  if (rms < 0.001) return null;

  return Math.min(1, rms * 3.5);
}
