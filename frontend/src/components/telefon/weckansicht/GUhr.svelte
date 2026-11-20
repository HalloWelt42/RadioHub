<script lang="ts">
  // Gestaltung "Uhr vollflächig" (die bisherige): die Uhr über die ganze Fläche, unten eine schmale Leiste; die Tasten
  // erscheinen nach Antippen in der Leiste. Beim Klingeln wird die Uhr kleiner, unten Quelle, Schlummern und Aus.
  import type { Gestaltungsprops } from "./typen";
  import Quellwahl from "./Quellwahl.svelte";
  import Ruhetasten from "./Ruhetasten.svelte";
  import Verbindungszeichen from "./Verbindungszeichen.svelte";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
</script>

<div class="wa-u-flaeche">
  <div class="wa-u-uhr uhr-box" class:zucken={b.zucken} style:font-size={b.lage === "klingelt" ? "160px" : null}>{b.zeit}</div>
  {#if b.lage === "klingelt"}
    <div class="wa-u-klingeln"><Quellwahl {...p} />
      <button type="button" class="wa-gross-taste schlummern" onclick={p.tun.schlummern}><i class="fa-solid fa-bed"></i>{p.t("schlummern")}</button>
      <button type="button" class="wa-gross-taste aus" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("aus")}</button></div>
  {:else}
    <div class="wa-u-leiste">
      <span><i class="fa-solid fa-radio"></i> {b.sender || "-"} <Verbindungszeichen verbindung={b.verbindung} /></span>
      {#if b.lage === "schlummert"}<span class="wa-w"><i class="fa-solid fa-bed"></i> {p.t("schlummertBis")} {b.schlummerBis}</span>
      {:else if b.naechster}<span class="wa-w"><i class="fa-solid fa-bell"></i> {b.naechster}</span>
      {:else}<span aria-label={p.t("keinWeckerAktiv")}><i class="fa-solid fa-bell-slash"></i></span>{/if}
      {#if b.lage === "schlummert"}<button type="button" class="wa-gross-taste aus" style:min-height="48px" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("weckerAus")}</button>
      {:else if b.tastenSichtbar}<Ruhetasten {...p} />
      {:else if b.sonne}<span><i class="fa-solid fa-sun"></i> {b.sonne.auf} <i class="fa-solid fa-moon"></i> {b.sonne.unter}</span>{/if}
    </div>
  {/if}
</div>
