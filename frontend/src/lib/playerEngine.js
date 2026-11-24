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
import { Stueckwache } from './stueckwache.js';
import { api } from './api.js';
import { ueberBackend } from './wiedergabeweg.js';
import { stromHalten } from './stromhalter.js';
import { nachbarstelle } from './reihenfolge.js';
import { bitratenwahlLesen, bitratenwahlSetzen } from './bitratenwahl.js';
import { LIVE_ABSTAND_S, pufferEnde, RAND_S, sendewerbung, startwahl } from './radio/sendewerbung';

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
/** hält den direkten Live-Strom mit eigenem Vorrat und verbindet bei Abriss neu (RAD-84) */
let _halter = null;
/** Stückwache (RAD-130): so lange ruht das Laden nach einer Schleife; weniger Vorrat als das gilt als aufgebraucht */
const LADEN_RUHT_MS = 1000, VORRAT_AUS_S = 0.5;

/** so lange darf ein Tonstück von 1 s laden, ohne aufzufallen (Messmodus) */
const STUECK_LANGSAM_MS = 800;

/** Zeit im Tonelement für "live" im Zeitversatz */
function _liveZeit() {
  const s = _audioEl.seekable;
  return Math.max(s.start(0), s.end(s.length - 1) - LIVE_ABSTAND_S);
}
/** RAD-33: den Spot beim Verbinden doch hören (die Wiedergabe beginnt dann am Anfang des Puffers) */
let _vorabHoeren = false;
const _MAX_RECONNECT = 3;
/** Weg der Wiedergabe (wiedergabeweg.js): Backend in der vollen App, direkt in der Webversion */
let _weg = ueberBackend;

/**
 * Zeigt die Fehlermeldung als Meldung der Schale (schale/Meldung.svelte).
 */
function _showPlayerError(msg) {
  if (!_appState) return;
  _appState.toast = { message: msg, type: 'error' };
  // verschwindet nach 4 s
  clearTimeout(_errorTimer);
  _errorTimer = setTimeout(() => {
    if (_appState) _appState.toast = null;
  }, 4000);
}

// === Initialisierung ===

/**
 * Setzt Audio-Element und State-Referenz.
 * Wird vom Tonausgang der Kanzel (Rechner) und von der Telefonansicht beim Einhängen aufgerufen.
 */
export function init(audioElement, appState) {
  _audioEl = audioElement;
  _appState = appState;
  if (_audioEl && _appState) {
    _audioEl.volume = _appState.volume / 100;
  }
}

/** @type {((art: string, werte: Record<string, unknown>) => void) | null} */
let _auffaellig = null;

/** Messmodus (RAD-143): was im Zeitversatz auffällt (Fehler von hls.js, Schleifen, langsame Stücke, Sprünge) */
export function beiAuffaelligem(melden) {
  _auffaellig = melden;
}

/** @type {(() => void) | null} */
let _aufnahmeVoll = null;

/** Was geschieht, wenn der Server eine Aufnahme wegen fast vollen Datenträgers beendet hat (RAD-139) */
export function beiVollemPlatz(melden) {
  _aufnahmeVoll = melden;
}

/**
 * Setzt den Weg der Wiedergabe (vor dem ersten Abspielen): woher der Strom kommt, ob es Zeitversatz und Aufnahme gibt.
 */
export function wegSetzen(weg) {
  _weg = weg;
}

/** Was der Weg kann (für die Kanzel: sie zeigt nur, was geht). */
export function faehigkeiten() {
  return { zeitversatz: _weg.zeitversatz, aufnahme: _weg.aufnahme, folgen: _weg.folgen, uebergabe: _weg.uebergabe };
}

