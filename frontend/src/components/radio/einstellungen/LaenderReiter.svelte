<script lang="ts">
  // Reiter Länder der Seitenleiste (Entwurf regeln.html, Entscheidung 6): legt nur fest, welche Länder in der
  // Seitenleiste als Schnellfilter stehen; blendet nie Sender aus. Ohne Wahl stehen dort alle Länder. Jede Änderung gilt
  // sofort (kurz gesammelt gespeichert).
  import { onMount } from "svelte";
  import { t } from "../../../lib/i18n.svelte.js";
  import { actions } from "../../../lib/store.svelte.js";
  import { senderquelle } from "../../../lib/radio";
  import { landName, zahl } from "../../../lib/radio/anzeige";
  import type { LandZahl } from "../../../lib/radio/quelle";

  let alle = $state<LandZahl[]>([]);
  let gewaehlt = $state<string[]>([]);
  let suche = $state("");
  let geladen = $state(false);

  onMount(() => {
    void Promise.all([senderquelle.laender(), senderquelle.laenderLeiste()]).then(([l, g]) => {
      alle = l;
      gewaehlt = g;
      geladen = true;
    }).catch((f: Error) => actions.showToast(f.message, "error"));
  });

  const liste = $derived.by(() => {
    const q = suche.trim().toLowerCase();
    return alle.filter((l) => !q || landName(l.code, l.name).toLowerCase().includes(q) || l.name.toLowerCase().includes(q) || l.code.toLowerCase() === q)
      .sort((a, b) => b.anzahl - a.anzahl);
  });

  let uhr: ReturnType<typeof setTimeout> | undefined;
  function speichern(neu: string[]) {
    gewaehlt = neu;
    clearTimeout(uhr);
    uhr = setTimeout(() => senderquelle.laenderLeisteSetzen(neu).catch((f: Error) => actions.showToast(f.message, "error")), 400);
  }
</script>

<section class="rh-reiter">
  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-earth-europe"></i>{t("radio.einst.reiter.laender")}</h2></div>
    <p class="hinweis-band"><i class="fa-solid fa-circle-info"></i><span>{t("radio.einst.laenderHinweis")} <b>{t("radio.einst.laenderKeinAusblenden")}</b></span></p>
    <div class="rh-l-werkzeug">
      <label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i>
        <input bind:value={suche} type="search" name="land-suche" placeholder={t("radio.einst.landSuchen")} aria-label={t("radio.einst.landSuchen")} autocomplete="off" /></label>
      <span class="rh-still">{#if gewaehlt.length}<b class="rh-zahl">{gewaehlt.length}</b> {t("radio.einst.gewaehltSortiert")}{:else}{t("radio.einst.ohneWahlAlle")}{/if}</span>
      <button class="knopf" type="button" disabled={!gewaehlt.length} onclick={() => speichern([])}><i class="fa-solid fa-xmark"></i>{t("radio.einst.auswahlLeeren")}</button>
    </div>
    {#if !geladen}<p class="rh-still">{t("radio.laedt")}</p>{/if}
    <div class="rh-laender">
      {#each liste as l (l.code)}
        <label class="rh-facette"><input type="checkbox" checked={gewaehlt.includes(l.code)}
               onchange={() => speichern(gewaehlt.includes(l.code) ? gewaehlt.filter((c) => c !== l.code) : [...gewaehlt, l.code])} />
          <span class="rh-kennung">{l.code}</span><span>{landName(l.code, l.name)}</span><span class="rh-zahl">{zahl(l.anzahl)}</span></label>
      {/each}
    </div>
  </div>
</section>
