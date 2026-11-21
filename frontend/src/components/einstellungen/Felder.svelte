<script lang="ts">
  // Zeilen zu Schlüsseln (RAD-11): "geraet:<name>" ist eine Einstellung dieses Geräts (lib/einstellungen/geraet), jeder
  // andere Schlüssel ein Feld des Servermodells. Felder, die es in dieser Ausgabe nicht gibt (Basic ohne Server), fallen
  // weg; die Ansicht schreibt nur, welche Werte wo stehen.
  import { GERAET, geraetSetzen, geraetZeile, server } from "../../lib/einstellungen";
  import Zeile from "./Zeile.svelte";

  let { felder }: { felder: readonly string[] } = $props();

  const zeilen = $derived(felder.map((f) => {
    if (f.startsWith("geraet:")) {
      const name = f.slice(7);
      return name in GERAET ? { zeile: geraetZeile(name), setzen: (w: unknown) => geraetSetzen(name, w) } : null;
    }
    const z = server.amServer ? server.zeile(f) : null;
    return z ? { zeile: z, setzen: (w: unknown) => server.setzen(f, w) } : null;
  }).filter((z) => z !== null));
</script>

{#if zeilen.length}
  <div class="rh-e-zeilen">
    {#each zeilen as z (z.zeile.schluessel)}<Zeile zeile={z.zeile} onwert={z.setzen} />{/each}
  </div>
{/if}
