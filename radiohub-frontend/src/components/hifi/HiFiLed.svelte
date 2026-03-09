<script>
  let {
    color = 'off',   // green | yellow | red | blue | amber | off
    blink = false,
    pulse = false,
    size = 'default' // small | large
  } = $props();
</script>

<div
  class="hifi-led"
  class:on-green={color === 'green'}
  class:on-yellow={color === 'yellow'}
  class:on-red={color === 'red'}
  class:on-blue={color === 'blue'}
  class:on-amber={color === 'amber'}
  class:blink
  class:pulse
  class:hifi-led-small={size === 'small'}
  class:hifi-led-large={size === 'large'}
></div>
