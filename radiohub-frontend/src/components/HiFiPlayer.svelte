<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import HiFiKnob from './hifi/HiFiKnob.svelte';
  import HiFiVuMeter from './hifi/HiFiVuMeter.svelte';
  import HiFiBitrateLed from './hifi/HiFiBitrateLed.svelte';
  import { appState, actions } from '../lib/store.svelte.js';
  import { api } from '../lib/api.js';
  import * as engine from '../lib/playerEngine.js';
  import { connect as connectAnalyser } from '../lib/audioAnalyser.js';
  import * as sfx from '../lib/uiSounds.js';
  import { formatTime, formatTimeShort } from '../lib/formatters.js';

  // Audio Element
  let audioEl = $state(null);

  // Lokaler Display-State (High-Frequency, nicht in appState)
  let currentTime = $state(0);
  let duration = $state(0);
  let seekPosition = $state(0);
  let isDragging = $state(false);
  let isSeeking = $state(false);
  let seekDebounceTimer = null;

  // Button Press States für gelbe LEDs
  let prevPressed = $state(false);
  let nextPressed = $state(false);
  let skipBackPressed = $state(false);
  let skipFwdPressed = $state(false);

  // === Engine Init ===
  $effect(() => {
    if (audioEl) {
      engine.init(audioEl, appState);
      connectAnalyser(audioEl);
    }
    return () => {
      // Cleanup bei Unmount: nicht stoppen, nur de-registrieren
    };
  });

  // === Volume Sync ===
  $effect(() => {
    if (audioEl) {
      audioEl.volume = appState.volume / 100;
    }
  });

  // === ICY Now-Playing Polling ===
  let icyPollTimer = null;

  $effect(() => {
    const station = appState.currentStation;
    const playing = appState.isPlaying;

    // Polling starten wenn Station spielt und ICY unterstuetzt
    if (playing && station?.icy && station?.uuid) {
      // Sofort ersten Titel holen
      fetchIcyTitle(station.uuid);
      // Dann alle 15 Sekunden
      icyPollTimer = setInterval(() => fetchIcyTitle(station.uuid), 15000);
    } else {
      appState.streamTitle = null;
    }

    return () => {
      if (icyPollTimer) {
        clearInterval(icyPollTimer);
        icyPollTimer = null;
      }
    };
  });

  async function fetchIcyTitle(uuid) {
    try {
      const result = await api.getNowPlaying(uuid);
      if (result?.title) {
        appState.streamTitle = result.title;
      }
    } catch (e) {
      // Stilles Fehlen -- kein Titel verfuegbar
    }
  }

  // === Handlers ===
  function handlePlayPause() {
    if (appState.isPlaying && !appState.isPaused) {
      engine.togglePause();
    } else if (appState.isPaused) {
      engine.resume();
    } else if (appState.currentStation || appState.currentEpisode || appState.currentRecording) {
      if (appState.currentStation) {
        engine.playStation(appState.currentStation);
      } else if (appState.currentEpisode) {
        engine.playPodcast(appState.currentEpisode, appState.currentEpisode?.podcast);
      } else if (appState.currentRecording) {
        engine.playRecording(appState.currentRecording);
      }
    }
  }

  function handleStop() {
    engine.stop();
  }

  function handleRec() {
    if (appState.isRecording) {
      actions.stopRecording();
    } else {
      actions.startRecording();
    }
  }

  // === Time Update ===
  function handleTimeUpdate() {
    if (isDragging || isSeeking) return;
    const result = engine.handleTimeUpdate();
    if (result) {
      currentTime = result.currentTime;
      duration = result.duration;
      seekPosition = result.seekPosition;
    }
  }

  function handleSeeking() {
    isSeeking = true;
  }

  function handleSeeked() {
    isSeeking = false;
  }

  // === Format (aus shared formatters.js) ===

  // === Skip ===
  function handleSkip(seconds) {
    engine.skip(seconds);
  }

  // === Navigation ===
  function navigatePrev() {
    if (canNavigate) actions.navigatePrev();
  }

  function navigateNext() {
    if (canNavigate) actions.navigateNext();
  }

  // === Fader Handlers ===
  function handleFaderStart() {
    isDragging = true;
    if (seekDebounceTimer) {
      clearTimeout(seekDebounceTimer);
      seekDebounceTimer = null;
    }
  }

  function handleFaderEnd() {
    // Seek sofort ausführen, isDragging erst danach aufheben
    // damit handleTimeUpdate die Position nicht zurücksetzt
    if (seekDebounceTimer) clearTimeout(seekDebounceTimer);
    engine.seek(seekPosition);
    seekDebounceTimer = setTimeout(() => {
      isDragging = false;
    }, 300);
  }

  function handleFaderInput(e) {
    seekPosition = parseFloat(e.target.value);
  }

  // === Derived States ===
  let isRecordingPlayback = $derived(appState.playerMode === 'recording');

  let displayName = $derived(
    appState.isPlaying || appState.isPaused
      ? (appState.streamTitle || appState.currentStation?.name || appState.currentEpisode?.title || appState.currentRecording?.name || '')
      : ''
  );

  let nowPlayingMeta = $derived(
    appState.isPlaying || appState.isPaused
      ? (appState.currentStation?.tags?.split(',')[0] || appState.currentEpisode?.podcast?.title || '')
      : ''
  );

  let sourceType = $derived(
    appState.isPlaying || appState.isPaused
      ? (appState.currentStation ? 'Tuner' : appState.currentEpisode ? 'Podcast' : appState.currentRecording ? 'Aufnahme' : '---')
      : '---'
  );

  let hasSource = $derived(appState.currentStation || appState.currentEpisode || appState.currentRecording);
  let isPodcast = $derived(!!appState.currentEpisode);
  let isStation = $derived(!!appState.currentStation);
  let isHLSMode = $derived(appState.playerMode === 'hls');
  let isLive = $derived(appState.isLive ?? true);
  let hlsSegRange = $derived(
    appState.hlsStatus?.last_segment != null && appState.hlsStatus?.first_segment != null
      ? appState.hlsStatus.last_segment - appState.hlsStatus.first_segment
      : 0
  );
  let secondsBehindLive = $derived(
    appState.hlsStatus?.last_segment != null && appState.currentSegment != null
      ? (appState.hlsStatus.last_segment - appState.currentSegment) * (appState.hlsStatus?.segment_duration || 1)
      : 0
  );
  let displayActive = $derived((appState.isPlaying || appState.isPaused) && hasSource);

  let _canSeek = $derived(appState.playerMode === 'podcast' || appState.playerMode === 'hls' || appState.playerMode === 'recording');
  let canNavigate = $derived(appState.stations?.length > 0 || isPodcast || (isRecordingPlayback && appState.recordingPlaylist?.length > 1));

  // Prev/Next Sendernamen für Tooltips
  let prevStationName = $derived(() => {
    // Recording-Modus: vorheriger Track
    if (isRecordingPlayback && appState.recordingPlaylist?.length > 1) {
      const idx = appState.recordingPlaylist.findIndex(s => s.path === appState.currentRecording?.path);
      if (idx > 0) return appState.recordingPlaylist[idx - 1].name;
      if (idx === 0) return appState.recordingPlaylist[appState.recordingPlaylist.length - 1].name;
      return null;
    }
    if (!appState.currentStation || !appState.stations?.length) return null;
    const idx = appState.stations.findIndex(s => s.uuid === appState.currentStation.uuid);
    if (idx > 0) return appState.stations[idx - 1].name;
    if (idx === 0) return appState.stations[appState.stations.length - 1].name;
    return null;
  });

  let nextStationName = $derived(() => {
    // Recording-Modus: nächster Track
    if (isRecordingPlayback && appState.recordingPlaylist?.length > 1) {
      const idx = appState.recordingPlaylist.findIndex(s => s.path === appState.currentRecording?.path);
      if (idx >= 0 && idx < appState.recordingPlaylist.length - 1) return appState.recordingPlaylist[idx + 1].name;
      if (idx === appState.recordingPlaylist.length - 1) return appState.recordingPlaylist[0].name;
      return null;
    }
    if (!appState.currentStation || !appState.stations?.length) return null;
    const idx = appState.stations.findIndex(s => s.uuid === appState.currentStation.uuid);
    if (idx >= 0 && idx < appState.stations.length - 1) return appState.stations[idx + 1].name;
    if (idx === appState.stations.length - 1) return appState.stations[0].name;
    return null;
  });

  // Quality Info
  let qualityLabel = $derived(() => {
    const q = appState.streamQuality;
    if (!q) return null;
    if (appState.playerMode === 'hls') {
      return `${q.inputCodec.toUpperCase()} ${q.inputBitrate}k -> HLS ${q.outputBitrate}k`;
    }
    if (appState.playerMode === 'direct' && q.inputBitrate) {
      return `${q.inputCodec.toUpperCase()} ${q.inputBitrate}k (Direct)`;
    }
    return null;
  });

  // Display Scroll
  let displayContainer = $state(null);
  let displayWidth = $state(200);

  $effect(() => {
    if (!displayContainer) return;
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        displayWidth = entry.contentRect.width - 24;
      }
    });
    resizeObserver.observe(displayContainer);
    return () => resizeObserver.disconnect();
  });

  const CHAR_WIDTH = 19.2;
  let needsScroll = $derived(displayName.length * CHAR_WIDTH > displayWidth);

  // Timer
  // Recording: Aufnahmedauer (rot)
  // HLS Timeshift: Abstand zu Live (gelb) -- nur wenn NICHT live
  // Podcast: aktuelle Position (grün)
  // Sonst: inaktiv (Direct, HLS Live, Idle)
  let timerColor = $derived(
    appState.recordingType === 'hls-rec' ? 'amber' :
    appState.recordingType === 'direct' ? 'red' :
    isRecordingPlayback ? 'green' :
    isHLSMode && !isLive ? 'yellow' :
    isPodcast ? 'green' :
    'default'
  );

  let timerDisplayTime = $derived(
    appState.isRecording ? appState.recordingElapsed :
    isRecordingPlayback ? currentTime :
    isHLSMode && !isLive ? secondsBehindLive :
    isPodcast ? currentTime :
    0
  );

  let timerActive = $derived(
    appState.isRecording ||
    isRecordingPlayback ||
    (isHLSMode && !isLive) ||
    isPodcast
  );

  // Recording-Bitrate + ICY-Count Anzeige
  let recordingBitrateLabel = $derived(() => {
    if (!appState.isRecording) return null;
    const q = appState.streamQuality;
    let bitrate = null;
    if (appState.recordingType === 'hls-rec' && q?.outputBitrate) {
      bitrate = `${q.outputBitrate} kbps`;
    } else if (appState.recordingType === 'direct' && q?.inputBitrate) {
      bitrate = `${q.inputBitrate} kbps`;
    }
    if (!bitrate) return null;
    const count = appState.recordingIcyCount || 0;
    return count > 0 ? `${bitrate} / ${count}` : bitrate;
  });

  // === LED States ===
  let playPauseLedColor = $derived(
    appState.isPaused ? 'yellow' :
    appState.isPlaying ? 'green' : 'off'
  );
  let stopLedColor = $derived(!appState.isPlaying && !appState.isPaused && hasSource ? 'yellow' : 'off');
  let recLedColor = $derived(
    appState.recordingType === 'direct' ? 'red' :
    appState.recordingType === 'hls-rec' ? 'amber' :
    'off'
  );
  let liveLedColor = $derived(isHLSMode && !isLive ? 'blue' : 'off');

  // Mode LED (zeigt aktuellen Modus)
  let modeLedColor = $derived(
    appState.playerMode === 'hls' ? 'green' :
    appState.playerMode === 'direct' ? 'yellow' :
    'off'
  );

  // Transport Section Label (kontextabhängig)
  let transportLabel = $derived(
    appState.recordingType === 'hls-rec' ? 'HLS-REC' :
    appState.recordingType === 'direct' ? 'RECORDING' :
    isRecordingPlayback ? 'PLAYBACK' :
    isPodcast ? 'PODCAST' :
    isHLSMode ? 'TIMESHIFT' :
    'TRANSPORT'
  );

  // Mode Toggle Verfügbarkeit
  let canToggleStreamMode = $derived(
    !appState.isRecording && (
      (appState.playerMode === 'hls' && appState.canPlayDirect) ||
      (appState.playerMode === 'direct' && appState.canPlayHLS === true)
    )
  );

  // Bitrate Override (persistent via localStorage)
  let bitrateOverride = $state(JSON.parse(localStorage.getItem('radiohub_bitrate_override') || 'null'));

  // Erkannte Input-Bitrate des Streams (Original, nicht die HLS-Encoding-Bitrate)
  let hlsInputBitrate = $derived(appState.streamQuality?.inputBitrate || 0);

  async function handleBitrateOverrideChange(newOverride) {
    bitrateOverride = newOverride;
    if (newOverride !== null) {
      localStorage.setItem('radiohub_bitrate_override', JSON.stringify(newOverride));
    } else {
      localStorage.removeItem('radiohub_bitrate_override');
    }
    // HLS aktiv -> neu starten mit neuer Bitrate
    if (appState.playerMode === 'hls' && appState.currentStation) {
      await engine.restartHLS();
    }
  }
