<script>
  import { t } from '../../lib/i18n.svelte.js';

  /**
   * HiFi Select - Dropdown im HiFi-Stil
   * Unterstützt Single und Multi-Select
   */
  let {
    options = [],        // [{ value, label }]
    value = $bindable(), // Single: string, Multi: string[]
    multiple = false,
    placeholder = 'Select...',
    label = '',
    onchange
  } = $props();
  
  let isOpen = $state(false);
  let container;
  
  // Aktuell ausgewählte Labels
  let displayText = $derived(() => {
    if (multiple) {
      if (!value || value.length === 0) return placeholder;
      if (value.length === 1) {
        const opt = options.find(o => o.value === value[0]);
        return opt?.label || value[0];
      }
      return t('hifi.ausgewaehlt', { count: value.length });
    } else {
      if (!value) return placeholder;
      const opt = options.find(o => o.value === value);
      return opt?.label || value;
    }
  });
  
  function toggle() {
    isOpen = !isOpen;
  }
  
  function selectOption(opt) {
    if (multiple) {
      const arr = value || [];
      if (arr.includes(opt.value)) {
        value = arr.filter(v => v !== opt.value);
      } else {
        value = [...arr, opt.value];
      }
    } else {
      value = opt.value;
      isOpen = false;
    }
    onchange?.({ value });
  }
  
  function isSelected(opt) {
    if (multiple) {
      return (value || []).includes(opt.value);
    }
    return value === opt.value;
  }
  
  function clearAll() {
    value = multiple ? [] : null;
    onchange?.({ value });
  }
  
  // Click outside schließt Dropdown
  function handleClickOutside(e) {
    if (container && !container.contains(e.target)) {
      isOpen = false;
    }
  }
  
  $effect(() => {
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  });
</script>

<div class="hifi-select-wrapper" bind:this={container}>
  {#if label}
    <span class="hifi-select-label">{label}</span>
  {/if}
  
  <button class="hifi-select-trigger" class:open={isOpen} onclick={toggle} title={isOpen ? t('hifi.auswahlSchliessen') : t('hifi.auswahlOeffnen')}>
    <span class="hifi-select-value">{displayText()}</span>
    <span class="hifi-select-arrow">{isOpen ? '▲' : '▼'}</span>
  </button>
  
  {#if isOpen}
    <div class="hifi-select-dropdown">
      {#if multiple && value?.length > 0}
        <button class="hifi-select-clear" onclick={clearAll} title={t('hifi.auswahlZuruecksetzen')}>
          ✕ {t('hifi.alleEntfernen')}
        </button>
      {/if}
      
      <div class="hifi-select-options">
        {#each options as opt}
          <button
            class="hifi-select-option"
            class:selected={isSelected(opt)}
            onclick={() => selectOption(opt)}
            title={isSelected(opt) ? t('hifi.abwaehlen', { label: opt.label }) : t('hifi.auswaehlen', { label: opt.label })}
          >
            {#if multiple}
              <span class="hifi-select-checkbox">
                {isSelected(opt) ? '☑' : '☐'}
              </span>
            {/if}
            <span>{opt.label}</span>
            {#if opt.count !== undefined}
              <span class="hifi-select-count">{opt.count}</span>
            {/if}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .hifi-select-wrapper {
    position: relative;
    min-width: 150px;
  }
  
  .hifi-select-label {
    display: block;
    font-size: 10px;
    letter-spacing: 1px;
    color: var(--hifi-text-secondary);
    margin-bottom: 4px;
    text-transform: uppercase;
  }
  
  .hifi-select-trigger {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    padding: 8px 12px;
    background: var(--hifi-bg-tertiary);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    color: var(--hifi-text-primary);
    font-family: var(--hifi-font-family);
    font-size: 12px;
    cursor: pointer;
    box-shadow: var(--hifi-shadow-inset);
    transition: all 0.15s ease;
  }
  
  .hifi-select-trigger:hover {
    background: var(--hifi-bg-secondary);
  }
  
  .hifi-select-trigger.open {
    border-color: var(--hifi-accent);
  }
  
  .hifi-select-value {
    flex: 1;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .hifi-select-arrow {
    font-size: 8px;
    color: var(--hifi-text-secondary);
  }
  
  .hifi-select-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    margin-top: 4px;
    background: var(--hifi-bg-panel);
    border: 1px solid var(--hifi-border-dark);
    border-radius: var(--hifi-border-radius-sm);
    box-shadow: var(--hifi-shadow-outset);
    z-index: var(--hifi-z-dropdown);
    max-height: 250px;
    display: flex;
    flex-direction: column;
  }
  
  .hifi-select-clear {
    padding: 8px 12px;
    background: none;
    border: none;
    border-bottom: 1px solid var(--hifi-border-dark);
    color: var(--hifi-text-secondary);
    font-size: 11px;
    cursor: pointer;
    text-align: left;
  }
  
  .hifi-select-clear:hover {
    color: var(--hifi-led-red);
  }
  
  .hifi-select-options {
    overflow-y: auto;
    flex: 1;
  }
  
  .hifi-select-option {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    color: var(--hifi-text-primary);
    font-size: 12px;
    cursor: pointer;
    text-align: left;
    transition: background 0.1s ease;
  }
  
  .hifi-select-option:hover {
    background: var(--hifi-row-hover);
  }
  
  .hifi-select-option.selected {
    background: var(--hifi-row-selected);
    color: var(--hifi-accent);
  }
  
  .hifi-select-checkbox {
    font-size: 14px;
  }
  
  .hifi-select-count {
    margin-left: auto;
    font-size: 10px;
    color: var(--hifi-text-secondary);
    background: var(--hifi-bg-tertiary);
    padding: 2px 6px;
    border-radius: 10px;
  }
</style>
