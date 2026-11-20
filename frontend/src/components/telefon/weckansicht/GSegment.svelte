<script lang="ts">
  // Gestaltung C "Segment-Uhr": Ziffern aus sieben Segmenten mit gedämpften Segmenten dahinter, darunter ein Lauftext.
  // Beim Klingeln eine Zeile mit Quelle, Schlummern und Aus, alle gleich hoch.
  import type { Gestaltungsprops } from "./typen";
  import Punktfeld from "./Punktfeld.svelte";
  import Quellwahl from "./Quellwahl.svelte";
  import Ruhetasten from "./Ruhetasten.svelte";
  import { breite, fuerMatrix } from "../../../lib/telefon/punktmatrix.js";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
  const gross = fuerMatrix;
  const SEG: Record<string, string> = { a: "8,0 52,0 44,8 16,8", b: "54,2 60,8 60,46 54,50 50,46 50,10", c: "54,52 60,56 60,94 54,100 50,92 50,56",
    d: "16,94 44,94 52,102 8,102", e: "6,52 10,56 10,92 6,100 0,94 0,56", f: "6,2 10,10 10,46 6,50 0,46 0,8", g: "10,47 50,47 54,51 50,55 10,55 6,51" };
  const ZIFFER: Record<string, string> = { 0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg" };
  const teile = $derived.by(() => {
    let x = 0;
    const aus: { art: "punkt" | "seg"; an: boolean; punkte?: string; cx?: number; cy?: number }[] = [];
    for (const c of b.zeit) {
      if (c === ":") { aus.push({ art: "punkt", an: true, cx: x + 8, cy: 34 }, { art: "punkt", an: true, cx: x + 8, cy: 70 }); x += 20; continue; }
      for (const [n, pkt] of Object.entries(SEG)) aus.push({ art: "seg", an: (ZIFFER[c] ?? "").includes(n),
        punkte: pkt.split(" ").map((xy) => { const [a, y] = xy.split(","); return `${+a + x},${y}`; }).join(" ") });
      x += 76;
    }
    return { aus, breite: x };
  });
  const lauf = $derived(b.lage === "klingelt" ? `@ ${gross(p.t("klingelt"))} ${b.klingelZeit ?? ""}   ${gross(b.sender)}`
    : b.lage === "schlummert" ? `~ ${gross(p.t("schlummertBis"))} ${b.schlummerBis}   ${b.senderKurz}`
    : `${gross(b.sender || "-")}${b.verbindung === "verbindet" ? " ..." : b.verbindung === "gestoert" ? " !" : ""}   ${b.naechster ? "@ " + gross(b.naechster) : ""}   ${b.sonne ? `*${b.sonne.auf} )${b.sonne.unter}` : ""}`);
</script>

<div class="wa-segment">
  <div class="wa-uhrfeld uhr-box" class:zucken={b.zucken} style:flex={b.lage === "klingelt" ? "0 0 58%" : null}>
    <svg viewBox="-8 -4 {teile.breite + 4} 110" role="timer" aria-label={b.zeit}>
      {#each teile.aus as s, i (i)}
        {#if s.art === "punkt"}<circle class="wa-seg" cx={s.cx} cy={s.cy} r="5" />{:else}<polygon class={s.an ? "wa-seg" : "wa-geist"} points={s.punkte} transform="skewX(-6)" />{/if}
      {/each}
    </svg>
  </div>
  {#if b.lage === "klingelt"}
    <div class="wa-unten"><Punktfeld spalten={breite(lauf) + 4} zeilen={9} modus={b.modus} glanz={b.modus !== "hell"} ebenen={[{ text: lauf, x: 2, y: 1, farbe: "--akzent" }]} /></div>
    <div class="wa-reihe"><Quellwahl {...p} />
      <button type="button" class="wa-gross-taste schlummern" style:flex="1" onclick={p.tun.schlummern}><i class="fa-solid fa-bed"></i>{p.t("schlummern")}</button>
      <button type="button" class="wa-gross-taste aus" style:flex="1" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("aus")}</button></div>
  {:else}
    <div class="wa-unten"><Punktfeld spalten={breite(lauf) + 4} zeilen={9} modus={b.modus} glanz={b.modus !== "hell"} ebenen={[{ text: lauf, x: 2, y: 1, farbe: b.lage === "schlummert" ? "--akzent" : "--an" }]} />
      {#if b.lage === "schlummert"}<button type="button" class="wa-gross-taste aus" style:min-height="52px" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i>{p.t("weckerAus")}</button>
      {:else}<Ruhetasten {...p} />{/if}</div>
  {/if}
</div>
