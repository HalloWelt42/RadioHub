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
    bottom: 100px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    animation: slideUp 0.3s ease;
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
