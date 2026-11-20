<script lang="ts">
  // Gestaltung H "Röhren": Ziffernröhren mit Glimmdraht (lib/telefon/nixie.js: Draht, ungeglühte Ziffern dahinter,
  // Anodengitter, plastischer Glaskolben, Kupferstifte), hell auf hellem Holz, dunkel auf dunklem. Beim Klingeln trägt der
  // Sockel Quelle, Schlummern und Aus; die Röhren bleiben frei.
  import type { Gestaltungsprops } from "./typen";
  import Quellwahl from "./Quellwahl.svelte";
  import Ruhetasten from "./Ruhetasten.svelte";
  import Verbindungszeichen from "./Verbindungszeichen.svelte";
  import { glimmpunkte, roehre } from "../../../lib/telefon/nixie.js";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
  const farbe = $derived(b.modus === "nacht" ? { glut: "#ff3a28", kern: "#ffb09a", kalt: "#3a1a14" } : { glut: "#ff7a1a", kern: "#ffe2b0", kalt: "#5a4a3c" });
  const ziffern = $derived(b.zeit.replace(":", "").split(""));
  const kennung = Math.random().toString(36).slice(2, 8);
</script>

<div class="wa-roehren">
  <div class="wa-reihe2 uhr-box" class:zucken={b.zucken} role="timer" aria-label={b.zeit}>
    {#each ziffern as z, i (i)}
      {#if i === 2}<div class="wa-glimm-feld">{@html glimmpunkte(farbe)}</div>{/if}
      <div class="wa-roehre-svg">{@html roehre(z, farbe, `${kennung}${i}`)}</div>
    {/each}
  </div>
  <div class="wa-sockel">
    {#if b.lage === "klingelt"}
      <span class="wa-w"><i class="fa-solid fa-bell fa-shake"></i> {b.klingelZeit}</span>
      <span class="wa-sockel-tasten"><Quellwahl {...p} />
        <button type="button" class="wa-hebel" onclick={p.tun.schlummern}><i class="fa-solid fa-bed"></i>{p.t("schlummern")}</button>
        <button type="button" class="wa-hebel voll" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("aus")}</button></span>
    {:else}
      <span><i class="fa-solid fa-radio"></i> {b.sender || "-"} <Verbindungszeichen verbindung={b.verbindung} /></span>
      <span class="wa-sockel-tasten">
        {#if b.lage === "schlummert"}<b><i class="fa-solid fa-bed"></i> {p.t("schlummertBis")} {b.schlummerBis}</b>
          <button type="button" class="wa-hebel voll" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("weckerAus")}</button>
        {:else}
          {#if b.naechster}<b><i class="fa-solid fa-bell"></i> {b.naechster}</b>{/if}
          {#if b.tastenSichtbar}<Ruhetasten {...p} klasse="wa-hebel wa-rund-hebel" />{/if}
        {/if}
      </span>
    {/if}
  </div>
</div>
