<script lang="ts">
  // Rückgängig-Band (Entwurf rechner.html und regeln.html): schwebt unten über der Abspielleiste, meldet eine Änderung und
  // bietet Rückgängig und einen Verweis; schließt nach zwölf Sekunden von selbst oder mit dem Knopf.
  import { t } from "../../lib/i18n.svelte.js";
  import type { BandInhalt } from "../../lib/radio/bedienung.svelte";
  import { actions } from "../../lib/store.svelte.js";

  let { inhalt = $bindable() }: { inhalt: BandInhalt | null } = $props();
  const STEHT_MS = 12_000;
  let arbeitet = $state(false);

  $effect(() => {
    if (!inhalt) return;
    const uhr = setTimeout(() => (inhalt = null), STEHT_MS);
    return () => clearTimeout(uhr);
  });

  async function zurueck() {
    const arbeit = inhalt?.rueckgaengig;
    if (!arbeit || arbeitet) return;
    arbeitet = true;
    try {
      await arbeit();
      inhalt = null;
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    } finally {
      arbeitet = false;
    }
  }
</script>

{#if inhalt}
  <div class="rh-band" class:gut={inhalt.art === "gut"} class:fehler={inhalt.art === "fehler"} role="status" aria-live="polite">
    <i class="fa-solid {inhalt.symbol}"></i>
    <span>{#if inhalt.name}<b>{inhalt.name}</b>{" "}{/if}{inhalt.text}</span>
    {#if inhalt.rueckgaengig}
      <button class="knopf primaer" type="button" disabled={arbeitet} onclick={zurueck}><i class="fa-solid fa-rotate-left"></i>{t("radio.rueckgaengig")}</button>
    {/if}
    {#if inhalt.verweis}
      {@const v = inhalt.verweis}
      <!-- den Verweis vor dem Schließen festhalten: danach gibt es den Inhalt (und damit v) nicht mehr -->
      {#if "pfad" in v}
        <a class="knopf still" href={v.pfad} onclick={(e) => { e.preventDefault(); const pfad = v.pfad; inhalt = null; actions.navigateTo(pfad); }}>{v.text}</a>
      {:else}
        <button class="knopf still" type="button" onclick={() => { const aktion = v.aktion; inhalt = null; aktion(); }}>{v.text}</button>
      {/if}
    {/if}
    <button class="rund rh-band-zu" type="button" aria-label={t("radio.schliessen")} title={t("radio.schliessen")} onclick={() => (inhalt = null)}>
      <i class="fa-solid fa-xmark"></i></button>
  </div>
{/if}
