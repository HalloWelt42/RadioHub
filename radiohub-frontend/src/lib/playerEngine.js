/**
 * RadioHub Player Engine v1.3.0
 *
 * Zentrale Playback-Steuerung mit State-Machine.
 * Löst die Probleme:
 * - Audio-Bleed bei Senderwechsel (Generation Counter)
 * - Race Conditions bei HLS-Start/Stop
 * - Unklare Button-States
 * - Fehlende Quality-Anzeige
 *
 * Prinzip: "Lieber nichts abspielen als Chaos verursachen"
 *
 * Playback Modes:
 *   'none'    - Nichts geladen
 *   'direct'  - Direkter Stream (kein Timeshift)
 *   'hls'     - HLS-Buffer (seekbar, Timeshift)
 *   'podcast' - Podcast-Episode (seekbar, feste Dauer)
 *   'recording' - Aufnahme-Wiedergabe (seekbar, feste Dauer)
 */
import Hls from 'hls.js';
import { api } from './api.js';

// === Interne State-Variablen (nicht reaktiv) ===
let _audioEl = null;
let _appState = null;
let _hlsInstance = null;
let _hlsPollInterval = null;
let _generation = 0;
let _recordingInterval = null;
let _recordingStartTime = null;
let _recordingPollInterval = null;
let _recordingStarting = false;
let _hlsSessionId = null;
let _lastSeekPosition = 0;
let _userModeOverride = false;
let _podcastPositionInterval = null;
let _errorTimer = null;
let _reconnectAttempts = 0;
const _MAX_RECONNECT = 3;

/**
 * Zeigt Fehlermeldung als Toast (nutzt das zentrale HiFiToast-System).
 */
function _showPlayerError(msg) {
  if (!_appState) return;
  _appState.toast = { message: msg, type: 'error' };
  // Auto-Dismiss nach 4s (HiFiToast hat eigene Animation)
  clearTimeout(_errorTimer);
  _errorTimer = setTimeout(() => {
    if (_appState) _appState.toast = null;
  }, 4000);
}

// === Initialisierung ===

/**
 * Setzt Audio-Element und State-Referenz.
 * Wird vom HiFiPlayer-Component beim Mount aufgerufen.
 */
export function init(audioElement, appState) {
  _audioEl = audioElement;
  _appState = appState;
  if (_audioEl && _appState) {
    _audioEl.volume = _appState.volume / 100;
  }
}

/**
 * Gibt die aktuelle Generation zurück (für Tests).
 */
export function getGeneration() {
  return _generation;
}

/**
 * Prüft ob Engine initialisiert ist.
 */
export function isInitialized() {
  return _audioEl !== null && _appState !== null;
}

// ============================================================
//  CASE A/B: Radio Station abspielen
// ============================================================

/**
 * Spielt einen Radiosender ab.
 *
 * Ablauf:
 * 1. Audio sofort stummschalten (kein Bleed!)
 * 2. HLS-Instanz zerstören
 * 3. Backend-HLS stoppen (await!)
 * 4. State zurücksetzen
 * 5. Direct Stream starten
 * 6. HLS-Buffer im Hintergrund starten
 * 7. Bei genug Segmenten: nahtlos zu HLS wechseln
 */
export async function playStation(station) {
  if (!_appState) return;

  // --- Phase 0: Bei aktiver Aufnahme sofort blockieren ---
  // MUSS vor HLS-Zerstoerung kommen, sonst wird HLS-REC im Backend
  // durch den gestoppten HLS-Buffer unbrauchbar (ERR-006).
  if (_appState.isRecording) {
    _showPlayerError('Aufnahme läuft - erst stoppen');
    return;
  }

  const gen = ++_generation;
  _reconnectAttempts = 0;

  // --- Phase 1: Sofortige Stille ---
  // REIHENFOLGE KRITISCH: Erst HLS zerstören (löst MediaSource),
  // dann Audio stummschalten (kann src jetzt sauber entfernen)
  _savePodcastPosition();
  _stopPodcastPositionSave();
  _destroyHLS();
  _stopHLSPolling();
  _silenceAudio();

  // --- Phase 2: Backend-HLS sauber stoppen ---
  if (_appState.hlsActive) {
    _appState.hlsActive = false;
    _appState.hlsStatus = null;
    _hlsSessionId = null;
    try {
      await api.stopHLS();
    } catch (e) {
      console.error('HLS stop error:', e);
    }
  }
  if (_generation !== gen) return;

  // --- Phase 4: State setzen ---
  _appState.currentStation = station;
  _appState.currentEpisode = null;
  _appState.currentRecording = null;
  _appState.isPlaying = true;
  _appState.isPaused = false;
  _appState.isLive = true;
  _appState.playerMode = 'direct';
  _appState.streamQuality = null;
  _appState.streamTitle = null;
  _appState.toast = null;
  _appState.currentSegment = null;
  _appState.canPlayDirect = true;
  _appState.canPlayHLS = null;
  _userModeOverride = false;
  _lastSeekPosition = 100; // Live = rechter Rand

  // --- Phase 5: Direct Stream starten ---
  if (!_audioEl) {
    _showPlayerError('Kein Audio-Element');
    _appState.isPlaying = false;
    return;
  }


  const url = station.custom_url || station.url_resolved || station.url;
  _audioEl.src = api.getStreamProxyUrl(url);
  _audioEl.load();

  try {
    await _audioEl.play();
  } catch (e) {
    // Autoplay-Restriction: nicht fatal, User kann manuell Play drücken
    console.warn('Autoplay blocked:', e.message);
  }
  if (_generation !== gen) return;

  // --- Phase 6: HLS-Buffer im Hintergrund starten ---
  _startHLSBackground(station, gen);

  // --- Phase 7: Last Station speichern ---
  api.updateConfig({
    last_station_uuid: station.uuid,
    last_station_name: station.name
  }).catch(() => {});
}

// ============================================================
//  CASE C: Podcast abspielen
// ============================================================

/**
 * Spielt eine Podcast-Episode ab.
 */
