<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import SetupAllgemein from './setup/SetupAllgemein.svelte';
  import SetupRadio from './setup/SetupRadio.svelte';
  import SetupPodcast from './setup/SetupPodcast.svelte';
  import SetupAufnahmen from './setup/SetupAufnahmen.svelte';
  import SetupSystem from './setup/SetupSystem.svelte';
  import SetupSpeicher from './setup/SetupSpeicher.svelte';
  import SetupDienste from './setup/SetupDienste.svelte';
  import SetupInfo from './setup/SetupInfo.svelte';
  import { appState } from '../lib/store.svelte.js';

  let activeTab = $state('allgemein');

  const tabs = [
    { id: 'allgemein', label: 'ALLGEMEIN' },
    { id: 'radio', label: 'RADIO' },
    { id: 'podcast', label: 'PODCAST' },
    { id: 'aufnahmen', label: 'AUFNAHMEN' },
    { id: 'speicher', label: 'SPEICHER' },
    { id: 'dienste', label: 'DIENSTE' },
    { id: 'system', label: 'SYSTEM' },
    { id: 'info', label: 'INFO' }
  ];

  // Deep-Link: Anderer Tab kann setupSubTab setzen um direkt zu einem Sub-Tab zu springen
  // Alte IDs (filter, sender, kategorien) werden auf 'radio' gemappt
  const subTabMapping = { filter: 'radio', sender: 'radio', kategorien: 'radio' };

  $effect(() => {
    if (appState.setupSubTab) {
      const target = subTabMapping[appState.setupSubTab] || appState.setupSubTab;
      activeTab = target;
      appState.setupSubTab = null;
    }
  });
</script>

<div class="setup-tab">
  <div class="setup-tab-bar">
    {#each tabs as tab}
      <button
        class="setup-tab-btn"
        class:active={activeTab === tab.id}
        onclick={() => activeTab = tab.id}
      >
        <HiFiLed color={activeTab === tab.id ? 'green' : 'off'} size="small" />
        <span class="setup-tab-label">{tab.label}</span>
      </button>
    {/each}
  </div>

  <div class="setup-content">
    {#if activeTab === 'allgemein'}
      <div class="setup-scroll-wrapper"><SetupAllgemein /></div>
    {:else if activeTab === 'radio'}
      <SetupRadio />
    {:else if activeTab === 'podcast'}
      <div class="setup-scroll-wrapper"><SetupPodcast /></div>
    {:else if activeTab === 'aufnahmen'}
      <div class="setup-scroll-wrapper"><SetupAufnahmen /></div>
    {:else if activeTab === 'speicher'}
      <div class="setup-scroll-wrapper"><SetupSpeicher /></div>
    {:else if activeTab === 'dienste'}
      <div class="setup-scroll-wrapper"><SetupDienste /></div>
    {:else if activeTab === 'system'}
      <div class="setup-scroll-wrapper"><SetupSystem /></div>
    {:else if activeTab === 'info'}
      <div class="setup-scroll-wrapper"><SetupInfo /></div>
    {/if}
  </div>
</div>

<style>
  .setup-tab {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .setup-tab-bar {
    display: flex;
    gap: 2px;
    padding: 8px 16px;
    background: var(--hifi-bg-secondary);
    border-bottom: 1px solid var(--hifi-border-dark);
    flex-shrink: 0;
  }

  .setup-tab-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--hifi-border-radius-md) var(--hifi-border-radius-md) 0 0;
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .setup-tab-btn:hover {
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-primary);
  }

  .setup-tab-btn.active {
    background: var(--hifi-bg-panel);
    border-color: var(--hifi-border-dark);
    border-bottom-color: var(--hifi-bg-panel);
    color: var(--hifi-accent);
  }

  .setup-tab-label {
    white-space: nowrap;
  }

  .setup-content {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 16px 24px;
  }

  .setup-scroll-wrapper {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

</style>
