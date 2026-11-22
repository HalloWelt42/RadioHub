<script lang="ts">
  // Sprachwahl als Aufklappliste mit Flaggen (RAD-99, Nutzer: "als dropdown, nicht rotierend"): im Kopf am Rechner ein
  // runder Knopf mit der Flagge, am Telefon (Darstellung) ein breiter Knopf mit Flagge und Namen. Die Liste zeigt alle
  // angebotenen Sprachen in ihrem eigenen Namen; schließt bei Klick daneben, mit Escape und nach der Wahl. Gewählt wird
  // über lib/sprache (gilt sofort, mit Server für alle Geräte).
  import { t } from "../lib/i18n.svelte.js";
  import { SPRACHEN, spracheJetzt, spracheWaehlen } from "../lib/sprache.svelte";
  import Flagge from "./Flagge.svelte";

  let { breit = false }: { breit?: boolean } = $props();
  const jetzt = $derived(spracheJetzt());
  let offen = $state(false);
  let wurzel: HTMLElement;

  function waehlen(code: string) {
    offen = false;
    void spracheWaehlen(code);
  }

  function draussen(e: MouseEvent) {
    if (offen && wurzel && !wurzel.contains(e.target as Node)) offen = false;
  }
</script>

<svelte:window onclick={draussen} onkeydown={(e) => e.key === "Escape" && (offen = false)} />

<span class="rh-sprachwahl-feld" class:breit bind:this={wurzel}>
  {#if breit}
    <button class="knopf rh-sprachwahl" type="button" aria-haspopup="listbox" aria-expanded={offen} title={t("schale.sprache")}
            onclick={() => (offen = !offen)}><Flagge sprache={jetzt.code} />{jetzt.label}<i class="fa-solid fa-chevron-down rh-sprachwahl-pfeil"></i></button>
  {:else}
    <button class="rund" type="button" aria-haspopup="listbox" aria-expanded={offen} title={`${t("schale.sprache")}: ${jetzt.label}`}
            aria-label={`${t("schale.sprache")}: ${jetzt.label}`} onclick={() => (offen = !offen)}><Flagge sprache={jetzt.code} /></button>
  {/if}
  {#if offen}
    <span class="rh-sprachliste" role="listbox" aria-label={t("schale.sprache")}>
      {#each SPRACHEN as s (s.code)}
        <button type="button" role="option" aria-selected={s.code === jetzt.code} class:aktiv={s.code === jetzt.code}
                lang={s.code} onclick={() => waehlen(s.code)}><Flagge sprache={s.code} />{s.label}</button>
      {/each}
    </span>
  {/if}
</span>
