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
  let centerX = 0;
  let centerY = 0;

  const startAngle = -135;
  const endAngle = 135;

  let angle = $derived(startAngle + ((value - min) / (max - min)) * (endAngle - startAngle));
  let display = $derived(step < 1 ? value.toFixed(1) : Math.round(value));

  // === Ziel-Speicher + Animation ===
  // Ein einziger Zustand: _target ist wo der Knob hin will.
  // Die Animation bewegt value Richtung _target, immer.
  let _target = value;
  let _animId = null;

  function setTarget(v) {
    _target = Math.max(min, Math.min(max, Math.round(v / step) * step));
    if (!_animId) _animId = requestAnimationFrame(animate);
  }

  function animate() {
    const diff = _target - value;
    if (diff === 0) {
      _animId = null;
      return;
    }
    // 18% der Restdistanz pro Frame, minimum 1 Step
    let delta = diff * 0.18;
    if (Math.abs(delta) < step) delta = Math.sign(diff) * step;

    let next = Math.round((value + delta) / step) * step;
    next = Math.max(min, Math.min(max, next));

    // Overshooting verhindern
    if ((diff > 0 && next > _target) || (diff < 0 && next < _target)) {
      next = _target;
    }

    if (next !== value) {
      value = next;
      onchange?.({ value });
    }

    _animId = (value !== _target) ? requestAnimationFrame(animate) : null;
  }

  // === Maus/Touch Drag ===
  function start(e) {
    e.preventDefault();
    dragging = true;
    const r = container.getBoundingClientRect();
    centerX = r.left + r.width / 2;
    centerY = r.top + r.height / 2;
  }

  function drag(e) {
    if (!dragging) return;
    const x = (e.touches?.[0]?.clientX ?? e.clientX) - centerX;
    const y = (e.touches?.[0]?.clientY ?? e.clientY) - centerY;
    let a = Math.atan2(y, x) * 180 / Math.PI + 90;
    if (a < -180) a += 360;
    if (a > 180) a -= 360;
    a = Math.max(startAngle, Math.min(endAngle, a));
    setTarget(min + ((a - startAngle) / (endAngle - startAngle)) * (max - min));
  }

  function end() {
    dragging = false;
    // Animation läuft weiter bis Ziel erreicht -- kein Snap, kein Abbruch
  }

  // === Mausrad: Trägheit durch Impulse auslassen ===
  let _wheelSkip = 0;
  function wheel(e) {
    e.preventDefault();
    _wheelSkip++;
    if (_wheelSkip % 3 !== 1) return; // Nur jeder 3. Impuls zählt
    setTarget(value + (e.deltaY > 0 ? -step * 2 : step * 2));
  }

  // === Externe Wertänderungen syncen (Tastatur-Shortcuts) ===
  $effect(() => {
    if (!dragging && !_animId) _target = value;
  });

  // === Event-Listener ===
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
      if (_animId) { cancelAnimationFrame(_animId); _animId = null; }
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
