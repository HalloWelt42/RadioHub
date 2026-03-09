<script>
  let { 
    min = 0, 
    max = 100, 
    value = $bindable(50), 
    step = 1, 
    unit = '', 
    label = '', 
    size = 'default', // small | large
    onchange
  } = $props();
  
  let container;
  let dragging = $state(false);
  let centerX = $state(0);
  let centerY = $state(0);
  
  const startAngle = -135;
  const endAngle = 135;
  
  let angle = $derived(startAngle + ((value - min) / (max - min)) * (endAngle - startAngle));
  let display = $derived(step < 1 ? value.toFixed(1) : Math.round(value));
  
  function start(e) { 
    e.preventDefault(); 
    dragging = true;
    const r = container.getBoundingClientRect();
    centerX = r.left + r.width / 2; 
    centerY = r.top + r.height / 2;
  }
  
  let _targetValue = value;
  let _smoothId = null;

  function drag(e) {
    if (!dragging) return;
    const x = (e.touches?.[0]?.clientX ?? e.clientX) - centerX;
    const y = (e.touches?.[0]?.clientY ?? e.clientY) - centerY;
    let a = Math.atan2(y, x) * 180 / Math.PI + 90;
    if (a < -180) a += 360;
    if (a > 180) a -= 360;
    a = Math.max(startAngle, Math.min(endAngle, a));
    let v = min + ((a - startAngle) / (endAngle - startAngle)) * (max - min);
    _targetValue = Math.max(min, Math.min(max, Math.round(v / step) * step));
    if (!_smoothId) smoothStep();
  }

  function smoothStep() {
    const diff = _targetValue - value;
    if (Math.abs(diff) < step) {
      value = _targetValue;
      onchange?.({ value });
      _smoothId = null;
      return;
    }
    // Daempfung: 5% pro Frame -- schwerer, mechanischer Widerstand
    value = Math.round((value + diff * 0.05) / step) * step;
    value = Math.max(min, Math.min(max, value));
    onchange?.({ value });
    _smoothId = requestAnimationFrame(smoothStep);
  }
  
  function end() {
    dragging = false;
    if (_smoothId) { cancelAnimationFrame(_smoothId); _smoothId = null; }
    if (value !== _targetValue) {
      value = _targetValue;
      onchange?.({ value });
    }
  }
  
  let _lastWheelTime = 0;
  function wheel(e) {
    e.preventDefault();
    // Throttle: max 1 Aenderung pro 120ms -- verhindert Ueberreaktion
    const now = Date.now();
    if (now - _lastWheelTime < 120) return;
    _lastWheelTime = now;
    _targetValue = Math.max(min, Math.min(max, _targetValue + (e.deltaY > 0 ? -step : step)));
    if (!_smoothId) smoothStep();
  }
  
  $effect(() => {
    window.addEventListener('mousemove', drag);
    window.addEventListener('mouseup', end);
    window.addEventListener('touchmove', drag);
    window.addEventListener('touchend', end);
    
    return () => {
      window.removeEventListener('mousemove', drag);
      window.removeEventListener('mouseup', end);
      window.removeEventListener('touchmove', drag);
      window.removeEventListener('touchend', end);
    };
  });
</script>

<div class="hifi-knob-wrapper" class:hifi-knob-small={size === 'small'} class:hifi-knob-large={size === 'large'}>
  <div class="hifi-knob-container" bind:this={container} onwheel={wheel}>
    <div class="hifi-knob-ticks">
      {#each Array(11) as _, i}
        <div 
          class="hifi-knob-tick" 
          class:active={i % 5 === 0} 
          style="transform:rotate({startAngle + i / 10 * (endAngle - startAngle)}deg)"
        ></div>
      {/each}
    </div>
    <div class="hifi-knob-base"></div>
    <div 
      class="hifi-knob" 
      style="transform:rotate({angle}deg)" 
      onmousedown={start} 
      ontouchstart={start}
      role="slider"
      tabindex="0"
      aria-valuenow={value}
      aria-valuemin={min}
      aria-valuemax={max}
    >
      <div class="hifi-knob-indicator"></div>
    </div>
  </div>
  <span class="hifi-knob-value">{display}{unit ? ' ' + unit : ''}</span>
  {#if label}<span class="hifi-knob-label">{label}</span>{/if}
</div>
