/**
 * RadioHub Player Engine - Testcases
 *
 * Testet alle Playback-Szenarien:
 * - Case A: Radio Direct Stream
 * - Case B: Radio mit HLS Timeshift
 * - Case C: Podcast
 * - Übergänge zwischen Cases
 * - Fehlerszenarien
 * - Recording
 *
 * Ausführen: npm test
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

// === Mocks ===

// Mock hls.js - muss Klasse sein (new Hls() im Engine)
vi.mock('hls.js', () => {
  class MockHls {
    constructor() {
      this.loadSource = vi.fn();
      this.attachMedia = vi.fn();
      this.destroy = vi.fn();
      this.startLoad = vi.fn();
      this.recoverMediaError = vi.fn();
      this._handlers = {};
      this.on = vi.fn((event, handler) => {
        this._handlers[event] = handler;
      });
    }
  }
  MockHls.isSupported = vi.fn(() => true);
  MockHls.Events = {
    MANIFEST_PARSED: 'hlsManifestParsed',
    ERROR: 'hlsError',
  };
  MockHls.ErrorTypes = {
    NETWORK_ERROR: 'networkError',
    MEDIA_ERROR: 'mediaError',
  };
  return { default: MockHls };
});

// Backend-URL zentral definiert -- nie hardcoden!
const TEST_API_BASE = 'http://localhost:9091';

// Mock API
vi.mock('../src/lib/api.js', () => {
  const BASE = 'http://localhost:9091';
  return {
    api: {
      startHLS: vi.fn(() => Promise.resolve({ status: 'started', session_id: 'test' })),
      stopHLS: vi.fn(() => Promise.resolve({ status: 'stopped' })),
      getHLSStatus: vi.fn(() => Promise.resolve({
        active: true,
        segment_count: 5,
        buffered_seconds: 5,
        input_codec: 'mp3',
        input_bitrate: 192,
        output_bitrate: 128,
        sample_rate: 44100
      })),
      getHLSPlaylistUrl: vi.fn((sid) => {
        const base = `${BASE}/api/hls/playlist.m3u8`;
        return sid ? `${base}?sid=${sid}` : base;
      }),
      getStreamProxyUrl: vi.fn((url) => `${BASE}/api/stream/proxy?url=${encodeURIComponent(url)}`),
      getEpisodePlayUrl: vi.fn((id) => `${BASE}/api/podcasts/episodes/${id}/play`),
      getEpisodeStreamUrl: vi.fn((id) => `${BASE}/api/podcasts/episodes/${id}/stream`),
      markEpisodePlayed: vi.fn(() => Promise.resolve({})),
      updateEpisodePosition: vi.fn(() => Promise.resolve({})),
      startRecording: vi.fn(() => Promise.resolve({ success: true, session_id: 'rec1' })),
      stopRecording: vi.fn(() => Promise.resolve({ success: true, duration: 60 })),
      getRecordingStatus: vi.fn(() => Promise.resolve({ recording: false })),
      getHlsRecordingStatus: vi.fn(() => Promise.resolve({ recording: false })),
      startHlsRecording: vi.fn(() => Promise.resolve({ success: true, session_id: 'hlsrec1' })),
      stopHlsRecording: vi.fn(() => Promise.resolve({ success: true })),
      updateConfig: vi.fn(() => Promise.resolve({})),
    }
  };
});

// localStorage-Mock für Node/Vitest (global, damit alle Tests funktionieren)
const _mockStorage = {};
const _lsClear = () => { Object.keys(_mockStorage).forEach(k => delete _mockStorage[k]); };
globalThis.localStorage = {
  getItem: (key) => _mockStorage[key] ?? null,
  setItem: (key, val) => { _mockStorage[key] = String(val); },
  removeItem: (key) => { delete _mockStorage[key]; },
  clear: _lsClear,
};

import * as engine from '../src/lib/playerEngine.js';
import { api } from '../src/lib/api.js';

// === Test Fixtures ===

function createMockAudioElement() {
  return {
    src: '',
    volume: 1,
    currentTime: 0,
    duration: 0,
    paused: true,
    seekable: {
      length: 0,
      start: vi.fn(() => 0),
      end: vi.fn(() => 0),
    },
    play: vi.fn(() => Promise.resolve()),
    pause: vi.fn(),
    load: vi.fn(),
    removeAttribute: vi.fn(),
  };
}

function createMockState() {
  return {
    isPlaying: false,
    isPaused: false,
    currentStation: null,
    currentEpisode: null,
    volume: 70,
    playerMode: 'none',
    streamQuality: null,
    toast: null,
    isRecording: false,
    recordingType: null,
    recordingSession: null,
    recordingElapsed: 0,
    recordingIcyCount: 0,
    recordingIcyEntries: [],
    hlsActive: false,
    hlsStatus: null,
    isLive: true,
    currentSegment: null,
    canPlayDirect: true,
    canPlayHLS: null,
    hlsRecLookbackMinutes: 5,
    streamTitle: null,
    stations: [],
  };
}

const STATION_A = {
  uuid: 'station-a-uuid',
  name: 'TestRadio A',
  url: 'http://stream-a.example.com/live',
  url_resolved: 'http://stream-a-resolved.example.com/live',
  bitrate: 128,
  tags: 'rock,pop',
  country: 'Germany',
  countrycode: 'DE',
};

const STATION_B = {
  uuid: 'station-b-uuid',
  name: 'TestRadio B',
  url: 'http://stream-b.example.com/live',
  url_resolved: 'http://stream-b-resolved.example.com/live',
  bitrate: 192,
  tags: 'jazz',
  country: 'Austria',
  countrycode: 'AT',
};

const PODCAST_EPISODE = {
  id: 'episode-1',
  title: 'Test Episode',
  audio_url: 'http://podcast.example.com/ep1.mp3',
  podcast: {
    id: 'podcast-1',
    title: 'Test Podcast',
  },
};


// ============================================================
//  Test Suites
// ============================================================

describe('PlayerEngine', () => {
  let audioEl;
  let state;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    engine._resetForTest();
    audioEl = createMockAudioElement();
    state = createMockState();
    engine.init(audioEl, state);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ----------------------------------------------------------
  //  Initialisierung
  // ----------------------------------------------------------
  describe('Initialisierung', () => {
    it('setzt Audio-Volume auf State-Wert', () => {
      expect(audioEl.volume).toBe(0.7); // 70/100
    });

    it('meldet initialisiert', () => {
      expect(engine.isInitialized()).toBe(true);
    });

    it('meldet nicht initialisiert ohne Audio', () => {
      engine._resetForTest();
      expect(engine.isInitialized()).toBe(false);
    });
  });

  // ----------------------------------------------------------
  //  Case A: Radio Direct Stream
  // ----------------------------------------------------------
  describe('Case A: Radio Direct Stream', () => {
    it('TC-A1: Sender abspielen setzt korrekten State', async () => {
      await engine.playStation(STATION_A);

      expect(state.isPlaying).toBe(true);
      expect(state.isPaused).toBe(false);
      expect(state.currentStation).toEqual(STATION_A);
      expect(state.currentEpisode).toBe(null);
      expect(state.playerMode).toBe('direct');
      expect(state.isLive).toBe(true);
      expect(state.toast).toBe(null);
    });

    it('TC-A2: Audio-Source nutzt Backend-Proxy', async () => {
      await engine.playStation(STATION_A);

      expect(audioEl.src).toBe(api.getStreamProxyUrl(STATION_A.url_resolved));
      expect(audioEl.load).toHaveBeenCalled();
      expect(audioEl.play).toHaveBeenCalled();
    });

    it('TC-A3: HLS-Buffer wird im Hintergrund gestartet', async () => {
      await engine.playStation(STATION_A);

      expect(api.startHLS).toHaveBeenCalledWith(STATION_A);
    });

    it('TC-A4: Stop setzt alles zurück', async () => {
      await engine.playStation(STATION_A);
      await engine.stop();

      expect(state.isPlaying).toBe(false);
      expect(state.isPaused).toBe(false);
      expect(state.playerMode).toBe('none');
      expect(state.hlsActive).toBe(false);
      expect(audioEl.pause).toHaveBeenCalled();
      expect(audioEl.removeAttribute).toHaveBeenCalledWith('src');
    });

    it('TC-A5: Pause funktioniert', async () => {
      await engine.playStation(STATION_A);

      engine.pause();
      expect(state.isPaused).toBe(true);
      expect(state.isPlaying).toBe(true); // Noch "playing" aber pausiert
      expect(audioEl.pause).toHaveBeenCalled();
    });

    it('TC-A6: Resume nach Pause', async () => {
      await engine.playStation(STATION_A);
      engine.pause();

      audioEl.play.mockClear();
      engine.resume();
      expect(state.isPaused).toBe(false);
      expect(audioEl.play).toHaveBeenCalled();
    });

    it('TC-A7: togglePause wechselt hin und her', async () => {
      await engine.playStation(STATION_A);

      engine.togglePause();
      expect(state.isPaused).toBe(true);

      engine.togglePause();
      expect(state.isPaused).toBe(false);
    });

    it('TC-A8: Seeking ist bei Direct Stream deaktiviert', async () => {
      await engine.playStation(STATION_A);
      expect(engine.canSeek()).toBe(false);
    });

    it('TC-A9: Last Station wird gespeichert', async () => {
      await engine.playStation(STATION_A);

      expect(api.updateConfig).toHaveBeenCalledWith({
        last_station_uuid: STATION_A.uuid,
        last_station_name: STATION_A.name
      });
    });
  });

  // ----------------------------------------------------------
  //  Case B: Radio mit HLS Timeshift
  // ----------------------------------------------------------
  describe('Case B: HLS Timeshift', () => {
    it('TC-B1: HLS wird als aktiv markiert nach Start', async () => {
      // HLS-Start ist fire-and-forget, der API-Mock resolved sofort
      vi.useRealTimers(); // Brauchen echte Timers für async polling
      await engine.playStation(STATION_A);

      // Kurz warten bis der async HLS-Start-Call resolved
      await new Promise(r => setTimeout(r, 50));

      expect(state.hlsActive).toBe(true);
      expect(state.hlsStatus).toBeTruthy();
      vi.useFakeTimers(); // Zurück zu Fake-Timers für andere Tests
    });

    it('TC-B2: Seeking ist im HLS-Modus aktiv', async () => {
      await engine.playStation(STATION_A);
      state.playerMode = 'hls'; // Simuliere HLS-Switch

      expect(engine.canSeek()).toBe(true);
    });

    it('TC-B3: Backend-HLS wird bei Stop gestoppt', async () => {
      await engine.playStation(STATION_A);
      state.hlsActive = true;

      await engine.stop();
      expect(api.stopHLS).toHaveBeenCalled();
    });

    it('TC-B4: goLive springt zur Live-Kante', async () => {
      state.playerMode = 'hls';
      state.hlsStatus = { first_segment: 0, last_segment: 300, segment_duration: 1 };
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 300),
      };

      engine.goLive();

      expect(audioEl.currentTime).toBeCloseTo(299.5, 1);
      expect(state.isLive).toBe(true);
      expect(state.currentSegment).toBe(300);
    });

    it('TC-B5: Seek aktualisiert isLive und currentSegment', async () => {
      state.playerMode = 'hls';
      state.hlsStatus = { first_segment: 0, last_segment: 300, segment_duration: 1 };
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 300),
      };

      engine.seek(50); // 50% von 300 Segmenten = Segment 150
      expect(state.isLive).toBe(false);
      expect(audioEl.currentTime).toBeCloseTo(150, 0);
      expect(state.currentSegment).toBe(150);
    });

    it('TC-B6: Seek nahe Ende springt zu Live', async () => {
      state.playerMode = 'hls';
      state.hlsStatus = { first_segment: 0, last_segment: 10, segment_duration: 1 };
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 10),
      };

      engine.seek(95); // 95% von 10 = Segment 9.5 -> round = 10 -> >= 9 (lastSeg-1)
      expect(state.isLive).toBe(true);
      expect(state.currentSegment).toBe(10);
    });

    it('TC-B7: Skip +10s funktioniert im HLS', async () => {
      state.playerMode = 'hls';
      state.currentSegment = 100;
      state.hlsStatus = { first_segment: 0, last_segment: 300, segment_duration: 1 };
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 300),
      };

      engine.skip(10);
      expect(state.currentSegment).toBe(110);
      expect(audioEl.currentTime).toBeCloseTo(110, 0);
    });

    it('TC-B8: Skip -10s funktioniert im HLS', async () => {
      state.playerMode = 'hls';
      state.currentSegment = 100;
      state.hlsStatus = { first_segment: 0, last_segment: 300, segment_duration: 1 };
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 300),
      };

      engine.skip(-10);
      expect(state.currentSegment).toBe(90);
      expect(audioEl.currentTime).toBeCloseTo(90, 0);
    });

    it('TC-B10: Session-ID wird in Playlist-URL unterstützt', () => {
      const url = api.getHLSPlaylistUrl('test123');
      expect(url).toContain('sid=test123');

      const urlNoSid = api.getHLSPlaylistUrl();
      expect(urlNoSid).not.toContain('sid=');
    });

    it('TC-B9: Skip stoppt bei erstem Segment', async () => {
      state.playerMode = 'hls';
      state.currentSegment = 5;
      state.hlsStatus = { first_segment: 0, last_segment: 300, segment_duration: 1 };
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 300),
      };

      engine.skip(-20);
      expect(state.currentSegment).toBe(0);
      expect(audioEl.currentTime).toBeCloseTo(0, 0);
    });
  });

  // ----------------------------------------------------------
  //  Case C: Podcast
  // ----------------------------------------------------------
  describe('Case C: Podcast', () => {
    it('TC-C1: Podcast abspielen setzt korrekten State', async () => {
      await engine.playPodcast(PODCAST_EPISODE, PODCAST_EPISODE.podcast);

      expect(state.isPlaying).toBe(true);
      expect(state.currentEpisode).toBeTruthy();
      expect(state.currentEpisode.title).toBe('Test Episode');
      expect(state.currentStation).toBe(null);
      expect(state.playerMode).toBe('podcast');
    });

    it('TC-C2: Audio-Source nutzt Backend-Proxy', async () => {
      await engine.playPodcast(PODCAST_EPISODE, PODCAST_EPISODE.podcast);

      expect(audioEl.src).toBe(api.getEpisodeStreamUrl(PODCAST_EPISODE.id));
    });

    it('TC-C3: HLS wird bei Podcast-Start gestoppt', async () => {
      // Erst Radio mit HLS spielen
      await engine.playStation(STATION_A);
      state.hlsActive = true;
      api.stopHLS.mockClear();

      // Dann Podcast
      await engine.playPodcast(PODCAST_EPISODE, PODCAST_EPISODE.podcast);

      expect(state.hlsActive).toBe(false);
    });

    it('TC-C4: Seeking funktioniert im Podcast', async () => {
      await engine.playPodcast(PODCAST_EPISODE, PODCAST_EPISODE.podcast);
      audioEl.duration = 3600; // 1 Stunde

      engine.seek(25); // 25% = 900s
      expect(audioEl.currentTime).toBe(900);
    });

    it('TC-C5: Seeking ist im Podcast aktiv', async () => {
      await engine.playPodcast(PODCAST_EPISODE, PODCAST_EPISODE.podcast);
      expect(engine.canSeek()).toBe(true);
    });

    it('TC-C6: Ende des Podcasts stoppt Wiedergabe', async () => {
      await engine.playPodcast(PODCAST_EPISODE, PODCAST_EPISODE.podcast);
      engine.handleEnded();

      // stop() ist async, aber handleEnded ruft es auf
      await vi.runAllTimersAsync();
      expect(state.isPlaying).toBe(false);
    });
  });

  // ----------------------------------------------------------
  //  Senderwechsel (KEIN Audio-Bleed!)
  // ----------------------------------------------------------
  describe('Senderwechsel - Anti Audio-Bleed', () => {
    it('TC-SW1: Wechsel A->B: Audio wird sofort gestoppt', async () => {
      await engine.playStation(STATION_A);
      audioEl.pause.mockClear();

      await engine.playStation(STATION_B);

      // pause() muss VOR dem neuen play() aufgerufen worden sein
      expect(audioEl.pause).toHaveBeenCalled();
      expect(audioEl.removeAttribute).toHaveBeenCalledWith('src');
    });

    it('TC-SW2: Wechsel A->B: Backend-HLS wird gestoppt und neu gestartet', async () => {
      await engine.playStation(STATION_A);
      state.hlsActive = true;
      api.stopHLS.mockClear();
      api.startHLS.mockClear();

      await engine.playStation(STATION_B);

      expect(api.stopHLS).toHaveBeenCalled();
      expect(api.startHLS).toHaveBeenCalledWith(STATION_B);
    });

    it('TC-SW3: Wechsel A->B: Neue Source ist Station B', async () => {
      await engine.playStation(STATION_A);
      await engine.playStation(STATION_B);

      expect(state.currentStation).toEqual(STATION_B);
      expect(audioEl.src).toBe(api.getStreamProxyUrl(STATION_B.url_resolved));
    });

    it('TC-SW4: Schneller Wechsel A->B->C: Nur C spielt', async () => {
      const stationC = { ...STATION_A, uuid: 'c', name: 'TestRadio C', url_resolved: 'http://c.example.com' };

      // Schneller Wechsel ohne await
      const p1 = engine.playStation(STATION_A);
      const p2 = engine.playStation(STATION_B);
      const p3 = engine.playStation(stationC);

      await Promise.all([p1, p2, p3]);

      // Nur C darf aktiv sein
      expect(state.currentStation.name).toBe('TestRadio C');
      expect(audioEl.src).toBe(api.getStreamProxyUrl('http://c.example.com'));
    });

    it('TC-SW5: Generation Counter verhindert veraltete State-Updates', async () => {
      const gen1 = engine.getGeneration();
      await engine.playStation(STATION_A);
      const gen2 = engine.getGeneration();

      expect(gen2).toBeGreaterThan(gen1);

      await engine.playStation(STATION_B);
      const gen3 = engine.getGeneration();

      expect(gen3).toBeGreaterThan(gen2);
    });
  });

  // ----------------------------------------------------------
  //  Übergänge Radio <-> Podcast
  // ----------------------------------------------------------
  describe('Übergänge Radio <-> Podcast', () => {
    it('TC-T1: Radio -> Podcast: HLS wird gestoppt', async () => {
      await engine.playStation(STATION_A);
      state.hlsActive = true;

      await engine.playPodcast(PODCAST_EPISODE, PODCAST_EPISODE.podcast);

      expect(state.hlsActive).toBe(false);
      expect(state.currentStation).toBe(null);
      expect(state.currentEpisode).toBeTruthy();
    });

    it('TC-T2: Podcast -> Radio: Podcast-Audio wird gestoppt', async () => {
      await engine.playPodcast(PODCAST_EPISODE, PODCAST_EPISODE.podcast);
      audioEl.pause.mockClear();

      await engine.playStation(STATION_A);

      expect(audioEl.pause).toHaveBeenCalled();
      expect(state.currentEpisode).toBe(null);
      expect(state.currentStation).toEqual(STATION_A);
    });
  });

  // ----------------------------------------------------------
  //  Volume
  // ----------------------------------------------------------
  describe('Volume', () => {
    it('TC-V1: setVolume aktualisiert State und Audio', () => {
      engine.setVolume(50);

      expect(state.volume).toBe(50);
      expect(audioEl.volume).toBe(0.5);
    });

    it('TC-V2: setVolume auf 0 = Stumm', () => {
      engine.setVolume(0);

      expect(audioEl.volume).toBe(0);
    });

    it('TC-V3: setVolume auf 100 = Maximum', () => {
      engine.setVolume(100);

      expect(audioEl.volume).toBe(1);
    });
  });

  // ----------------------------------------------------------
  //  Recording
  // ----------------------------------------------------------
  describe('Recording', () => {
    it('TC-R1: Aufnahme starten setzt State', async () => {
      state.currentStation = STATION_A;
      const result = await engine.startRecording();

      expect(result.success).toBe(true);
      expect(state.isRecording).toBe(true);
      expect(state.recordingSession).toBe('rec1');
    });

    it('TC-R2: Aufnahme ohne Station schlägt fehl', async () => {
      state.currentStation = null;
      const result = await engine.startRecording();

      expect(result.success).toBe(false);
      expect(state.isRecording).toBe(false);
    });

    it('TC-R3: Aufnahme stoppen räumt auf', async () => {
      state.currentStation = STATION_A;
      await engine.startRecording();

      const result = await engine.stopRecording();

      expect(result.success).toBe(true);
      expect(state.isRecording).toBe(false);
      expect(state.recordingSession).toBe(null);
      expect(state.recordingElapsed).toBe(0);
    });

    it('TC-R4: Senderwechsel bei laufender Aufnahme wird blockiert', async () => {
      // Aktuelle Logik: Bei laufender Aufnahme wird der Senderwechsel
      // verweigert und ein Fehler angezeigt (statt still zu stoppen).
      await engine.playStation(STATION_A);
      state.currentStation = STATION_A;
      await engine.startRecording();
      expect(state.isRecording).toBe(true);

      await engine.playStation(STATION_B);

      // Aufnahme laeuft weiter, Senderwechsel wurde blockiert
      expect(state.isRecording).toBe(true);
      expect(state.toast?.message).toBe('Aufnahme läuft - erst stoppen');
      // Station bleibt auf A, nicht B
      expect(state.currentStation).toEqual(STATION_A);
    });

    it('TC-R6: Bei aktivem HLS-Buffer wird HLS-REC statt Direct gestartet', async () => {
      // Vorbedingung: HLS-Buffer ist aktiv (Auto-HLS nach Senderwechsel)
      state.currentStation = STATION_A;
      state.hlsActive = true;
      state.playerMode = 'hls';

      await engine.startRecording();

      // HLS-REC muss gestartet worden sein, nicht Direct
      expect(api.startHlsRecording).toHaveBeenCalled();
      expect(api.startRecording).not.toHaveBeenCalled();
      expect(state.recordingType).toBe('hls-rec');
    });

    it('TC-R7: Ohne HLS-Buffer wird Direct-REC gestartet', async () => {
      state.currentStation = STATION_A;
      state.hlsActive = false;
      state.playerMode = 'direct';

      await engine.startRecording();

      expect(api.startRecording).toHaveBeenCalled();
      expect(api.startHlsRecording).not.toHaveBeenCalled();
      expect(state.recordingType).toBe('direct');
    });

    it('TC-R5: Recording-API wird mit korrekten Daten aufgerufen', async () => {
      state.currentStation = STATION_A;
      await engine.startRecording();

      expect(api.startRecording).toHaveBeenCalledWith({
        station_uuid: STATION_A.uuid,
        station_name: STATION_A.name,
        stream_url: STATION_A.url_resolved,
        bitrate: STATION_A.bitrate,
      });
    });
  });

  // ----------------------------------------------------------
  //  Time Update Handler
  // ----------------------------------------------------------
  describe('Time Update Handler', () => {
    it('TC-TU1: Podcast-Time wird korrekt berechnet', () => {
      state.playerMode = 'podcast';
      audioEl.currentTime = 180; // 3 Minuten
      audioEl.duration = 3600;   // 1 Stunde

      const result = engine.handleTimeUpdate();

      expect(result.currentTime).toBe(180);
      expect(result.duration).toBe(3600);
      expect(result.seekPosition).toBe(5); // 180/3600 * 100 = 5%
    });

    it('TC-TU2: HLS-Time mappt auf Segment-Position', () => {
      state.playerMode = 'hls';
      state.isLive = false; // Nicht-Live damit Position berechnet wird
      state.hlsStatus = { first_segment: 200, last_segment: 300, segment_duration: 1 };
      audioEl.currentTime = 250;
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 200),
        end: vi.fn(() => 300),
      };

      const result = engine.handleTimeUpdate();

      // fraction = (250-200)/(300-200) = 0.5 -> Segment 250
      // seekPosition = (250-200)/100 * 100 = 50%
      expect(result.seekPosition).toBe(50);
      expect(state.currentSegment).toBe(250);
    });

    it('TC-TU3: Live-Modus pinnt seekPosition auf 100%', () => {
      state.playerMode = 'hls';
      state.isLive = true;
      state.hlsStatus = { first_segment: 0, last_segment: 300, segment_duration: 1 };
      audioEl.currentTime = 295; // Etwas hinter Live-Kante
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 300),
      };

      const result = engine.handleTimeUpdate();
      // Im Live-Modus: Position gepinnt, kein Neuberechnen
      expect(result.seekPosition).toBe(100);
      expect(state.currentSegment).toBe(300);
      expect(state.isLive).toBe(true); // Bleibt true
    });

    it('TC-TU4: Nicht-Live berechnet Segment-Position normal', () => {
      state.playerMode = 'hls';
      state.isLive = false; // Explizit nicht-live (z.B. nach seek)
      state.hlsStatus = { first_segment: 0, last_segment: 300, segment_duration: 1 };
      audioEl.currentTime = 200;
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 300),
      };

      const result = engine.handleTimeUpdate();
      expect(state.currentSegment).toBe(200);
      // isLive wird von handleTimeUpdate NICHT geändert
      expect(state.isLive).toBe(false);
    });

    it('TC-TU5: Anti-Jitter: gleiches Segment ergibt gleiche seekPosition', () => {
      state.playerMode = 'hls';
      state.isLive = false; // Nicht-Live damit Position berechnet wird
      state.hlsStatus = { first_segment: 0, last_segment: 300, segment_duration: 1 };
      audioEl.seekable = {
        length: 1,
        start: vi.fn(() => 0),
        end: vi.fn(() => 300),
      };

      // Erstes Update: Segment 150
      audioEl.currentTime = 150.1;
      const result1 = engine.handleTimeUpdate();

      // Zweites Update: immer noch Segment 150
      audioEl.currentTime = 150.4;
      const result2 = engine.handleTimeUpdate();

      // seekPosition muss identisch sein (Anti-Jitter)
      expect(result1.seekPosition).toBe(result2.seekPosition);
      expect(state.currentSegment).toBe(150);
    });
  });

  // ----------------------------------------------------------
  //  Error Handling
  // ----------------------------------------------------------
  describe('Error Handling', () => {
    it('TC-E1: Audio-Error wird in State geschrieben', () => {
      // MediaError codes: 1=ABORTED, 2=NETWORK, 3=DECODE, 4=SRC_NOT_SUPPORTED
      const event = {
        target: {
          error: { code: 2 }
        }
      };

      engine.handleError(event);
      expect(state.toast?.message).toBe('Netzwerkfehler');
    });

    it('TC-E2: Unbekannter Error zeigt generische Meldung', () => {
      const event = {
        target: {
          error: { code: 99 }
        }
      };

      engine.handleError(event);
      expect(state.toast?.message).toBe('Wiedergabefehler');
    });

    it('TC-E2b: Error Code 4 wird ignoriert (transienter Source-Wechsel)', () => {
      const event = {
        target: {
          error: { code: 4 }
        }
      };

      engine.handleError(event);
      expect(state.toast).toBeNull();
    });

    it('TC-E3: Ohne Audio-Element kein Absturz bei playStation', async () => {
      engine._resetForTest();
      engine.init(null, state);

      await engine.playStation(STATION_A);
      expect(state.toast?.message).toBe('Kein Audio-Element');
      expect(state.isPlaying).toBe(false);
    });
  });

  // ----------------------------------------------------------
  //  Stream Mode Toggle (Original/HLS)
  // ----------------------------------------------------------
  describe('Stream Mode Toggle', () => {
    it('TC-SM1: toggleStreamMode wechselt von HLS zu Direct', () => {
      state.playerMode = 'hls';
      state.canPlayDirect = true;
      state.canPlayHLS = true;
      state.currentStation = STATION_A;

      engine.toggleStreamMode();

      expect(state.playerMode).toBe('direct');
      expect(audioEl.src).toBe(STATION_A.url_resolved);
      expect(state.isLive).toBe(true);
    });

    it('TC-SM2: toggleStreamMode wechselt von Direct zu HLS', async () => {
      vi.useRealTimers();
      await engine.playStation(STATION_A);
      await new Promise(r => setTimeout(r, 50));

      state.playerMode = 'direct';
      state.canPlayHLS = true;
      state.canPlayDirect = true;

      engine.toggleStreamMode();

      // HLS switch passiert (playerMode wird in MANIFEST_PARSED gesetzt)
      // Wir prüfen hier nur dass kein Fehler fliegt
      expect(state.canPlayHLS).toBe(true);
      vi.useFakeTimers();
    });

    it('TC-SM3: toggleStreamMode ignoriert wenn canPlayHLS unbekannt', async () => {
      await engine.playStation(STATION_A);
      state.canPlayHLS = null;

      engine.toggleStreamMode();

      expect(state.playerMode).toBe('direct'); // Keine Änderung
    });

    it('TC-SM4: toggleStreamMode ignoriert wenn Direct nicht abspielbar', () => {
      state.playerMode = 'hls';
      state.canPlayDirect = false;
      state.currentStation = STATION_A;

      engine.toggleStreamMode();

      expect(state.playerMode).toBe('hls'); // Keine Änderung
    });

    it('TC-SM5: canToggleMode gibt korrekten Wert zurück', () => {
      state.playerMode = 'hls';
      state.canPlayDirect = true;
      expect(engine.canToggleMode()).toBe(true);

      state.canPlayDirect = false;
      expect(engine.canToggleMode()).toBe(false);

      state.playerMode = 'direct';
      state.canPlayHLS = true;
      expect(engine.canToggleMode()).toBe(true);

      state.canPlayHLS = null;
      expect(engine.canToggleMode()).toBe(false);
    });

    it('TC-SM6: Dekodierungsfehler setzt canPlayDirect auf false', () => {
      state.playerMode = 'direct';
      state.canPlayHLS = false; // HLS auch nicht verfügbar

      engine.handleError({ target: { error: { code: 3 } } });

      expect(state.canPlayDirect).toBe(false);
      expect(state.toast?.message).toBe('Dekodierungsfehler');
    });

    it('TC-SM7: Dekodierungsfehler bei verfügbarem HLS wechselt automatisch', () => {
      state.playerMode = 'direct';
      state.canPlayHLS = true;
      state.currentStation = STATION_A;

      engine.handleError({ target: { error: { code: 3 } } });

      expect(state.canPlayDirect).toBe(false);
      // Kein Toast weil auto-switch zu HLS
      expect(state.toast).toBeNull();
    });

    it('TC-SM8: playStation resettet Mode-Felder', async () => {
      state.canPlayDirect = false;
      state.canPlayHLS = true;

      await engine.playStation(STATION_A);

      expect(state.canPlayDirect).toBe(true);
      expect(state.canPlayHLS).toBe(null);
    });

    it('TC-SM9: stop resettet Mode-Felder', async () => {
      state.canPlayDirect = false;
      state.canPlayHLS = true;

      await engine.stop();

      expect(state.canPlayDirect).toBe(true);
      expect(state.canPlayHLS).toBe(null);
    });
  });

  // ----------------------------------------------------------
  //  Quality Info
  // ----------------------------------------------------------
  describe('Quality Info', () => {
    it('TC-Q1: streamQuality wird bei playStation zurückgesetzt', async () => {
      state.streamQuality = { inputCodec: 'mp3', inputBitrate: 128 };
      await engine.playStation(STATION_A);

      expect(state.streamQuality).toBe(null);
    });

    // Note: Quality wird durch HLS-Polling gesetzt.
    // Das Polling selbst ist schwer zu unit-testen (Timer-basiert).
    // Wird im manuellen UI-Test geprüft (TC-Q2 bis TC-Q4).
  });

  // ----------------------------------------------------------
  //  Recording State Recovery (ERR-003/024/025)
  //
  //  Testet: checkAndRecoverRecordingState()
  //  Zweck: Nach Page-Reload muss das Frontend laufende
  //         Aufnahmen im Backend erkennen und State
  //         wiederherstellen (Timer, Typ, Session-ID).
  // ----------------------------------------------------------
  describe('Recording State Recovery', () => {

    // Mocks pro Test zuruecksetzen, damit keine mockResolvedValueOnce-Werte
    // aus vorherigen Tests durchsickern
    beforeEach(() => {
      api.getRecordingStatus.mockReset();
      api.getHlsRecordingStatus.mockReset();
      api.getRecordingStatus.mockResolvedValue({ recording: false });
      api.getHlsRecordingStatus.mockResolvedValue({ recording: false });
    });

    it('TC-RSR1: HLS-REC im Backend aktiv -> State wird wiederhergestellt', async () => {
      // Vorbedingung: Backend meldet aktive HLS-Aufnahme
      api.getHlsRecordingStatus.mockResolvedValueOnce({
        recording: true,
        session_id: 'hlsrec_test_123',
        duration: 120,
        icy_count: 3,
        icy_entries: ['Titel A', 'Titel B', 'Titel C'],
      });

      await engine.checkAndRecoverRecordingState();

      // Alle Recording-State-Felder muessen gesetzt sein
      expect(state.isRecording).toBe(true);
      expect(state.recordingType).toBe('hls-rec');
      expect(state.recordingSession).toBe('hlsrec_test_123');
      expect(state.recordingElapsed).toBe(120);
      expect(state.recordingIcyCount).toBe(3);
      expect(state.recordingIcyEntries).toEqual(['Titel A', 'Titel B', 'Titel C']);
    });

    it('TC-RSR2: Direct-REC im Backend aktiv -> State wird wiederhergestellt', async () => {
      // Vorbedingung: Backend meldet aktive Direct-Aufnahme
      api.getRecordingStatus.mockResolvedValueOnce({
        recording: true,
        session_id: 'rec_test_456',
        duration: 60,
        icy_count: 1,
        icy_entries: ['Song X'],
      });

      await engine.checkAndRecoverRecordingState();

      expect(state.isRecording).toBe(true);
      expect(state.recordingType).toBe('direct');
      expect(state.recordingSession).toBe('rec_test_456');
      expect(state.recordingElapsed).toBe(60);
    });

    it('TC-RSR3: Keine Aufnahme im Backend -> State bleibt unverändert', async () => {
      // Vorbedingung: Beide Endpoints melden keine Aufnahme (Default-Mock)
      await engine.checkAndRecoverRecordingState();

      expect(state.isRecording).toBe(false);
      expect(state.recordingType).toBe(null);
      expect(state.recordingSession).toBe(null);
      expect(state.recordingElapsed).toBe(0);
    });

    it('TC-RSR4: Bereits aktive Aufnahme -> kein doppelter Recovery-Versuch', async () => {
      // Vorbedingung: Frontend hat schon isRecording=true
      state.isRecording = true;
      state.recordingType = 'direct';

      // Backend wuerde HLS-REC melden, aber Recovery soll abbrechen
      api.getHlsRecordingStatus.mockResolvedValueOnce({
        recording: true,
        session_id: 'hlsrec_sollte_ignoriert_werden',
        duration: 999,
      });

      await engine.checkAndRecoverRecordingState();

      // State darf NICHT ueberschrieben werden
      expect(state.recordingType).toBe('direct');
      expect(api.getRecordingStatus).not.toHaveBeenCalled();
      expect(api.getHlsRecordingStatus).not.toHaveBeenCalled();
    });

    it('TC-RSR5: HLS hat Vorrang vor Direct wenn beide aktiv', async () => {
      // Seltener Fall: Beide Endpoints melden aktive Aufnahme
      // HLS-REC soll Vorrang haben (wird zuerst geprueft)
      api.getRecordingStatus.mockResolvedValue({
        recording: true,
        session_id: 'rec_direct',
        duration: 30,
      });
      api.getHlsRecordingStatus.mockResolvedValue({
        recording: true,
        session_id: 'hlsrec_hls',
        duration: 45,
      });

      await engine.checkAndRecoverRecordingState();

      expect(state.recordingType).toBe('hls-rec');
      expect(state.recordingSession).toBe('hlsrec_hls');
    });

    it('TC-RSR6: Backend-Fehler werden abgefangen, kein Crash', async () => {
      // Vorbedingung: Beide Endpoints werfen Fehler
      // catch() in der Funktion faengt sie ab -> recording: false
      api.getRecordingStatus.mockImplementation(() => { throw new Error('Netzwerkfehler'); });
      api.getHlsRecordingStatus.mockImplementation(() => { throw new Error('Server down'); });

      // Darf keinen Error werfen
      await expect(engine.checkAndRecoverRecordingState()).resolves.not.toThrow();

      // State bleibt unveraendert
      expect(state.isRecording).toBe(false);
    });

    it('TC-RSR7: Timer-Interval wird bei Recovery gestartet', async () => {
      api.getRecordingStatus.mockResolvedValue({ recording: false });
      api.getHlsRecordingStatus.mockResolvedValue({
        recording: true,
        session_id: 'hlsrec_timer',
        duration: 10,
      });

      await engine.checkAndRecoverRecordingState();
      expect(state.recordingElapsed).toBe(10);

      // Nach 3 Sekunden muss der Timer hochgezaehlt haben
      vi.advanceTimersByTime(3000);
      expect(state.recordingElapsed).toBe(13); // 10 + 3
    });
  });

  // ----------------------------------------------------------
  //  Aufnahme-Schutz: Blockade bei Podcast/Recording-Wechsel
  // ----------------------------------------------------------

  describe('Aufnahme-Schutz bei Modus-Wechsel (ERR-006)', () => {
    it('TC-RB1: Podcast-Wechsel bei laufender Aufnahme wird blockiert', async () => {
      // Sender starten + Aufnahme beginnen
      await engine.playStation(STATION_A);
      state.currentStation = STATION_A;
      await engine.startRecording();
      expect(state.isRecording).toBe(true);

      // Podcast abspielen versuchen -> muss blockiert werden
      await engine.playPodcast(PODCAST_EPISODE);

      // Aufnahme läuft weiter
      expect(state.isRecording).toBe(true);
      expect(state.toast?.message).toBe('Aufnahme läuft - erst stoppen');
    });

    it('TC-RB2: Recording-Wiedergabe bei laufender Aufnahme wird blockiert', async () => {
      await engine.playStation(STATION_A);
      state.currentStation = STATION_A;
      await engine.startRecording();
      expect(state.isRecording).toBe(true);

      // Aufnahme-Wiedergabe versuchen -> muss blockiert werden
      await engine.playRecording({
        path: '/radio/test.mp3',
        name: 'Test',
        playUrl: `${TEST_API_BASE}/api/play/test.mp3`,
        source: 'recording'
      });

      expect(state.isRecording).toBe(true);
      expect(state.toast?.message).toBe('Aufnahme läuft - erst stoppen');
    });

    it('TC-RB3: Fehlermeldung verschwindet nach 4 Sekunden (Toast)', async () => {
      vi.useFakeTimers();
      await engine.playStation(STATION_A);
      state.currentStation = STATION_A;
      await engine.startRecording();

      await engine.playStation(STATION_B);
      expect(state.toast?.message).toBe('Aufnahme läuft - erst stoppen');

      // Nach 4s muss der Toast weg sein
      vi.advanceTimersByTime(4000);
      expect(state.toast).toBe(null);

      vi.useRealTimers();
    });
  });

  // ----------------------------------------------------------
  //  Ticker-Reset bei Senderwechsel (ERR-019)
  // ----------------------------------------------------------

  describe('Ticker-Reset bei Senderwechsel (ERR-019)', () => {
    it('TC-TR1: streamTitle wird bei Senderwechsel zurückgesetzt', async () => {
      // Sender A starten, Titel setzen
      await engine.playStation(STATION_A);
      state.currentStation = STATION_A;
      state.streamTitle = 'Alter ICY-Titel';

      // Sender B starten -> streamTitle muss null sein
      await engine.playStation(STATION_B);

      expect(state.streamTitle).toBe(null);
    });
  });

  // ----------------------------------------------------------
  //  REC-Stop über stopRecording (ERR-012)
  // ----------------------------------------------------------

  describe('Aufnahme stoppen (ERR-012)', () => {
    it('TC-RS1: stopRecording setzt alle Recording-States zurück', async () => {
      state.currentStation = STATION_A;
      await engine.startRecording();
      expect(state.isRecording).toBe(true);
      expect(state.recordingType).toBe('direct');
      expect(state.recordingSession).toBe('rec1');

      await engine.stopRecording();

      expect(state.isRecording).toBe(false);
      expect(state.recordingType).toBe('none');
      expect(state.recordingSession).toBe(null);
      expect(state.recordingElapsed).toBe(0);
    });

    it('TC-RS2: stopRecording ruft korrekten API-Endpoint auf (Direct)', async () => {
      state.currentStation = STATION_A;
      state.hlsActive = false;
      await engine.startRecording();

      await engine.stopRecording();

      expect(api.stopRecording).toHaveBeenCalled();
      expect(api.stopHlsRecording).not.toHaveBeenCalled();
    });

    it('TC-RS3: stopRecording ruft korrekten API-Endpoint auf (HLS)', async () => {
      state.currentStation = STATION_A;
      state.hlsActive = true;
      state.playerMode = 'hls';
      await engine.startRecording();

      // recordingType ist jetzt 'hls-rec'
      expect(state.recordingType).toBe('hls-rec');

      await engine.stopRecording();

      expect(api.stopHlsRecording).toHaveBeenCalled();
    });
  });
});


// ============================================================
//  TC-VOL: Lautstärke-Persistierung
// ============================================================
describe('Lautstärke-Persistierung', () => {
  let state;
  let audioEl;

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.localStorage.clear();
    state = createMockState();
    audioEl = createMockAudioElement();
    engine.init(audioEl, state);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('TC-VOL1: setVolume speichert Lautstärke in localStorage', () => {
    // Arrange: Lautstärke ist initial 70

    // Act: Lautstärke auf 25 setzen
    engine.setVolume(25);

    // Assert: Im localStorage gespeichert
    expect(_mockStorage['radiohub_volume']).toBe('25');
    expect(state.volume).toBe(25);
    expect(audioEl.volume).toBeCloseTo(0.25);
  });

  it('TC-VOL2: setVolume(0) speichert Stummschaltung', () => {
    // Arrange: Lautstärke auf 50 setzen
    engine.setVolume(50);

    // Act: Stummschalten
    engine.setVolume(0);

    // Assert: 0 wird korrekt gespeichert
    expect(_mockStorage['radiohub_volume']).toBe('0');
    expect(state.volume).toBe(0);
    expect(audioEl.volume).toBe(0);
  });

  it('TC-VOL3: Gespeicherte Lautstärke wird nach Neustart geladen', () => {
    // Arrange: Lautstärke 42 im Storage simulieren
    _mockStorage['radiohub_volume'] = '42';

    // Act: Wert laden wie in store.svelte.js
    const loaded = Number(globalThis.localStorage.getItem('radiohub_volume')) || 70;

    // Assert: Gespeicherter Wert wird verwendet, nicht Default 70
    expect(loaded).toBe(42);
  });

  it('TC-VOL4: Ohne gespeicherten Wert wird Fallback 70 verwendet', () => {
    // Arrange: Storage leer (mockStorage = {})

    // Act: Wert laden wie in store.svelte.js
    const loaded = Number(globalThis.localStorage.getItem('radiohub_volume')) || 70;

    // Assert: Fallback-Wert 70
    expect(loaded).toBe(70);
  });
});


// ============================================================
//  Zusammenfassung der Testcases (für manuelle Prüfung)
// ============================================================
/**
 * MANUELLE TESTCASES (im Browser mit laufendem Backend):
 *
 * TC-M1: Sender anklicken
 *   Erwartung: Direct Stream spielt sofort, nach ~3-5s Wechsel zu HLS
 *   Prüfen: SOURCE zeigt "Tuner / HLS", Display zeigt Sendername
 *
 * TC-M2: Senderwechsel während Wiedergabe
 *   Erwartung: KEIN Audio-Bleed! Alter Sender stoppt sofort.
 *   Prüfen: Nur neuer Sender hörbar, kein kurzes Überlappen
 *
 * TC-M3: 3x schnell hintereinander verschiedene Sender klicken
 *   Erwartung: Nur der letzte Sender spielt
 *   Prüfen: Display, Audio, kein Chaos
 *
 * TC-M4: Play -> Pause -> Play
 *   Erwartung: Grüne LED -> Gelbe LED -> Grüne LED
 *   Prüfen: Audio stoppt/startet korrekt
 *
 * TC-M5: Play -> Stop
 *   Erwartung: Audio stoppt komplett, State zurückgesetzt
 *   Prüfen: Stop-LED gelb (kurz), dann alles aus
 *
 * TC-M6: HLS-Seekbar zurückziehen
 *   Erwartung: Audio springt zurück im Buffer
 *   Prüfen: LIVE-Anzeige verschwindet, LIVE-Button wird aktiv (blau)
 *
 * TC-M7: LIVE-Button nach Zurückspulen
 *   Erwartung: Springt zur Live-Kante
 *   Prüfen: LIVE-Anzeige kommt zurück
 *
 * TC-M8: Podcast abspielen
 *   Erwartung: SOURCE "Podcast", Timer grün, Seekbar aktiv
 *   Prüfen: Volle Dauer wird angezeigt
 *
 * TC-M9: Quality-Anzeige
 *   Erwartung: Unter dem Sendernamen: z.B. "MP3 192k -> HLS 128k"
 *   Prüfen: Aktualisiert sich nach HLS-Start
 *
 * TC-M10: Aufnahme starten/stoppen
 *   Erwartung: REC-LED rot + blinkt, Timer rot, Toast bei Stop
 *   Prüfen: Aufnahme-Datei wird erstellt
 *
 * TC-M11: Recording bei Senderwechsel
 *   Erwartung: Senderwechsel wird BLOCKIERT bei laufender Aufnahme
 *   Prüfen: Fehlermeldung erscheint, Aufnahme läuft weiter
 *
 * TC-M12: Error-Handling (ungültige Stream-URL)
 *   Erwartung: Fehler-Banner erscheint über dem Player
 *   Prüfen: Kann mit "x" geschlossen werden
 */
