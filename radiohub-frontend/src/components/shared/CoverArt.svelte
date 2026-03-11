<script>
  /**
   * CoverArt - Wiederverwendbare Bild-Komponente mit Fallback
   * Zeigt Cover-Art mit lazy loading und Fallback-Icon bei Fehler.
   * Hover-Zoom bei kleinen Größen (sm, md).
   */
  let {
    src = null,
    alt = '',
    size = 'md',       // 'sm' (32px) | 'md' (64px) | 'lg' (120px)
    fallbackIcon = 'fa-podcast',
    rounded = true,
    zoomable = true
  } = $props();

  let hasError = $state(false);
  let isHovering = $state(false);
  let hoverPos = $state({ x: 0, y: 0 });
  let coverEl;

  const sizeMap = { sm: 32, md: 64, lg: 120 };
  let canZoom = $derived(zoomable && (size === 'sm' || size === 'md') && src && !hasError);

  function onError() {
    hasError = true;
  }

  // Reset error state when src changes
  $effect(() => {
    if (src) hasError = false;
  });

  function handleMouseEnter(e) {
    if (!canZoom) return;
    isHovering = true;
    updatePos(e);
  }

  function handleMouseLeave() {
    isHovering = false;
  }

  function updatePos(e) {
    if (!coverEl) return;
    const rect = coverEl.getBoundingClientRect();
    hoverPos = {
      x: rect.right + 8,
      y: rect.top
    };
  }
</script>

<div
  class="cover-art cover-{size}"
  class:rounded
  style="--cover-size: {sizeMap[size] || 64}px"
  bind:this={coverEl}
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
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

{#if isHovering && canZoom}
  <div
    class="cover-zoom"
    style="left: {hoverPos.x}px; top: {hoverPos.y}px;"
  >
    <img src={src} alt={alt} draggable="false" />
  </div>
{/if}

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
    position: relative;
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

  .cover-zoom {
    position: fixed;
    z-index: 100;
    width: 180px;
    height: 180px;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
    border: 1px solid var(--hifi-border-dark);
    pointer-events: none;
    animation: zoomIn 0.15s ease;
  }

  .cover-zoom img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  @keyframes zoomIn {
    from {
      opacity: 0;
      transform: scale(0.8);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }
</style>
