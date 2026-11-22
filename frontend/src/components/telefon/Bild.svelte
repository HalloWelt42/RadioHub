<script>
  /** Quadratisches Bild; fehlt es oder lädt es nicht, die Kachel der Liste mit Kürzel auf Lackfarbe aus dem Namen
   *  (RAD-100, in Basic die Vorgabe), ohne Namen ein Ersatzsymbol. Größe in Pixeln oder als CSS-Länge. */
  import { kuerzel, lack } from '../../lib/radio/anzeige';

  let { src = null, symbol = 'fa-music', groesse = 48, name = '' } = $props();
  let kaputt = $state(false);
  $effect(() => { src; kaputt = false; });
  const g = $derived(typeof groesse === 'number' ? `${groesse}px` : groesse);
</script>

{#if src && !kaputt}
  <span class="tf-bild" style="--g: {g}">
    <img {src} alt="" loading="lazy" onerror={() => (kaputt = true)}
      onload={(e) => { if (e.currentTarget.naturalWidth < 4) kaputt = true; }} />
  </span>
{:else if name}
  <span class="tf-bild rh-logo-bild" style="--g: {g}; --s: {g}; --lack: {lack(name)}" aria-hidden="true">{kuerzel(name)}</span>
{:else}
  <span class="tf-bild" style="--g: {g}"><i class="fa-solid {symbol}" aria-hidden="true"></i></span>
{/if}

<style>
  .tf-bild {
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
  /* Kachel der Liste: Lack, Kürzel und Prägung aus .rh-logo-bild (radio.css) */
  .tf-bild.rh-logo-bild { background-color: var(--lack); color: var(--auf-farbe); font-size: calc(var(--g) * 0.34); }
  img { width: 100%; height: 100%; object-fit: cover; }
</style>
