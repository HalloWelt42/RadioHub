<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import HiFiKnob from './hifi/HiFiKnob.svelte';
  import HiFiVuMeter from './hifi/HiFiVuMeter.svelte';
  import { appState, actions } from '../lib/store.svelte.js';
  import * as engine from '../lib/playerEngine.js';

  // Audio Element
  let audioEl = $state(null);

  // Lokaler Display-State (High-Frequency, nicht in appState)
  let currentTime = $state(0);
  let duration = $state(0);
  let seekPosition = $state(0);
  let isDragging = $state(false);
  let isSeeking = $state(false);
  let seekDebounceTimer = null;

  // Button Press States fuer gelbe LEDs
  let prevPressed = $state(false);
  let nextPressed = $state(false);
  let skipBackPressed = $state(false);
  let skipFwdPressed = $state(false);

  // === Engine Init ===
  $effect(() => {
    if (audioEl) {
      engine.init(audioEl, appState);
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

  // === Handlers ===
  function handlePlayPause() {
    if (appState.isPlaying && !appState.isPaused) {
      engine.togglePause();
    } else if (appState.isPaused) {
      engine.resume();
    } else if (appState.currentStation || appState.currentEpisode) {
      if (appState.currentStation) {
        engine.playStation(appState.currentStation);
      } else if (appState.currentEpisode) {
        engine.playPodcast(appState.currentEpisode, appState.currentEpisode?.podcast);
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

  // === Format ===
  function formatTime(seconds) {
    if (!seconds || !isFinite(seconds)) return '00:00:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  function formatTimeShort(seconds) {
    if (!seconds || !isFinite(seconds)) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

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
    // Seek sofort ausfuehren, isDragging erst danach aufheben
    // damit handleTimeUpdate die Position nicht zuruecksetzt
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
  let displayName = $derived(
    appState.isPlaying || appState.isPaused
      ? (appState.currentStation?.name || appState.currentEpisode?.title || '')
      : ''
  );

  let nowPlayingMeta = $derived(
    appState.isPlaying || appState.isPaused
      ? (appState.currentStation?.tags?.split(',')[0] || appState.currentEpisode?.podcast?.title || '')
      : ''
  );

  let sourceType = $derived(
    appState.isPlaying || appState.isPaused
      ? (appState.currentStation ? 'Tuner' : appState.currentEpisode ? 'Podcast' : '---')
      : '---'
  );

  let hasSource = $derived(appState.currentStation || appState.currentEpisode);
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

  let _canSeek = $derived(appState.playerMode === 'podcast' || appState.playerMode === 'hls');
  let canNavigate = $derived(appState.stations?.length > 0 || isPodcast);

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

  const CHAR_WIDTH = 9.6;
  let needsScroll = $derived(displayName.length * CHAR_WIDTH > displayWidth);

  // Timer
  let timerColor = $derived(
    appState.isRecording ? 'red' :
    isHLSMode ? 'yellow' :
    isPodcast ? 'green' :
    'default'
  );

  let timerDisplayTime = $derived(
    appState.isRecording ? appState.recordingElapsed :
    (appState.hlsStatus?.buffered_seconds) ? appState.hlsStatus.buffered_seconds :
    currentTime
  );

  let timerActive = $derived(appState.isRecording || appState.hlsActive || isPodcast);

  // === LED States ===
  let playPauseLedColor = $derived(
    appState.isPaused ? 'yellow' :
    appState.isPlaying ? 'green' : 'off'
  );
  let stopLedColor = $derived(!appState.isPlaying && !appState.isPaused && hasSource ? 'yellow' : 'off');
  let recLedColor = $derived(appState.isRecording ? 'red' : 'off');
  let liveLedColor = $derived(isHLSMode && !isLive ? 'blue' : 'off');

  // Mode LED (zeigt aktuellen Modus)
  let modeLedColor = $derived(
    appState.playerMode === 'hls' ? 'green' :
    appState.playerMode === 'direct' ? 'yellow' :
    'off'
  );
</script>

<footer class="hifi-player">
  <audio
    bind:this={audioEl}
    ontimeupdate={handleTimeUpdate}
    onloadedmetadata={handleTimeUpdate}
    ondurationchange={handleTimeUpdate}
    onseeking={handleSeeking}
    onseeked={handleSeeked}
    onended={() => engine.handleEnded()}
    onerror={(e) => engine.handleError(e)}
  ></audio>

  <!-- SOURCE -->
  <div class="player-section source-section">
    <div class="section-label">SOURCE</div>
    <div class="section-content">
      <div class="display-box source-display" class:display-inactive={!displayActive}>
        <span class="display-text">{sourceType}</span>
        {#if appState.playerMode !== 'none' && displayActive}
          <span class="source-mode">{appState.playerMode === 'hls' ? 'HLS' : appState.playerMode === 'direct' ? 'LIVE' : 'FILE'}</span>
        {/if}
      </div>
    </div>
  </div>

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
        {#if displayActive}
          <div class="display-meta">
            {#if nowPlayingMeta}
              {nowPlayingMeta}
            {/if}
            {#if appState.streamQuality && appState.playerMode !== 'podcast'}
              <span class="quality-info">
                {appState.streamQuality.inputCodec.toUpperCase()}
                {appState.streamQuality.inputBitrate}k
                {#if appState.playerMode === 'hls'}
                  &rarr; HLS {appState.streamQuality.outputBitrate}k
                {/if}
              </span>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- VU-METER LINKS -->
  <div class="player-section vu-section">
    <div class="section-label">VU</div>
    <div class="section-content">
      <HiFiVuMeter volume={appState.volume} active={appState.isPlaying && !appState.isPaused} />
    </div>
  </div>

  <!-- VOLUME (Drehregler) -->
  <div class="player-section volume-section">
    <div class="section-label">VOLUME</div>
    <div class="section-content">
      <HiFiKnob
        bind:value={appState.volume}
        min={0}
        max={100}
        onchange={(e) => engine.setVolume(e.value)}
      />
    </div>
  </div>

  <!-- VU-METER RECHTS -->
  <div class="player-section vu-section">
    <div class="section-label">VU</div>
    <div class="section-content">
      <HiFiVuMeter volume={appState.volume} active={appState.isPlaying && !appState.isPaused} />
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
        class:timer-inactive={!timerActive}
      >
        <span class="timer-text">{timerActive ? formatTime(timerDisplayTime) : '00:00:00'}</span>
      </div>
    </div>
  </div>

  <!-- TRANSPORT -->
  <div class="player-section transport-section">
    <div class="transport-header">
      <span class="transport-time">
        {#if isPodcast}
          {formatTimeShort(currentTime)}
        {:else if isHLSMode && appState.hlsStatus}
          {#if appState.isLive}
            <span class="live-indicator">LIVE</span>
          {:else}
            -{formatTimeShort(secondsBehindLive)}
          {/if}
        {/if}
      </span>
      <span class="section-label">TRANSPORT</span>
      <span class="transport-time">
        {#if isPodcast && duration > 0}
          {formatTimeShort(duration)}
        {:else if isHLSMode && appState.hlsStatus?.buffered_seconds}
          {formatTimeShort(appState.hlsStatus.buffered_seconds)}
        {/if}
      </span>
    </div>
    <div class="section-content transport-content">
      <!-- Fader (horizontal) -->
      <div class="transport-fader-container" class:disabled={!_canSeek} class:seeking={isSeeking}>
        <div class="transport-fader-track">
          <input
            type="range"
            class="transport-fader"
            min="0"
            max="100"
            step={isHLSMode && hlsSegRange > 0 && !isLive ? (100 / hlsSegRange) : 0.1}
            value={seekPosition}
            disabled={!_canSeek || isSeeking}
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
          disabled={!canNavigate}
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
          disabled={!_canSeek}
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
        <button class="transport-btn" onclick={handleStop}>
          <HiFiLed color={stopLedColor} size="small" />
          <i class="fa-solid fa-stop transport-icon"></i>
        </button>

        <!-- Play/Pause -->
        <button class="transport-btn" onclick={handlePlayPause}>
          <HiFiLed color={playPauseLedColor} size="small" />
          <i class="fa-solid {appState.isPaused ? 'fa-pause' : 'fa-play'} transport-icon"></i>
        </button>

        <!-- Rec -->
        <button class="transport-btn rec" onclick={handleRec} disabled={!isStation}>
          <HiFiLed color={recLedColor} size="small" blink={appState.isRecording} />
          <i class="fa-solid fa-circle transport-icon"></i>
        </button>

        <!-- +10s -->
        <button
          class="transport-btn"
          disabled={!_canSeek}
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
          disabled={!canNavigate}
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
          disabled={isLive || !isHLSMode}
          onclick={() => engine.goLive()}
        >
          <HiFiLed color={liveLedColor} size="small" />
          <i class="fa-solid fa-tower-broadcast transport-icon"></i>
        </button>
      </div>
    </div>
  </div>

  <!-- Error Overlay -->
  {#if appState.playerError}
    <div class="player-error">
      <span>{appState.playerError}</span>
      <button onclick={() => appState.playerError = null}>x</button>
    </div>
  {/if}
</footer>

<style>
  .hifi-player {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 15px 22px;
    background: var(--hifi-bg-panel);
    border-top: 1px solid var(--hifi-border-dark);
    position: relative;
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
  }

  .section-label {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 400;
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
    border: 1px solid var(--hifi-display-border);
    border-radius: var(--hifi-border-radius-sm);
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
    font-weight: 400;
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
    font-weight: 400;
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
  }

  .display-text-wrapper {
    width: 100%;
    overflow: hidden;
    position: relative;
  }

  .display-text-scroll {
    font-family: var(--hifi-font-display);
    font-size: 16px;
    font-weight: 400;
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
    color: var(--hifi-display-blue);
    text-shadow: 0 0 4px var(--hifi-display-blue);
    letter-spacing: 0.5px;
  }

  /* VOLUME */
  .volume-section {
    width: 55px;
    margin: 0 12px;
  }

  .volume-section .section-content {
    margin-top: 10px;
  }

  /* TIMER */
  .timer-section {
    width: 98px;
  }

  .timer-display {
    width: 84px;
    height: 64px;
    padding: 0 8px;
  }

  .timer-text {
    font-family: var(--hifi-font-values);
    font-size: 12px;
    font-weight: 400;
    color: var(--hifi-display-text);
    text-shadow: 0 0 8px var(--hifi-display-text);
    letter-spacing: 1px;
  }

  .timer-display.timer-inactive .timer-text {
    opacity: 0.3;
  }

  .timer-display.timer-red .timer-text {
    color: var(--hifi-led-red);
    text-shadow: 0 0 8px var(--hifi-led-red-glow);
  }

  .timer-display.timer-yellow .timer-text {
    color: var(--hifi-led-yellow);
    text-shadow: 0 0 8px var(--hifi-led-yellow-glow);
  }

  .timer-display.timer-green .timer-text {
    color: var(--hifi-display-text);
    text-shadow: 0 0 8px var(--hifi-display-text);
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
    font-weight: 400;
    color: var(--hifi-text-secondary);
    min-width: 50px;
  }

  .transport-time:last-child {
    text-align: right;
  }

  .live-indicator {
    color: var(--hifi-led-blue);
    font-weight: 700;
    text-shadow: 0 0 6px var(--hifi-led-blue-glow);
  }

  .transport-content {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 100%;
    height: 64px;
    justify-content: center;
  }

  /* Horizontal Fader */
  .transport-fader-container {
    width: 100%;
    height: 16px;
    padding: 0 4px;
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
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    cursor: pointer;
    transition: background 0.1s ease;
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

  .transport-btn.rec .transport-icon {
    color: var(--hifi-led-red);
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
