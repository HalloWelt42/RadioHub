<script lang="ts">
  // Zeichen der Verbindung neben dem Sender: verbindet (dreht), gestört (Warnung); ok und aus zeigen nichts.
  import type { Verbindung } from "./typen";
  let { verbindung }: { verbindung: Verbindung } = $props();
</script>

{#if verbindung === "verbindet"}<i class="fa-solid fa-rotate fa-spin" aria-label="verbindet"></i>
{:else if verbindung === "gestoert"}<i class="fa-solid fa-triangle-exclamation wa-w" aria-label="gestört"></i>{/if}
