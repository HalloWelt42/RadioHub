<script lang="ts">
  // Modul Quelle und Zeit: Quelle in 14 Segmenten (Farbe nach Zustand), Zeit in 7 Segmenten; darunter im Zeitversatz
  // 30 Sekunden zurück, Puffer, 30 Sekunden vor und Live, bei Folgen und Aufnahmen 10 Sekunden zurück, Position und 10
  // Sekunden vor. Gilt keins von beiden, steht die Zeile des Zeitversatzes gesperrt da (sie verschwindet nie).
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import Spulzeile from "./Spulzeile.svelte";
  import { live, spulen } from "./aktionen";
  import { positionStand, SPUL_RUHE, zeitversatzStand, type Anzeige, type Stand } from "./kanzel";
  import type { Wiedergabe } from "./wiedergabe.svelte";

  let { anzeige, stand, wiedergabe }: { anzeige: Anzeige; stand: Stand; wiedergabe: Wiedergabe } = $props();

  const ruht = $derived(anzeige.zeile === null);
  const versatz = $derived(anzeige.zeile === "zeitversatz" ? zeitversatzStand(stand, t) : ruht ? SPUL_RUHE : null);
  const position = $derived(anzeige.zeile === "position" ? positionStand(stand, t) : null);
  const spulenGesperrt = $derived(stand.isRecording || anzeige.zustand === "laedt" || anzeige.zustand === "fehler");
</script>

<section class="rh-modul rh-m-zeit" aria-label={t("kanzel.quelleUndZeit")}><span class="ak-etikett">{t("kanzel.quelleUndZeit")}</span>
  <div class="rh-zeit">
    <div class="ak-glas rh-zeit-glas">
      <ak-segmente class="rh-zeit-quelle" art="14" stellen="7" text={anzeige.quelle.text} hilfe={t("kanzel.quelleHilfe")}
        style:--farbe="var(--led-{anzeige.quelle.farbe})"></ak-segmente>
      <ak-segmente class="rh-zeit-uhr" art="7" stellen="7" farbe="gruen" text={anzeige.zeit} hilfe={t("kanzel.zeitHilfe")}></ak-segmente>
    </div>
    {#if versatz}
      <Spulzeile stand={versatz} {wiedergabe} hilfe={t("kanzel.pufferHilfe", { max: versatz.max })}>
        {#snippet links()}
          <button class="knopf" type="button" title={t("kanzel.zurueck30Hilfe")} aria-label={t("kanzel.zurueck30Hilfe")} disabled={spulenGesperrt || versatz.gesperrt}
            onmouseenter={sfx.hover} onclick={() => { spulen(-30); sfx.click(); }}><i class="fa-solid fa-rotate-left"></i>{t("kanzel.sekunden30")}</button>
        {/snippet}
        {#snippet rechts()}
          <span class="rh-puffer-rechts">
            <button class="knopf" type="button" title={t("kanzel.vor30Hilfe")} aria-label={t("kanzel.vor30Hilfe")} disabled={spulenGesperrt || versatz.gesperrt || versatz.live}
              onmouseenter={sfx.hover} onclick={() => { spulen(30); sfx.click(); }}><i class="fa-solid fa-rotate-right"></i>{t("kanzel.sekunden30")}</button>
            <button class="knopf" type="button" title={versatz.live ? t("player.bereitsLive") : t("player.goLive")} disabled={ruht || versatz.live || stand.isRecording}
              onmouseenter={sfx.hover} onclick={() => { live(); sfx.click(); }}><i class="fa-solid fa-tower-broadcast"></i>{t("kanzel.live")}</button>
          </span>
        {/snippet}
      </Spulzeile>
    {:else if position}
      <Spulzeile stand={position} {wiedergabe} hilfe={t("kanzel.positionHilfe")}>
        {#snippet links()}
          <button class="knopf" type="button" title={t("player.skipBack")} aria-label={t("player.skipBack")} disabled={spulenGesperrt || position.gesperrt}
            onmouseenter={sfx.hover} onclick={() => { spulen(-10); sfx.click(); }}><i class="fa-solid fa-rotate-left"></i>10 s</button>
        {/snippet}
        {#snippet rechts()}
          <button class="knopf" type="button" title={t("player.skipForward")} aria-label={t("player.skipForward")} disabled={spulenGesperrt || position.gesperrt}
            onmouseenter={sfx.hover} onclick={() => { spulen(10); sfx.click(); }}><i class="fa-solid fa-rotate-right"></i>10 s</button>
        {/snippet}
      </Spulzeile>
    {/if}
  </div>
</section>
