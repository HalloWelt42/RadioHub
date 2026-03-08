<script>
  let { 
    isPlaying = false,
    isRecording = false,
    onplay,
    onstop,
    onprev,
    onnext,
    onrec
  } = $props();
</script>

<div class="hifi-transport">
  {#if onprev}
    <button class="hifi-transport-btn" onclick={onprev} title="Vorheriger Titel">⏪</button>
  {/if}

  <button class="hifi-transport-btn" class:active={!isPlaying} onclick={onstop} title="Stopp">⏹</button>
  <button class="hifi-transport-btn" class:active={isPlaying} onclick={onplay} title="Abspielen">▶</button>

  {#if onnext}
    <button class="hifi-transport-btn" onclick={onnext} title="Naechster Titel">⏩</button>
  {/if}

  {#if onrec}
    <button class="hifi-transport-btn rec" class:active={isRecording} onclick={onrec} title={isRecording ? 'Aufnahme stoppen' : 'Aufnahme starten'}>⏺</button>
  {/if}
</div>