/** Bild einer Folge über den Weg der Wiedergabe (Backend oder direkt, RAD-102), null ohne */
export function folgenBild(folge) {
  return _weg.folge?.bild(folge) ?? null;
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

  // Eine laufende Aufnahme hängt am Empfang ihres Senders, nicht am Puffer (RAD-46): sie läuft beim Senderwechsel
  // weiter, der neue Sender bekommt einen eigenen Puffer.

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
    await _pufferBeenden();
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
  _appState.werbeStart = null;
  _userModeOverride = false;
  _lastSeekPosition = 100; // Live = rechter Rand

  // --- Phase 5: Direct Stream starten ---
  if (!_audioEl) {
    _showPlayerError('Kein Audio-Element');
    _appState.isPlaying = false;
    return;
  }

  // RAD-33: wird angekündigte Werbung übersprungen, kommt der Ton von Anfang an aus dem Zeitversatz (eine Verbindung
  // zum Sender: die erkannte Werbung gehört zu dem Ton, der zu hören ist, und der Spot beim Verbinden wird nicht
  // gespielt); direkt nur, wenn das nicht geht
  if (_weg.zeitversatz && await _werbungUeberspringen(station)) {
    if (_generation !== gen) return;
    if (await _ueberZeitversatz(station, gen)) {
      _weg.merken(station);
      return;
    }
    if (_generation !== gen) return;
  }


  _direktStarten(station);

  // --- Phase 6: HLS-Buffer im Hintergrund starten (nur mit Zeitversatz im Weg) ---
  if (_weg.zeitversatz) _startHLSBackground(station, gen);

  // --- Phase 7: Last Station speichern ---
  _weg.merken(station);
}

// ============================================================
//  CASE C: Podcast abspielen
// ============================================================

/**
 * Spielt eine Podcast-Episode ab.
 */
