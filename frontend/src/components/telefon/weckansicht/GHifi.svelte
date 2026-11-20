<script lang="ts">
  // Gestaltung B "HiFi-Gerät": Gehäuse wie die Abspielleiste (hell Silber, dunkel Anthrazit), links das Glas mit der
  // Matrixuhr, rechts drei kleine Anzeigen und Tasten mit Licht. Beim Klingeln rechts Schlummern und Aus groß, darunter
  // Radio und Weckton als Tasten mit Licht.
  import type { Gestaltungsprops } from "./typen";
  import Punktfeld from "./Punktfeld.svelte";
  import { breite, fuerMatrix } from "../../../lib/telefon/punktmatrix.js";
  let p: Gestaltungsprops = $props();
  const b = $derived(p.bild);
  const gross = fuerMatrix;
  const zeile = $derived(b.lage === "klingelt" ? `@ ${gross(p.t("klingelt"))} ${b.klingelZeit ?? ""}   ${b.senderKurz}` : `${b.datum}   ${gross(b.sender || "-")}`);
  const kleine = $derived([
    { t: b.lage === "schlummert" ? `~ ${b.schlummerBis}` : b.naechster ? `@ ${gross(b.naechster)}` : "-", f: "--akzent" },
    { t: `${b.senderKurz}  ${b.verbindung === "verbindet" ? "..." : b.verbindung === "gestoert" ? "!" : b.spielt ? "LIVE" : ""}`, f: "--an" },
    { t: b.sonne ? `*${b.sonne.auf} )${b.sonne.unter}` : "", f: "--an" },
  ]);
  const stellen = $derived(Math.max(...kleine.map((k) => breite(k.t))) + 6);
</script>

<div class="wa-geraet">
  <div class="wa-glas gross uhr-box" class:zucken={b.zucken}>
    <Punktfeld klasse="matrix wa-haupt" spalten={80} zeilen={26} modus={b.modus} ebenen={[{ text: b.zeit, y: 2, mass: 3, mitte: true, farbe: "--an" }]} />
    <Punktfeld klasse="matrix wa-zeile" spalten={breite(zeile) + 8} zeilen={9} modus={b.modus} ebenen={[{ text: zeile, y: 1, mitte: true, farbe: b.lage === "klingelt" ? "--akzent" : "--an" }]} />
  </div>
  <div class="wa-spalte">
    {#if b.lage === "klingelt"}
      <button type="button" class="wa-taste gross wa-licht" style:--l="#ffb21f" onclick={p.tun.schlummern}><i class="fa-solid fa-bed"></i><span>{gross(p.t("schlummern"))}</span></button>
      <button type="button" class="wa-taste gross wa-licht" style:--l="#ff3b30" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i><span>{gross(p.t("aus"))}</span></button>
      <div class="wa-tasten">
        <button type="button" class="wa-taste wa-klein" class:wa-licht={b.quelle === "radio"} onclick={() => p.tun.quelle("radio")} aria-pressed={b.quelle === "radio"}><i class="fa-solid fa-radio"></i><span>{gross(b.quelleName)}</span></button>
        <button type="button" class="wa-taste wa-klein" class:wa-licht={b.quelle === "weckton"} style:--l="#ffb21f" onclick={() => p.tun.quelle("weckton")} aria-pressed={b.quelle === "weckton"}><i class="fa-solid fa-bell"></i><span>{gross(p.t("weckton"))}</span></button>
      </div>
    {:else}
      {#each kleine as k (k.f + k.t)}<div class="wa-glas"><Punktfeld spalten={stellen} zeilen={9} modus={b.modus} ebenen={[{ text: k.t, y: 1, mitte: true, farbe: k.f }]} /></div>{/each}
      <div class="wa-tasten">
        {#if b.lage === "schlummert"}
          <button type="button" class="wa-taste wa-licht" style:--l="#ff3b30" onclick={p.tun.aus}><i class="fa-solid fa-power-off"></i><span>{gross(p.t("weckerAus"))}</span></button>
        {:else}
          <button type="button" class="wa-taste" class:wa-licht={b.spielt} disabled={!b.sender} onclick={p.tun.umschalten} aria-label={b.spielt ? p.t("pause") : p.t("abspielen")}>
            <i class="fa-solid {b.spielt ? (b.stoppStattPause ? 'fa-stop' : 'fa-pause') : 'fa-play'}"></i></button>
          <button type="button" class="wa-taste" class:wa-licht={b.ansage.an} style:--l={b.ansage.gesperrt ? "#ffb21f" : null} onclick={p.tun.ansage} aria-pressed={b.ansage.an} aria-label={p.t("zeitansage")}>
            <i class="fa-solid {b.ansage.laeuft ? 'fa-volume-high' : b.ansage.an ? 'fa-comment-dots' : 'fa-comment-slash'}"></i></button>
          <button type="button" class="wa-taste" class:wa-licht={b.nachtWahl !== "aus"} style:--l={b.modus === "nacht" ? "#ff3a28" : "#3d8bff"} onclick={p.tun.nacht} aria-label={p.t("nacht")}>
            <i class="fa-solid {b.nachtWahl === 'auto' ? 'fa-circle-half-stroke' : b.nachtWahl === 'an' ? 'fa-moon' : 'fa-sun'}"></i></button>
        {/if}
      </div>
    {/if}
  </div>
</div>
