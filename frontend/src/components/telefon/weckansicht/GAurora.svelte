<script lang="ts">
  // Gestaltung G "Polarlicht": wabernde Farbschleier hinter einer großen, halb durchscheinenden Uhr, hell als Pastell.
  // Unten schwebende Glaspillen; beim Klingeln wogen die Farben schneller, unten Schlummern, Aus, Radio und Weckton.
  import type { Gestaltungsprops } from "./typen";
  import Ruhetasten from "./Ruhetasten.svelte";
  import Verbindungszeichen from "./Verbindungszeichen.svelte";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
</script>

<div class="wa-aurora" class:klingelt={b.lage === "klingelt"}>
  <div class="wa-licht" aria-hidden="true"></div>
  <div class="wa-zeit uhr-box" class:zucken={b.zucken}>{b.zeit}</div>
  {#if b.lage === "klingelt"}
    <div class="wa-stapel">
      <div class="wa-pillen"><span class="wa-pille wa-w"><i class="fa-solid fa-bell fa-shake"></i>{p.t("klingelt")} {b.klingelZeit}</span><span class="wa-pille"><i class="fa-solid fa-radio"></i>{b.sender}</span></div>
      <div class="wa-pillen">
        <button type="button" class="wa-pille gross voll" onclick={p.tun.schlummern}><i class="fa-solid fa-bed"></i>{p.t("schlummern")}</button>
        <button type="button" class="wa-pille gross" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("aus")}</button>
        <button type="button" class="wa-pille gross" class:voll={b.quelle === "radio"} aria-pressed={b.quelle === "radio"} aria-label={b.quelleName} onclick={() => p.tun.quelle("radio")}><i class="fa-solid fa-radio"></i></button>
        <button type="button" class="wa-pille gross" class:voll={b.quelle === "weckton"} aria-pressed={b.quelle === "weckton"} aria-label={p.t("weckton")} onclick={() => p.tun.quelle("weckton")}><i class="fa-solid fa-bell"></i></button>
      </div>
    </div>
  {:else}
    <div class="wa-pillen">
      <span class="wa-pille"><i class="fa-solid fa-radio"></i>{b.sender || "-"} <Verbindungszeichen verbindung={b.verbindung} /></span>
      {#if b.lage === "schlummert"}<span class="wa-pille wa-w"><i class="fa-solid fa-bed"></i>{p.t("schlummertBis")} {b.schlummerBis}</span>
        <button type="button" class="wa-pille" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("weckerAus")}</button>
      {:else}
        {#if b.naechster}<span class="wa-pille wa-w"><i class="fa-solid fa-bell"></i>{b.naechster}</span>{/if}
        {#if b.tastenSichtbar}<Ruhetasten {...p} klasse="wa-pille wa-rund-pille" />
        {:else if b.sonne}<span class="wa-pille"><i class="fa-solid fa-sun"></i>{b.sonne.auf} <i class="fa-solid fa-moon"></i>{b.sonne.unter}</span>{/if}
      {/if}
    </div>
  {/if}
</div>
