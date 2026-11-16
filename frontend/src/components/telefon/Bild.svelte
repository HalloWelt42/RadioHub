<script>
  /** Quadratisches Bild mit Ersatzsymbol, wenn es fehlt oder nicht lädt. */
  let { src = null, symbol = 'fa-music', groesse = 48 } = $props();
  let kaputt = $state(false);
  $effect(() => { src; kaputt = false; });
</script>

<span class="bild" style="--g: {groesse}px">
  {#if src && !kaputt}
    <img {src} alt="" loading="lazy" onerror={() => (kaputt = true)}
      onload={(e) => { if (e.currentTarget.naturalWidth < 4) kaputt = true; }} />
  {:else}
    <i class="fa-solid {symbol}" aria-hidden="true"></i>
  {/if}
</span>

<style>
  .bild {
    width: var(--g);
    height: var(--g);
    flex: none;
    display: grid;
    place-items: center;
    border-radius: 10px;
    overflow: hidden;
    background: var(--t-flaeche-2);
    color: var(--t-text-2);
    font-size: calc(var(--g) * 0.4);
  }
  img { width: 100%; height: 100%; object-fit: cover; }
</style>
