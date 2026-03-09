<script>
  import { getRMS } from '../../lib/audioAnalyser.js';

  let { volume = 50, active = false } = $props();

  // 8 LEDs für das VU-Meter
  let levels = $state([false, false, false, false, false, false, false, false]);
  let intervalId = null;

  function updateLevels() {
    if (!active) {
      levels = [false, false, false, false, false, false, false, false];
      return;
    }

    const realLevel = getRMS();
    let peakLevel;

    if (realLevel !== null) {
      // Echte Analyse: AnalyserNode sieht bereits das volume-angepasste Signal
      // (audioEl.volume wird vor MediaElementSource angewendet)
      peakLevel = Math.round(realLevel * 8);
    } else {
      // Fallback: Simulation -- Volume manuell einrechnen
      const volumeBase = Math.floor((volume / 100) * 6);
      const variation = Math.floor(Math.random() * 4) - 1;
      peakLevel = Math.max(1, Math.min(8, volumeBase + variation));
    }

    peakLevel = Math.max(0, Math.min(8, peakLevel));
    levels = levels.map((_, i) => i < peakLevel);
  }

  // Interval-Management
  $effect(() => {
    if (active) {
      intervalId = setInterval(updateLevels, 200);
    } else {
      // Deferred Reset: $state-Schreiben außerhalb des synchronen $effect
      setTimeout(() => {
        levels = [false, false, false, false, false, false, false, false];
      }, 0);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };
  });

  // Farbe je nach Position: unten grün, mitte gelb, oben rot (180° gedreht)
  function getLedColor(index, isOn) {
    if (!isOn) return '';
    if (index >= 6) return 'red';
    if (index >= 4) return 'yellow';
    return 'green';
  }
</script>

<div class="hifi-vu-meter">
  {#each levels as isOn, i}
    <div
      class="hifi-vu-led"
      class:on={isOn}
      class:green={getLedColor(i, isOn) === 'green'}
      class:yellow={getLedColor(i, isOn) === 'yellow'}
      class:red={getLedColor(i, isOn) === 'red'}
    ></div>
  {/each}
</div>

<style>
  .hifi-vu-meter {
    display: grid;
    grid-template-rows: repeat(8, 5px);
    gap: 2px;
    padding: 3px;
    background: var(--hifi-display-bg);
    border: 1px solid var(--hifi-display-border);
    border-radius: 3px;
    height: 64px;
    width: 20px;
    box-sizing: border-box;
    overflow: hidden;
    align-content: center;
    /* 180° gedreht - LEDs von oben nach unten */
    transform: rotate(180deg);
  }

  .hifi-vu-led {
    width: 100%;
    border-radius: 1px;
    background: rgba(255, 255, 255, 0.08);
    transition: all 0.08s;
  }

  .hifi-vu-led.on.green {
    background: var(--hifi-led-green);
    box-shadow: 0 0 4px var(--hifi-led-green-glow);
  }

  .hifi-vu-led.on.yellow {
    background: var(--hifi-led-yellow);
    box-shadow: 0 0 4px var(--hifi-led-yellow-glow);
  }

  .hifi-vu-led.on.red {
    background: var(--hifi-led-red);
    box-shadow: 0 0 4px var(--hifi-led-red-glow);
  }
</style>
