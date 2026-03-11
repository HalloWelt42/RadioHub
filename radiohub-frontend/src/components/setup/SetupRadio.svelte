<script>
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import SetupFilter from './SetupFilter.svelte';
  import SetupSender from './SetupSender.svelte';
  import SetupKategorien from './SetupKategorien.svelte';

  let subTab = $state('filter');

  const subTabs = [
    { id: 'filter', label: 'FILTER' },
    { id: 'sender', label: 'SENDER' },
    { id: 'kategorien', label: 'KATEGORIEN' }
  ];
</script>

<div class="radio-setup">
  <div class="sub-tab-bar">
    {#each subTabs as tab}
      <button
        class="sub-tab-btn"
        class:active={subTab === tab.id}
        onclick={() => subTab = tab.id}
      >
        <HiFiLed color={subTab === tab.id ? 'green' : 'off'} size="small" />
        {tab.label}
      </button>
    {/each}
  </div>

  <div class="radio-content">
    {#if subTab === 'filter'}
      <SetupFilter />
    {:else if subTab === 'sender'}
      <SetupSender />
    {:else if subTab === 'kategorien'}
      <div class="scroll-wrapper"><SetupKategorien /></div>
    {/if}
  </div>
</div>

<style>
  .radio-setup {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .sub-tab-bar {
    display: flex;
    align-items: center;
    gap: 2px;
    margin-bottom: 12px;
    flex-shrink: 0;
  }

  .sub-tab-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 6px 14px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    cursor: pointer;
  }

  .sub-tab-btn:hover {
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-primary);
  }

  .sub-tab-btn.active {
    background: var(--hifi-bg-tertiary);
    border-color: var(--hifi-border-dark);
    color: var(--hifi-accent);
  }

  .radio-content {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .scroll-wrapper {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }
</style>