export async function playPodcast(episode, podcast) {
  if (!_appState) return;

  const gen = ++_generation;
  _reconnectAttempts = 0;

  _savePodcastPosition();
  _stopPodcastPositionSave();
  _destroyHLS();
  _stopHLSPolling();
  _silenceAudio();

  if (_appState.hlsActive) {
    await _pufferBeenden();
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


  const folgenweg = _weg.folge;
  if (!folgenweg) {
    _showPlayerError('Folgen gibt es hier nicht');
    _appState.isPlaying = false;
    return;
  }

  // Nicht gespeicherte Folgen über den Puffer des Backends (stabiler Strom, 128 kbps AAC); gespeicherte und die der
  // Webversion spielen direkt (RAD-102)
  if (folgenweg.puffern && !episode.fassung && !episode.is_downloaded && episode.remote_audio_url && Hls.isSupported()) {
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

  // direkt: gespeichert, ohne Puffer oder wenn der Puffer nicht startet
  _audioEl.src = folgenweg.adresse(episode);
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

/**
 * Die laufende Folge in einer anderen Fassung weiterhören (RAD-26), an derselben Stelle: Original und Fassung sind gleich lang.
 * Angehalten bleibt sie angehalten.
 */
export async function folgenfassung(fassung) {
  const folge = _appState?.currentEpisode;
  if (!folge || !_audioEl || (folge.fassung || '') === fassung) return;
  const stelle = _audioEl.currentTime || 0;
  const neu = { ...folge, fassung, is_downloaded: 1, resume_position: stelle };   // wer eine Fassung hat, ist gespeichert
  if (_appState.isPlaying && !_appState.isPaused) return playPodcast(neu, folge.podcast);
  _appState.currentEpisode = neu;
  const el = _audioEl;
  el.src = _weg.folge.adresse(neu);
  el.addEventListener('loadedmetadata', () => { el.currentTime = stelle; }, { once: true });
  el.load();
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

  const gen = ++_generation;
  _reconnectAttempts = 0;

  _savePodcastPosition();
  _stopPodcastPositionSave();
  _destroyHLS();
  _stopHLSPolling();
  _silenceAudio();

  if (_appState.hlsActive) {
    await _pufferBeenden();
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
  // ein direkter Strom geht nach der Pause ab live weiter (resume): solange nicht weiterladen (RAD-84)
  if (_appState.playerMode === 'direct') _halterBeenden();
  // Podcast: Position sofort speichern
  if (_appState.playerMode === 'podcast') {
    _savePodcastPosition();
  }
}

/**
 * Setzt die Wiedergabe fort.
 * Ein direkter Strom hat keinen Puffer: weiter heißt dort neu verbinden, ab live (Nutzer 20.11.2026: Pause ist erneut
 * Spielen drücken, beendet wird nur über Stopp). Eine Wahrheit für Kanzel, Tastatur, Telefon und Sperrbildschirm.
 */
export function resume() {
  if (!_audioEl || !_appState?.isPaused) return;
  if (_appState.playerMode === 'direct' && _appState.currentStation) {
    playStation(_appState.currentStation);
    return;
  }

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

  // 0. Podcast (direkt oder HLS): Stelle speichern, solange das Tonelement sie noch kennt (danach steht sie auf 0)
  if (_appState.playerMode === 'podcast' || (_appState.playerMode === 'hls' && _appState.currentEpisode)) {
    _savePodcastPosition();
    _stopPodcastPositionSave();
  }

  // 1. HLS zerstören (löst MediaSource VOR Audio-Cleanup)
  _destroyHLS();
  _stopHLSPolling();

  // 2. Audio sofort stumm
  _silenceAudio();

  // 3. Backend HLS stoppen
  if (_appState.hlsActive) {
    void _pufferBeenden();
  }

  // 4. Eine Aufnahme läuft weiter, bis sie beendet wird (RAD-46)

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
  _appState.werbeStart = null;
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
        _audioEl.currentTime = _liveZeit();
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
        _audioEl.currentTime = _liveZeit();
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
    _audioEl.currentTime = _liveZeit();
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
        await _pufferBeenden();
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

  // auch hier über den Durchleiter: unter HTTPS lädt der Browser keinen http-Strom, und die Adresse kennt das Backend
  _direktStarten(_appState.currentStation);

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
    await _pufferBeenden();

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
 * Startet Aufnahme. Läuft der Zeitversatz, beginnt sie am Anfang des laufenden Titels (das entscheidet der Server,
 * RAD-46) und hat dann schon Ton: die Uhr beginnt bei `vorlauf_s`.
 */
export async function startRecording() {
  if (!_appState?.currentStation) return { success: false };
  if (_recordingStarting) return { success: false };
  _recordingStarting = true;

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
      _appState.recordingStationUuid = _appState.currentStation.uuid;
      _appState.recordingVorlaufS = result.vorlauf_s || 0;
      _recordingStartTime = Date.now() - (result.vorlauf_s || 0) * 1000;
      _appState.recordingElapsed = Math.floor(result.vorlauf_s || 0);
      _recordingInterval = setInterval(() => {
        _appState.recordingElapsed = Math.floor((Date.now() - _recordingStartTime) / 1000);
      }, 1000);
      _startRecordingPoll();
    }
    return result;
  } catch (e) {
    console.error('REC start error:', e);
    return { success: false, error: e.message };
  } finally {
    _recordingStarting = false;
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
      const status = await api.getRecordingStatus();

      if (!status?.recording) {
        // Backend sagt: keine Aufnahme. Frontend-State zurücksetzen.
        console.warn('Recording-Status-Poll: Backend hat keine aktive Aufnahme, setze State zurück');
        const voll = status?.ende?.status === 'disk_full' && status.ende.session_id === _appState.recordingSession;
        _resetRecordingState();
        if (voll) _aufnahmeVoll?.();
      } else {
        // die Uhr nach dem Ton der Aufnahme (mit nachgespieltem Vorlauf, ohne Wartezeit vor Werbung)
        if (typeof status.duration === 'number') {
          _recordingStartTime = Date.now() - status.duration * 1000;
        }
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
    _appState.recordingStationUuid = null;
    _appState.recordingElapsed = 0;
    _appState.recordingVorlaufS = 0;
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
  if (!_weg.aufnahme) return;        // ohne Aufnahme im Weg (Webversion) gibt es nichts wiederherzustellen
  if (_appState.isRecording) return; // Bereits aktiv, nichts tun

  try {
    const directStatus = await api.getRecordingStatus().catch(() => ({ recording: false }));
    const activeStatus = directStatus?.recording ? directStatus : null;
    if (!activeStatus) return;

    _appState.isRecording = true;
    _appState.recordingType = 'direct';
    _appState.recordingSession = activeStatus.session_id || null;
    _appState.recordingStationUuid = activeStatus.station_uuid || null;
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

    console.log('Recording State Recovery: aktiv, Session', activeStatus.session_id,
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

  if (_recordingInterval) {
    clearInterval(_recordingInterval);
    _recordingInterval = null;
  }
  _stopRecordingPoll();
  _recordingStartTime = null;

  try {
    const result = await api.stopRecording();
    _appState.isRecording = false;
    _appState.recordingType = 'none';
    _appState.recordingSession = null;
    _appState.recordingStationUuid = null;
    _appState.recordingElapsed = 0;
    return result;
  } catch (e) {
    // nur der Server weiß, ob sie noch läuft: läuft sie, bleibt sie sichtbar, sonst ist sie zu Ende
    const stand = await api.getRecordingStatus().catch(() => null);
    _resetRecordingState();
    if (!stand || stand.recording) await checkAndRecoverRecordingState();
    return { success: !!stand && !stand.recording, error: e.message };
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
    const reihe = _appState.recordingPlaylist ?? [];
    const ziel = nachbarstelle(reihe.length, reihe.findIndex(x => x.path === _appState.currentRecording?.path), 1, _appState.playMode || 'linear');
    if (ziel !== null) playRecording(reihe[ziel]);
    else stop();
  } else if (_appState?.playerMode === 'podcast' || (_appState?.playerMode === 'hls' && _appState?.currentEpisode)) {
    // Episode als gehört markieren
    if (_appState.currentEpisode?.id) {
      _weg.folge?.gehoert(_appState.currentEpisode.id);
    }
    _stopPodcastPositionSave();

    const folgen = _appState.podcastPlaylist ?? [];
    const ziel = nachbarstelle(folgen.length, _appState.currentEpisodeIndex, 1, _appState.playMode || 'linear');
    if (ziel !== null) {
      _appState.currentEpisodeIndex = ziel;
      playPodcast(folgen[ziel], _appState.podcastPlaylistPodcast);
      return;
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
    _weg.folge?.stelleMerken(_appState.currentEpisode.id, pos);
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
  // abgerissener Live-Strom: der Stromhalter verbindet selbst neu und meldet erst, wenn er aufgibt (RAD-84)
  if (error.code === 2 && _halter && _appState.playerMode === 'direct') return;

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

async function _werbungUeberspringen(station) {
  try {
    return (await sendewerbung.steckbrief(station.uuid || station.stationuuid)).ueberspringen;
  } catch {
    return false;
  }
}

/**
 * RAD-33: Wiedergabe aus dem Zeitversatz von Anfang an. Wartet, bis der Puffer genug Stücke hat; spielt der Sender
 * beim Verbinden einen Spot, beginnt die Wiedergabe nach ihm (die Restzeit steht bis dahin in appState.werbeStart).
 * Gibt false zurück, wenn der Zeitversatz nicht anläuft (dann spielt der Aufrufer direkt).
 */
async function _ueberZeitversatz(station, gen) {
  _vorabHoeren = false;
  _appState.playerMode = 'hls';      // die Kanzel zeigt nicht "direkt", während der Zeitversatz anläuft
  let result;
  try {
    result = await api.startHLS(station);
  } catch (e) {
    console.warn('Zeitversatz startet nicht, direkt:', e.message);
    _appState.playerMode = 'direct';
    return false;
  }
  if (_generation !== gen) { _verspaetet(result); return true; }
  if (result.status !== 'started' && result.status !== 'already_active') { _appState.playerMode = 'direct'; return false; }
  _hlsSessionId = result.session_id || null;
  _appState.hlsActive = true;
  _appState.canPlayHLS = true;
  _startHLSPolling(gen);
  // höchstens so lange auf Stücke und das Ende eines Spots warten (Spots sind selten länger als eine Minute)
  for (let i = 0; i < 240; i++) {
    await new Promise(r => setTimeout(r, 500));
    if (_generation !== gen) return true;
    let status;
    try { status = await api.getHLSStatus(); } catch { continue; }
    if (_generation !== gen) return true;
    _appState.hlsStatus = status;
    const wahl = _vorabHoeren ? { art: 'start', sekunde: 0 } : startwahl(status);
    if (wahl.art === 'werbung') {
      _appState.werbeStart = { stelle: wahl.stelle, rest: wahl.rest };
      continue;
    }
    if (wahl.art === 'start') {
      _appState.werbeStart = null;
      _appState.isLive = wahl.sekunde === null || pufferEnde(status) - wahl.sekunde <= LIVE_ABSTAND_S + 2;
      _switchToHLS(gen, wahl.sekunde);
      return true;
    }
  }
  _appState.werbeStart = null;
  _appState.playerMode = 'direct';
  _destroyHLS();
  return false;
}

/** Den eigenen Puffer am Server beenden, genau diese Sitzung: ein verspätetes Ende trifft keine neuere (RAD-130) */
async function _pufferBeenden(sitzung = _hlsSessionId) {
  if (sitzung === _hlsSessionId) {
    _appState.hlsActive = false;
    _appState.hlsStatus = null;
    _hlsSessionId = null;
  }
  try {
    await api.stopHLS(sitzung);
  } catch (e) {
    console.error('HLS stop error:', e);
  }
}

/** Ein Start kam erst an, als man schon gestoppt hatte: der Puffer liefe sonst ungehört weiter */
function _verspaetet(result) {
  if (result?.status === 'started' && result.session_id && !_appState?.isPlaying) void _pufferBeenden(result.session_id);
}

/** RAD-33: den Spot beim Verbinden doch hören */
export function vorabHoeren() {
  _vorabHoeren = true;
}

/** Fragmente der laufenden Wiedergabeliste (hls.js): Nummer (wie die Stücke des Puffers) und Zeit im Tonelement */
function _fragmente() {
  const stufen = _hlsInstance?.levels;
  if (!stufen?.length) return [];
  const stufe = stufen[_hlsInstance.currentLevel >= 0 ? _hlsInstance.currentLevel : 0];
  return stufe?.details?.fragments ?? [];
}

/** Sekunde des Puffers (Stelle im Ton beim Sender) -> Zeit im Tonelement; null ohne Wiedergabeliste */
export function pufferZuTon(sekunde, fragmente = _fragmente()) {
  if (!fragmente.length) return null;
  const dauer = _appState?.hlsStatus?.segment_duration || 1;
  const nummer = Math.floor(sekunde / dauer);
  const f = fragmente.find((x) => x.sn === nummer) ?? fragmente[0];
  return f.start + (sekunde - f.sn * dauer);
}

/** Zeit im Tonelement -> Sekunde des Puffers; null ohne Wiedergabeliste */
export function tonZuPuffer(zeit, fragmente = _fragmente()) {
  if (!fragmente.length) return null;
  const dauer = _appState?.hlsStatus?.segment_duration || 1;
  const f = fragmente.find((x) => zeit >= x.start && zeit < x.start + x.duration)
    ?? (zeit < fragmente[0].start ? fragmente[0] : fragmente[fragmente.length - 1]);
  return f.sn * dauer + (zeit - f.start);
}

/** RAD-33: an eine Sekunde des Puffers springen (Werbung überspringen, zurück zum Anfang einer Stelle). Nach vorn springt es
 *  nur, wenn das Ziel erreichbar ist: nie dichter an die Kante als "live" (RAD-84), sonst spränge man davor und gleich wieder
 *  (RAD-142). Liefert, ob gesprungen wurde. */
export function springeZuPuffer(sekunde) {
  const zeit = pufferZuTon(sekunde);
  if (zeit === null || !_audioEl) return false;
  const live = _audioEl.seekable.length ? _liveZeit() : Infinity;
  if (zeit > _audioEl.currentTime && live < zeit - RAND_S) return false;
  _auffaellig?.('sprung', { von: _audioEl.currentTime, nach: Math.min(zeit, live), ziel: sekunde });
  _audioEl.currentTime = Math.min(zeit, live);
  const hs = _appState.hlsStatus;
  const segment = Math.floor(sekunde / (hs?.segment_duration || 1));
  _appState.isLive = hs?.last_segment != null && zeit >= live - RAND_S;
  _appState.currentSegment = _appState.isLive ? hs.last_segment : segment;
  return true;
}

async function _startHLSBackground(station, gen) {
  try {
    const result = await api.startHLS(station);
    if (_generation !== gen) { _verspaetet(result); return; }

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

/** Fehler von hls.js, die heißen: dieses Gerät kann den Codec des unveränderten Tons nicht (RAD-92) */
const _CODEC_FEHLER = new Set(['manifestIncompatibleCodecsError', 'bufferAddCodecError', 'bufferIncompatibleCodecsError']);

function _originalNichtAbspielbar(data) {
  return _CODEC_FEHLER.has(data.details) && _appState?.hlsStatus?.original === true && bitratenwahlLesen() === 'original';
}

function _switchToHLS(gen, startSekunde = null) {
  if (_generation !== gen) return;
  if (!_audioEl || !Hls.isSupported()) return;

  _halterBeenden();
  _destroyHLS();

  // RAD-33: mit `startSekunde` beginnt die Wiedergabe an dieser Stelle des Puffers (nach dem Spot beim Verbinden)
  // statt an der Live-Kante; die Stelle ist erst mit der Wiedergabeliste bekannt
  _hlsInstance = new Hls({
    debug: false,
    enableWorker: true,
    lowLatencyMode: false,
    backBufferLength: 90,
    liveSyncDuration: LIVE_ABSTAND_S,   // Start und Live mit Vorrat statt 3 Stücken hinter der Kante (RAD-84)
    autoStartLoad: startSekunde === null
  });
  if (startSekunde !== null) {
    _hlsInstance.once(Hls.Events.LEVEL_LOADED, (event, data) => {
      if (_generation !== gen) return;
      const fragmente = data.details?.fragments ?? [];
      const roh = pufferZuTon(startSekunde, fragmente);
      const letztes = fragmente[fragmente.length - 1];
      // nie dichter an die Kante als "live" (RAD-84)
      const zeit = roh === null || !letztes ? roh : Math.max(fragmente[0].start, Math.min(roh, letztes.start + letztes.duration - LIVE_ABSTAND_S));
      _hlsInstance?.startLoad(zeit ?? -1);
      if (zeit !== null) _audioEl.currentTime = zeit;
    });
  }

  _stueckeWachen(_hlsInstance, gen);

  _hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
    if (_generation !== gen) return;
    _appState.playerMode = 'hls';
    _audioEl.play().catch(e => console.error('HLS play error:', e));
    // Nahtloser Wechsel zu HLS-Modus
  });

  _hlsInstance.on(Hls.Events.ERROR, (event, data) => {
    if (_generation !== gen) return;

    // RAD-92: kann dieses Gerät den unveränderten Ton des Senders nicht abspielen, nimmt es die Umwandlung (voll)
    if (_originalNichtAbspielbar(data)) {
      bitratenwahlSetzen('voll');
      _showPlayerError('Original wird hier nicht abgespielt: Zeitversatz umgewandelt (voll)');
      void restartHLS();
      return;
    }

    _auffaellig?.('hls_fehler', { fehler: data.details, ernst: !!data.fatal, stueck: data.frag?.sn ?? null });
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

/** Lädt hls.js dasselbe Stück in einer Schleife, ruht das Laden kurz; ist der Vorrat schon aufgebraucht, geht es hinter dem Stück
 *  weiter. Hilft das nicht, setzt die Wiedergabe neu an (RAD-130) */
function _stueckeWachen(hls, gen) {
  const wache = new Stueckwache();
  hls.on(Hls.Events.FRAG_LOADED, (event, data) => {
    if (_generation !== gen || _hlsInstance !== hls) return;
    const laden = data.frag.stats?.loading;
    if (_auffaellig && laden?.end - laden?.start > STUECK_LANGSAM_MS) _auffaellig('stueck_langsam', { stueck: data.frag.sn, ms: Math.round(laden.end - laden.start) });
    const tat = wache.geladen(data.frag.sn, Date.now());
    if (tat === 'weiter') return;
    console.warn(`Tonstück ${data.frag.sn} in einer Schleife:`, tat);
    _auffaellig?.('stueckschleife', { stueck: data.frag.sn, tat });
    if (tat === 'neu') return tonAuffrischen();
    hls.stopLoad();
    if (_audioEl && data.frag.start - _audioEl.currentTime < VORRAT_AUS_S) _audioEl.currentTime = data.frag.end + 0.05;
    setTimeout(() => { if (_generation === gen && _hlsInstance === hls) hls.startLoad(-1); }, LADEN_RUHT_MS);
  });
}

/** Die Wiedergabe am selben Ort neu ansetzen, wenn sie steht, obwohl sie laufen soll */
export function tonAuffrischen() {
  if (!_audioEl || !_appState?.isPlaying || _appState.isPaused) return;
  if (_hlsInstance) {
    _hlsInstance.recoverMediaError();
    _audioEl.play().catch(e => console.warn('Wiedergabe neu angesetzt:', e.message));
  } else if (_appState.playerMode === 'direct' && _appState.currentStation) {
    _direktStarten(_appState.currentStation);
  }
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
          _audioEl.src = _weg.folge.adresse(episode);
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
  _direktStarten(_appState.currentStation);
}

/** Den direkten Live-Strom eines Senders starten: über den Stromhalter mit Vorlauf und Neuverbinden (RAD-84) */
function _direktStarten(station) {
  _halterBeenden();
  _halter = stromHalten(_audioEl, _weg.stromAdresse(station), {
    darfSpielen: () => !_appState?.isPaused,
    beiAufgabe: (grund) => _showPlayerError(grund),
  });
}

function _halterBeenden() {
  _halter?.beenden();
  _halter = null;
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
  _halterBeenden();
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
    // RAD-81: die Quelle löst hls.js beim Abbau selbst (src entfernen und load(), das bricht ein noch laufendes Laden
    // der Blob-Adresse ab). Nimmt man src vorher selbst weg, überspringt hls.js diesen Schritt, gibt die Blob-Adresse
    // frei, und der Browser lädt sie trotzdem noch: net::ERR_FILE_NOT_FOUND in der Konsole.
    _audioEl?.pause();
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
  _weg = ueberBackend;
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
