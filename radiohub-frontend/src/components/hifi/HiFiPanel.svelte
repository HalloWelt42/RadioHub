<script>
  let { 
    title = '',
    variant = 'default', // default | inset | raised
    children 
  } = $props();
</script>

<div 
  class="hifi-panel"
  class:hifi-panel-inset={variant === 'inset'}
  class:hifi-panel-raised={variant === 'raised'}
>
  {#if title}
    <div class="hifi-panel-header">
      <span class="hifi-panel-title">{title}</span>
    </div>
  {/if}
  <div class="hifi-panel-content">
    {@render children?.()}
  </div>
</div>