</script>

<footer class="hifi-player">
  <audio
    bind:this={audioEl}
    crossorigin="anonymous"
    ontimeupdate={handleTimeUpdate}
    onloadedmetadata={handleTimeUpdate}
    ondurationchange={handleTimeUpdate}
    onseeking={handleSeeking}
    onseeked={handleSeeked}
    onended={() => engine.handleEnded()}
    onerror={(e) => engine.handleError(e)}
  ></audio>

  <!-- DISPLAY (Scrolling Text) -->
  <div class="player-section display-section">
    <div class="section-label">DISPLAY</div>
    <div class="section-content">
      <div class="display-box name-display" class:display-inactive={!displayActive} bind:this={displayContainer}>
        <div class="display-text-wrapper">
          {#if displayActive}
            <div class="display-text-scroll" class:scroll={needsScroll}>
              <span>{displayName}</span>
              {#if needsScroll}
                <span>{displayName}</span>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <!-- SOURCE -->
  <div class="player-section source-section">
    <div class="section-label">SOURCE</div>
    <div class="section-content">
      <div class="display-box source-display" class:display-inactive={!displayActive}>
        <span class="display-text">{sourceType}</span>
        {#if appState.playerMode !== 'none' && displayActive}
          <span class="source-mode">{appState.recordingType === 'hls-rec' ? 'HLS-REC' : appState.recordingType === 'direct' ? 'REC' : appState.playerMode === 'hls' ? 'HLS' : appState.playerMode === 'direct' ? 'LIVE' : appState.playerMode === 'recording' ? 'REC' : 'FILE'}</span>
        {/if}
      </div>
    </div>
  </div>

  <!-- VU / VOLUME / VU -->
  <div class="center-group">
    <div class="player-section vu-section">
      <div class="section-label">VU</div>
      <div class="section-content">
        <HiFiVuMeter volume={appState.volume} active={appState.isPlaying && !appState.isPaused} />
      </div>
    </div>

    <div class="player-section volume-section">
      <div class="section-label">VOLUME</div>
      <div class="section-content">
        <HiFiKnob
          bind:value={appState.volume}
          min={0}
          max={100}
          size="large"
          onchange={(e) => engine.setVolume(e.value)}
        />
      </div>
    </div>

    <div class="player-section vu-section">
      <div class="section-label">VU</div>
      <div class="section-content">
        <HiFiVuMeter volume={appState.volume} active={appState.isPlaying && !appState.isPaused} />
      </div>
    </div>
  </div>

  <!-- TIMER (hh:mm:ss) -->
  <div class="player-section timer-section">
    <div class="section-label">TIMER</div>
    <div class="section-content">
      <div class="display-box timer-display"
        class:timer-red={timerColor === 'red'}
        class:timer-yellow={timerColor === 'yellow'}
        class:timer-green={timerColor === 'green'}
        class:timer-amber={timerColor === 'amber'}
        class:timer-inactive={!timerActive}
      >
        <span class="timer-text">{timerActive ? formatTime(timerDisplayTime) : '00:00:00'}</span>
        {#if appState.isRecording && recordingBitrateLabel()}
          <span class="timer-kbps">{recordingBitrateLabel()}</span>
        {/if}
      </div>
    </div>
  </div>

  <!-- TRANSPORT -->
  <div class="player-section transport-section">
    <div class="transport-header">
      <span class="transport-time">
        {#if isRecordingPlayback}
          {formatTimeShort(currentTime)}
        {:else if isPodcast}
          {formatTimeShort(currentTime)}
        {:else if isHLSMode && appState.hlsStatus}
          {#if appState.isLive}
            <span class="live-indicator">LIVE</span>
          {:else}
            -{formatTimeShort(secondsBehindLive)}
          {/if}
        {/if}
      </span>
      <span class="section-label">{transportLabel}</span>
      <span class="transport-time" class:time-blue={isHLSMode && appState.hlsStatus?.buffered_seconds}>
        {#if isRecordingPlayback && duration > 0}
          {formatTimeShort(duration)}
        {:else if isPodcast && duration > 0}
          {formatTimeShort(duration)}
        {:else if isHLSMode && appState.hlsStatus?.buffered_seconds}
          {formatTimeShort(appState.hlsStatus.buffered_seconds)}
        {/if}
      </span>
    </div>
    <div class="section-content transport-content">
      <!-- Fader (horizontal) -->
      <div class="transport-fader-container" class:disabled={!_canSeek || appState.isRecording} class:seeking={isSeeking}>
        <div class="transport-fader-track">
          <input
            type="range"
            class="transport-fader"
            min="0"
            max="100"
            step={isHLSMode && hlsSegRange > 0 && !isLive ? (100 / hlsSegRange) : 0.1}
            value={seekPosition}
            disabled={!_canSeek || isSeeking || appState.isRecording}
            oninput={handleFaderInput}
            onmousedown={handleFaderStart}
            ontouchstart={handleFaderStart}
            onmouseup={handleFaderEnd}
            ontouchend={handleFaderEnd}
          />
          <div class="fader-knob" class:seeking={isSeeking} style="left: {seekPosition}%"></div>
        </div>
      </div>

      <!-- Transport Buttons -->
      <div class="transport-controls">
        <!-- Prev Track -->
        <button
          class="transport-btn"
          disabled={!canNavigate || appState.isRecording}
          title={appState.isRecording ? 'Aufnahme läuft' : !canNavigate ? 'Kein vorheriger Sender verfügbar' : prevStationName() || 'Vorheriger Sender'}
          onmouseenter={sfx.hover}
          onmousedown={() => prevPressed = true}
          onmouseup={() => { prevPressed = false; navigatePrev(); }}
          onmouseleave={() => prevPressed = false}
          ontouchstart={() => prevPressed = true}
          ontouchend={() => { prevPressed = false; navigatePrev(); }}
        >
          <HiFiLed color={prevPressed ? 'yellow' : 'off'} size="small" />
          <i class="fa-solid fa-backward-step transport-icon"></i>
        </button>

        <!-- -10s -->
        <button
          class="transport-btn"
          disabled={!_canSeek || appState.isRecording}
          title={appState.isRecording ? 'Aufnahme läuft' : !_canSeek ? 'Spulen nicht verfügbar (nur im HLS-Modus)' : '10 Sekunden zurückspulen'}
          onmouseenter={sfx.hover}
          onmousedown={() => skipBackPressed = true}
          onmouseup={() => { skipBackPressed = false; handleSkip(-10); }}
          onmouseleave={() => skipBackPressed = false}
          ontouchstart={() => skipBackPressed = true}
          ontouchend={() => { skipBackPressed = false; handleSkip(-10); }}
        >
          <HiFiLed color={skipBackPressed ? 'yellow' : 'off'} size="small" />
          <i class="fa-solid fa-backward transport-icon"></i>
        </button>

        <!-- Stop -->
        <button class="transport-btn" onmouseenter={sfx.hover} onclick={() => { handleStop(); sfx.click(); }} disabled={appState.isRecording} title={appState.isRecording ? 'Aufnahme läuft -- erst REC stoppen' : 'Wiedergabe stoppen'}>
          <HiFiLed color={stopLedColor} size="small" />
          <i class="fa-solid fa-stop transport-icon"></i>
        </button>

        <!-- Play/Pause -->
        <button class="transport-btn" onmouseenter={sfx.hover} onclick={() => { handlePlayPause(); sfx.click(); }} disabled={appState.isRecording} title={appState.isRecording ? 'Aufnahme läuft' : appState.isPaused ? 'Pause' : 'Abspielen'}>
          <HiFiLed color={playPauseLedColor} size="small" />
          <i class="fa-solid {appState.isPaused ? 'fa-pause' : 'fa-play'} transport-icon"></i>
        </button>

        <!-- Rec -->
        <button class="transport-btn rec" onmouseenter={sfx.hover} onclick={() => { handleRec(); sfx.click(); }} disabled={!isStation || isRecordingPlayback} title={isRecordingPlayback ? 'Nicht bei Aufnahme-Wiedergabe' : !isStation ? 'Kein Sender ausgewaehlt' : appState.isRecording ? 'Aufnahme stoppen' : 'Aufnahme starten'}>
          <HiFiLed color={recLedColor} size="small" blink={appState.isRecording} />
          <i class="fa-solid fa-circle transport-icon"></i>
        </button>

        <!-- +10s -->
        <button
          class="transport-btn"
          disabled={!_canSeek || appState.isRecording}
          title={appState.isRecording ? 'Aufnahme läuft' : !_canSeek ? 'Spulen nicht verfügbar (nur im HLS-Modus)' : '10 Sekunden vorspulen'}
          onmouseenter={sfx.hover}
          onmousedown={() => skipFwdPressed = true}
          onmouseup={() => { skipFwdPressed = false; handleSkip(10); }}
          onmouseleave={() => skipFwdPressed = false}
          ontouchstart={() => skipFwdPressed = true}
          ontouchend={() => { skipFwdPressed = false; handleSkip(10); }}
        >
          <HiFiLed color={skipFwdPressed ? 'yellow' : 'off'} size="small" />
          <i class="fa-solid fa-forward transport-icon"></i>
        </button>

        <!-- Next Track -->
        <button
          class="transport-btn"
          disabled={!canNavigate || appState.isRecording}
          title={appState.isRecording ? 'Aufnahme läuft' : !canNavigate ? 'Kein nächster Sender verfügbar' : nextStationName() || 'Nächster Sender'}
          onmouseenter={sfx.hover}
          onmousedown={() => nextPressed = true}
          onmouseup={() => { nextPressed = false; navigateNext(); }}
          onmouseleave={() => nextPressed = false}
          ontouchstart={() => nextPressed = true}
          ontouchend={() => { nextPressed = false; navigateNext(); }}
        >
          <HiFiLed color={nextPressed ? 'yellow' : 'off'} size="small" />
          <i class="fa-solid fa-forward-step transport-icon"></i>
        </button>

        <!-- Live -->
        <button
          class="transport-btn live-btn"
          disabled={isLive || !isHLSMode || appState.isRecording}
          title={appState.isRecording ? 'Aufnahme läuft' : isLive ? 'Bereits live' : !isHLSMode ? 'Live nur im HLS-Modus verfügbar' : 'Zur Live-Position springen'}
          onclick={() => engine.goLive()}
        >
          <HiFiLed color={liveLedColor} size="small" />
          <i class="fa-solid fa-tower-broadcast transport-icon"></i>
        </button>

        <!-- Mode Toggle (Original/HLS) -->
        {#if isStation}
          <button
            class="transport-btn mode-btn"
            disabled={!canToggleStreamMode}
            title={!canToggleStreamMode ? 'Moduswechsel nicht verfügbar' : appState.playerMode === 'hls' ? 'Zu Original-Stream wechseln (Direct)' : 'Zu HLS-Stream wechseln (zeitversetzt)'}
            onclick={() => engine.toggleStreamMode()}
          >
            <HiFiLed color={modeLedColor} size="small" />
            <i class="fa-solid {appState.playerMode === 'hls' ? 'fa-arrows-rotate' : 'fa-wave-square'} transport-icon"></i>
          </button>
        {/if}
      </div>

      <!-- Bitrate LED Selector (nur bei HLS sichtbar) -->
      {#if isHLSMode && appState.hlsActive}
        <div class="bitrate-bar">
          <span class="bitrate-label">BITRATE</span>
          <HiFiBitrateLed
            activeBitrate={hlsInputBitrate}
            overrideBitrate={bitrateOverride}
            onchange={handleBitrateOverrideChange}
          />
        </div>
      {/if}
    </div>
  </div>

  <!-- Error Overlay -->
  {#if appState.playerError}
    <div class="player-error">
      <span>{appState.playerError}</span>
      <button onclick={() => appState.playerError = null} title="Fehlermeldung schließen">x</button>
    </div>
  {/if}
</footer>

<style>
  .hifi-player {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 15px 10px;
    background: var(--hifi-bg-panel);
    border-top: 1px solid var(--hifi-border-dark);
    position: relative;
    z-index: 30;
    overflow: visible;
    box-shadow: 0 -4px 8px var(--hifi-shadow-dark);
    user-select: none;
    -webkit-user-select: none;
  }

  .center-group {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: var(--hifi-bg-panel);
    padding: 6px 16px 14px;
    border-radius: 20px 20px 0 0;
    box-shadow: var(--hifi-shadow-button);
    position: relative;
    z-index: 3;
    margin-top: -40px;
    margin-bottom: -30px;
  }

  .player-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
  }

  /* Display-Section darf wachsen */
  .player-section.display-section {
    flex-shrink: 1;
    flex-grow: 1;
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
  }

  /* VU-Meter Sektion */
  .vu-section {
    width: 26px;
    min-width: 26px;
    margin-top: 30px;
  }

  .section-label {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
    margin-bottom: 8px;
    height: 12px;
  }

  .section-content {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 64px;
  }

  .display-section .section-content {
    width: 100%;
  }

  /* Display-Box */
  .display-box {
    background: var(--hifi-display-bg);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    height: 64px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }

  .display-box.display-inactive .display-text {
    opacity: 0.2;
  }

  .display-text {
    font-family: var(--hifi-font-display);
    color: var(--hifi-display-text);
    text-shadow: 0 0 8px var(--hifi-display-text);
  }

  /* SOURCE */
  .source-section {
    width: 98px;
  }

  .source-display {
    width: 84px;
    padding: 0 8px;
  }

  .source-display .display-text {
    font-family: var(--hifi-font-values);
    font-size: 11px;
    font-weight: 700;
    color: var(--hifi-display-blue);
    text-shadow: 0 0 8px var(--hifi-display-blue);
  }

  .source-display.display-inactive .display-text {
    color: var(--hifi-display-blue);
    opacity: 0.2;
    text-shadow: none;
  }

  .source-mode {
    font-family: var(--hifi-font-values);
    font-size: 7px;
    font-weight: 700;
    color: var(--hifi-display-text);
    text-shadow: 0 0 4px var(--hifi-display-text);
    opacity: 0.7;
    margin-top: 2px;
    letter-spacing: 1px;
  }

  /* DISPLAY */
  .name-display {
    width: 100%;
    padding: 0 12px;
    overflow: hidden;
    box-sizing: border-box;
    display: flex;
    align-items: center;
  }

  .display-text-wrapper {
    width: 100%;
    overflow: hidden;
    position: relative;
    text-align: center;
  }

  .display-text-scroll {
    font-family: var(--hifi-font-display);
    font-size: 32px;
    font-weight: 500;
    color: var(--hifi-display-text);
    text-shadow: 0 0 8px var(--hifi-display-text);
    white-space: nowrap;
    display: inline-flex;
  }

  .display-text-scroll.scroll {
    animation: scrollText 15s linear infinite;
  }

  .display-text-scroll.scroll span {
    padding-right: 100px;
  }

  @keyframes scrollText {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
  }

  .display-meta {
    font-family: var(--hifi-font-display);
    font-size: 9px;
    color: var(--hifi-display-text);
    opacity: 0.6;
    margin-top: 1px;
    display: flex;
    gap: 8px;
    justify-content: center;
    width: 100%;
  }

  .quality-info {
    font-family: var(--hifi-font-values);
    font-size: 7px;
    color: var(--hifi-display-text);
    text-shadow: 0 0 4px var(--hifi-display-text);
    letter-spacing: 0.5px;
  }

  /* VOLUME */
  .volume-section {
    width: 80px;
    margin: 0 8px;
  }

  .volume-section .section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
  }

  .volume-section .section-content {
    margin-top: 5px;
    height: auto;
    padding-bottom: 0;
  }

  /* TIMER */
  .timer-section {
    width: 110px;
  }

  .timer-display {
    width: 96px;
    height: 64px;
    padding: 0 14px;
  }

  .timer-text {
    font-family: var(--hifi-font-values);
    font-size: 13px;
    font-weight: 700;
    color: var(--hifi-display-text);
    text-shadow: 0 0 6px var(--hifi-display-text);
    letter-spacing: 1px;
  }

  .timer-display.timer-inactive .timer-text {
    opacity: 0.3;
  }

  .timer-display.timer-red .timer-text {
    color: var(--hifi-led-red);
    text-shadow: none;
  }

  .timer-display.timer-yellow .timer-text {
    color: var(--hifi-led-yellow);
    text-shadow: none;
  }

  .timer-display.timer-green .timer-text {
    color: var(--hifi-display-text);
    text-shadow: 0 0 8px var(--hifi-display-text);
  }

  .timer-display.timer-amber .timer-text {
    color: var(--hifi-led-amber);
    text-shadow: none;
  }

  .timer-kbps {
    font-family: var(--hifi-font-body);
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    opacity: 0.8;
    margin-top: 2px;
  }

  .timer-display.timer-red .timer-kbps {
    color: var(--hifi-led-red);
  }

  .timer-display.timer-amber .timer-kbps {
    color: var(--hifi-led-amber);
  }

  /* TRANSPORT */
  .transport-section {
    width: 360px;
  }

  .transport-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    margin-bottom: 4px;
  }

  .transport-time {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    min-width: 50px;
  }

  .transport-time:last-child {
    text-align: right;
  }

  .transport-time.time-blue {
    color: var(--hifi-led-blue);
    text-shadow: 0 0 4px var(--hifi-led-blue-glow);
  }

  .live-indicator {
    color: var(--hifi-led-blue);
    font-weight: 700;
    text-shadow: 0 0 6px var(--hifi-led-blue-glow);
  }

  .transport-content {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
    min-height: 80px;
  }

  .bitrate-bar {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding: 0 4px;
    gap: 6px;
  }

  .bitrate-label {
    font-family: var(--hifi-font-labels);
    font-size: 8px;
    font-weight: 600;
    color: var(--hifi-text-secondary);
    letter-spacing: 0.5px;
    text-transform: uppercase;
    white-space: nowrap;
  }

  /* Horizontal Fader */
  .transport-fader-container {
    width: 100%;
    height: 16px;
    padding: 0 4px;
    margin-top: -5px;
  }

  .transport-fader-container.disabled {
    opacity: 0.3;
    pointer-events: none;
  }

  .transport-fader-container.seeking {
    opacity: 0.7;
  }

  .transport-fader-container.seeking .transport-fader-track {
    animation: seeking-pulse 0.6s ease-in-out infinite;
  }

  @keyframes seeking-pulse {
    0%, 100% { opacity: 0.7; }
    50% { opacity: 1; }
  }

  .transport-fader-track {
    position: relative;
    width: 100%;
    height: 8px;
    background: var(--hifi-fader-track);
    border-radius: 4px;
    margin-top: 4px;
  }

  .transport-fader {
    position: absolute;
    top: -4px;
    left: 0;
    width: 100%;
    height: 16px;
    appearance: none;
    background: transparent;
    cursor: pointer;
    z-index: 2;
  }

  .transport-fader::-webkit-slider-thumb {
    appearance: none;
    width: 16px;
    height: 16px;
    background: var(--hifi-fader-cap);
    border-radius: 3px;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.4);
  }

  .transport-fader::-moz-range-thumb {
    width: 16px;
    height: 16px;
    background: var(--hifi-fader-cap);
    border-radius: 3px;
    cursor: pointer;
    border: none;
  }

  .fader-knob {
    display: none;
  }

  /* Transport Buttons */
  .transport-controls {
    display: flex;
    gap: 3px;
    justify-content: center;
  }

  .transport-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    padding: 5px 6px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-button);
    cursor: pointer;
    transition: background 0.1s ease, box-shadow 0.1s ease;
    min-width: 34px;
  }

  .transport-btn:hover:not(:disabled) {
    background: var(--hifi-bg-secondary);
  }

  .transport-btn:active:not(:disabled) {
    box-shadow: var(--hifi-shadow-inset);
  }

  .transport-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .transport-icon {
    font-size: 12px;
    color: var(--hifi-text-primary);
    line-height: 1;
  }

  .transport-btn.live-btn .transport-icon {
    color: var(--hifi-led-blue);
  }

  .transport-btn.live-btn:disabled .transport-icon {
    color: var(--hifi-led-blue);
    opacity: 1;
  }

  .transport-btn.rec {
    background: rgba(180, 40, 40, 0.08);
  }

  .transport-btn.rec:hover:not(:disabled) {
    background: rgba(180, 40, 40, 0.15);
  }

  .transport-btn.rec .transport-icon {
    color: var(--hifi-led-red);
    opacity: 0.6;
  }

  /* Player Error */
  .player-error {
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: var(--hifi-led-red);
    color: white;
    padding: 4px 12px;
    border-radius: 4px 4px 0 0;
    font-size: 11px;
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }

  .player-error button {
    background: none;
    border: none;
    color: white;
    cursor: pointer;
    font-size: 14px;
    padding: 0 4px;
    opacity: 0.7;
  }

  .player-error button:hover {
    opacity: 1;
  }
</style>
