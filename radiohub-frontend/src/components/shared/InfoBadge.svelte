<script>
  /**
   * InfoBadge - Wiederverwendbarer Status-Badge
   * Farbige Mini-Badges analog ICY/AD-Badges der StationsTab.
   */
  let {
    type = 'default',   // 'downloaded' | 'played' | 'resume' | 'new' | 'auto' | 'default'
    label = ''
  } = $props();
</script>

<span class="info-badge badge-{type}" title={label}>{label}</span>

<style>
  .info-badge {
    display: inline-flex;
    align-items: center;
    padding: 1px 4px;
    font-family: var(--hifi-font-values, 'Orbitron', monospace);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    border-radius: 2px;
    white-space: nowrap;
    cursor: default;
  }

  .badge-downloaded {
    color: #5ba8d9;
    background: rgba(91, 168, 217, 0.15);
    border: 1px solid rgba(91, 168, 217, 0.3);
  }

  .badge-played {
    color: var(--hifi-led-green, #4caf50);
    background: rgba(76, 175, 80, 0.12);
    border: 1px solid rgba(76, 175, 80, 0.25);
  }

  .badge-resume {
    color: var(--hifi-led-amber, #e5a00d);
    background: rgba(229, 160, 13, 0.12);
    border: 1px solid rgba(229, 160, 13, 0.25);
  }

  .badge-new {
    color: var(--hifi-led-green, #4caf50);
    background: rgba(76, 175, 80, 0.12);
    border: 1px solid rgba(76, 175, 80, 0.25);
  }

  .badge-auto {
    color: #5ba8d9;
    background: rgba(91, 168, 217, 0.15);
    border: 1px solid rgba(91, 168, 217, 0.3);
  }

  .badge-default {
    color: var(--hifi-text-secondary);
    background: rgba(102, 102, 102, 0.12);
    border: 1px solid rgba(102, 102, 102, 0.25);
  }
</style>
