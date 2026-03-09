<script>
  import { appState, actions } from '../lib/store.svelte.js';
  import { formatTimeShort as formatTime } from '../lib/formatters.js';

  let audioEl = $state(null);
  let currentTime = $state(0);
  let duration = $state(0);
  
  // Reaktiv auf State-Änderungen
  $effect(() => {
    if (!audioEl) return;
    
    if (appState.isPlaying) {
      const url = appState.currentStation?.url_resolved || 
                  appState.currentStation?.url ||
                  appState.currentEpisode?.audio_url;
      if (url && audioEl.src !== url) {
        audioEl.src = url;
        audioEl.load();
      }
      audioEl.play().catch(console.error);
    } else {
      audioEl.pause();
    }
  });
  
  $effect(() => {
    if (audioEl) {
      audioEl.volume = appState.volume / 100;
    }
  });
  
  function togglePlay() {
    if (appState.isPlaying) {
      actions.stop();
    } else if (appState.currentStation || appState.currentEpisode) {
      appState.isPlaying = true;
    }
  }
  
  function toggleRecording() {
    if (appState.isRecording) {
      actions.stopRecording();
    } else {
      actions.startRecording();
    }
  }
  
  function handleTimeUpdate() {
    currentTime = audioEl?.currentTime || 0;
    duration = audioEl?.duration || 0;
  }
  
  function handleSeek(e) {
    if (audioEl && duration) {
      audioEl.currentTime = (e.target.value / 100) * duration;
    }
  }
  
  // Computed
  let nowPlayingName = $derived(
    appState.currentStation?.name || 
    appState.currentEpisode?.title || 
    'Kein Sender ausgewählt'
  );
  
  let nowPlayingMeta = $derived(
    appState.currentStation?.tags?.split(',')[0] ||
    appState.currentEpisode?.podcast?.title ||
    ''
  );
  
  let showSeekbar = $derived(!!appState.currentEpisode);
  let seekProgress = $derived(duration ? (currentTime / duration) * 100 : 0);
</script>

<footer class="player">
  <!-- Hidden Audio Element -->
  <audio 
    bind:this={audioEl}
    ontimeupdate={handleTimeUpdate}
    onended={() => actions.stop()}
  ></audio>
  
  <!-- Now Playing Info -->
  <div class="now-playing">
    <div class="now-playing-icon" class:playing={appState.isPlaying}>
      <i class="fa-solid {appState.currentEpisode ? 'fa-podcast' : 'fa-radio'}"></i>
    </div>
    <div class="now-playing-text">
      <div class="now-playing-name truncate">{nowPlayingName}</div>
      {#if nowPlayingMeta}
        <div class="now-playing-meta truncate text-muted text-sm">{nowPlayingMeta}</div>
      {/if}
    </div>
  </div>
  
  <!-- Controls -->
  <div class="controls">
    {#if showSeekbar}
      <button class="btn btn-icon btn-ghost" onclick={() => audioEl.currentTime -= 10}>
        <i class="fa-solid fa-backward-step"></i>
      </button>
    {/if}
    
    <button class="btn btn-icon btn-primary play-btn" onclick={togglePlay}>
      <i class="fa-solid {appState.isPlaying ? 'fa-pause' : 'fa-play'}"></i>
    </button>
    
    {#if showSeekbar}
      <button class="btn btn-icon btn-ghost" onclick={() => audioEl.currentTime += 10}>
        <i class="fa-solid fa-forward-step"></i>
      </button>
    {/if}
  </div>
  
  <!-- Seekbar (nur für Episoden) -->
  {#if showSeekbar}
    <div class="seekbar">
      <span class="time">{formatTime(currentTime)}</span>
      <input 
        type="range" 
        min="0" 
        max="100" 
        value={seekProgress}
        oninput={handleSeek}
      />
      <span class="time">{formatTime(duration)}</span>
    </div>
  {/if}
  
  <!-- Volume & Recording -->
  <div class="player-actions">
    <div class="volume-control">
      <i class="fa-solid {appState.volume === 0 ? 'fa-volume-xmark' : 'fa-volume-high'}"></i>
      <input 
        type="range" 
        min="0" 
        max="100" 
        value={appState.volume}
        oninput={(e) => actions.setVolume(parseInt(e.target.value))}
      />
    </div>
    
    {#if appState.currentStation}
      <button 
        class="btn btn-icon rec-btn"
        class:recording={appState.isRecording}
        onclick={toggleRecording}
        title={appState.isRecording ? 'Aufnahme stoppen' : 'Aufnahme starten'}
      >
        <i class="fa-solid {appState.isRecording ? 'fa-stop' : 'fa-microphone'}"></i>
      </button>
    {/if}
  </div>
</footer>

<style>
  .player {
    display: flex;
    align-items: center;
    gap: var(--space-lg);
    padding: var(--space-md) var(--space-lg);
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    min-height: 72px;
  }
  
  .now-playing {
    display: flex;
    align-items: center;
    gap: var(--space-md);
    flex: 1;
    min-width: 0;
  }
  
  .now-playing-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
  }
  
  .now-playing-icon.playing {
    color: var(--accent);
  }
  
  .now-playing-text {
    flex: 1;
    min-width: 0;
  }
  
  .now-playing-name {
    font-weight: 500;
  }
  
  .controls {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
  }
  
  .play-btn {
    width: 48px;
    height: 48px;
  }
  
  .seekbar {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    flex: 1;
    max-width: 300px;
  }
  
  .seekbar input {
    flex: 1;
    height: 4px;
    -webkit-appearance: none;
    background: var(--bg-tertiary);
    border-radius: var(--radius-full);
    border: none;
    padding: 0;
  }
  
  .seekbar input::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px;
    height: 12px;
    background: var(--accent);
    border-radius: 50%;
    cursor: pointer;
  }
  
  .time {
    font-size: 12px;
    color: var(--text-muted);
    min-width: 40px;
  }
  
  .player-actions {
    display: flex;
    align-items: center;
    gap: var(--space-md);
  }
  
  .volume-control {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    color: var(--text-secondary);
  }
  
  .volume-control input {
    width: 80px;
    height: 4px;
    -webkit-appearance: none;
    background: var(--bg-tertiary);
    border-radius: var(--radius-full);
    border: none;
    padding: 0;
  }
  
  .volume-control input::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px;
    height: 12px;
    background: var(--text-secondary);
    border-radius: 50%;
    cursor: pointer;
  }
  
  .rec-btn {
    color: var(--text-secondary);
  }
  
  .rec-btn.recording {
    color: var(--error);
    animation: pulse 1s ease-in-out infinite;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
</style>
