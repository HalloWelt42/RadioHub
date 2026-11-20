<script lang="ts">
  // Bild eines Abos oder einer Folge über die eigene App; ohne Bild (oder wenn es nicht lädt) das Kürzel auf einer
  // Lackfläche wie die Senderlogos (gleicher Baustein rh-logo-bild).
  import { kuerzel, lack } from "../../lib/radio/anzeige";

  let { abo, bild = abo.bild, klein = false, gross = false }: { abo: { titel: string; bild: string }; bild?: string; klein?: boolean; gross?: boolean } = $props();
  let kaputt = $state<string | null>(null);
  const zeigen = $derived(bild && kaputt !== bild ? bild : null);
</script>

<span class="rh-logo-bild" class:klein class:gross class:mit-bild={!!zeigen} style="--lack:{lack(abo.titel)}" aria-hidden="true">
  {#if zeigen}<img src={zeigen} alt="" loading="lazy" onerror={() => (kaputt = bild)} />{:else}{kuerzel(abo.titel)}{/if}
</span>
