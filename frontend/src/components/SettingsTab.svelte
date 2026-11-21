<script lang="ts">
  // Einstellungen der vollen App (RAD-11): die Seite nach dem Entwurf; die Zahl der Bereiche oben braucht die Tastatur.
  import EinstellungenSeite from "./einstellungen/EinstellungenSeite.svelte";

  let { bereichszahl }: { bereichszahl: number } = $props();
</script>

<EinstellungenSeite {bereichszahl} />
