<script>
  let { 
    checked = $bindable(false),
    label = '',
    count = undefined,
    onchange
  } = $props();
  
  function toggle() {
    checked = !checked;
    onchange?.({ checked });
  }
</script>

<button class="hifi-checkbox" class:checked onclick={toggle}>
  <span class="hifi-checkbox-box">
    {#if checked}
      <span class="hifi-checkbox-mark">✓</span>
    {/if}
  </span>
  {#if label}
    <span class="hifi-checkbox-label">{label}</span>
  {/if}
  {#if count !== undefined}
    <span class="hifi-checkbox-count">{count}</span>
  {/if}
</button>

<style>
  .hifi-checkbox {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-size: 12px;
    cursor: pointer;
    width: 100%;
    text-align: left;
    border-radius: var(--hifi-border-radius-sm);
    transition: background 0.1s ease;
  }
  
  .hifi-checkbox:hover {
    background: var(--hifi-row-hover);
  }
  
  .hifi-checkbox.checked {
    color: var(--hifi-accent);
  }
  
  .hifi-checkbox-box {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: 3px;
    font-size: 10px;
    box-shadow: var(--hifi-shadow-inset);
  }
  
  .hifi-checkbox.checked .hifi-checkbox-box {
    background: var(--hifi-accent);
    border-color: var(--hifi-accent);
  }
  
  .hifi-checkbox-mark {
    color: white;
    font-weight: bold;
  }
  
  .hifi-checkbox-label {
    flex: 1;
  }
  
  .hifi-checkbox-count {
    font-size: 10px;
    color: var(--hifi-text-secondary);
    background: var(--hifi-bg-tertiary);
    padding: 2px 6px;
    border-radius: 10px;
  }
</style>
