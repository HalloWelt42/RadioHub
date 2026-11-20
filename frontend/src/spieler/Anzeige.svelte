<script lang="ts">
  // Modul Anzeige: das Glas zeigt nur an (Nutzer 17.11.2026: keine Bedienelemente im Glas). Statuszeile (Leuchte, was
  // geschieht, Codec und Bitrate, Hinweis), Punktmatrix mit dem Sender und die Titelzeile, nur mit Titel. Die Matrix hat
  // so viele Stellen, wie ihre Breite trägt (rasterbreite.ts), läuft über ihr Merkmal lauf, wenn der Name länger ist, und
  // führt zur Quelle. Der Hinweis rechts ist Leuchtschrift: Wechsel gesperrt während der Aufnahme, sonst die Bitrate des
  // Zeitversatzes (gewählt wird sie in der Steuerung).
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import { zurQuelle } from "./aktionen";
  import type { Anzeige } from "./kanzel";
  import { rasterStellen } from "./rasterbreite";

  let { anzeige, hinweis, aufnahme }: {
    anzeige: Anzeige;
    /** Leuchtschrift rechts in der Statuszeile (Bitrate des Zeitversatzes), oder keine */
    hinweis: string | null;
    /** eine Aufnahme läuft (Sprung zum aufnehmenden Sender) */
    aufnahme: boolean;
  } = $props();

  let stellen = $state(16);
  const quelleHilfe = $derived(aufnahme ? t("player.zumSender") : t("player.zurQuelle"));
</script>

<section class="rh-modul rh-m-anzeige" aria-label={t("kanzel.anzeige")}><span class="ak-etikett">{t("kanzel.anzeige")}</span>
  <div class="ak-glas rh-display" data-ton={anzeige.ton}>
    <div class="rh-display-zeile">
      <ak-led farbe={anzeige.led.farbe} zustand={anzeige.led.zustand} groesse="klein"></ak-led>
      <span>{anzeige.art}</span>
      {#if anzeige.format}<span class="rh-display-format">{anzeige.format}</span>{/if}
      {#if anzeige.zustand === "aufnahme"}
        <span class="rh-display-hinweis" title={t("kanzel.wechselGesperrtHilfe")}><ak-led farbe="bernstein" zustand="an" groesse="klein"></ak-led>{t("kanzel.wechselGesperrt")}</span>
      {:else if hinweis}
        <span class="rh-display-hinweis" title={t("kanzel.bitrate")}>{hinweis}</span>
      {/if}
    </div>
    <button class="rh-display-quelle" type="button" disabled={!anzeige.sender} title={anzeige.sender ? quelleHilfe : undefined}
      aria-label={anzeige.sender ? `${anzeige.sender}: ${quelleHilfe}` : t("kanzel.senderHilfe")}
      onclick={() => { zurQuelle(); sfx.click(); }} use:rasterStellen={(n) => (stellen = n)}>
      <!-- der Appkern liest die Stellen beim Einhängen: neue Stellenzahl, neue Anzeige (nur wenn sich die Breite ändert) -->
      {#key stellen}<ak-segmente art="punkt" {stellen} lauf="280" farbe="gruen" text={anzeige.sender}></ak-segmente>{/key}
    </button>
    {#if anzeige.titel}<div class="rh-display-titel" title={anzeige.titel}>{anzeige.titel}</div>{/if}
  </div>
</section>
