<script>
  let {
    color = 'off',   // green | yellow | red | blue | amber | white | off
    blink = false,
    pulse = false,
    size = 'default', // small | large
    title = ''
  } = $props();
</script>

<div
  class="hifi-led"
  class:on-green={color === 'green'}
  class:on-yellow={color === 'yellow'}
  class:on-red={color === 'red'}
  class:on-blue={color === 'blue'}
  class:on-amber={color === 'amber'}
  class:on-white={color === 'white'}
  class:blink
  class:pulse
  class:hifi-led-small={size === 'small'}
  class:hifi-led-wide={size === 'wide'}
  class:hifi-led-large={size === 'large'}
  {title}
></div>
