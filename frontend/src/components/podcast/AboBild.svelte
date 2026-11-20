<script lang="ts">
  // Bild eines Abos oder einer Folge über die eigene App; ohne Bild (oder wenn es nicht lädt) das Kürzel auf einer
  // Lackfläche wie die Senderlogos (gleicher Baustein rh-logo-bild).
  import { kuerzel, lack } from "../../lib/radio/anzeige";

  let { abo, bild, klein = false, gross = false }: { abo: { titel: string; bild: string }; bild?: string; klein?: boolean; gross?: boolean } = $props();
  let kaputt = $state<string | null>(null);
  // abgeleitet, nicht als Vorgabewert der Eigenschaft: der Kopf des Abos bleibt beim Wechsel derselbe Baustein und muss
  // dem neuen Abo folgen (sonst stand das Bild des vorigen da)
  const adresse = $derived(bild ?? abo.bild);
  const zeigen = $derived(adresse && kaputt !== adresse ? adresse : null);
</script>

<span class="rh-logo-bild" class:klein class:gross class:mit-bild={!!zeigen} style="--lack:{lack(abo.titel)}" aria-hidden="true">
  {#if zeigen}<img src={zeigen} alt="" loading="lazy" onerror={() => (kaputt = adresse)} />{:else}{kuerzel(abo.titel)}{/if}
</span>