export async function playPodcast(episode, podcast) {
  if (!_appState) return;

  if (_appState.isRecording) {
    _showPlayerError('Aufnahme läuft - erst stoppen');
    return;
  }

  const gen = ++_generation;
  _reconnectAttempts = 0;

  _savePodcastPosition();
  _stopPodcastPositionSave();
  _destroyHLS();
  _stopHLSPolling();
  _silenceAudio();

  if (_appState.hlsActive) {
    _appState.hlsActive = false;
    _appState.hlsStatus = null;
    _hlsSessionId = null;
    try { await api.stopHLS(); } catch (_) {}
  }
  if (_generation !== gen) return;

  // State setzen
  _appState.currentEpisode = { ...episode, podcast };
  _appState.currentStation = null;
  _appState.currentRecording = null;
  _appState.isPlaying = true;
  _appState.isPaused = false;
  _appState.isLive = true;
  _appState.playerMode = 'podcast';
  _appState.streamQuality = null;
  _appState.toast = null;
  _appState.currentSegment = null;
  _lastSeekPosition = 0;

  if (!_audioEl) {
    _showPlayerError('Kein Audio-Element');
    _appState.isPlaying = false;
    return;
  }


  // Heruntergeladene Episoden: Direct Play (schnell, kein FFmpeg nötig)
  if (episode.is_downloaded && episode.id) {
    _audioEl.src = api.getEpisodePlayUrl(episode.id);
    _audioEl.playbackRate = _appState.podcastSpeed || 1.0;
    _audioEl.load();
    try {
      await _audioEl.play();
      if (episode.resume_position > 0) {
        _audioEl.currentTime = episode.resume_position;
      }
    } catch (e) {
      console.warn('Podcast autoplay blocked:', e.message);
    }
    _startPodcastPositionSave();
    return;
  }

  // Remote-Episoden: HLS-Buffer fuer stabilen Stream (128 kbps AAC)
  if (episode.remote_audio_url && Hls.isSupported()) {
    try {
      const result = await api.startHLSPodcast(episode);
      if (_generation !== gen) return;

      if (result.status === 'started' || result.status === 'already_active') {
        _hlsSessionId = result.session_id || null;
        _appState.hlsActive = true;
        _appState.hlsStatus = result;
        _startHLSPolling(gen);

        // Warten bis mind. 3 Segmente bereit sind (max 15s)
        for (let i = 0; i < 30; i++) {
          await new Promise(r => setTimeout(r, 500));
          if (_generation !== gen) return;
          const status = await api.getHLSStatus();
          if (status?.segment_count >= 3) {
            _switchToHLSPodcast(gen, episode);
            return;
          }
        }
        // Timeout: trotzdem versuchen
        _switchToHLSPodcast(gen, episode);
        return;
      }
    } catch (e) {
      console.warn('Podcast HLS fehlgeschlagen, Fallback auf Direct:', e.message);
    }
  }

  // Fallback: Direct Stream (wenn HLS nicht verfuegbar)
  _audioEl.src = api.getEpisodeStreamUrl(episode.id);
  _audioEl.playbackRate = _appState.podcastSpeed || 1.0;
  _audioEl.load();
  try {
    await _audioEl.play();
    if (episode.resume_position > 0) {
      _audioEl.currentTime = episode.resume_position;
    }
  } catch (e) {
    console.warn('Podcast autoplay blocked:', e.message);
  }
  _startPodcastPositionSave();
}

// ============================================================
//  CASE D: Aufnahme abspielen
// ============================================================

/**
 * Spielt eine Aufnahme ab.
 * recording = { path, name, session_id, station_name, date, duration, playUrl }
 * startTime: Optionale Startposition in Sekunden (verhindert kurzes Abspielen ab 0:00)
 */
export async function playRecording(recording, startTime = 0) {
  if (!_appState) return;

  if (_appState.isRecording) {
    _showPlayerError('Aufnahme läuft - erst stoppen');
    return;
  }

  const gen = ++_generation;
  _reconnectAttempts = 0;

  _savePodcastPosition();
  _stopPodcastPositionSave();
  _destroyHLS();
  _stopHLSPolling();
  _silenceAudio();

  if (_appState.hlsActive) {
    _appState.hlsActive = false;
    _appState.hlsStatus = null;
    _hlsSessionId = null;
    try { await api.stopHLS(); } catch (_) {}
  }
  if (_generation !== gen) return;

  // State setzen
  _appState.currentRecording = recording;
  _appState.currentStation = null;
  _appState.currentEpisode = null;
  _appState.isPlaying = true;
  _appState.isPaused = false;
  _appState.isLive = false;
  _appState.playerMode = 'recording';
  _appState.streamQuality = null;
  _appState.toast = null;
  _appState.currentSegment = null;
  _lastSeekPosition = 0;

  if (!_audioEl) {
    _showPlayerError('Kein Audio-Element');
    _appState.isPlaying = false;
    return;
  }

  // Media Fragment: #t=X sorgt dafür, dass der Browser direkt ab startTime lädt
  _audioEl.src = startTime > 0
    ? `${recording.playUrl}#t=${startTime}`
    : recording.playUrl;
  _audioEl.load();

  try {
    await _audioEl.play();
  } catch (e) {
    console.warn('Recording autoplay blocked:', e.message);
  }
}

// ============================================================
//  Playback Control
// ============================================================

/**
 * Pausiert die Wiedergabe.
 * HLS-Buffer läuft im Backend weiter!
 */
export function pause() {
  if (!_audioEl || !_appState?.isPlaying || _appState.isPaused) return;
  _audioEl.pause();
  _appState.isPaused = true;
  // Podcast: Position sofort speichern
  if (_appState.playerMode === 'podcast') {
    _savePodcastPosition();
  }
}

/**
 * Setzt die Wiedergabe fort.
 */
export function resume() {
  if (!_audioEl || !_appState?.isPaused) return;

  // HLS: Nach Pause sind wir hinter der Live-Kante,
  // weil während der Pause neue Segmente dazukamen.
  // isLive = false damit handleTimeUpdate die echte Position berechnet
  // statt auf 100% zu pinnen. User kann mit goLive() zurückspringen.
  if (_appState.playerMode === 'hls') {
    _appState.isLive = false;
  }

  _audioEl.play().catch(e => {
    if (_audioEl.src) {
      console.error('Resume error:', e);
      _showPlayerError('Wiedergabe konnte nicht fortgesetzt werden');
    }
  });
  _appState.isPaused = false;
}

/**
 * Wechselt zwischen Pause und Play.
 */
export function togglePause() {
  if (_appState?.isPaused) {
    resume();
  } else if (_appState?.isPlaying) {
    pause();
  }
}

/**
 * Stoppt alles: Audio, HLS, Recording.
 * "Lieber nichts abspielen als Chaos."
 */
