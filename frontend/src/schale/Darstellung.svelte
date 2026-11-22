<script lang="ts">
  // Darstellung dieses Geräts: Vorlage (alle Vorlagen des Appkerns, HiFi als Vorgabe), Thema (Hell, Dunkel, System) und
  // Schrift in Stufen; gilt sofort und bleibt im Browser. Inhalt der Tafel im Kopf (Rechner) und der Einstellungen am
  // Telefon; Aufbau wie im Entwurf (mockups/radio-filter, Tafel Darstellung).
  import { Auswahl } from "appkern-oberflaeche";
  import { ANGEBOTENE_VORLAGEN, darstellung, darstellungSetzen, schriftAmRand, schriftSchritt } from "../lib/darstellung.svelte";
  import { t } from "../lib/i18n.svelte.js";
  import { SPRACHEN, spracheDanach, spracheJetzt, spracheWaehlen } from "../lib/sprache.svelte";
  import Flagge from "./Flagge.svelte";

  const sprache = $derived(spracheJetzt());
  const naechste = $derived(spracheDanach());

  const THEMEN = [["hell", "fa-sun"], ["dunkel", "fa-moon"], ["system", "fa-display"]] as const;
  const vorlagen = ANGEBOTENE_VORLAGEN.map((v) => ({ wert: v.id, titel: v.name, hinweis: v.text }));
  const symbol = $derived(ANGEBOTENE_VORLAGEN.find((v) => v.id === darstellung.vorlage)?.symbol ?? "fa-swatchbook");
</script>

{#if SPRACHEN.length > 1}
  <!-- Sprache (RAD-90): ein Tippen schaltet zur nächsten vollständig übersetzten, gilt für alle Geräte -->
  <div class="rh-wahl">
    <h3>{t("schale.sprache")}</h3>
    <button class="knopf rh-sprachwahl" type="button" title={t("schale.spracheWechsel", { jetzt: sprache.label, danach: naechste.label })}
            onclick={() => void spracheWaehlen(naechste.code)}><Flagge sprache={sprache.code} />{sprache.label}</button>
  </div>
{/if}
<div class="rh-wahl">
  <h3>{t("schale.vorlage")}</h3>
  <Auswahl wert={darstellung.vorlage} optionen={vorlagen} {symbol} titel={t("schale.vorlage")}
           onwahl={(v) => darstellungSetzen({ vorlage: v })} />
</div>
<div class="rh-wahl">
  <h3>{t("schale.thema")}</h3>
  <div class="segment" role="group" aria-label={t("schale.thema")}>
    {#each THEMEN as [thema, zeichen] (thema)}
      <button type="button" class:aktiv={darstellung.thema === thema} aria-pressed={darstellung.thema === thema}
              onclick={() => darstellungSetzen({ thema })}><i class="fa-solid {zeichen}"></i>{t(`schale.thema_${thema}`)}</button>
    {/each}
  </div>
</div>
<div class="rh-wahl">
  <h3>{t("schale.schrift")}</h3>
  <div class="rh-schrift-wahl">
    <button class="knopf" type="button" aria-label={t("schale.kleiner")} title={t("schale.kleiner")} disabled={schriftAmRand(-1)}
            onclick={() => schriftSchritt(-1)}><i class="fa-solid fa-minus"></i></button>
    <output aria-live="polite">{t(`schale.schrift_${darstellung.schrift}`)}</output>
    <button class="knopf" type="button" aria-label={t("schale.groesser")} title={t("schale.groesser")} disabled={schriftAmRand(1)}
            onclick={() => schriftSchritt(1)}><i class="fa-solid fa-plus"></i></button>
  </div>
</div>
