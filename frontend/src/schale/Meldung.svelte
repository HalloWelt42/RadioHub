<script lang="ts">
  // Meldung der App (appState.toast: Text und Art), schwebend über der Abspielleiste in der Form des Rückgängig-Bands
  // aus dem Entwurf; am Rechner und am Telefon dieselbe. Wie lange sie steht, regelt der Zustand (actions.showToast).
  import { appState } from "../lib/store.svelte.js";

  const SYMBOL: Record<string, string> = {
    success: "fa-circle-check", error: "fa-circle-exclamation", warning: "fa-triangle-exclamation", info: "fa-circle-info",
  };
  const meldung = $derived(appState.toast as { message: string; type?: string } | null);
</script>

{#if meldung}
  <div class="rh-band" class:gut={meldung.type === "success"} class:fehler={meldung.type === "error"} role="status" aria-live="polite">
    <i class="fa-solid {SYMBOL[meldung.type ?? 'info'] ?? SYMBOL.info}"></i><span>{meldung.message}</span>
  </div>
{/if}