export async function stop() {
  if (!_appState) return;
  _generation++; // Alle laufenden Operationen abbrechen

  // 1. HLS zerstören (löst MediaSource VOR Audio-Cleanup)
  _destroyHLS();
  _stopHLSPolling();

  // 2. Audio sofort stumm
  _silenceAudio();

  // 3. Backend HLS stoppen
  if (_appState.hlsActive) {
    api.stopHLS().catch(e => console.error('HLS stop error:', e));
  }

  // 4. Recording stoppen
  if (_appState.isRecording) {
    await _stopRecordingInternal();
  }

  // 4b. Podcast (direkt oder HLS): Position speichern + Intervall stoppen
  if (_appState.playerMode === 'podcast' || (_appState.playerMode === 'hls' && _appState.currentEpisode)) {
    _savePodcastPosition();
    _stopPodcastPositionSave();
  }

  // 5. State zurücksetzen
  _appState.isPlaying = false;
  _appState.isPaused = false;
  _appState.hlsActive = false;
  _appState.hlsStatus = null;
  _appState.isLive = true;
  _appState.playerMode = 'none';
  _appState.streamQuality = null;
  _appState.toast = null;
  _appState.currentSegment = null;
  _appState.canPlayDirect = true;
  _appState.canPlayHLS = null;
  _appState.currentRecording = null;
  _appState.recordingPlaylist = [];
  _appState.podcastPlaylist = [];
  _appState.podcastPlaylistPodcast = null;
  _hlsSessionId = null;
  _lastSeekPosition = 0;
  _userModeOverride = false;
}

/**
 * Setzt die Lautstärke.
 */
export function setVolume(vol) {
  if (!_appState) return;
  _appState.volume = vol;
  if (_audioEl) _audioEl.volume = vol / 100;
  localStorage.setItem('radiohub_volume', vol);
}

// ============================================================
//  Seeking
// ============================================================

/**
 * Seeked zu einer Position (0-100%).
 * Im HLS-Modus: Mappt auf Segment-Nummern für exaktes Seeking.
 */
export function seek(position) {
  if (!_audioEl) return;

  if (_appState?.playerMode === 'hls' && _appState?.currentEpisode) {
    // Podcast-HLS: Episode-Gesamtdauer fuer Seekbar, aber auf HLS-Puffer begrenzen
    const epDuration = _appState.currentEpisode.duration || _audioEl.duration || 0;
    const hlsDuration = _audioEl.duration || 0;
    if (epDuration > 0) {
      const targetTime = (position / 100) * epDuration;
      // Nicht ueber verfuegbaren HLS-Puffer hinaus seeken
      _audioEl.currentTime = Math.min(targetTime, hlsDuration > 0 ? hlsDuration - 0.5 : targetTime);
      _lastSeekPosition = position;
    }
  } else if (_appState?.playerMode === 'hls') {
    // Radio-HLS: Segment-basiertes Seeking mit Live-Pinning
    const hs = _appState.hlsStatus;
    if (!hs || hs.first_segment == null || hs.last_segment == null) {
      _lastSeekPosition = position;
      return;
    }

    const firstSeg = hs.first_segment;
    const lastSeg = hs.last_segment;
    const segRange = lastSeg - firstSeg;
    const targetSeg = Math.round(firstSeg + (position / 100) * segRange);

    if (targetSeg >= lastSeg - 1) {
      _appState.isLive = true;
      _appState.currentSegment = lastSeg;
    } else {
      _appState.isLive = false;
      _appState.currentSegment = targetSeg;
    }
    _lastSeekPosition = position;

    if (_audioEl.seekable.length > 0) {
      if (targetSeg >= lastSeg - 1) {
        const seekEnd = _audioEl.seekable.end(_audioEl.seekable.length - 1);
        _audioEl.currentTime = seekEnd - 0.3;
      } else {
        const seekStart = _audioEl.seekable.start(0);
        const seekEnd = _audioEl.seekable.end(_audioEl.seekable.length - 1);
        const seekRange = seekEnd - seekStart;
        const fraction = segRange > 0 ? (targetSeg - firstSeg) / segRange : 0;
        _audioEl.currentTime = seekStart + fraction * seekRange;
      }
    }
  } else if (_appState?.playerMode === 'podcast' || _appState?.playerMode === 'recording') {
    const dur = _audioEl.duration || 0;
    if (dur > 0) {
      _audioEl.currentTime = (position / 100) * dur;
    }
  }
}

/**
 * Springt relativ (+/- Sekunden).
 * Im HLS-Modus: Rechnet in Segment-Einheiten.
 */
export function skip(seconds) {
  if (!_audioEl || !_appState) return;
  const mode = _appState.playerMode;
  if (mode !== 'hls' && mode !== 'podcast' && mode !== 'recording') return;

  if (mode === 'hls' && _appState.currentEpisode) {
    // Podcast-HLS: Zeitbasiertes Skipping (wie normaler Podcast)
    const newTime = Math.max(0, Math.min(
      _audioEl.duration || 0,
      _audioEl.currentTime + seconds
    ));
    _audioEl.currentTime = newTime;
  } else if (mode === 'hls') {
    // Radio-HLS: Segment-basiertes Skipping
    const hs = _appState.hlsStatus;
    if (hs && hs.first_segment != null && hs.last_segment != null && _audioEl.seekable.length > 0) {
      const segDur = hs.segment_duration || 1;
      const segDelta = Math.round(seconds / segDur);
      const currentSeg = _appState.currentSegment ?? hs.last_segment;
      const firstSeg = hs.first_segment;
      const lastSeg = hs.last_segment;
      const targetSeg = Math.max(firstSeg, Math.min(lastSeg, currentSeg + segDelta));
      const segRange = lastSeg - firstSeg;

      if (targetSeg >= lastSeg - 1) {
        const seekEnd = _audioEl.seekable.end(_audioEl.seekable.length - 1);
        _audioEl.currentTime = seekEnd - 0.3;
        _appState.isLive = true;
      } else {
        const seekStart = _audioEl.seekable.start(0);
        const seekEnd = _audioEl.seekable.end(_audioEl.seekable.length - 1);
        const seekRange = seekEnd - seekStart;
        const fraction = segRange > 0 ? (targetSeg - firstSeg) / segRange : 0;
        _audioEl.currentTime = seekStart + fraction * seekRange;
        _appState.isLive = false;
      }
      _appState.currentSegment = targetSeg;
    }
  } else {
    // Podcast
    const newTime = Math.max(0, Math.min(
      _audioEl.duration || 0,
      _audioEl.currentTime + seconds
    ));
    _audioEl.currentTime = newTime;
  }
}

