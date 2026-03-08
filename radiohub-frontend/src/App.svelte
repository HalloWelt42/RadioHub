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
  
  let backendOnline = $state(false);
  
  // Theme init
  $effect(() => {
    actions.initTheme();
  });
  
  // Health Check
  $effect(() => {
    api.health().then(h => {
      console.log('RadioHub Backend:', h);
      backendOnline = true;
    }).catch(e => {
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
</script>

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
          onclick={() => actions.setTab(tab.id)}
        >
          <HiFiLed color={appState.activeTab === tab.id ? 'green' : 'off'} size="small" />
          {tab.label}
        </button>
      {/each}
    </nav>
    
    <div class="hifi-header-right">
      <!-- Theme Switch -->
      <button class="theme-switch" onclick={() => actions.toggleTheme()}>
        <HiFiLed color={appState.theme === 'dark' ? 'off' : 'yellow'} size="small" />
        <span class="theme-label hifi-value">{appState.theme === 'dark' ? 'DARK' : 'LIGHT'}</span>
      </button>
      
      <!-- Status -->
      <div class="hifi-status">
        <HiFiLed color={backendOnline ? 'green' : 'red'} />
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
  
  <!-- Toast -->
  <HiFiToast />
</div>

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
  }
  
  .hifi-nav-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    background: var(--hifi-bg-tertiary);
    border: none;
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 600;
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
  
  .theme-switch {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  
  .theme-switch:hover {
    background: var(--hifi-bg-secondary);
    color: var(--hifi-text-primary);
  }
  
  .theme-label {
    font-weight: 600;
    letter-spacing: 1px;
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
