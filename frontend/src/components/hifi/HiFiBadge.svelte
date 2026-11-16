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
    border-radius: 3px;
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
    background: rgba(100, 180, 255, 0.18);
    border-color: rgba(100, 180, 255, 0.4);
  }
  .badge-purple {
    color: #a078ff;
    background: rgba(160, 120, 255, 0.18);
    border-color: rgba(160, 120, 255, 0.4);
  }
  .badge-green {
    color: #4caf50;
    background: rgba(76, 175, 80, 0.18);
    border-color: rgba(76, 175, 80, 0.4);
  }
  .badge-green-bright {
    color: #00c878;
    background: rgba(0, 200, 120, 0.18);
    border-color: rgba(0, 200, 120, 0.4);
  }
  .badge-amber {
    color: #e5a00d;
    background: rgba(229, 160, 13, 0.18);
    border-color: rgba(229, 160, 13, 0.4);
  }
  .badge-red {
    color: #f44336;
    background: rgba(244, 67, 54, 0.18);
    border-color: rgba(244, 67, 54, 0.4);
  }
  .badge-gold {
    color: #ffd740;
    background: rgba(255, 215, 0, 0.15);
    border-color: rgba(255, 215, 0, 0.35);
  }
  .badge-muted {
    color: var(--hifi-text-secondary);
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.15);
  }
  .badge-accent {
    color: var(--hifi-accent, #3399ff);
    background: rgba(51, 153, 255, 0.18);
    border-color: rgba(51, 153, 255, 0.4);
  }

  /* -- Light-Mode: dunklere Farben für Lesbarkeit -- */
  :global([data-theme="light"]) .badge-blue,
  :global(:root:not([data-theme="dark"])) .badge-blue {
    color: #2070c0;
    background: rgba(32, 112, 192, 0.12);
    border-color: rgba(32, 112, 192, 0.3);
  }
  :global([data-theme="light"]) .badge-purple,
  :global(:root:not([data-theme="dark"])) .badge-purple {
    color: #6a40d0;
    background: rgba(106, 64, 208, 0.12);
    border-color: rgba(106, 64, 208, 0.3);
  }
  :global([data-theme="light"]) .badge-green,
  :global(:root:not([data-theme="dark"])) .badge-green {
    color: #2e7d32;
    background: rgba(46, 125, 50, 0.12);
    border-color: rgba(46, 125, 50, 0.3);
  }
  :global([data-theme="light"]) .badge-green-bright,
  :global(:root:not([data-theme="dark"])) .badge-green-bright {
    color: #00875a;
    background: rgba(0, 135, 90, 0.12);
    border-color: rgba(0, 135, 90, 0.3);
  }
  :global([data-theme="light"]) .badge-amber,
  :global(:root:not([data-theme="dark"])) .badge-amber {
    color: #b07800;
    background: rgba(176, 120, 0, 0.12);
    border-color: rgba(176, 120, 0, 0.3);
  }
  :global([data-theme="light"]) .badge-red,
  :global(:root:not([data-theme="dark"])) .badge-red {
    color: #c62828;
    background: rgba(198, 40, 40, 0.12);
    border-color: rgba(198, 40, 40, 0.3);
  }
  :global([data-theme="light"]) .badge-gold,
  :global(:root:not([data-theme="dark"])) .badge-gold {
    color: #a68600;
    background: rgba(166, 134, 0, 0.12);
    border-color: rgba(166, 134, 0, 0.3);
  }
  :global([data-theme="light"]) .badge-muted,
  :global(:root:not([data-theme="dark"])) .badge-muted {
    color: var(--hifi-text-secondary);
    background: rgba(0, 0, 0, 0.06);
    border-color: rgba(0, 0, 0, 0.15);
  }
  :global([data-theme="light"]) .badge-accent,
  :global(:root:not([data-theme="dark"])) .badge-accent {
    color: #2060b0;
    background: rgba(32, 96, 176, 0.12);
    border-color: rgba(32, 96, 176, 0.3);
  }
</style>
