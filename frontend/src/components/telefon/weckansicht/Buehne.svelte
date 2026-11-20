<script lang="ts">
  // Bühne der Weckansicht: jede Gestaltung ist für 364 Bezugspixel Höhe gebaut (das Querformat eines Telefons ohne Rand)
  // und wird auf die verfügbare Höhe skaliert; die Breite folgt dem Platz. So sieht jede Gestaltung auf jedem Gerät gleich
  // aus, Schrift und Tasten wachsen mit, und keine Gestaltung braucht eigene Regeln für Bildschirmgrößen.
  import type { Snippet } from "svelte";

  const HOEHE = 364;
  let { children }: { children: Snippet } = $props();
  let flaeche: HTMLDivElement | undefined = $state();
  let skala = $state(1);
  let breite = $state(780);

  $effect(() => {
    if (!flaeche) return;
    const el = flaeche;
    const messen = () => {
      skala = Math.max(0.4, el.clientHeight / HOEHE);
      breite = el.clientWidth / skala;
    };
    messen();
    const beobachter = new ResizeObserver(messen);
    beobachter.observe(el);
    return () => beobachter.disconnect();
  });
</script>

<div class="wa-flaeche" bind:this={flaeche}>
  <div class="wa-buehne" style:width="{breite}px" style:transform="scale({skala})">{@render children()}</div>
</div>
