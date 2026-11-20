<script lang="ts">
  // Gestaltung D "Ruhig": große Uhr mit Sonnenband, rechts eine Spalte (ersetzt die bisherige Sonnen-Ansicht). Beim Klingeln
  // wird die rechte Spalte zu den Tasten, Wecker und Sender stehen unter der Uhr.
  import type { Gestaltungsprops } from "./typen";
  import Quellwahl from "./Quellwahl.svelte";
  import Ruhetasten from "./Ruhetasten.svelte";
  import Verbindungszeichen from "./Verbindungszeichen.svelte";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
  const anteil = (hhmm: string) => { const [h, m] = hhmm.split(":").map(Number); return ((h * 60 + m) / 1440) * 100; };
  const band = $derived(b.sonne ? { von: anteil(b.sonne.auf), bis: anteil(b.sonne.unter) } : null);
  const jetzt = $derived(((b.jetzt.getHours() * 60 + b.jetzt.getMinutes()) / 1440) * 100);
</script>

<div class="wa-ruhig">
  <div class="wa-links">
    <div class="wa-ziffern uhr-box" class:zucken={b.zucken} style:font-size={b.lage === "klingelt" ? "140px" : null}>{b.zeit}</div>
    {#if b.lage === "klingelt"}
      <div class="wa-info" style:flex-direction="row" style:justify-content="center" style:gap="24px" style:font-size="20px">
        <div class="wa-w"><i class="fa-solid fa-bell fa-shake"></i>{b.klingelZeit}</div><div><i class="fa-solid fa-radio"></i><b>{b.sender}</b></div></div>
    {:else}
      <div class="wa-band" style:--von="{band?.von ?? 0}%" style:--bis="{band?.bis ?? 0}%" style:--jetzt="{jetzt}%"></div>
    {/if}
  </div>
  {#if b.lage === "klingelt"}
    <div class="wa-knopfspalte">
      <button type="button" class="wa-gross-taste schlummern" onclick={p.tun.schlummern}><i class="fa-solid fa-bed"></i>{p.t("schlummern")}</button>
      <button type="button" class="wa-gross-taste aus" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("aus")}</button>
      <Quellwahl {...p} /></div>
  {:else}
    <div class="wa-info">
      <div><i class="fa-solid fa-radio"></i><b>{b.sender || "-"}</b><Verbindungszeichen verbindung={b.verbindung} /></div>
      {#if b.lage === "schlummert"}<div class="wa-w"><i class="fa-solid fa-bed"></i>{p.t("schlummertBis")} {b.schlummerBis}</div>
      {:else if b.naechster}<div class="wa-w"><i class="fa-solid fa-bell"></i>{b.naechster}</div>
      {:else}<div class="wa-leise"><i class="fa-solid fa-bell-slash"></i>{p.t("keinWeckerAktiv")}</div>{/if}
      {#if b.sonne}<div class="wa-leise"><i class="fa-solid fa-sun"></i>{b.sonne.auf} <i class="fa-solid fa-moon"></i>{b.sonne.unter}</div>{/if}
      {#if b.lage === "schlummert"}<button type="button" class="wa-gross-taste aus" style:min-height="54px" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("weckerAus")}</button>
      {:else}<Ruhetasten {...p} />{/if}
    </div>
  {/if}
</div>
