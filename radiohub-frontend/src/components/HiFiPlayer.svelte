<script>
  import Hls from 'hls.js';
  import HiFiLed from './hifi/HiFiLed.svelte';
  import HiFiKnob from './hifi/HiFiKnob.svelte';
  import HiFiVuMeter from './hifi/HiFiVuMeter.svelte';
  import { appState, actions } from '../lib/store.svelte.js';
  import { api } from '../lib/api.js';
  
  // Audio Element und HLS Instanz
  let audioEl = $state(null);
  let hlsInstance = null;
  let hlsReady = $state(false);
  
  // Playback State
  let currentTime = $state(0);
  let duration = $state(0);
  let seekPosition = $state(0);
  let isDragging = $state(false);
  let isSeeking = $state(false);  // Zeigt Seek in Progress
  let isPaused = $state(false);   // Pause-Status
  let seekDebounceTimer = null;   // Debounce für schnelles Ziehen
  
  // Button Press States für gelbe LEDs
  let prevPressed = $state(false);
  let nextPressed = $state(false);
  let skipBackPressed = $state(false);
  let skipFwdPressed = $state(false);
  
  // Recording Timer
  let recordingStartTime = $state(null);
  let recordingElapsed = $state(0);
  let recordingInterval = $state(null);
  
  // === HLS Setup ===
  function initHLS() {
    if (!audioEl || !Hls.isSupported()) {
      console.log('HLS nicht unterstützt, nutze Fallback');
      return false;
    }
    
    if (hlsInstance) {
      hlsInstance.destroy();
    }
    
    hlsInstance = new Hls({
      debug: false,
      enableWorker: true,
      lowLatencyMode: false,
      backBufferLength: 90  // 90 Sekunden Back-Buffer für Seeking
    });
    
    hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
      console.log('HLS Playlist geladen');
      hlsReady = true;
      audioEl.play().catch(err => console.error('HLS play error:', err));
    });
    
    hlsInstance.on(Hls.Events.ERROR, (event, data) => {
      console.error('HLS Error:', data.type, data.details);
      if (data.fatal) {
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            console.log('HLS Network Error - Reconnect in 3s');
            setTimeout(() => hlsInstance?.startLoad(), 3000);
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            console.log('HLS Media Error - Recovery');
            hlsInstance.recoverMediaError();
            break;
          default:
            console.log('Fataler HLS Error - Fallback zu Direkt-Stream');
            destroyHLS();
            playDirectStream();
            break;
        }
      }
    });
    
    return true;
  }
  
  function destroyHLS() {
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }
    hlsReady = false;
  }
  
  function loadHLSPlaylist() {
    if (!hlsInstance || !audioEl) return;
    
    const playlistUrl = api.getHLSPlaylistUrl();
    hlsInstance.loadSource(playlistUrl);
    hlsInstance.attachMedia(audioEl);
    console.log('HLS Playlist laden:', playlistUrl);
  }
  
  // Direkt-Stream ohne HLS (Fallback)
  function playDirectStream() {
    if (!audioEl || !appState.currentStation) return;
    
    destroyHLS();
    const url = appState.currentStation.url_resolved || appState.currentStation.url;
    audioEl.src = url;
    audioEl.load();
    audioEl.play().catch(err => console.error('Direct play error:', err));
    console.log('Direkt-Stream:', url);
  }
  
  // === Main Play Effect ===
  $effect(() => {
    if (!audioEl) return;
    
    if (appState.isPlaying) {
      if (appState.currentStation) {
        // Radio: HLS wenn verfügbar, sonst Direkt
        if (appState.hlsActive && Hls.isSupported()) {
          // Warten bis erste Segmente da sind
          setTimeout(() => {
            if (appState.hlsActive && appState.hlsStatus?.segment_count > 0) {
              initHLS();
              loadHLSPlaylist();
            } else {
              // Noch keine Segmente - direkt abspielen
              playDirectStream();
            }
          }, 3000);
        } else {
          playDirectStream();
        }
      } else if (appState.currentEpisode) {
        // Podcast: Direkt abspielen
        destroyHLS();
        audioEl.src = appState.currentEpisode.audio_url;
        audioEl.load();
        audioEl.play().catch(err => console.error('Podcast play error:', err));
      }
    } else {
      audioEl.pause();
      destroyHLS();
    }
  });
  
  // Volume Effect
  $effect(() => {
    if (audioEl) {
      audioEl.volume = appState.volume / 100;
    }
  });
  
  // Recording Timer Effect
  $effect(() => {
    if (appState.isRecording && !recordingInterval) {
      recordingStartTime = Date.now();
      recordingElapsed = 0;
      recordingInterval = setInterval(() => {
        recordingElapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
      }, 1000);
    } else if (!appState.isRecording && recordingInterval) {
      clearInterval(recordingInterval);
      recordingInterval = null;
      recordingStartTime = null;
      recordingElapsed = 0;
    }
  });
  
  // HLS Status Polling
  let hlsPollInterval = null;
  
  $effect(() => {
    const shouldPoll = appState.hlsActive;
    
    if (shouldPoll && !hlsPollInterval) {
      hlsPollInterval = setInterval(() => {
        actions.updateHLSStatus();
      }, 2000);
    } else if (!shouldPoll && hlsPollInterval) {
      clearInterval(hlsPollInterval);
      hlsPollInterval = null;
    }
    
    return () => {
      if (hlsPollInterval) {
        clearInterval(hlsPollInterval);
        hlsPollInterval = null;
      }
    };
  });
  
  // === Handlers ===
  function handlePlay() {
    if (appState.currentStation || appState.currentEpisode) {
      if (isPaused && audioEl) {
        // Resume from pause
        audioEl.play().catch(err => console.error('Resume error:', err));
        isPaused = false;
      } else {
        appState.isPlaying = true;
      }
    }
  }
  
  function handleStop() {
    actions.stop();
    isPaused = false;
  }
  
  function handlePause() {
    if (!audioEl) return;
    
    if (isPaused) {
      // Resume
      audioEl.play().catch(err => console.error('Resume error:', err));
      isPaused = false;
    } else {
      // Pause
      audioEl.pause();
      isPaused = true;
    }
  }
  
  function handleRec() {
    if (appState.isRecording) {
      actions.stopRecording();
    } else {
      actions.startRecording();
    }
  }
  
  function handleTimeUpdate() {
    if (!audioEl) return;
    
    currentTime = audioEl.currentTime || 0;
    duration = audioEl.duration || 0;
    
    // Seekbar-Position updaten (nicht während Dragging oder Seeking)
    if (!isDragging && !isSeeking) {
      if (isHLSMode && audioEl.seekable.length > 0) {
        // HLS: Position relativ zum seekbaren Bereich
        const seekEnd = audioEl.seekable.end(audioEl.seekable.length - 1);
        const seekStart = audioEl.seekable.start(0);
        const seekRange = seekEnd - seekStart;
        
        if (seekRange > 0) {
          seekPosition = ((currentTime - seekStart) / seekRange) * 100;
          
          // Live wenn am Ende (±2 Sekunden)
          const isAtLive = (seekEnd - currentTime) < 2;
          if (isAtLive !== appState.isLive) {
            actions.setLive(isAtLive);
          }
        }
      } else if (duration > 0) {
        // Podcast: Normal
        seekPosition = (currentTime / duration) * 100;
      }
    }
  }
  
  // Event: Seek gestartet
  function handleSeeking() {
    isSeeking = true;
  }
  
  // Event: Seek abgeschlossen
  function handleSeeked() {
    isSeeking = false;
    console.log('Seek abgeschlossen bei:', audioEl?.currentTime?.toFixed(1), 's');
  }
  
  // Format: HH:MM:SS
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
  
  // Skip ±10 Sekunden
  function skip(seconds) {
    if (!audioEl || !canSeek) return;
    const newTime = Math.max(0, Math.min(audioEl.duration || 0, audioEl.currentTime + seconds));
    audioEl.currentTime = newTime;
  }
  
  // Navigation
  function navigatePrev() {
    if (canNavigate) actions.navigatePrev();
  }
  
  function navigateNext() {
    if (canNavigate) actions.navigateNext();
  }
  
  // Zu Live springen (HLS)
  function goLive() {
    if (!audioEl) return;
    
    if (isHLSMode && audioEl.seekable.length > 0) {
      const seekEnd = audioEl.seekable.end(audioEl.seekable.length - 1);
      audioEl.currentTime = seekEnd - 0.5;
      actions.setLive(true);
      seekPosition = 100;
      console.log('Springe zu Live:', seekEnd);
    }
  }
  
  // Fader Handlers
  function handleFaderStart() {
    isDragging = true;
    // Debounce-Timer löschen wenn neu gestartet
    if (seekDebounceTimer) {
      clearTimeout(seekDebounceTimer);
      seekDebounceTimer = null;
    }
  }
  
  function handleFaderEnd() {
    isDragging = false;
    
    // Debounce: 150ms warten bevor Seek ausgeführt wird
    // Verhindert Probleme bei schnellem Hin-und-her-Ziehen
    if (seekDebounceTimer) clearTimeout(seekDebounceTimer);
    
    seekDebounceTimer = setTimeout(() => {
      executeSeek();
    }, 150);
  }
  
  function executeSeek() {
    if (isHLSMode && audioEl && audioEl.seekable.length > 0) {
      // HLS Seek
      const seekStart = audioEl.seekable.start(0);
      const seekEnd = audioEl.seekable.end(audioEl.seekable.length - 1);
      const seekRange = seekEnd - seekStart;
      const targetTime = seekStart + (seekPosition / 100) * seekRange;
      
      // Prüfen ob ans Ende geseekt (Live)
      const isSeekingToLive = seekPosition >= 97;
      
      isSeeking = true;  // Wird von handleSeeked() zurückgesetzt
      
      if (isSeekingToLive) {
        // Zu Live springen
        audioEl.currentTime = seekEnd - 0.3;
        actions.setLive(true);
        seekPosition = 100;
        console.log('Seek zu LIVE');
      } else {
        audioEl.currentTime = targetTime;
        actions.setLive(false);
        console.log('HLS Seek zu:', targetTime.toFixed(1), 's (Range:', seekRange.toFixed(0), 's)');
      }
      return;
    }
    
    // Podcast Seek
    if (audioEl && duration > 0) {
      isSeeking = true;
      audioEl.currentTime = (seekPosition / 100) * duration;
    }
  }
  
  function handleFaderInput(e) {
    seekPosition = parseFloat(e.target.value);
  }
  
  // === Derived States ===
  let displayName = $derived(
    appState.isPlaying ? (appState.currentStation?.name || appState.currentEpisode?.title || '') : ''
  );
  
  let nowPlayingMeta = $derived(
    appState.isPlaying ? (
      appState.currentStation?.tags?.split(',')[0] ||
      appState.currentEpisode?.podcast?.title ||
      ''
    ) : ''
  );
  
  let sourceType = $derived(
    appState.isPlaying ? (
      appState.currentStation ? 'Tuner' : 
      appState.currentEpisode ? 'Podcast' : 
      '---'
    ) : '---'
  );
  
  let hasSource = $derived(appState.currentStation || appState.currentEpisode);
  let isPodcast = $derived(!!appState.currentEpisode);
  let isStation = $derived(!!appState.currentStation);
  let isHLSMode = $derived(hlsReady && appState.hlsActive);
  let isLive = $derived(appState.isLive ?? true);
  
  let displayActive = $derived(appState.isPlaying && hasSource);
  
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
    appState.isRecording ? recordingElapsed :
    (appState.hlsStatus?.buffered_seconds) ? appState.hlsStatus.buffered_seconds :
    currentTime
  );
  
  let canSeek = $derived(isPodcast || isHLSMode);
  let canNavigate = $derived(appState.stations?.length > 0 || isPodcast);
  
  // LED States
  let playLedColor = $derived(appState.isPlaying && !isPaused ? 'green' : 'off');
  let pauseLedColor = $derived(isPaused ? 'yellow' : 'off');
  let stopLedColor = $derived(hasSource && !appState.isPlaying ? 'yellow' : 'off');
  let recLedColor = $derived(appState.isRecording ? 'red' : 'off');
  let liveLedColor = $derived(!isLive && isHLSMode ? 'blue' : 'off');
  
  let timerActive = $derived(appState.isRecording || appState.hlsActive || isPodcast);
  
  // Error Handlers
  function handleAudioEnded() {
    if (isPodcast) {
      actions.stop();
    }
    // HLS: Stream läuft weiter
  }
  
  function handleAudioError(e) {
    const error = e.target?.error;
    console.error('Audio error:', error);
    
    if (error) {
      switch (error.code) {
        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
          actions.showToast('Format nicht unterstützt', 'error');
          break;
        case MediaError.MEDIA_ERR_NETWORK:
          actions.showToast('Netzwerkfehler', 'error');
          break;
        case MediaError.MEDIA_ERR_DECODE:
          actions.showToast('Dekodierungsfehler', 'error');
          break;
        default:
          actions.showToast('Wiedergabefehler', 'error');
      }
    }
  }
