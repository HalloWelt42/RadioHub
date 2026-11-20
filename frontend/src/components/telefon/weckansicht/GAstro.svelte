<script lang="ts">
  // Gestaltung F "Astrolabium": der äußere Ring ist der ganze Tag (0 oben, 12 unten), der Bogen die Zeit zwischen Sonnenauf-
  // und -untergang, der helle Punkt der Wecker, innen die Minuten. Hell auf Pergament, dunkel in Gold auf Indigo. Beim
  // Klingeln pulsiert der Ring, rechts Siegel und die Quelle.
  import type { Gestaltungsprops } from "./typen";
  import Quellwahl from "./Quellwahl.svelte";
  import Ruhetasten from "./Ruhetasten.svelte";
  import Verbindungszeichen from "./Verbindungszeichen.svelte";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
  const pkt = (st: number, r: number) => { const a = (st / 24) * 2 * Math.PI - Math.PI / 2; return [181 + Math.cos(a) * r, 181 + Math.sin(a) * r]; };
  const std = (t: string | null) => { if (!t) return 0; const [h, m] = t.split(":").map(Number); return h + m / 60; };
  const STUNDEN = Array.from({ length: 24 }, (_, s) => s);
  const MINUTEN = Array.from({ length: 60 }, (_, m) => m);
  const minute = $derived(Number(b.zeit.split(":")[1]));
  const bogen = $derived.by(() => {
    if (!b.sonne) return null;
    const [ax, ay] = pkt(std(b.sonne.auf), 160), [ux, uy] = pkt(std(b.sonne.unter), 160);
    return `M ${ax} ${ay} A 160 160 0 ${std(b.sonne.unter) - std(b.sonne.auf) > 12 ? 1 : 0} 1 ${ux} ${uy}`;
  });
  const zeiger = $derived(pkt(std(b.zeit), 166));
  const weckpunkt = $derived(b.lage === "schlummert" ? pkt(std(b.schlummerBis), 160) : b.lage === "klingelt" ? pkt(std(b.klingelZeit), 160)
    : b.naechster ? pkt(std(b.naechster.slice(-5)), 160) : null);
  const datum = $derived(b.jetzt.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "long" }).toUpperCase());
</script>

<div class="wa-astro" class:klingelt={b.lage === "klingelt"}>
  <svg viewBox="0 0 362 362" class="uhr-box" class:zucken={b.zucken} role="timer" aria-label={b.zeit}>
    <circle cx="181" cy="181" r="174" fill="none" stroke="currentColor" opacity=".5" />
    <circle class="wa-puls" cx="181" cy="181" r="160" fill="none" stroke="currentColor" opacity=".35" />
    {#if bogen}<path d={bogen} class="wa-tagbogen" />{/if}
    {#each STUNDEN as s (s)}
      {@const [x1, y1] = pkt(s, s % 3 ? 150 : 144)}{@const [x2, y2] = pkt(s, 156)}
      <line {x1} {y1} {x2} {y2} stroke="currentColor" stroke-width={s % 3 ? 1 : 2} />
      {#if s % 3 === 0}{@const [tx, ty] = pkt(s, 130)}<text class="wa-klein" x={tx} y={ty + 4}>{s}</text>{/if}
    {/each}
    {#each MINUTEN as m (m)}
      {@const a = (m / 60) * 2 * Math.PI - Math.PI / 2}{@const r1 = m === minute ? 92 : 100}
      <line x1={181 + Math.cos(a) * r1} y1={181 + Math.sin(a) * r1} x2={181 + Math.cos(a) * 106} y2={181 + Math.sin(a) * 106}
        stroke="currentColor" stroke-width={m === minute ? 3 : 1} opacity={m === minute ? 1 : 0.45} />
    {/each}
    {#if weckpunkt}<circle class="wa-puls wa-weckpunkt" cx={weckpunkt[0]} cy={weckpunkt[1]} r={b.lage === "klingelt" ? 11 : 8} />{/if}
    <line x1="181" y1="181" x2={zeiger[0]} y2={zeiger[1]} stroke="currentColor" stroke-width="2" opacity=".6" />
    <circle cx={zeiger[0]} cy={zeiger[1]} r="5" fill="currentColor" />
    <text class="wa-zahl" x="181" y="204">{b.zeit}</text><text class="wa-klein" x="181" y="232">{datum}</text>
  </svg>
  <div class="wa-seite">
    {#if b.lage === "klingelt"}
      <span class="wa-w"><i class="fa-solid fa-bell fa-shake"></i> {b.klingelZeit}</span><span>{b.sender}</span>
      <button type="button" class="wa-siegel voll" onclick={p.tun.schlummern}><i class="fa-solid fa-bed"></i>{p.t("schlummern")}</button>
      <button type="button" class="wa-siegel" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("aus")}</button>
      <Quellwahl {...p} />
    {:else}
      {#if b.lage === "schlummert"}<span class="wa-w"><i class="fa-solid fa-bed"></i> {p.t("schlummertBis")} {b.schlummerBis}</span>
      {:else if b.naechster}<span class="wa-w"><i class="fa-solid fa-bell"></i> {b.naechster}</span>
      {:else}<span class="wa-leise"><i class="fa-solid fa-bell-slash"></i> {p.t("keinWeckerAktiv")}</span>{/if}
      <span><i class="fa-solid fa-radio"></i> {b.sender || "-"} <Verbindungszeichen verbindung={b.verbindung} /></span>
      {#if b.sonne}<span class="wa-leise">{p.t("astroHinweis", { auf: b.sonne.auf, unter: b.sonne.unter })}</span>{/if}
      {#if b.lage === "schlummert"}<button type="button" class="wa-siegel" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("weckerAus")}</button>
      {:else}<Ruhetasten {...p} />{/if}
    {/if}
  </div>
</div>