/**
 * Springt zur Live-Kante (nur HLS).
 */
export function goLive() {
  if (!_audioEl || _appState?.playerMode !== 'hls') return;
  if (_audioEl.seekable.length > 0) {
    const seekEnd = _audioEl.seekable.end(_audioEl.seekable.length - 1);
    _audioEl.currentTime = seekEnd - 0.5;
    _appState.isLive = true;
    const hs = _appState.hlsStatus;
    if (hs && hs.last_segment != null) {
      _appState.currentSegment = hs.last_segment;
    }
    _lastSeekPosition = 100;
  }
}

/**
 * Prüft ob Seeking möglich ist.
 */
export function canSeek() {
  if (!_appState) return false;
  return _appState.playerMode === 'podcast' || _appState.playerMode === 'hls' || _appState.playerMode === 'recording';
}

// ============================================================
//  Stream Mode Toggle (Original/HLS)
// ============================================================

/**
 * Wechselt zwischen Direct (Original) und HLS (re-encoded) Modus.
 * Nur möglich wenn der Zielmodus verfügbar ist.
 * Blockiert während aktiver Aufnahme (Mode-Wechsel würde Aufnahme stören).
 */
export function toggleStreamMode() {
  if (!_appState || !_audioEl) return;

  // Guard: Kein Mode-Wechsel während Aufnahme
  if (_appState.isRecording) return;

  if (_appState.playerMode === 'hls' && _appState.canPlayDirect) {
    _switchToDirect();
    _userModeOverride = true;
  } else if (_appState.playerMode === 'direct' && _appState.canPlayHLS === true) {
    // Backend-Buffer neu starten + direkt umschalten wenn ready
    _userModeOverride = true;
    const station = _appState.currentStation;
    const gen = _generation;
    (async () => {
      try {
        await api.stopHLS();
        _appState.hlsActive = false;
        const result = await api.startHLS(station);
        if (_generation !== gen) return;
        if (result.status === 'started' || result.status === 'already_active') {
          _hlsSessionId = result.session_id || null;
          _appState.hlsActive = true;
          _appState.hlsStatus = result;
          _startHLSPolling(gen);
          // Warten bis Segmente bereit, dann umschalten
          for (let i = 0; i < 30; i++) {
            await new Promise(r => setTimeout(r, 500));
            if (_generation !== gen) return;
            const status = await api.getHLSStatus();
            if (status?.segment_count >= 3) {
              _switchToHLS(gen);
              return;
            }
          }
          // Timeout: trotzdem versuchen
          _switchToHLS(gen);
        }
      } catch (e) {
        console.error('HLS restart on toggle failed:', e);
        _switchToHLS(gen);
      }
    })();
  }
  // canPlayHLS === null: HLS noch nicht bereit, ignorieren
}

/**
 * Wechselt von HLS zurück zu Direct Stream.
 * HLS-Polling + Backend-Buffer laufen weiter, damit
 * späteres Zurückschalten sofort möglich ist.
 */
function _switchToDirect() {
  if (!_audioEl || !_appState?.currentStation) return;

  // HLS.js Instanz zerstören, aber Backend-Buffer + Polling behalten
  _destroyHLS();

  const url = _appState.currentStation.url_resolved || _appState.currentStation.url;
  _audioEl.src = url;
  _audioEl.load();
  _audioEl.play().catch(e => console.error('Direct play error:', e));

  _appState.playerMode = 'direct';
  _appState.isLive = true;
  _appState.currentSegment = null;
  _lastSeekPosition = 100;
  // Wechsel zu Direct-Modus
}

/**
 * Prüft ob der Stream-Modus gewechselt werden kann.
 * Blockiert während aktiver Aufnahme.
 */
export function canToggleMode() {
  if (!_appState) return false;
  if (_appState.isRecording) return false;
  return (_appState.playerMode === 'hls' && _appState.canPlayDirect) ||
         (_appState.playerMode === 'direct' && _appState.canPlayHLS === true);
}

/**
 * Startet HLS-Session neu (z.B. nach Bitrate-Override-Änderung).
 * Backend-Buffer wird gestoppt und mit neuen Parametern gestartet.
 */
export async function restartHLS() {
  if (!_appState || _appState.playerMode !== 'hls') return;
  const station = _appState.currentStation;
  if (!station) return;

  try {
    // 1. Alte hls.js-Instanz komplett zerstoeren (Buffer leeren!)
    _destroyHLS();
    _stopHLSPolling();

    // 2. Backend-Session stoppen
    await api.stopHLS();
    _appState.hlsActive = false;
    _appState.hlsStatus = null;
    _hlsSessionId = null;

    // 3. Neue Session starten + auf Segmente warten + neue hls.js-Instanz
    const gen = _generation;
    const result = await api.startHLS(station);
    if (_generation !== gen) return;

    if (result.status === 'started' || result.status === 'already_active') {
      _hlsSessionId = result.session_id || null;
      _appState.hlsActive = true;
      _appState.hlsStatus = result;
      _startHLSPolling(gen);

      // Warten bis mind. 3 Segmente bereit
      for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 500));
        if (_generation !== gen) return;
        const status = await api.getHLSStatus();
        if (status?.segment_count >= 3) break;
      }
      if (_generation !== gen) return;

      // 4. Neue hls.js-Instanz mit neuer Playlist-URL verbinden
      _switchToHLS(gen);
    }
  } catch (e) {
    console.error('HLS restart failed:', e);
  }
}

// ============================================================
//  Recording (modus-abhängig: Direct-REC vs HLS-REC)
// ============================================================

/**
 * Startet Aufnahme. Bei aktivem HLS-Buffer: HLS-REC mit Lookback, sonst Direct-REC.
 * Prüft hlsActive (tatsaechlicher HLS-Status), nicht playerMode.
 */
export async function startRecording() {
  if (!_appState?.currentStation) return { success: false };
  if (_recordingStarting) return { success: false };
  _recordingStarting = true;

  try {
    if (_appState.hlsActive) {
      return await _startHlsRecording();
    }
    return await _startDirectRecording();
  } finally {
    _recordingStarting = false;
  }
}