</script>

<footer class="hifi-player">
  <audio 
    bind:this={audioEl}
    ontimeupdate={handleTimeUpdate}
    onloadedmetadata={handleTimeUpdate}
    ondurationchange={handleTimeUpdate}
    onseeking={handleSeeking}
    onseeked={handleSeeked}
    onended={handleAudioEnded}
    onerror={handleAudioError}
  ></audio>
  
  <!-- SOURCE -->
  <div class="player-section source-section">
    <div class="section-label">SOURCE</div>
    <div class="section-content">
      <div class="display-box source-display" class:display-inactive={!displayActive}>
        <span class="display-text">{sourceType}</span>
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
        {#if nowPlayingMeta && displayActive}
          <div class="display-meta">{nowPlayingMeta}</div>
        {/if}
      </div>
    </div>
  </div>
  
  <!-- VU-METER LINKS -->
  <div class="player-section vu-section">
    <div class="section-label">VU</div>
    <div class="section-content">
      <HiFiVuMeter volume={appState.volume} active={appState.isPlaying} />
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
        onchange={(e) => actions.setVolume(e.value)}
      />
    </div>
  </div>
  
  <!-- VU-METER RECHTS -->
  <div class="player-section vu-section">
    <div class="section-label">VU</div>
    <div class="section-content">
      <HiFiVuMeter volume={appState.volume} active={appState.isPlaying} />
    </div>
  </div>
  
  <!-- TIMER (hh:mm:ss) -->
  <div class="player-section timer-section">
    <div class="section-label">TIMER</div>
    <div class="section-content">
      <div class="display-box timer-display" class:timer-red={timerColor === 'red'} class:timer-yellow={timerColor === 'yellow'} class:timer-green={timerColor === 'green'} class:timer-inactive={!timerActive}>
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
        {:else if isHLSMode && appState.hlsStatus?.buffered_seconds}
          {#if appState.isLive}
            <span class="live-indicator">LIVE</span>
          {:else}
            {formatTimeShort(appState.hlsStatus?.playback_position || 0)}
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
      <div class="transport-fader-container" class:disabled={!canSeek} class:seeking={isSeeking}>
        <div class="transport-fader-track">
          <input 
            type="range" 
            class="transport-fader"
            min="0" 
            max="100" 
            step="0.1"
            value={seekPosition}
            disabled={!canSeek || isSeeking}
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
          <span class="transport-icon">|◀</span>
        </button>
        
        <!-- -10s -->
        <button 
          class="transport-btn" 
          disabled={!canSeek}
          onmousedown={() => skipBackPressed = true}
          onmouseup={() => { skipBackPressed = false; skip(-10); }}
          onmouseleave={() => skipBackPressed = false}
          ontouchstart={() => skipBackPressed = true}
          ontouchend={() => { skipBackPressed = false; skip(-10); }}
        >
          <HiFiLed color={skipBackPressed ? 'yellow' : 'off'} size="small" />
          <span class="transport-icon">◀◀</span>
        </button>
        
        <!-- Stop -->
        <button class="transport-btn" onclick={handleStop}>
          <HiFiLed color={stopLedColor} size="small" />
          <span class="transport-icon">■</span>
        </button>
        
        <!-- Pause -->
        <button class="transport-btn" onclick={handlePause} disabled={!appState.isPlaying}>
          <HiFiLed color={pauseLedColor} size="small" />
          <span class="transport-icon">❚❚</span>
        </button>
        
        <!-- Play -->
        <button class="transport-btn" onclick={handlePlay}>
          <HiFiLed color={playLedColor} size="small" />
          <span class="transport-icon">▶</span>
        </button>
        
        <!-- Rec -->
        <button class="transport-btn rec" onclick={handleRec} disabled={!isStation}>
          <HiFiLed color={recLedColor} size="small" blink={appState.isRecording} />
          <span class="transport-icon">●</span>
        </button>
        
        <!-- +10s -->
        <button 
          class="transport-btn" 
          disabled={!canSeek}
          onmousedown={() => skipFwdPressed = true}
          onmouseup={() => { skipFwdPressed = false; skip(10); }}
          onmouseleave={() => skipFwdPressed = false}
          ontouchstart={() => skipFwdPressed = true}
          ontouchend={() => { skipFwdPressed = false; skip(10); }}
        >
          <HiFiLed color={skipFwdPressed ? 'yellow' : 'off'} size="small" />
          <span class="transport-icon">▶▶</span>
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
          <span class="transport-icon">▶|</span>
        </button>
        
        <!-- Live -->
        <button 
          class="transport-btn live-btn" 
          disabled={isLive || !isHLSMode}
          onclick={goLive}
        >
          <HiFiLed color={liveLedColor} size="small" />
          <span class="transport-label">LIVE</span>
        </button>
      </div>
    </div>
  </div>
</footer>

<style>
  .hifi-player {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 15px 22px;
    background: var(--hifi-bg-panel);
    border-top: 1px solid var(--hifi-border-dark);
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
  
  /* VU-Meter Sektion - Breite für Label "VU" */
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
  
  /* Display Section Content volle Breite */
  .display-section .section-content {
    width: 100%;
  }
  
  /* Gemeinsame Display-Box Styles */
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
  
  /* SOURCE - BLAU, 40% breiter, Orbitron bold */
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
  
  /* DISPLAY - volle Restbreite */
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
  }
  
  /* VOLUME - mit etwas Abstand links/rechts */
  .volume-section {
    width: 55px;
    margin: 0 20px;
  }
  
  /* Knob 10px nach unten verschieben */
  .volume-section .section-content {
    margin-top: 10px;
  }
  
  .volume-fader-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    height: 52px;
  }
  
  .fader-track {
    position: relative;
    width: 24px;
    height: 36px;
    background: var(--hifi-fader-track);
    border-radius: 2px;
    overflow: hidden;
  }
  
  .volume-fader {
    position: absolute;
    width: 36px;
    height: 24px;
    transform: rotate(-90deg) translateX(-36px);
    transform-origin: left top;
    appearance: none;
    background: transparent;
    cursor: pointer;
    z-index: 2;
  }
  
  .volume-fader::-webkit-slider-thumb {
    appearance: none;
    width: 24px;
    height: 12px;
    background: var(--hifi-fader-cap);
    border-radius: 2px;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.4);
  }
  
  .fader-fill {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--hifi-accent);
    opacity: 0.5;
    pointer-events: none;
  }
  
  .volume-value {
    font-family: var(--hifi-font-values);
    font-size: 10px;
    color: var(--hifi-text-secondary);
  }
  
  /* TIMER - gleiche Breite wie Source (84px), Orbitron bold */
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
    width: 320px;
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
    display: none; /* Using native thumb instead */
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
    padding: 6px 7px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    cursor: pointer;
    transition: background 0.1s ease;
    min-width: 37px;
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
    font-family: 'Roboto', sans-serif;
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    color: var(--hifi-text-primary);
    line-height: 1;
  }
  
  .transport-label {
    font-family: var(--hifi-font-values);
    font-size: 7px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--hifi-text-primary);
    letter-spacing: 0.5px;
    line-height: 1;
  }
  
  .transport-btn.live-btn .transport-label {
    color: var(--hifi-led-blue);
  }
  
  .transport-btn.live-btn:disabled .transport-label {
    color: var(--hifi-led-blue);
    opacity: 1;
  }
  
  .transport-btn.rec .transport-icon {
    color: var(--hifi-led-red);
  }
  
  .blink {
    animation: blink 1s step-start infinite;
  }
  
  @keyframes blink {
    50% { opacity: 0; }
  }
</style>
