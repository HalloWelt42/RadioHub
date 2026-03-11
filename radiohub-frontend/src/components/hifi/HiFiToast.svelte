<script>
  import { appState } from '../../lib/store.svelte.js';
</script>

{#if appState.toast}
  <div 
    class="hifi-toast"
    class:success={appState.toast.type === 'success'}
    class:error={appState.toast.type === 'error'}
    class:warning={appState.toast.type === 'warning'}
    class:info={appState.toast.type === 'info'}
  >
    {appState.toast.message}
  </div>
{/if}

<style>
  .hifi-toast {
    position: fixed;
    bottom: 140px;
    left: 50%;
    transform: translateX(-50%) !important;
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
    animation: slideUp 0.3s ease;
    pointer-events: none;
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

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
</style>