async function _startDirectRecording() {
  try {
    const result = await api.startRecording({
      station_uuid: _appState.currentStation.uuid,
      station_name: _appState.currentStation.name,
      stream_url: _appState.currentStation.url_resolved || _appState.currentStation.url,
      bitrate: _appState.currentStation.bitrate || 128
    });

    if (result.success) {
      _appState.isRecording = true;
      _appState.recordingType = 'direct';
      _appState.recordingSession = result.session_id;
      _recordingStartTime = Date.now();
      _appState.recordingElapsed = 0;
      _recordingInterval = setInterval(() => {
        _appState.recordingElapsed = Math.floor((Date.now() - _recordingStartTime) / 1000);
      }, 1000);
      _startRecordingPoll();
    }
    return result;
  } catch (e) {
    console.error('Direct-REC start error:', e);
    return { success: false, error: e.message };
  }
}

async function _startHlsRecording() {
  try {
    // Lookback aus Config (Default 5 Minuten = 300s)
    const lookbackMinutes = _appState.hlsRecLookbackMinutes || 5;
    const result = await api.startHlsRecording(lookbackMinutes * 60);

    if (result.success) {
      _appState.isRecording = true;
      _appState.recordingType = 'hls-rec';
      _appState.recordingSession = result.session_id;
      _recordingStartTime = Date.now();
      _appState.recordingElapsed = 0;
      _recordingInterval = setInterval(() => {
        _appState.recordingElapsed = Math.floor((Date.now() - _recordingStartTime) / 1000);
      }, 1000);
      _startRecordingPoll();
    }
    return result;
  } catch (e) {
    console.error('HLS-REC start error:', e);
    return { success: false, error: e.message };
  }
}

/**
 * Pollt Backend-Recording-Status alle 5 Sekunden.
 * Erkennt Backend-Neustart/Crash: Wenn Backend keine aktive Aufnahme
 * meldet aber Frontend denkt es läuft eine, wird State zurückgesetzt.
 */
function _startRecordingPoll() {
  _stopRecordingPoll();
  _recordingPollInterval = setInterval(async () => {
    if (!_appState?.isRecording) {
      _stopRecordingPoll();
      return;
    }
    try {
      const recType = _appState.recordingType;
      const status = recType === 'hls-rec'
        ? await api.getHlsRecordingStatus()
        : await api.getRecordingStatus();

      if (!status?.recording) {
        // Backend sagt: keine Aufnahme. Frontend-State zurücksetzen.
        console.warn('Recording-Status-Poll: Backend hat keine aktive Aufnahme, setze State zurück');
        _resetRecordingState();
      } else {
        // ICY-Daten und Events aus Status in State übernehmen
        _appState.recordingIcyCount = status.icy_count || 0;
        _appState.recordingIcyEntries = status.icy_entries || [];
        _appState.recordingEvents = status.events || [];
        // ICY-Titel live aktualisieren
        if (status.icy_title) {
          _appState.streamTitle = status.icy_title;
        }
        // Codec/Bitrate aus Backend aktualisieren (einmalig wenn noch nicht gesetzt)
        if (!_appState.streamQuality && (status.codec || status.bitrate)) {
          _appState.streamQuality = {
            inputCodec: status.codec || null,
            inputBitrate: status.bitrate || null,
            outputBitrate: null,
            sampleRate: null
          };
        }
      }
    } catch (e) {
      // Netzwerkfehler: nicht sofort reagieren, nächster Poll klärt
    }
  }, 5000);
}

function _stopRecordingPoll() {
  if (_recordingPollInterval) {
    clearInterval(_recordingPollInterval);
    _recordingPollInterval = null;
  }
}

function _resetRecordingState() {
  if (_recordingInterval) {
    clearInterval(_recordingInterval);
    _recordingInterval = null;
  }
  _stopRecordingPoll();
  _recordingStartTime = null;
  if (_appState) {
    _appState.isRecording = false;
    _appState.recordingType = 'none';
    _appState.recordingSession = null;
    _appState.recordingElapsed = 0;
    _appState.recordingIcyCount = 0;
    _appState.recordingIcyEntries = [];
    _appState.recordingEvents = [];
  }
}

/**
 * Prüft beim App-Start ob im Backend eine Aufnahme läuft
 * und stellt den Frontend-State entsprechend wieder her.
 */
export async function checkAndRecoverRecordingState() {
  if (!_appState) return;
  if (_appState.isRecording) return; // Bereits aktiv, nichts tun

  try {
    const [directStatus, hlsStatus] = await Promise.all([
      api.getRecordingStatus().catch(() => ({ recording: false })),
      api.getHlsRecordingStatus().catch(() => ({ recording: false }))
    ]);

    const activeStatus = hlsStatus?.recording ? hlsStatus : directStatus?.recording ? directStatus : null;
    if (!activeStatus) return;

    const recType = hlsStatus?.recording ? 'hls-rec' : 'direct';

    _appState.isRecording = true;
    _appState.recordingType = recType;
    _appState.recordingSession = activeStatus.session_id || null;
    _appState.recordingElapsed = Math.floor(activeStatus.duration || 0);
    _appState.recordingIcyCount = activeStatus.icy_count || 0;
    _appState.recordingIcyEntries = activeStatus.icy_entries || [];
    _appState.recordingEvents = activeStatus.events || [];
    _recordingStartTime = Date.now() - (_appState.recordingElapsed * 1000);
    _recordingInterval = setInterval(() => {
      _appState.recordingElapsed = Math.floor((Date.now() - _recordingStartTime) / 1000);
    }, 1000);
    _startRecordingPoll();

    // Sender wiederherstellen falls nicht bereits gesetzt
    if (!_appState.currentStation && activeStatus.station_uuid) {
      const stations = _appState.stations || [];
      const match = stations.find(s => s.uuid === activeStatus.station_uuid);
      if (match) {
        _appState.currentStation = match;
      } else {
        // Minimales Station-Objekt aus Status-Daten
        _appState.currentStation = {
          uuid: activeStatus.station_uuid,
          name: activeStatus.station_name || 'Unbekannt'
        };
      }
    }

    // Display-Daten wiederherstellen
    if (activeStatus.icy_title) {
      _appState.streamTitle = activeStatus.icy_title;
    }
    if (activeStatus.codec) {
      _appState.streamQuality = {
        inputCodec: activeStatus.codec,
        inputBitrate: activeStatus.bitrate || null,
        outputBitrate: null,
        sampleRate: null
      };
    }

    console.log('Recording State Recovery:', recType, 'aktiv, Session', activeStatus.session_id,
      'Station:', activeStatus.station_name);
  } catch (e) {
    // Fehler bei Recovery ignorieren -- normaler Betrieb ohne Aufnahme
  }
}

/**
 * Stoppt Aufnahme (automatisch den richtigen Modus).
 */
