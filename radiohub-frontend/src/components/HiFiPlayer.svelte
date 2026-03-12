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
  import { t } from '../lib/i18n.svelte.js';

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

    // Polling starten wenn Station spielt und ICY unterstützt
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
      // Stilles Fehlen -- kein Titel verfügbar
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
    if (!appState.isRecording) {
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

  let sourceType = $derived(
    appState.isPlaying || appState.isPaused
      ? (appState.currentStation ? t('player.tuner') : appState.currentEpisode ? 'Podcast' : appState.currentRecording ? t('player.aufnahme') : '---')
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

  // Prev/Next Namen für Tooltips
  let prevStationName = $derived(() => {
    // Podcast-Modus: vorherige Episode
    if (isPodcast && appState.podcastPlaylist?.length > 1) {
      const idx = appState.currentEpisodeIndex ?? -1;
      if (idx > 0) return appState.podcastPlaylist[idx - 1]?.episode?.title;
      return null;
    }
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
    // Podcast-Modus: nächste Episode
    if (isPodcast && appState.podcastPlaylist?.length > 1) {
      const idx = appState.currentEpisodeIndex ?? -1;
      if (idx >= 0 && idx < appState.podcastPlaylist.length - 1) return appState.podcastPlaylist[idx + 1]?.episode?.title;
      return null;
    }
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
    appState.recordingType === 'hls-rec' ? t('playerLabel.hlsRec') :
    appState.recordingType === 'direct' ? t('playerLabel.recording') :
    isRecordingPlayback ? t('playerLabel.playback') :
    isPodcast ? t('playerLabel.podcast') :
    isHLSMode ? t('playerLabel.timeshift') :
    t('playerLabel.transport')
  );

  // Mode Toggle Verfügbarkeit
  let canToggleStreamMode = $derived(
    !appState.isRecording && (
      (appState.playerMode === 'hls' && appState.canPlayDirect) ||
      (appState.playerMode === 'direct' && appState.canPlayHLS === true)
    )
  );

  // Play-Modus: linear -> reverse -> loop -> shuffle -> linear
  let canTogglePlayMode = $derived(isRecordingPlayback || appState.playerMode === 'podcast' || appState.activeTab === 'recordings');
  const playModeOrder = ['linear', 'reverse', 'loop', 'shuffle'];
  const playModeIcons = { linear: 'fa-arrow-right', reverse: 'fa-arrow-left', loop: 'fa-repeat', shuffle: 'fa-shuffle' };
  const playModeLabels = { linear: 'player.linear', reverse: 'player.rueckwaerts', loop: 'player.endlosschleife', shuffle: 'player.zufall' };
  let playModeLedColor = $derived(
    !canTogglePlayMode ? 'off' :
    appState.playMode === 'linear' ? 'white' :
    appState.playMode === 'reverse' ? 'amber' :
    appState.playMode === 'loop' ? 'green' :
    appState.playMode === 'shuffle' ? 'yellow' :
    'off'
  );

  function cyclePlayMode() {
    const idx = playModeOrder.indexOf(appState.playMode);
    appState.playMode = playModeOrder[(idx + 1) % playModeOrder.length];
  }

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
    <div class="section-label">{t('playerLabel.display')}</div>
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
    <div class="section-label">{t('playerLabel.source')}</div>
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
      <div class="section-label">{t('playerLabel.vu')}</div>
      <div class="section-content">
        <HiFiVuMeter volume={appState.volume} active={appState.isPlaying && !appState.isPaused} />
      </div>
    </div>

    <div class="player-section volume-section">
      <div class="section-label">{t('playerLabel.volume')}</div>
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
      <div class="section-label">{t('playerLabel.vu')}</div>
      <div class="section-content">
        <HiFiVuMeter volume={appState.volume} active={appState.isPlaying && !appState.isPaused} />
      </div>
    </div>
  </div>

  <!-- TIMER (hh:mm:ss) -->
  <div class="player-section timer-section">
    <div class="section-label">{t('playerLabel.timer')}</div>
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
            <span class="live-indicator">{t('playerLabel.live')}</span>
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
          title={appState.isRecording ? t('player.recLaeuft') : !canNavigate ? (isPodcast ? t('player.keinePrevEpisode') : isRecordingPlayback ? t('player.keinePrevTitel') : t('player.keinPrev')) : prevStationName() || (isPodcast ? t('player.prevEpisode') : isRecordingPlayback ? t('player.prevTitel') : t('player.prevSender'))}
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
          title={appState.isRecording ? t('player.recLaeuft') : !_canSeek ? t('player.spulenNicht') : t('player.skipBack')}
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
        <button class="transport-btn" onmouseenter={sfx.hover} onclick={() => { handleStop(); sfx.click(); }} title={t('player.stop')}>
          <HiFiLed color={stopLedColor} size="small" />
          <i class="fa-solid fa-stop transport-icon"></i>
        </button>

        <!-- Play/Pause -->
        <button class="transport-btn" onmouseenter={sfx.hover} onclick={() => { handlePlayPause(); sfx.click(); }} disabled={appState.isRecording} title={appState.isRecording ? t('player.recLaeuft') : appState.isPaused ? t('player.pause') : t('player.play')}>
          <HiFiLed color={playPauseLedColor} size="small" />
          <i class="fa-solid {appState.isPaused ? 'fa-pause' : 'fa-play'} transport-icon"></i>
        </button>

        <!-- Rec -->
        <button class="transport-btn rec" onmouseenter={sfx.hover} onclick={() => { handleRec(); sfx.click(); }} disabled={appState.isRecording || !isStation || isRecordingPlayback} title={appState.isRecording ? t('player.recLaeuft') : isRecordingPlayback ? t('player.nichtBeiWiedergabe') : !isStation ? t('player.keinSender') : t('player.recStart')}>
          <HiFiLed color={recLedColor} size="small" blink={appState.isRecording} />
          <i class="fa-solid fa-circle transport-icon"></i>
        </button>

        <!-- +10s -->
        <button
          class="transport-btn"
          disabled={!_canSeek || appState.isRecording}
          title={appState.isRecording ? t('player.recLaeuft') : !_canSeek ? t('player.spulenNicht') : t('player.skipForward')}
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
          title={appState.isRecording ? t('player.recLaeuft') : !canNavigate ? (isPodcast ? t('player.keineNextEpisode') : isRecordingPlayback ? t('player.keineNextTitel') : t('player.keinNext')) : nextStationName() || (isPodcast ? t('player.nextEpisode') : isRecordingPlayback ? t('player.nextTitel') : t('player.nextSender'))}
          onmouseenter={sfx.hover}
          onmousedown={() => nextPressed = true}
          onmouseup={() => { nextPressed = false; navigateNext(); }}
          onmouseleave={() => nextPressed = false}
          ontouchstart={() => nextPressed = true}
          ontouchend={() => { nextPressed = false; navigateNext(); }}
        >
          <HiFiLed color={nextPressed ? 'yellow' : 'off'} size="small" />
          <i class="fa-solid fa-forward-step transport-icon" class:reversed={appState.playMode === 'reverse'}></i>
        </button>

        <!-- Live -->
        <button
          class="transport-btn live-btn"
          disabled={isLive || !isHLSMode || appState.isRecording}
          title={appState.isRecording ? t('player.recLaeuft') : isLive ? t('player.bereitsLive') : !isHLSMode ? t('player.liveNurHls') : t('player.goLive')}
          onclick={() => engine.goLive()}
        >
          <HiFiLed color={liveLedColor} size="small" />
          <i class="fa-solid fa-tower-broadcast transport-icon"></i>
        </button>

        <!-- Mode Toggle (Original/HLS) -- immer sichtbar, disabled wenn nicht nutzbar -->
        <button
          class="transport-btn mode-btn"
          disabled={!canToggleStreamMode}
          title={appState.isRecording ? t('player.recModuswechsel') : !canToggleStreamMode ? t('player.moduswechselNicht') : appState.playerMode === 'hls' ? t('player.directMode') : t('player.hlsMode')}
          onclick={() => engine.toggleStreamMode()}
        >
          <HiFiLed color={modeLedColor} size="small" />
          <i class="fa-solid {appState.playerMode === 'hls' ? 'fa-arrows-rotate' : 'fa-wave-square'} transport-icon"></i>
        </button>

        <!-- Play-Modus (Linear/Loop/Shuffle) -->
        <button
          class="transport-btn mode-btn"
          disabled={!canTogglePlayMode}
          title={!canTogglePlayMode ? t('player.wiedergabeModus') : t(playModeLabels[appState.playMode])}
          onmouseenter={sfx.hover}
          onclick={() => { cyclePlayMode(); sfx.click(); }}
        >
          <HiFiLed color={playModeLedColor} size="small" />
          <i class="fa-solid {playModeIcons[appState.playMode]} transport-icon"></i>
        </button>
      </div>

      <!-- Bitrate LED Selector (nur bei HLS sichtbar) -->
      {#if isHLSMode && appState.hlsActive}
        <div class="bitrate-bar">
          <span class="bitrate-label">{t('playerLabel.bitrate')}</span>
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
      <button onclick={() => appState.playerError = null} title={t('player.fehlerSchliessen')}>x</button>
    </div>
  {/if}
</footer>

<style>
  .hifi-player {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 15px 10px;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 50%, rgba(0,0,0,0.02) 100%),
        var(--hifi-brushed-metal),
        var(--hifi-bg-panel);
    border-top: 1px solid var(--hifi-border-dark);
    position: relative;
    z-index: 30;
    overflow: visible;
    box-shadow: 0 -4px 8px var(--hifi-shadow-dark), inset 0 1px 0 rgba(255,255,255,0.08);
  }

  .center-group {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.06) 0%, transparent 40%, rgba(0,0,0,0.03) 100%),
        var(--hifi-brushed-metal),
        var(--hifi-bg-panel);
    padding: 6px 16px 14px;
    border-radius: 20px 20px 0 0;
    box-shadow:
        var(--hifi-shadow-button),
        inset 0 1px 0 rgba(255,255,255,0.12),
        inset 1px 0 0 rgba(255,255,255,0.04),
        inset -1px 0 0 rgba(0,0,0,0.04);
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
    color: #888;
    text-transform: uppercase;
    margin-bottom: 8px;
    height: 12px;
    text-shadow:
        -1px -1px 1px rgba(0,0,0,0.8),
        1px 1px 0 rgba(255,255,255,0.12);
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
    color: var(--hifi-text-amber);
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
    color: var(--hifi-text-amber);
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
    pointer-events: none;
  }

  .transport-fader-container.disabled .transport-fader-track {
    opacity: 0.3;
  }

  .transport-fader-container.disabled .transport-fader {
    opacity: 0.3;
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
    cursor: not-allowed;
    background: var(--hifi-bg-tertiary);
    box-shadow: var(--hifi-shadow-button);
  }

  .transport-btn:disabled .transport-icon {
    opacity: 0.25;
  }

  .transport-icon {
    font-size: 12px;
    color: var(--hifi-text-primary);
    line-height: 1;
    transition: transform 0.2s;
  }

  .transport-icon.reversed {
    transform: scaleX(-1);
  }

  .transport-btn.live-btn .transport-icon {
    color: var(--hifi-led-blue);
  }

  .transport-btn.live-btn:disabled .transport-icon {
    color: var(--hifi-led-blue);
    opacity: 0.25;
  }

  .transport-btn.rec {
    background: color-mix(in srgb, var(--hifi-bg-tertiary) 92%, #b42828);
  }

  .transport-btn.rec:hover:not(:disabled) {
    background: color-mix(in srgb, var(--hifi-bg-secondary) 85%, #b42828);
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
