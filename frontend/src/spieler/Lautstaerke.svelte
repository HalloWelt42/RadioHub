<script lang="ts">
  // Modul Lautstärke: Gehäuse mit Schrauben, Drehregler zwischen zwei Pegeln. Der Regler meldet jede Bedienung
  // ("input") an die Engine; ändert sich die Lautstärke anders (Tastatur), folgt er ohne Meldung. Die Pegel zeigen, wie
  // bisher die Leuchtketten, ein nachgestelltes Signal, solange etwas hörbar spielt; sonst stehen sie unten.
  import type { Drehregler } from "appkern-oberflaeche/instrumente";
  import { app } from "./app";
  import { t } from "../lib/i18n.svelte.js";
  import { lautstaerke } from "./aktionen";

  let { hoerbar }: { hoerbar: boolean } = $props();

  /** Pegel ohne Ton: ganz unten */
  const STILL_DB = -60;
  const pegel = $derived(hoerbar && app.volume > 0 ? undefined : STILL_DB);

  function gedreht(e: Event) {
    const wert = (e.currentTarget as Drehregler).wert;
    if (wert !== undefined && wert !== app.volume) lautstaerke(Math.round(wert));
  }
</script>

<section class="rh-modul rh-m-laut">
  <div class="ak-geraet rh-laut" data-bauform="inspektor">
    <span class="ak-schraube lo" style="--dreh:12deg"></span><span class="ak-schraube ro" style="--dreh:58deg"></span>
    <span class="ak-etikett">{t("kanzel.lautstaerke")}</span>
    <div class="rh-laut-reihe">
      <span class="rh-vu"><ak-pegel richtung="senkrecht" kanaele="1" segmente="12" skala="" beschriftung={t("kanzel.pegelLinks")} hilfe={t("kanzel.pegelLinks")}
        wert={pegel}></ak-pegel>L</span>
      <ak-dreh name={t("kanzel.lautstaerke")} hilfe={t("kanzel.lautstaerkeHilfe")} wert={app.volume} vorgabe="50" einheit="%" oninput={gedreht}></ak-dreh>
      <span class="rh-vu"><ak-pegel richtung="senkrecht" kanaele="1" segmente="12" skala="" beschriftung={t("kanzel.pegelRechts")} hilfe={t("kanzel.pegelRechts")}
        wert={pegel}></ak-pegel>R</span>
    </div>
  </div>
</section>
