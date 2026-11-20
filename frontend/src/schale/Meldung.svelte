<script lang="ts">
  // Meldung der App (appState.toast: Text und Art), schwebend über der Abspielleiste in der Form des Rückgängig-Bands
  // aus dem Entwurf; am Rechner und am Telefon dieselbe. Wie lange sie steht, regelt der Zustand (actions.showToast).
  // Ohne Meldung steht dort der Hinweis auf eine neue Fassung (RAD-20): neu laden nur auf Wunsch, oder später.
  import { appState } from "../lib/store.svelte.js";
  import { t } from "../lib/i18n.svelte.js";
  import { aktualisierung, neuLaden, spaeter } from "../lib/aktualisierung.svelte.js";

  const SYMBOL: Record<string, string> = {
    success: "fa-circle-check", error: "fa-circle-exclamation", warning: "fa-triangle-exclamation", info: "fa-circle-info",
  };
  const meldung = $derived(appState.toast as { message: string; type?: string } | null);
</script>

{#if meldung}
  <div class="rh-band" class:gut={meldung.type === "success"} class:fehler={meldung.type === "error"} role="status" aria-live="polite">
    <i class="fa-solid {SYMBOL[meldung.type ?? 'info'] ?? SYMBOL.info}"></i><span>{meldung.message}</span>
  </div>
{:else if aktualisierung.neu && !aktualisierung.spaeter}
  <div class="rh-band" role="status" aria-live="polite">
    <i class="fa-solid fa-rotate"></i><span>{t("schale.neueFassung")}</span>
    <button class="knopf primaer" type="button" onclick={neuLaden}><i class="fa-solid fa-rotate"></i>{t("schale.neuLaden")}</button>
    <button class="knopf still" type="button" onclick={spaeter}>{t("schale.spaeter")}</button>
  </div>
{/if}
