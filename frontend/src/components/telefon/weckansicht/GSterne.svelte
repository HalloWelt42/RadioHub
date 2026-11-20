<script lang="ts">
  // Gestaltung E "Sternenzeit": hell ein Morgenhimmel, dunkel der Sternenhimmel mit der Mondphase des Tages. Beim Klingeln
  // geht von unten die Sonne auf, rechts zwei leuchtende Kugeln (Schlummern, Aus), unter der Uhr die Quelle.
  import type { Gestaltungsprops } from "./typen";
  import Quellwahl from "./Quellwahl.svelte";
  import Ruhetasten from "./Ruhetasten.svelte";
  import Verbindungszeichen from "./Verbindungszeichen.svelte";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
  let himmel: HTMLCanvasElement | undefined = $state();

  // Sterne fest gesät (gleiche Lage bei jedem Zeichnen), nur dunkel und nachts
  $effect(() => {
    const c = himmel;
    if (!c || b.lage === "klingelt") return;
    const modus = b.modus;
    const malen = () => {
      const px = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
      c.width = w * px; c.height = h * px;
      const g = c.getContext("2d");
      if (!g) return;
      g.scale(px, px);
      if (modus === "hell") return;
      let s = 7;
      const zu = () => ((s = (s * 16807) % 2147483647) / 2147483647);
      for (let k = 0; k < 260; k++) {
        const r = zu() ** 3 * 1.8 + 0.3;
        g.beginPath(); g.arc(zu() * w, zu() * h, r, 0, Math.PI * 2);
        g.fillStyle = modus === "nacht" ? `rgba(220,40,24,${0.3 + zu() * 0.5})` : `rgba(${200 + zu() * 55},${210 + zu() * 45},255,${0.35 + zu() * 0.65})`;
        g.shadowColor = g.fillStyle; g.shadowBlur = r * 4; g.fill();
      }
    };
    malen();
    const beobachter = new ResizeObserver(malen);
    beobachter.observe(c);
    return () => beobachter.disconnect();
  });

  const phase = $derived(((((b.jetzt.getTime() - Date.UTC(2000, 0, 6, 18, 14)) / 86400000 / 29.530588) % 1) + 1) % 1);
  const mond = $derived.by(() => {
    const r = 44, zu = phase < 0.5, k = Math.cos(phase * 2 * Math.PI) * r;
    return { r, bogen: `M 50 ${50 - r} A ${r} ${r} 0 0 ${zu ? 1 : 0} 50 ${50 + r} A ${Math.abs(k)} ${r} 0 0 ${(k > 0) === zu ? 0 : 1} 50 ${50 - r}`,
      name: phase < 0.03 || phase > 0.97 ? "neumond" : phase < 0.47 ? "mondZunehmend" : phase < 0.53 ? "vollmond" : "mondAbnehmend" };
  });
</script>

<div class="wa-sterne" class:klingelt={b.lage === "klingelt"}>
  <canvas class="himmel" bind:this={himmel}></canvas>
  <div>
    <div class="wa-zeit uhr-box" class:zucken={b.zucken} style:font-size={b.lage === "klingelt" ? "124px" : null}>{b.zeit}</div>
    <div class="wa-unter">
      {#if b.lage === "klingelt"}<span class="wa-w"><i class="fa-solid fa-bell fa-shake"></i> {p.t("klingelt")} {b.klingelZeit}</span>
      {:else if b.lage === "schlummert"}<span class="wa-w"><i class="fa-solid fa-bed"></i> {p.t("schlummertBis")} {b.schlummerBis}</span>
      {:else if b.naechster}<span class="wa-w"><i class="fa-solid fa-bell"></i> {b.naechster}</span>{/if}
      <span><i class="fa-solid fa-radio"></i> {b.sender || "-"} <Verbindungszeichen verbindung={b.verbindung} /></span>
    </div>
    {#if b.lage === "klingelt"}<div class="wa-mittig"><Quellwahl {...p} /></div>{/if}
  </div>
  {#if b.lage === "klingelt"}
    <div class="wa-kugeln">
      <button type="button" class="wa-kugel sonne" onclick={p.tun.schlummern}><i class="fa-solid fa-bed"></i>{p.t("minutenKurz", { n: b.schlummerMinuten })}</button>
      <button type="button" class="wa-kugel still" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("aus")}</button>
    </div>
  {:else}
    <div class="wa-mond">
      <svg viewBox="0 0 100 100" width="96" height="96" aria-hidden="true"><circle cx="50" cy="50" r={mond.r} class="wa-mond-dunkel" /><path d={mond.bogen} class="wa-mond-hell" /></svg>
      <span>{p.t(mond.name)}</span>
      {#if b.sonne}<span><i class="fa-solid fa-sun"></i> {b.sonne.auf} <i class="fa-solid fa-moon"></i> {b.sonne.unter}</span>{/if}
      {#if b.lage === "schlummert"}<button type="button" class="wa-gross-taste aus" style:min-height="50px" style:font-size="17px" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("weckerAus")}</button>
      {:else}<Ruhetasten {...p} />{/if}
    </div>
  {/if}
</div>
