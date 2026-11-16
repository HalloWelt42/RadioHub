<script>
  import { appState } from '../../lib/store.svelte.js';

  let visible = $state(false);
  let currentToast = $state(null);
  let fadeTimer = null;

  // Toast-Wechsel beobachten
  $effect(() => {
    const toast = appState.toast;
    if (toast) {
      currentToast = toast;
      visible = true;
      clearTimeout(fadeTimer);
      // Fade-Out nach 2.5s starten (Animation dauert 0.4s)
      fadeTimer = setTimeout(() => {
        visible = false;
      }, 2500);
    } else {
      visible = false;
    }
  });
</script>

{#if currentToast}
  <div
    class="hifi-toast"
    class:visible
    class:success={currentToast.type === 'success'}
    class:error={currentToast.type === 'error'}
    class:warning={currentToast.type === 'warning'}
    class:info={currentToast.type === 'info'}
    ontransitionend={() => { if (!visible) currentToast = null; }}
  >
    {currentToast.message}
  </div>
{/if}

<style>
  .hifi-toast {
    position: fixed;
    bottom: 140px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    z-index: 5000;
    padding: 8px 20px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm, 4px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    font-family: 'Barlow', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: var(--hifi-text-primary);
    min-width: 160px;
    text-align: center;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s ease, transform 0.3s ease;
  }

  .hifi-toast.visible {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }

  .hifi-toast.success {
    border-color: var(--hifi-led-green);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 8px rgba(51, 204, 51, 0.2);
  }
  .hifi-toast.error {
    border-color: var(--hifi-led-red);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 8px rgba(255, 51, 51, 0.2);
  }
  .hifi-toast.warning {
    border-color: var(--hifi-led-yellow);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 8px rgba(255, 204, 0, 0.2);
  }
  .hifi-toast.info {
    border-color: var(--hifi-led-blue);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 8px rgba(51, 153, 255, 0.2);
  }
</style>
