<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import SetupAllgemein from './setup/SetupAllgemein.svelte';
  import SetupRadio from './setup/SetupRadio.svelte';
  import SetupPodcast from './setup/SetupPodcast.svelte';
  import SetupAufnahmen from './setup/SetupAufnahmen.svelte';
  import SetupSpeicher from './setup/SetupSpeicher.svelte';
  import SetupDienste from './setup/SetupDienste.svelte';
  import SetupSystem from './setup/SetupSystem.svelte';
  import { appState, actions } from '../lib/store.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import * as router from '../lib/router.js';

  const tabs = [
    { id: 'allgemein', icon: 'fa-sliders' },
    { id: 'radio', icon: 'fa-tower-broadcast' },
    { id: 'podcast', icon: 'fa-podcast' },
    { id: 'aufnahmen', icon: 'fa-microphone' },
    { id: 'speicher', icon: 'fa-hard-drive' },
    { id: 'dienste', icon: 'fa-plug' },
    { id: 'system', icon: 'fa-terminal' }
  ];

  // activeTab aus Route-Segmenten ableiten
  let activeTab = $derived.by(() => {
    if (appState.activeTab !== 'settings') return 'allgemein';
    const seg = appState.routeSegments;
    const tabId = seg?.[0] || 'allgemein';
    // Prüfen ob Tab-ID gültig ist
    return tabs.some(t => t.id === tabId) ? tabId : 'allgemein';
  });

  // Redirect wenn /setup ohne Sub-Tab aufgerufen wird
  $effect(() => {
    if (appState.activeTab === 'settings' && (!appState.routeSegments || appState.routeSegments.length === 0)) {
      router.navigate('/setup/allgemein/einstellungen', { replace: true });
      appState.routeSegments = ['allgemein', 'einstellungen'];
    }
  });

  function selectSetupTab(tabId) {
    const subDefaults = router.getSubDefault(tabId);
    const path = router.buildPath('setup', tabId, ...subDefaults);
    actions.navigateTo(path);
  }
</script>

<div class="setup-layout">
  <!-- Sidebar Navigation -->
  <nav class="setup-sidebar">
    {#each tabs as tab}
      <button
        class="setup-nav-btn"
        class:active={activeTab === tab.id}
        onclick={() => selectSetupTab(tab.id)}
      >
        <HiFiLed color={activeTab === tab.id ? 'green' : 'off'} size="small" />
        <i class="fa-solid {tab.icon}"></i>
        <span>{t('setup.' + tab.id)}</span>
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
