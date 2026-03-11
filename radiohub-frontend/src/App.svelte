<script>
  import HiFiPlayer from './components/HiFiPlayer.svelte';
  import HiFiToast from './components/hifi/HiFiToast.svelte';
  import HiFiLed from './components/hifi/HiFiLed.svelte';
  import StationsTab from './components/StationsTab.svelte';
  import RecordingsTab from './components/RecordingsTab.svelte';
  import PodcastsTab from './components/PodcastsTab.svelte';
  import SettingsTab from './components/SettingsTab.svelte';
  import { appState, actions } from './lib/store.svelte.js';
  import { api } from './lib/api.js';
  import * as sfx from './lib/uiSounds.js';
  
  let backendOnline = $state(false);
  
  // Theme init
  $effect(() => {
    actions.initTheme();
  });
  
  // Health Check
  $effect(() => {
    api.health().then(() => {
      backendOnline = true;
    }).catch(() => {
      actions.showToast('Backend nicht erreichbar', 'error');
      backendOnline = false;
    });
  });
  
  const tabs = [
    { id: 'radio', label: 'TUNER' },
    { id: 'recordings', label: 'RECORDER' },
    { id: 'podcasts', label: 'PODCAST' },
    { id: 'settings', label: 'SETUP' }
  ];

  // === Globale Tastatursteuerung ===
  function handleGlobalKeydown(e) {
    // Nicht abfangen wenn in Input/Textarea
    const tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    switch (e.key) {
      case ' ':  // Space = Play/Pause
        e.preventDefault();
        if (appState.playerMode !== 'none') {
          actions.togglePause();
        }
        break;

      case 's':  // S = Stop
        if (!e.ctrlKey && !e.metaKey) {
          actions.stop();
        }
        break;

      case 'ArrowUp':  // Pfeil hoch = Lauter
        e.preventDefault();
        actions.setVolume(Math.min(100, appState.volume + 5));
        break;

      case 'ArrowDown':  // Pfeil runter = Leiser
        e.preventDefault();
        actions.setVolume(Math.max(0, appState.volume - 5));
        break;

      case 'ArrowLeft':  // Pfeil links = Vorheriger Sender
        e.preventDefault();
        actions.navigatePrev();
        break;

      case 'ArrowRight':  // Pfeil rechts = Nächster Sender
        e.preventDefault();
        actions.navigateNext();
        break;

      case 'm':  // M = Mute toggle
        if (!e.ctrlKey && !e.metaKey) {
          actions.setVolume(appState.volume > 0 ? 0 : 70);
        }
        break;

      case '1':  // 1-4 = Tab wechseln
        actions.setTab('radio');
        break;
      case '2':
        actions.setTab('recordings');
        break;
      case '3':
        actions.setTab('podcasts');
        break;
      case '4':
        actions.setTab('settings');
        break;

      case 'Escape':  // Escape = Overlays schließen
        // Wird von Komponenten selbst behandelt
        break;
    }
  }
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

<div class="hifi-app">
  <!-- Header -->
  <header class="hifi-header">
    <div class="hifi-logo">
      <span class="hifi-logo-text">RadioHub</span>
      <span class="hifi-logo-sub">DIGITAL AUDIO SYSTEM</span>
    </div>
    
    <nav class="hifi-nav">
      {#each tabs as tab}
        <button
          class="hifi-nav-btn"
          class:active={appState.activeTab === tab.id}
          onclick={() => { actions.setTab(tab.id); sfx.select(); }}
          onmouseenter={sfx.hoverSoft}
          title={tab.label + ' anzeigen'}
        >
          <HiFiLed color={appState.activeTab === tab.id ? 'green' : 'off'} size="small" />
          {tab.label}
        </button>
      {/each}
    </nav>
    
    <div class="hifi-header-right">
      <!-- Theme Switch -->
      <button class="hifi-nav-btn active" onclick={() => actions.toggleTheme()} onmouseenter={sfx.hoverSoft} title={appState.theme === 'dark' ? 'Zu hellem Design wechseln' : 'Zu dunklem Design wechseln'}>
        <HiFiLed color={appState.theme === 'dark' ? 'off' : 'yellow'} size="small" />
        {appState.theme === 'dark' ? 'DARK' : 'LIGHT'}
      </button>
      
      <!-- Status -->
      <div class="hifi-status">
        <HiFiLed color={backendOnline ? 'green' : 'red'} size="small" />
        <span class="hifi-font-label">{backendOnline ? 'ONLINE' : 'OFFLINE'}</span>
      </div>
    </div>
  </header>
  
  <!-- Main Content -->
  <main class="hifi-main">
    {#if appState.activeTab === 'radio'}
      <StationsTab />
    {:else if appState.activeTab === 'recordings'}
      <RecordingsTab />
    {:else if appState.activeTab === 'podcasts'}
      <PodcastsTab />
    {:else if appState.activeTab === 'settings'}
      <SettingsTab />
    {/if}
  </main>
  
  <!-- Player -->
  <HiFiPlayer />
</div>

<!-- Toast ausserhalb hifi-app fuer korrektes z-index Stacking -->
<HiFiToast />

<style>
  .hifi-app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
    background: var(--hifi-bg-primary);
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-values);
  }
  
  .hifi-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    background: var(--hifi-bg-panel);
    border-bottom: 1px solid var(--hifi-border-dark);
    border-radius: 0;
  }
  
  .hifi-logo {
    display: flex;
    flex-direction: column;
  }
  
  /* Logo bleibt bei separater Schrift */
  .hifi-logo-text {
    font-family: var(--hifi-font-display);
    font-size: 22px;
    font-weight: 700;
    color: var(--hifi-accent);
    letter-spacing: 2px;
  }
  
  .hifi-logo-sub {
    font-family: var(--hifi-font-values);
    font-size: 8px;
    letter-spacing: 3px;
    color: var(--hifi-text-secondary);
    text-transform: uppercase;
  }
  
  .hifi-nav {
    display: flex;
    gap: 4px;
    background: var(--hifi-bg-panel);
    padding: 10px 16px;
    border-radius: var(--hifi-border-radius-pill);
    box-shadow: var(--hifi-shadow-button);
    position: relative;
    z-index: 2;
    transform: translateY(20px);
  }

  .hifi-nav-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 18px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-pill);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  
  .hifi-nav-btn:hover {
    background: var(--hifi-bg-secondary);
  }
  
  .hifi-nav-btn.active {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }
  
  .hifi-header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  
  .hifi-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--hifi-font-values);
    font-size: 10px;
  }
  
  .hifi-main {
    flex: 1;
    overflow: hidden;
    background: var(--hifi-bg-secondary);
  }
</style>
