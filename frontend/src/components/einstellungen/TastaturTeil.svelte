<script lang="ts">
  // Einstellungen > Allgemein > Tastatur (RAD-11): aus der wirksamen Belegung (schale/tastatur.ts, TASTEN), nicht von Hand.
  import { t } from "../../lib/i18n.svelte.js";
  import { TASTEN } from "../../schale/tastatur";
  import Karte from "./Karte.svelte";

  let { bereiche }: { bereiche: number } = $props();
  const name = (taste: string) => (taste === " " ? t("einstellungen.tastatur.taste_leer") : taste.startsWith("Arrow") ? t(`einstellungen.tastatur.taste_${taste}`) : taste.toUpperCase());
</script>

<Karte titel={t("einstellungen.tastatur.titel")} symbol="fa-keyboard" still={t("einstellungen.tastatur.hilfe")}>
  <div class="rh-tasten">
    <section><h3>{t("einstellungen.tastatur.wiedergabe")}</h3>
      <dl>{#each TASTEN as taste (taste.name)}
        <dt>{#each taste.tasten as k (k)}<kbd>{name(k)}</kbd>{/each}</dt>
        <dd>{t(`einstellungen.tastatur.${taste.name}`)}{#if taste.gesperrtBeiAufnahme} <span class="rh-still">({t("einstellungen.tastatur.gesperrt")})</span>{/if}</dd>
      {/each}</dl></section>
    <section><h3>{t("einstellungen.tastatur.bereiche")}</h3>
      <dl><dt><kbd>{t("einstellungen.tastatur.taste_ziffern", { n: bereiche })}</kbd></dt><dd>{t("einstellungen.tastatur.ziffern")}</dd></dl></section>
  </div>
</Karte>
