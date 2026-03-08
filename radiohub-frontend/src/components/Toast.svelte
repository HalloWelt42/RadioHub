<script>
  import Icon from './Icon.svelte';
  import { appState } from '../lib/store.svelte.js';
  
  let iconName = $derived(
    appState.toast?.type === 'success' ? 'check' :
    appState.toast?.type === 'error' ? 'x' : 'radio'
  );
</script>

{#if appState.toast}
  <div class="toast" class:success={appState.toast.type === 'success'} class:error={appState.toast.type === 'error'}>
    <Icon name={iconName} size={18} />
    <span>{appState.toast.message}</span>
  </div>
{/if}

<style>
  .toast {
    position: fixed;
    bottom: 100px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-sm) var(--space-md);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    color: var(--text-primary);
    font-size: 14px;
    z-index: 1000;
    animation: slideUp 0.2s ease;
  }
  
  .toast.success {
    border-color: var(--success);
    color: var(--success);
  }
  
  .toast.error {
    border-color: var(--error);
    color: var(--error);
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