export async function stopRecording() {
  return _stopRecordingInternal();
}

async function _stopRecordingInternal() {
  if (!_appState) return { success: false };

  const recType = _appState.recordingType;

  if (_recordingInterval) {
    clearInterval(_recordingInterval);
    _recordingInterval = null;
  }
  _stopRecordingPoll();
  _recordingStartTime = null;

  try {
    const result = recType === 'hls-rec'
      ? await api.stopHlsRecording()
      : await api.stopRecording();
    _appState.isRecording = false;
    _appState.recordingType = 'none';
    _appState.recordingSession = null;
    _appState.recordingElapsed = 0;
    return result;
  } catch (e) {
    _appState.isRecording = false;
    _appState.recordingType = 'none';
    _appState.recordingSession = null;
    _appState.recordingElapsed = 0;
    return { success: false, error: e.message };
  }
}

// ============================================================
//  Audio Event Handlers (vom Component aufgerufen)
// ============================================================

/**
 * Berechnet Seek-Position und Live-Status.
 * Im HLS-Modus: Segment-basiert mit Anti-Jitter.
 * Gibt { currentTime, duration, seekPosition } zurück.
 */
export function handleTimeUpdate() {
  if (!_audioEl || !_appState) return null;

  const currentTime = _audioEl.currentTime || 0;
  const duration = _audioEl.duration || 0;
  let seekPosition = _lastSeekPosition;

  if (_appState.playerMode === 'hls' && _appState.currentEpisode) {
    // Podcast-HLS: Episode-Gesamtdauer verwenden (nicht die wachsende HLS-Puffer-Dauer)
    const epDuration = _appState.currentEpisode.duration || duration;
    if (epDuration > 0) {
      seekPosition = (currentTime / epDuration) * 100;
      _lastSeekPosition = seekPosition;
    }
    return { currentTime, duration: epDuration, seekPosition };
  } else if (_appState.playerMode === 'hls') {
    // Radio-HLS: Segment-basiertes Tracking mit Live-Pinning
    const hs = _appState.hlsStatus;
    if (hs && hs.first_segment != null && hs.last_segment != null && _audioEl.seekable.length > 0) {
      const firstSeg = hs.first_segment;
      const lastSeg = hs.last_segment;
      const segRange = lastSeg - firstSeg;

      if (segRange > 0) {
        if (_appState.isLive) {
          _appState.currentSegment = lastSeg;
          seekPosition = 100;
          _lastSeekPosition = 100;
        } else {
          const seekStart = _audioEl.seekable.start(0);
          const seekEnd = _audioEl.seekable.end(_audioEl.seekable.length - 1);
          const seekRange = seekEnd - seekStart;

          const fraction = seekRange > 0 ? (currentTime - seekStart) / seekRange : 0;
          const currentSeg = Math.round(firstSeg + fraction * segRange);

          if (_appState.currentSegment !== currentSeg) {
            _appState.currentSegment = currentSeg;
            seekPosition = ((currentSeg - firstSeg) / segRange) * 100;
            _lastSeekPosition = seekPosition;
          }
        }
      }
    }
  } else if (duration > 0 && (_appState.playerMode === 'podcast' || _appState.playerMode === 'recording')) {
    seekPosition = (currentTime / duration) * 100;
    _lastSeekPosition = seekPosition;
  }

  return { currentTime, duration, seekPosition };
}

/**
 * Audio-Ende Handler.
 * Bei Recording-Playlist: automatisch nächsten Track abspielen.
 */
export function handleEnded() {
  if (_appState?.playerMode === 'recording') {
    const playlist = _appState.recordingPlaylist;
    const mode = _appState.playMode || 'linear';

    if (playlist?.length > 0 && _appState.currentRecording) {
      const idx = playlist.findIndex(s => s.path === _appState.currentRecording.path);

      if (mode === 'shuffle') {
        // Zufällig, aber nicht denselben Track
        const candidates = playlist.length > 1
          ? playlist.filter((_, i) => i !== idx)
          : playlist;
        const next = candidates[Math.floor(Math.random() * candidates.length)];
        playRecording(next);
        return;
      }

      if (mode === 'reverse') {
        // Rückwärts: vorheriger Track, am Anfang stoppen
        if (idx > 0) {
          playRecording(playlist[idx - 1]);
        }
        return;
      }

      if (mode === 'loop') {
        // Nächster Track, am Ende zurück zum Anfang
        if (idx >= 0 && idx < playlist.length - 1) {
          playRecording(playlist[idx + 1]);
        } else {
          playRecording(playlist[0]);
        }
        return;
      }

      // linear: nächster Track, am Ende stoppen
      if (idx >= 0 && idx < playlist.length - 1) {
        playRecording(playlist[idx + 1]);
        return;
      }
    }
    stop();
  } else if (_appState?.playerMode === 'podcast' || (_appState?.playerMode === 'hls' && _appState?.currentEpisode)) {
    // Episode als gehört markieren
    if (_appState.currentEpisode?.id) {
      api.markEpisodePlayed(_appState.currentEpisode.id).catch(() => {});
      api.updateEpisodePosition(_appState.currentEpisode.id, 0).catch(() => {});
    }
    _stopPodcastPositionSave();

    const playlist = _appState.podcastPlaylist;
    const mode = _appState.playMode || 'linear';
    const podcast = _appState.podcastPlaylistPodcast;

    if (playlist?.length > 0) {
      const idx = _appState.currentEpisodeIndex;

      if (mode === 'shuffle') {
        const candidates = playlist.length > 1
          ? playlist.filter((_, i) => i !== idx) : playlist;
        const next = candidates[Math.floor(Math.random() * candidates.length)];
        _appState.currentEpisodeIndex = playlist.indexOf(next);
        playPodcast(next, podcast);
        return;
      }

      if (mode === 'reverse') {
        // Rückwärts: vorherige Episode, am Anfang stoppen
        if (idx > 0) {
          _appState.currentEpisodeIndex = idx - 1;
          playPodcast(playlist[idx - 1], podcast);
        }
        return;
      }

      if (mode === 'loop') {
        if (idx >= 0 && idx < playlist.length - 1) {
          _appState.currentEpisodeIndex = idx + 1;
          playPodcast(playlist[idx + 1], podcast);
        } else {
          _appState.currentEpisodeIndex = 0;
          playPodcast(playlist[0], podcast);
        }
        return;
      }

      // linear: nächster Track, am Ende stoppen
      if (idx >= 0 && idx < playlist.length - 1) {
        _appState.currentEpisodeIndex = idx + 1;
        playPodcast(playlist[idx + 1], podcast);
        return;
      }
    }
    stop();
  }
}

