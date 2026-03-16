<script>
  /**
   * HiFiBadge - Universeller kompakter Badge
   *
   * Farb-Varianten (color):
   *   blue, purple, green, green-bright, amber, red, gold, muted, accent
   *
   * Props:
   *   label    - Angezeigter Text
   *   color    - Farb-Variante (default: 'muted')
   *   icon     - FontAwesome-Klasse, z.B. 'fa-solid fa-thumbs-up'
   *   title    - Tooltip
   *   onclick  - Wenn gesetzt, wird ein <button> gerendert
   */
  let {
    label = '',
    color = 'muted',
    icon = '',
    title = '',
    onclick = null,
  } = $props();
</script>

{#if onclick}
  <button class="hifi-badge badge-{color}" {title} {onclick}>
    {#if icon}<i class="{icon}"></i>{/if}{label}
  </button>
{:else}
  <span class="hifi-badge badge-{color}" {title}>
    {#if icon}<i class="{icon}"></i>{/if}{label}
  </span>
{/if}

<style>
  .hifi-badge {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 1px 5px;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    border-radius: 2px;
    white-space: nowrap;
    cursor: default;
    border: 1px solid transparent;
    line-height: 14px;
  }

  .hifi-badge i { font-size: 8px; }

  button.hifi-badge {
    cursor: pointer;
    background: none;
  }
  button.hifi-badge:hover { filter: brightness(1.3); }

  /* -- Farb-Varianten -- */
  .badge-blue {
    color: #64b4ff;
    background: rgba(100, 180, 255, 0.12);
    border-color: rgba(100, 180, 255, 0.25);
  }
  .badge-purple {
    color: #a078ff;
    background: rgba(160, 120, 255, 0.12);
    border-color: rgba(160, 120, 255, 0.25);
  }
  .badge-green {
    color: #4caf50;
    background: rgba(76, 175, 80, 0.10);
    border-color: rgba(76, 175, 80, 0.25);
  }
  .badge-green-bright {
    color: #00c878;
    background: rgba(0, 200, 120, 0.12);
    border-color: rgba(0, 200, 120, 0.25);
  }
  .badge-amber {
    color: #e5a00d;
    background: rgba(229, 160, 13, 0.10);
    border-color: rgba(229, 160, 13, 0.25);
  }
  .badge-red {
    color: #f44336;
    background: rgba(244, 67, 54, 0.12);
    border-color: rgba(244, 67, 54, 0.25);
  }
  .badge-gold {
    color: #ffd740;
    background: rgba(255, 215, 0, 0.08);
    border-color: rgba(255, 215, 0, 0.2);
  }
  .badge-muted {
    color: var(--hifi-text-secondary);
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.1);
  }
  .badge-accent {
    color: var(--hifi-accent, #3399ff);
    background: rgba(51, 153, 255, 0.10);
    border-color: rgba(51, 153, 255, 0.25);
  }
</style>
