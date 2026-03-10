<script>
  /**
   * CoverArt - Wiederverwendbare Bild-Komponente mit Fallback
   * Zeigt Cover-Art mit lazy loading und Fallback-Icon bei Fehler.
   */
  let {
    src = null,
    alt = '',
    size = 'md',       // 'sm' (32px) | 'md' (64px) | 'lg' (120px)
    fallbackIcon = 'fa-podcast',
    rounded = true
  } = $props();

  let hasError = $state(false);

  const sizeMap = { sm: 32, md: 64, lg: 120 };

  function onError() {
    hasError = true;
  }

  // Reset error state when src changes
  $effect(() => {
    if (src) hasError = false;
  });
</script>

<div
  class="cover-art cover-{size}"
  class:rounded
  style="--cover-size: {sizeMap[size] || 64}px"
>
  {#if src && !hasError}
    <img
      {src}
      {alt}
      loading="lazy"
      onerror={onError}
      draggable="false"
    />
  {:else}
    <div class="cover-fallback">
      <i class="fa-solid {fallbackIcon}"></i>
    </div>
  {/if}
</div>

<style>
  .cover-art {
    width: var(--cover-size);
    height: var(--cover-size);
    min-width: var(--cover-size);
    min-height: var(--cover-size);
    overflow: hidden;
    background: var(--hifi-bg-tertiary);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .cover-art.rounded {
    border-radius: 4px;
  }

  .cover-art img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .cover-fallback {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--hifi-text-secondary);
    opacity: 0.5;
  }

  .cover-sm .cover-fallback i { font-size: 14px; }
  .cover-md .cover-fallback i { font-size: 24px; }
  .cover-lg .cover-fallback i { font-size: 40px; }
</style>
