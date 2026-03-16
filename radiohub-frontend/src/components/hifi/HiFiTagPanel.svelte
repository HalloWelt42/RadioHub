<script>
  /**
   * HiFiTagPanel - Universelle Toggle-Button-Gruppe mit LED-Header
   *
   * 3 Zustaende: zu (off) -> Anzeige aktiver (gruen) -> Bearbeitung aller (gelb) -> zu
   *
   * Props:
   *   title      - Ueberschrift (Orbitron)
   *   items      - Array von { key, label, icon?, color? }
   *   activeKeys - Set oder Array der aktiven Keys
   *   ontoggle   - Callback(key) beim Klick (nur im gelb-Modus)
   */
  import HiFiLed from './HiFiLed.svelte';

  let {
    title = '',
    items = [],
    activeKeys = [],
    ontoggle = null,
  } = $props();

  // 0 = zu, 1 = anzeige (gruen), 2 = bearbeitung (gelb)
  let mode = $state(0);

  function cycle() {
    const hasActive = activeItems.length > 0;
    if (mode === 0) {
      // Wenn aktive vorhanden: gruen, sonst direkt gelb
      mode = hasActive ? 1 : 2;
    } else if (mode === 1) {
      mode = 2;
    } else {
      mode = 0;
    }
  }

  function isActive(key) {
    if (activeKeys instanceof Set) return activeKeys.has(key);
    return Array.isArray(activeKeys) && activeKeys.includes(key);
  }

  let activeItems = $derived(items.filter(i => isActive(i.key)));
  let ledColor = $derived(mode === 2 ? 'yellow' : mode === 1 ? 'green' : 'off');
  let visibleItems = $derived(mode === 2 ? items : mode === 1 ? activeItems : []);
</script>

<div class="tag-panel">
  <button class="tag-panel-header" onclick={cycle}>
    <HiFiLed color={ledColor} size="small" />
    <span class="tag-panel-title">{title}</span>
    {#if mode === 0 && activeItems.length > 0}
      <span class="tag-panel-count">{activeItems.length}</span>
    {/if}
  </button>

  {#if mode > 0 && visibleItems.length > 0}
    <div class="tag-panel-body">
      {#each visibleItems as item (item.key)}
        {@const active = isActive(item.key)}
        {#if mode === 2}
          <button
            class="tag-btn"
            class:active
            style={active && item.color ? `border-color: ${item.color}; color: ${item.color};` : ''}
            onclick={() => ontoggle?.(item.key)}
            title={item.label}
          >
            {#if item.icon}<i class="{item.icon}"></i>{/if}
            <span>{item.label}</span>
          </button>
        {:else}
          <span
            class="tag-btn active readonly"
            style={item.color ? `border-color: ${item.color}; color: ${item.color};` : ''}
            title={item.label}
          >
            {#if item.icon}<i class="{item.icon}"></i>{/if}
            <span>{item.label}</span>
          </span>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<style>
  .tag-panel {
    display: flex;
    flex-direction: column;
  }

  .tag-panel-header {
    display: flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px 0;
  }

  .tag-panel-title {
    font-family: var(--hifi-font-display, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: var(--hifi-text-secondary);
  }

  .tag-panel-count {
    font-family: var(--hifi-font-display, 'Orbitron', monospace);
    font-size: 8px;
    font-weight: 700;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .tag-panel-header:hover .tag-panel-title {
    color: var(--hifi-text-primary);
  }

  .tag-panel-body {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 3px;
    padding: 4px 0;
    max-height: 120px;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }
  .tag-panel-body::-webkit-scrollbar {
    display: none;
  }

  .tag-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 6px;
    font-family: var(--hifi-font-family, 'Barlow', sans-serif);
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border: 1px solid var(--hifi-border-dark);
    border-radius: 3px;
    cursor: pointer;
    background: var(--hifi-bg-tertiary);
    color: var(--hifi-text-secondary);
    transition: background 0.1s, color 0.1s, border-color 0.1s;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 14px;
  }

  .tag-btn i {
    font-size: 8px;
    flex-shrink: 0;
  }

  .tag-btn:hover {
    background: var(--hifi-row-hover);
    color: var(--hifi-text-primary);
  }

  .tag-btn.active {
    background: rgba(229, 160, 13, 0.12);
    color: var(--hifi-led-amber, #e5a00d);
    border-color: var(--hifi-led-amber, #e5a00d);
  }

  .tag-btn.readonly {
    cursor: default;
  }
  .tag-btn.readonly:hover {
    background: rgba(229, 160, 13, 0.12);
  }

  /* -- Light-Mode -- */
  :global([data-theme="light"]) .tag-btn.active,
  :global(:root:not([data-theme="dark"])) .tag-btn.active {
    background: rgba(176, 120, 0, 0.1);
    color: #8a6200;
    border-color: #b07800;
  }
  :global([data-theme="light"]) .tag-btn.readonly:hover,
  :global(:root:not([data-theme="dark"])) .tag-btn.readonly:hover {
    background: rgba(176, 120, 0, 0.1);
  }
</style>
