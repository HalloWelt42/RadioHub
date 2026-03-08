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
    <button class="hifi-transport-btn" onclick={onprev}>⏪</button>
  {/if}
  
  <button class="hifi-transport-btn" class:active={!isPlaying} onclick={onstop}>⏹</button>
  <button class="hifi-transport-btn" class:active={isPlaying} onclick={onplay}>▶</button>
  
  {#if onnext}
    <button class="hifi-transport-btn" onclick={onnext}>⏩</button>
  {/if}
  
  {#if onrec}
    <button class="hifi-transport-btn rec" class:active={isRecording} onclick={onrec}>⏺</button>
  {/if}
</div>
