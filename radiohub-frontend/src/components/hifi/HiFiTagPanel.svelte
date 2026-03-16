<script>
  /**
   * HiFiTagPanel - Universelle Toggle-Button-Gruppe mit LED-Header
   *
   * Props:
   *   title      - Ueberschrift (Orbitron)
   *   items      - Array von { key, label, icon?, color? }
   *   activeKeys - Set oder Array der aktiven Keys
   *   ontoggle   - Callback(key) beim Klick
   *   open       - Initial offen? (default false)
   *   columns    - Spaltenanzahl (default 2)
   */
  import HiFiLed from './HiFiLed.svelte';

  let {
    title = '',
    items = [],
    activeKeys = [],
    ontoggle = null,
    open = false,
    columns = 2,
  } = $props();

  let expanded = $state(open);

  function toggle() {
    expanded = !expanded;
  }

  function isActive(key) {
    if (activeKeys instanceof Set) return activeKeys.has(key);
    return Array.isArray(activeKeys) && activeKeys.includes(key);
  }
</script>

<div class="tag-panel">
  <button class="tag-panel-header" onclick={toggle}>
    <HiFiLed color={expanded ? 'yellow' : 'off'} size="small" />
    <span class="tag-panel-title">{title}</span>
  </button>

  {#if expanded}
    <div class="tag-panel-body">
      {#each items as item (item.key)}
        {@const active = isActive(item.key)}
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
</style>
