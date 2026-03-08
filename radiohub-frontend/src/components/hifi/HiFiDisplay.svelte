<script>
  let { 
    size = 'medium',   // small | medium | large
    color = 'green',   // green | amber | blue | red | cyan
    segment = false,
    children 
  } = $props();
</script>

<div 
  class="hifi-display"
  class:hifi-display-small={size === 'small'}
  class:hifi-display-medium={size === 'medium'}
  class:hifi-display-large={size === 'large'}
  class:hifi-display-segment={segment}
  class:hifi-display-amber={color === 'amber'}
  class:hifi-display-blue={color === 'blue'}
  class:hifi-display-red={color === 'red'}
  class:hifi-display-cyan={color === 'cyan'}
>{@render children?.()}</div>
