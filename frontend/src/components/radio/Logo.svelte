<script lang="ts">
  // Senderlogo: das Bild aus dem Zwischenspeicher des Backends, ohne Bild (oder wenn es nicht lädt) das Kürzel auf einer
  // Lackfläche wie im Entwurf.
  import { kuerzel, lack } from "../../lib/radio/anzeige";
  import { senderquelle } from "../../lib/radio";

  let { uuid, name, logo, klein = false }: { uuid: string; name: string; logo: string; klein?: boolean } = $props();

  let kaputt = $state<string | null>(null);
  const bild = $derived(kaputt === uuid ? null : senderquelle.logoAdresse(uuid, logo));

  function geladen(e: Event) {
    if ((e.currentTarget as HTMLImageElement).naturalWidth < 4) kaputt = uuid;   // leere Bildchen der Verzeichnisse
  }
</script>

<span class="rh-logo-bild" class:klein class:mit-bild={!!bild} style="--lack:{lack(name)}" aria-hidden="true">
  {#if bild}<img src={bild} alt="" loading="lazy" onerror={() => (kaputt = uuid)} onload={geladen} />{:else}{kuerzel(name)}{/if}
</span>
