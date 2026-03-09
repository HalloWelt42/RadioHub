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
    bottom: 110px;
    left: 50%;
    transform: translateX(-50%) !important;
    z-index: 5000;
    padding: 12px 24px;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-md);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    font-size: var(--hifi-font-size-md);
    font-weight: 600;
    color: var(--hifi-text-primary);
    min-width: 200px;
    text-align: center;
    animation: slideUp 0.3s ease;
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
