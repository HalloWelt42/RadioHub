<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import SetupAllgemein from './setup/SetupAllgemein.svelte';
  import SetupRadio from './setup/SetupRadio.svelte';
  import SetupPodcast from './setup/SetupPodcast.svelte';
  import SetupAufnahmen from './setup/SetupAufnahmen.svelte';
  import SetupSpeicher from './setup/SetupSpeicher.svelte';
  import SetupDienste from './setup/SetupDienste.svelte';
  import SetupSystem from './setup/SetupSystem.svelte';
  import { appState } from '../lib/store.svelte.js';

  let activeTab = $state('allgemein');

  const tabs = [
    { id: 'allgemein', label: 'ALLGEMEIN', icon: 'fa-sliders' },
    { id: 'radio', label: 'RADIO', icon: 'fa-tower-broadcast' },
    { id: 'podcast', label: 'PODCAST', icon: 'fa-podcast' },
    { id: 'aufnahmen', label: 'AUFNAHMEN', icon: 'fa-microphone' },
    { id: 'speicher', label: 'SPEICHER', icon: 'fa-hard-drive' },
    { id: 'dienste', label: 'DIENSTE', icon: 'fa-plug' },
    { id: 'system', label: 'SYSTEM', icon: 'fa-terminal' }
  ];

  // Deep-Link: Anderer Tab kann setupSubTab setzen um direkt zu einem Sub-Tab zu springen
  const subTabMapping = { filter: 'radio', sender: 'radio', kategorien: 'radio' };

  $effect(() => {
    if (appState.setupSubTab) {
      const target = subTabMapping[appState.setupSubTab] || appState.setupSubTab;
      activeTab = target;
      appState.setupSubTab = null;
    }
  });
</script>

<div class="setup-layout">
  <!-- Sidebar Navigation -->
  <nav class="setup-sidebar">
    {#each tabs as tab}
      <button
        class="setup-nav-btn"
        class:active={activeTab === tab.id}
        onclick={() => activeTab = tab.id}
      >
        <HiFiLed color={activeTab === tab.id ? 'green' : 'off'} size="small" />
        <i class="fa-solid {tab.icon}"></i>
        <span>{tab.label}</span>
      </button>
    {/each}
  </nav>

  <!-- Content -->
  <main class="setup-main">
    {#if activeTab === 'allgemein'}
      <SetupAllgemein />
    {:else if activeTab === 'radio'}
      <SetupRadio />
    {:else if activeTab === 'podcast'}
      <div class="setup-scroll"><SetupPodcast /></div>
    {:else if activeTab === 'aufnahmen'}
      <div class="setup-scroll"><SetupAufnahmen /></div>
    {:else if activeTab === 'speicher'}
      <div class="setup-scroll"><SetupSpeicher /></div>
    {:else if activeTab === 'dienste'}
      <div class="setup-scroll"><SetupDienste /></div>
    {:else if activeTab === 'system'}
      <div class="setup-scroll"><SetupSystem /></div>
    {/if}
  </main>
</div>

<style>
  .setup-layout {
    display: flex;
    height: 100%;
  }

  /* === Sidebar === */
  .setup-sidebar {
    width: 180px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 12px;
    background: var(--hifi-bg-panel);
    border-right: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
    overflow-y: auto;
  }

  /* === Nav Buttons (Pill-Design wie obere Navigation) === */
  .setup-nav-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
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
    width: 100%;
  }

  .setup-nav-btn:hover {
    background: var(--hifi-bg-secondary);
    color: var(--hifi-text-primary);
  }

  .setup-nav-btn.active {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }

  .setup-nav-btn i {
    width: 14px;
    text-align: center;
    font-size: 11px;
  }

  /* === Main Content === */
  .setup-main {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    padding: 16px 24px;
    display: flex;
    flex-direction: column;
  }

  .setup-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }
</style>
