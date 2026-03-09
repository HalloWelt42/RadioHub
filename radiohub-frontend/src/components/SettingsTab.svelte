<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import SetupAllgemein from './setup/SetupAllgemein.svelte';
  import SetupSystem from './setup/SetupSystem.svelte';
  import { appState } from '../lib/store.svelte.js';

  let activeTab = $state('allgemein');

  const tabs = [
    { id: 'allgemein', label: 'ALLGEMEIN' },
    { id: 'filter', label: 'FILTER' },
    { id: 'sender', label: 'SENDER' },
    { id: 'kategorien', label: 'KATEGORIEN' },
    { id: 'system', label: 'SYSTEM' }
  ];

  // Deep-Link: Anderer Tab kann setupSubTab setzen um direkt zu einem Sub-Tab zu springen
  $effect(() => {
    if (appState.setupSubTab) {
      activeTab = appState.setupSubTab;
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
      <SetupAllgemein />
    {:else if activeTab === 'filter'}
      <div class="setup-placeholder">
        <span class="hifi-font-label">FILTER -- wird migriert</span>
      </div>
    {:else if activeTab === 'sender'}
      <div class="setup-placeholder">
        <span class="hifi-font-label">SENDER -- wird migriert</span>
      </div>
    {:else if activeTab === 'kategorien'}
      <div class="setup-placeholder">
        <span class="hifi-font-label">KATEGORIEN -- wird erstellt</span>
      </div>
    {:else if activeTab === 'system'}
      <SetupSystem />
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
    overflow-y: auto;
    padding: 16px;
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
  }

  .setup-placeholder {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 60px;
    color: var(--hifi-text-muted);
  }
</style>
