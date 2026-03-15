<script>
  /**
   * HiFi Bitrate LED Selector
   *
   * 8 kompakte LEDs für Standard-Bitrate-Stufen.
   * Grün = erkannte Bitrate, Gelb = User-Override.
   * Klick auf LED: Override setzen/entfernen.
   * locked = Anzeige aktiv, aber nicht bedienbar (z.B. bei Aufnahme)
   */
  const STEPS = [32, 48, 64, 96, 128, 192, 256, 320];

  let { activeBitrate = 0, overrideBitrate = null, onchange, disabled = false, locked = false } = $props();

  let isInteractive = $derived(!disabled && !locked);

  function nearestStep(bitrate) {
    if (!bitrate || bitrate <= 0) return null;
    let best = STEPS[0];
    for (const step of STEPS) {
      if (step <= bitrate) best = step;
    }
    return best;
  }

  let activeStep = $derived(nearestStep(activeBitrate));
  let displayValue = $derived(overrideBitrate || activeStep || 0);
  let hasOverride = $derived(overrideBitrate != null);

  function handleClick(step) {
    if (!isInteractive) return;
    if (overrideBitrate === step) {
      onchange?.(null);
    } else {
      onchange?.(step);
    }
  }

  function getLedState(step) {
    if (overrideBitrate === step) return 'override';
    if (activeStep === step && overrideBitrate != null) return 'dimmed';
    if (activeStep === step) return 'active';
    return 'off';
  }
</script>

<div class="bitrate-leds" class:disabled class:locked>
  {#each STEPS as step}
    <button
      class="br-led"
      class:active={!disabled && getLedState(step) === 'active'}
      class:override={!disabled && getLedState(step) === 'override'}
      class:dimmed={!disabled && getLedState(step) === 'dimmed'}
      disabled={disabled || locked}
      onclick={() => handleClick(step)}
      title={disabled ? '' : `${step} kbps${getLedState(step) === 'active' ? ' (erkannt)' : getLedState(step) === 'override' ? ' (Override)' : ''}`}
    ></button>
  {/each}
  {#if !disabled && displayValue > 0}
    <span class="br-value" class:override={hasOverride} class:locked>{displayValue}k</span>
  {/if}
</div>

<style>
  .bitrate-leds {
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .br-led {
    width: 8px;
    height: 8px;
    border-radius: 2px;
    border: none;
    padding: 0;
    background: var(--hifi-led-off);
    box-shadow: inset 1px 1px 2px rgba(0,0,0,0.5);
    cursor: pointer;
    transition: all 0.12s;
    flex-shrink: 0;
  }

  :root .br-led {
    border: 1px solid rgba(0,0,0,0.3);
  }
  :global([data-theme="dark"]) .br-led {
    border: none;
  }

  .br-led:hover {
    background: rgba(255, 255, 255, 0.25);
    transform: scale(1.3);
  }

  .br-led.active {
    background: var(--hifi-led-green);
    box-shadow: 0 0 8px var(--hifi-led-green-glow), inset 0 0 4px rgba(255,255,255,0.3);
  }

  .br-led.active:hover {
    box-shadow: 0 0 10px var(--hifi-led-green-glow), inset 0 0 4px rgba(255,255,255,0.3);
  }

  .br-led.override {
    background: var(--hifi-led-yellow);
    box-shadow: 0 0 8px var(--hifi-led-yellow-glow), inset 0 0 4px rgba(255,255,255,0.3);
  }

  .br-led.override:hover {
    box-shadow: 0 0 10px var(--hifi-led-yellow-glow), inset 0 0 4px rgba(255,255,255,0.3);
  }

  .br-led.dimmed {
    background: var(--hifi-led-green);
    box-shadow: 0 0 4px var(--hifi-led-green-glow), inset 0 0 2px rgba(255,255,255,0.2);
    opacity: 0.35;
  }

  .br-value {
    font-family: var(--hifi-font-values);
    font-size: 9px;
    font-weight: 700;
    color: var(--hifi-text-green);
    text-shadow: 0 0 4px var(--hifi-led-green-glow);
    margin-left: 3px;
    white-space: nowrap;
    line-height: 1;
  }

  .br-value.override {
    color: var(--hifi-led-yellow);
    text-shadow: 0 0 4px var(--hifi-led-yellow-glow);
  }

  /* Deaktivierter Zustand - alles grau */
  .bitrate-leds.disabled .br-led {
    background: var(--hifi-led-off);
    box-shadow: inset 1px 1px 2px rgba(0,0,0,0.5);
    cursor: not-allowed;
    opacity: 0.4;
  }

  .bitrate-leds.disabled .br-led:hover {
    background: var(--hifi-led-off);
    transform: none;
  }

  /* Gesperrter Zustand (Aufnahme) - LED-Status sichtbar, aber gedaempft */
  .bitrate-leds.locked .br-led {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .bitrate-leds.locked .br-led.active {
    background: var(--hifi-led-amber, #e8a317);
    box-shadow: 0 0 6px rgba(232, 163, 23, 0.4), inset 0 0 3px rgba(255,255,255,0.2);
  }

  .bitrate-leds.locked .br-led.override {
    background: var(--hifi-led-amber, #e8a317);
    box-shadow: 0 0 6px rgba(232, 163, 23, 0.4), inset 0 0 3px rgba(255,255,255,0.2);
  }

  .bitrate-leds.locked .br-led:hover {
    transform: none;
  }

  .br-value.locked {
    color: var(--hifi-led-amber, #e8a317);
    text-shadow: 0 0 4px rgba(232, 163, 23, 0.4);
  }
</style>
