<script>
  import HiFiKnob from '../hifi/HiFiKnob.svelte';
  import HiFiLed from '../hifi/HiFiLed.svelte';
  import { api } from '../../lib/api.js';
  import { appState, actions } from '../../lib/store.svelte.js';
  import * as sfx from '../../lib/uiSounds.js';

  let config = $state({});
  let isLoading = $state(true);
  let clickSoundsEnabled = $state(true);

  $effect(() => {
    loadConfig();
  });

  async function loadConfig() {
    try {
      config = await api.getConfig();
      // HLS-REC Lookback in globalen State übernehmen
      if (config.hls_rec_lookback_minutes) {
        appState.hlsRecLookbackMinutes = config.hls_rec_lookback_minutes;
      }
      // Click-Sounds Status
      clickSoundsEnabled = config.ui_click_sounds !== false;
    } catch (e) {
      // Netzwerkfehler ignorieren
    }
    isLoading = false;
  }

  async function saveConfig(key, value) {
    try {
      await api.updateConfig({ [key]: value });
      config[key] = value;
    } catch (e) {
      actions.showToast('Speichern fehlgeschlagen', 'error');
    }
  }

  function toggleClickSounds() {
    clickSoundsEnabled = !clickSoundsEnabled;
    sfx.setEnabled(clickSoundsEnabled);
    saveConfig('ui_click_sounds', clickSoundsEnabled);
    if (clickSoundsEnabled) {
      sfx.click(); // Feedback: Sound ist an
    }
  }
</script>

{#if isLoading}
  <div class="hifi-flex" style="justify-content:center; padding:60px;">
    <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
  </div>
{:else}
  <div class="allgemein-grid">
    <!-- Theme -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">DISPLAY THEME</span>
      </div>
      <div class="hifi-flex hifi-gap-md" style="padding:16px; align-items:center;">
        <button
          class="theme-btn"
          class:active={appState.theme === 'dark'}
          onclick={() => actions.setTheme('dark')}
        >
          <HiFiLed color={appState.theme === 'dark' ? 'green' : 'off'} />
          <span>DARK</span>
        </button>
        <button
          class="theme-btn"
          class:active={appState.theme === 'light'}
          onclick={() => actions.setTheme('light')}
        >
          <HiFiLed color={appState.theme === 'light' ? 'green' : 'off'} />
          <span>LIGHT</span>
        </button>
      </div>
    </div>

    <!-- Click-Sounds -->
    <div class="hifi-panel">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">UI SOUNDS</span>
      </div>
      <div class="hifi-flex hifi-gap-md" style="padding:16px; align-items:center;">
        <button
          class="theme-btn"
          class:active={clickSoundsEnabled}
          onclick={toggleClickSounds}
        >
          <HiFiLed color={clickSoundsEnabled ? 'green' : 'off'} />
          <span>CLICK-SOUNDS</span>
        </button>
      </div>
    </div>

    <!-- Timeshift Buffer (volle Breite) -->
    <div class="hifi-panel span-full">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">TIMESHIFT BUFFER</span>
      </div>
      <div class="hifi-flex hifi-gap-xl" style="padding:24px; justify-content:center;">
        <HiFiKnob
          bind:value={config.hls_min_bitrate}
          min={32}
          max={128}
          step={16}
          unit="kbps"
          label="MIN BITRATE"
          onchange={(e) => saveConfig('hls_min_bitrate', e.value)}
        />
        <HiFiKnob
          bind:value={config.hls_max_bitrate}
          min={64}
          max={320}
          step={32}
          unit="kbps"
          label="MAX BITRATE"
          onchange={(e) => saveConfig('hls_max_bitrate', e.value)}
        />
      </div>
      <div style="padding:0 16px 16px; text-align:center;">
        <span class="hifi-font-small" style="color:var(--hifi-text-muted);">
          Output-Bitrate wird automatisch an Input angepasst (nicht höher als Quelle)
        </span>
      </div>
    </div>

    <!-- HLS-REC (volle Breite) -->
    <div class="hifi-panel span-full">
      <div class="hifi-panel-header">
        <span class="hifi-font-label">HLS-REC</span>
        <span class="hifi-font-small" style="color:var(--hifi-text-amber); margin-left:8px;">BUFFER-AUFNAHME</span>
      </div>
      <div class="hifi-flex hifi-gap-xl" style="padding:24px; justify-content:center;">
        <HiFiKnob
          value={appState.hlsRecLookbackMinutes}
          min={1}
          max={120}
          step={1}
          unit="min"
          label="LOOKBACK"
          onchange={(e) => { appState.hlsRecLookbackMinutes = e.value; saveConfig('hls_rec_lookback_minutes', e.value); }}
        />
      </div>
      <div style="padding:0 16px 16px; text-align:center;">
        <span class="hifi-font-small" style="color:var(--hifi-text-muted);">
          Wie viele Minuten soll die HLS-Aufnahme in die Vergangenheit zurückgreifen?
        </span>
      </div>
    </div>
  </div>
{/if}

<style>
  .allgemein-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .span-full {
    grid-column: 1 / -1;
  }

  .theme-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-md);
    color: var(--hifi-text-secondary);
    font-family: var(--hifi-font-body);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: var(--hifi-shadow-outset);
  }

  .theme-btn:hover {
    background: var(--hifi-bg-secondary);
  }

  .theme-btn.active {
    background: var(--hifi-bg-panel);
    color: var(--hifi-accent);
    box-shadow: var(--hifi-shadow-inset);
  }
</style>
