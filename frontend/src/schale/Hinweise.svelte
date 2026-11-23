<script lang="ts">
  // Datenschutz und Herkunft der Sender (RAD-120, RAD-123): runder Knopf oben, am Rechner im Kopf und am Telefon neben den
  // Einstellungen, immer erreichbar. Er öffnet ein Fenster über allem (dialog des Browsers: Escape, Fokus und Hintergrund
  // sind damit geregelt). Ohne Hinweise in der Ausgabe gibt es den Knopf nicht (PRO).
  import { t, currentLanguage } from "../lib/i18n.svelte.js";
  import { rechtstexte } from "../lib/rechtstexte";
  import { EINSTELLUNGEN } from "$ziel/einstellungen";

  const HINWEISE: readonly string[] = EINSTELLUNGEN.hinweise;
  let fenster: HTMLDialogElement | undefined = $state();
  let offen = $state(false);
  let inhalt = $state<string | null>(null);

  function oeffnen() {
    offen = true;
    fenster?.showModal();
  }

  $effect(() => {
    void t("schale.hinweise");          // folgt dem Sprachwechsel
    const sprache = currentLanguage() || "de";
    if (!offen) return;
    let gilt = true;
    void rechtstexte(HINWEISE, sprache).then((html) => { if (gilt) inhalt = html; });
    return () => { gilt = false; };
  });
</script>

{#if HINWEISE.length}
  <button class="rund" type="button" title={t("schale.hinweise")} aria-label={t("schale.hinweise")} aria-haspopup="dialog"
          onclick={oeffnen}><i class="fa-solid fa-shield-halved"></i></button>
  <dialog class="rh-hinweise" bind:this={fenster} aria-label={t("schale.hinweise")} onclose={() => (offen = false)}
          onkeydown={(e) => e.stopPropagation()} onclick={(e) => { if (e.target === fenster) fenster?.close(); }}>
    <div class="rh-hinweise-blatt">
      <div class="rh-hinweise-kopf"><h2><i class="fa-solid fa-shield-halved"></i>{t("schale.hinweise")}</h2>
        <button class="rund" type="button" title={t("schale.schliessen")} aria-label={t("schale.schliessen")} onclick={() => fenster?.close()}><i class="fa-solid fa-xmark"></i></button></div>
      <div class="rh-hinweise-text">
        {#if inhalt}<div class="rh-md">{@html inhalt}</div>
        {:else if inhalt === ""}<p class="rh-still">{t("einstellungen.ueber.fehlt")}</p>
        {:else}<p class="rh-still"><i class="fa-solid fa-spinner fa-spin"></i> {t("schale.laedt")}</p>{/if}
      </div>
    </div>
  </dialog>
{/if}
