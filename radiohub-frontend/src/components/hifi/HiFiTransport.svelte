<script>
  import { t } from '../../lib/i18n.svelte.js';

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
    <button class="hifi-transport-btn" onclick={onprev} title={t('player.prevTitel')}>⏪</button>
  {/if}

  <button class="hifi-transport-btn" class:active={!isPlaying} onclick={onstop} title={t('player.stop')}>⏹</button>
  <button class="hifi-transport-btn" class:active={isPlaying} onclick={onplay} title={t('player.play')}>▶</button>

  {#if onnext}
    <button class="hifi-transport-btn" onclick={onnext} title={t('player.nextTitel')}>⏩</button>
  {/if}

  {#if onrec}
    <button class="hifi-transport-btn rec" class:active={isRecording} onclick={onrec} title={isRecording ? t('player.recStop') : t('player.recStart')}>⏺</button>
  {/if}
</div>