// ============================================================
//  Podcast Position-Speicherung (alle 15s)
// ============================================================

function _startPodcastPositionSave() {
  _stopPodcastPositionSave();
  _podcastPositionInterval = setInterval(() => {
    _savePodcastPosition();
  }, 15000);
}

function _stopPodcastPositionSave() {
  if (_podcastPositionInterval) {
    clearInterval(_podcastPositionInterval);
    _podcastPositionInterval = null;
  }
}

function _savePodcastPosition() {
  if (!_appState?.currentEpisode?.id || !_audioEl) return;
  if (_appState.playerMode !== 'podcast') return;
  const pos = Math.floor(_audioEl.currentTime || 0);
  if (pos > 0) {
    api.updateEpisodePosition(_appState.currentEpisode.id, pos).catch(() => {});
  }
}

// ============================================================
//  Playback Rate
// ============================================================

export function setPlaybackRate(rate) {
  if (_audioEl) {
    _audioEl.playbackRate = rate;
  }
}

/**
 * Audio-Error Handler.
 *
 * Error Code 4 (SRC_NOT_SUPPORTED) wird ignoriert:
 * - Tritt bei Source-Wechseln auf wenn die alte blob-URL ungültig wird
 * - Echte Format-Fehler werden durch play()-Promise und HLS-Error-Handler gefangen
 */
export function handleError(event) {
  const error = event?.target?.error;
  if (!error || !_appState) return;
  if (error.code === 4) return; // Transienter Fehler bei Source-Wechsel

  const messages = {
    1: 'Medienladen abgebrochen',
    2: 'Netzwerkfehler',
    3: 'Dekodierungsfehler'
  };

  // Dekodierungsfehler im Direct-Modus: Codec nicht abspielbar
  if (error.code === 3 && _appState.playerMode === 'direct') {
    _appState.canPlayDirect = false;
    // Automatisch zu HLS wechseln wenn verfügbar
    if (_appState.canPlayHLS === true) {
      _switchToHLS(_generation);
      return;
    }
  }

  // Netzwerkfehler bei Podcast/Recording: Auto-Reconnect
  const mode = _appState.playerMode;
  if (error.code === 2 && (mode === 'podcast' || mode === 'recording')) {
    if (_reconnectAttempts < _MAX_RECONNECT) {
      _reconnectAttempts++;
      console.warn(`Netzwerkfehler bei ${mode}, Reconnect ${_reconnectAttempts}/${_MAX_RECONNECT}...`);
      _showPlayerError(`Verbindung unterbrochen - Reconnect ${_reconnectAttempts}/${_MAX_RECONNECT}...`);
      _attemptReconnect(_generation);
      return;
    }
    // Max Retries erreicht
    _reconnectAttempts = 0;
  }

  const msg = messages[error.code] || 'Wiedergabefehler';
  _showPlayerError(msg);
  console.error('Audio error:', error.code, msg);
}

/**
 * Reconnect bei Podcast/Recording nach Netzwerkfehler.
 * Speichert Position, lädt neu, seeked zurück.
 */
function _attemptReconnect(gen) {
  if (!_audioEl || !_appState || _generation !== gen) return;

  const savedTime = _audioEl.currentTime || 0;
  const savedSrc = _audioEl.src;

  setTimeout(() => {
    if (_generation !== gen || !_audioEl || !_appState) return;

    _audioEl.src = savedSrc;
    _audioEl.load();
    _audioEl.play().then(() => {
      if (_generation !== gen) return;
      if (savedTime > 0) {
        _audioEl.currentTime = savedTime;
      }
      _reconnectAttempts = 0;
      _appState.toast = null; // Reconnect-Toast ausblenden
      console.log('Reconnect erfolgreich, Position:', savedTime);
    }).catch(e => {
      console.error('Reconnect fehlgeschlagen:', e);
      _showPlayerError('Wiedergabe konnte nicht fortgesetzt werden');
    });
  }, 2000); // 2s warten vor Retry
}

// ============================================================
//  HLS Management (intern)
// ============================================================

async function _startHLSBackground(station, gen) {
  try {
    const result = await api.startHLS(station);
    if (_generation !== gen) return;

    if (result.status === 'started' || result.status === 'already_active') {
      _hlsSessionId = result.session_id || null;
      _appState.hlsActive = true;
      _appState.hlsStatus = result;
      _startHLSPolling(gen);
      _waitForHLSSegments(gen);
    }
  } catch (e) {
    if (_generation !== gen) return;
    console.error('HLS start failed:', e);
    _appState.canPlayHLS = false;
    // Direct Stream läuft weiter - HLS ist optional
  }
}

function _startHLSPolling(gen) {
  _stopHLSPolling();
  _hlsPollInterval = setInterval(async () => {
    if (_generation !== gen || !_appState?.hlsActive) {
      _stopHLSPolling();
      return;
    }
    try {
      const status = await api.getHLSStatus();
      if (_generation !== gen) return;
      _appState.hlsStatus = status;

      // Quality-Info aktualisieren
      if (status.input_codec) {
        _appState.streamQuality = {
          inputCodec: status.input_codec,
          inputBitrate: status.input_bitrate,
          outputBitrate: status.output_bitrate,
          sampleRate: status.sample_rate
        };
      }

      // ICY-Titel aus HLS-Buffer propagieren
      if (status.icy_title) {
        _appState.streamTitle = status.icy_title;
      }

      // Wenn Live, Position an rechten Rand pinnen
      if (_appState.isLive && status.last_segment != null) {
        _appState.currentSegment = status.last_segment;
        _lastSeekPosition = 100;
      }
    } catch (e) {
      // Still - Polling kann mal scheitern
    }
  }, 2000);
}

function _stopHLSPolling() {
  if (_hlsPollInterval) {
    clearInterval(_hlsPollInterval);
    _hlsPollInterval = null;
  }
}

async function _waitForHLSSegments(gen) {
  // Alle 500ms prüfen, max 15 Sekunden warten
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 500));
    if (_generation !== gen) return;
    if (!_appState?.hlsActive) return;
    if (!_appState?.isPlaying) return;

    if (_appState.hlsStatus?.segment_count >= 3) {
      _appState.canPlayHLS = true;
      // Kein Auto-Switch: Direct bleibt Default.
      // User kann manuell zu HLS wechseln (Mode-Button).
      // Nur bei Codec-Fehler (handleError) wird automatisch gewechselt.
      return;
    }
  }
  // HLS-Segmente nicht rechtzeitig bereit
}

