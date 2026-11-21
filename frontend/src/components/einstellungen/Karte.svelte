<script lang="ts">
  // Karte eines Bereichs (RAD-11): Kopf mit Symbol und Titel, rechts im Kopf Ergänzendes (Geltung, Verweis), darunter
  // ein Hinweisband und der Inhalt. Dieselbe Karte wie in Einstellungen > Radio.
  import type { Snippet } from "svelte";

  let { titel, symbol, hinweis = "", still = "", kopf, children }: {
    titel: string;
    symbol: string;
    hinweis?: string;
    /** leiser Satz neben dem Titel */
    still?: string;
    kopf?: Snippet;
    children?: Snippet;
  } = $props();
</script>

<div class="karte rh-karte">
  <div class="rh-karte-kopf"><h2><i class="fa-solid {symbol}"></i>{titel}</h2>{#if still}<span class="rh-still">{still}</span>{/if}{@render kopf?.()}</div>
  {#if hinweis}<p class="hinweis-band"><i class="fa-solid fa-circle-info"></i><span>{hinweis}</span></p>{/if}
  {@render children?.()}
</div>
