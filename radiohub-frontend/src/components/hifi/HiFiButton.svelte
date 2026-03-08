<script>
  let { 
    variant = 'default',  // primary | danger | success
    size = 'default',     // small | large
    active = false,
    disabled = false,
    onclick,
    children 
  } = $props();
</script>

<button 
  class="hifi-btn"
  class:hifi-btn-primary={variant === 'primary'}
  class:hifi-btn-danger={variant === 'danger'}
  class:hifi-btn-success={variant === 'success'}
  class:hifi-btn-small={size === 'small'}
  class:hifi-btn-large={size === 'large'}
  class:active
  {disabled}
  {onclick}
>{@render children?.()}</button>