function _switchToHLS(gen) {
  if (_generation !== gen) return;
  if (!_audioEl || !Hls.isSupported()) return;

  _destroyHLS();

  _hlsInstance = new Hls({
    debug: false,
    enableWorker: true,
    lowLatencyMode: false,
    backBufferLength: 90
  });

  _hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
    if (_generation !== gen) return;
    _appState.playerMode = 'hls';
    _audioEl.play().catch(e => console.error('HLS play error:', e));
    // Nahtloser Wechsel zu HLS-Modus
  });

  _hlsInstance.on(Hls.Events.ERROR, (event, data) => {
    if (_generation !== gen) return;

    if (data.fatal) {
      console.error('HLS Fatal Error:', data.type, data.details);
      if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
        // HLS Network Error - Reconnect in 3s
        setTimeout(() => _hlsInstance?.startLoad(), 3000);
      } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
        // HLS Media Error - Recovery
        _hlsInstance?.recoverMediaError();
      } else {
        // Fatal: Zurück zu Direct Stream
        // Fataler HLS Error - Fallback zu Direct Stream
        _destroyHLS();
        _appState.playerMode = 'direct';
        _playDirectFallback(gen);
      }
    }
  });

  const playlistUrl = api.getHLSPlaylistUrl(_hlsSessionId);
  _hlsInstance.loadSource(playlistUrl);
  _hlsInstance.attachMedia(_audioEl);
}

/**
 * HLS-Podcast-Modus: hls.js fuer Podcast-Episode initialisieren.
 * Unterschied zu Radio-HLS: playerMode bleibt 'podcast', Resume-Position wird gesetzt.
 */
function _switchToHLSPodcast(gen, episode) {
  if (_generation !== gen) return;
  if (!_audioEl || !Hls.isSupported()) return;

  _destroyHLS();

  _hlsInstance = new Hls({
    debug: false,
    enableWorker: true,
    lowLatencyMode: false,
    backBufferLength: 300  // Podcast: mehr Back-Buffer fuer Seeking
  });

  _hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
    if (_generation !== gen) return;
    // playerMode bleibt 'podcast' damit Navigation/Skip korrekt funktionieren
    // (HLS ist nur der Transport, nicht der logische Modus)
    _appState.playerMode = 'podcast';
    _audioEl.playbackRate = _appState?.podcastSpeed || 1.0;
    _audioEl.play().then(() => {
      if (_generation !== gen || !_audioEl) return;
      if (episode.resume_position > 0) {
        _audioEl.currentTime = episode.resume_position;
      }
    }).catch(e => console.error('Podcast HLS play error:', e));
    _startPodcastPositionSave();
  });

  let podcastHlsRetries = 0;
  _hlsInstance.on(Hls.Events.ERROR, (event, data) => {
    if (_generation !== gen) return;
    if (data.fatal) {
      console.error('Podcast HLS Fatal Error:', data.type, data.details);
      if (data.type === Hls.ErrorTypes.NETWORK_ERROR && podcastHlsRetries < 3) {
        podcastHlsRetries++;
        setTimeout(() => _hlsInstance?.startLoad(), 3000);
      } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
        _hlsInstance?.recoverMediaError();
      } else {
        // Fatal: Fallback zu Direct-Stream
        _destroyHLS();
        if (_appState && episode?.id) {
          _audioEl.src = api.getEpisodeStreamUrl(episode.id);
          _audioEl.load();
          _audioEl.play().catch(e => console.warn('Podcast fallback error:', e));
        }
      }
    }
  });

  const playlistUrl = api.getHLSPlaylistUrl(_hlsSessionId);
  _hlsInstance.loadSource(playlistUrl);
  _hlsInstance.attachMedia(_audioEl);
}

function _playDirectFallback(gen) {
  if (_generation !== gen || !_audioEl || !_appState?.currentStation) return;
  const url = _appState.currentStation.url_resolved || _appState.currentStation.url;
  _audioEl.src = url;
  _audioEl.load();
  _audioEl.play().catch(e => console.error('Fallback play error:', e));
}

// ============================================================
//  Interne Hilfsfunktionen
// ============================================================

/**
 * Audio sofort stummschalten und Source entfernen.
 * Verhindert Audio-Bleed bei Senderwechsel.
 *
 * WICHTIG: _destroyHLS() MUSS vorher aufgerufen werden!
 * Wenn HLS.js eine MediaSource hält, kann removeAttribute('src')
 * den alten Stream nicht korrekt lösen.
 */
function _silenceAudio() {
  if (!_audioEl) return;
  _audioEl.pause();
  _audioEl.srcObject = null;      // MediaSource-Referenz lösen
  _audioEl.removeAttribute('src');
  // KEIN load() hier - das feuert Error Code 4 (SRC_NOT_SUPPORTED) async.
  // Der nächste src-Zuweisung + load() bricht den alten Request automatisch ab.
}


/**
 * HLS.js-Instanz zerstören.
 * Muss VOR _silenceAudio() aufgerufen werden,
 * damit die MediaSource sauber gelöst wird.
 */
function _destroyHLS() {
  if (_hlsInstance) {
    // Audio-Element VOR destroy() vom Blob-URL lösen,
    // damit kein Error Code 4 feuert wenn MediaSource wegfällt
    if (_audioEl) {
      _audioEl.pause();
      _audioEl.removeAttribute('src');
      _audioEl.srcObject = null;
    }
    _hlsInstance.destroy(); // Ruft intern detachMedia() auf
    _hlsInstance = null;
  }
}

// ============================================================
//  Test-Hilfsfunktionen
// ============================================================

/**
 * Für Tests: Setzt alle internen State-Variablen zurück.
 */
export function _resetForTest() {
  _destroyHLS();
  _stopHLSPolling();
  _silenceAudio();
  if (_recordingInterval) {
    clearInterval(_recordingInterval);
    _recordingInterval = null;
  }
  _stopRecordingPoll();
  _audioEl = null;
  _appState = null;
  _generation = 0;
  _recordingStartTime = null;
  _hlsSessionId = null;
  _lastSeekPosition = 0;
  _userModeOverride = false;
}

/**
 * Für Tests: Zugriff auf interne HLS-Instanz.
 */
export function _getHLSInstance() {
  return _hlsInstance;
}
