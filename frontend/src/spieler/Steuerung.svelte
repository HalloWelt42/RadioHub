<script lang="ts">
  // Modul Steuerung: alle Tasten in einer Reihe, in jeder Breite (Nutzer 20.11.2026), gleich groß und auf einer
  // Grundlinie; erst der Transport (Zurück, Stopp, Spielen oder Anhalten, Aufnahme, Weiter), mit Abstand das Seltene
  // (Original oder Zeitversatz, Reihenfolge), am Ende die Bitrate des Zeitversatzes als Drehwahl (Nutzer 17.11.2026).
  // Die Kappen leuchten nie, nur ihr Tastenlicht (Nutzer 20.11.2026). Zurück, Stopp und Weiter leuchten, solange sie
  // gedrückt sind; Spielen und Aufnahme folgen dem Zustand (Aufnahme blinkt rot); nach einem Fehler wird Spielen zu Neu
  // verbinden. Während der Aufnahme sind Senderwechsel und Anhalten gesperrt. Was in einem Zustand nicht gilt, bleibt
  // sichtbar und ist gesperrt, wie in HiFiPlayer.
  import type { Drehregler } from "appkern-oberflaeche/instrumente";
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import { aufnehmen, quelleStarten, reihenfolgeWeiter, spielenOderPause, stoppen, vor, zurueck } from "./aktionen";
  import { bitrateAusStellung, bitrateRaster, bitrateStellung, type BitrateLage, type Tasten } from "./kanzel";
  import type { Bitrate } from "./bitrate.svelte";
  import { taste } from "./taste";

  let { tasten, onmodus, bitrate, lage }: {
    tasten: Tasten;
    onmodus: () => void;
    bitrate: Bitrate;
    /** Bitratenwahl wirkt (frei), gesperrt, fest (Folge im Puffer, 128) oder gilt nicht (aus, gesperrt sichtbar) */
    lage: BitrateLage;
  } = $props();

  /** Bedienung mit Klang (Senderwechsel ohne, wie bisher) */
  const mitKlang = (tun: () => void) => () => { tun(); sfx.click(); };
  const zeigen = () => sfx.hover();

  const drehFrei = $derived(lage === "frei" && !bitrate.wechselt);
  const stellung = $derived(lage === "fest" ? bitrateStellung(128) : bitrateStellung(bitrate.vorgabe));
  function gedreht(e: Event) {
    const wert = (e.currentTarget as Drehregler).wert;
    if (drehFrei && wert !== undefined) bitrate.vormerken(bitrateAusStellung(Math.round(wert)));
  }
</script>

<section class="rh-modul rh-m-steuerung" aria-label={t("kanzel.steuerung")}><span class="ak-etikett">{t("kanzel.steuerung")}</span>
  <div class="rh-steuerung">
    <div class="rh-transport ak-tastenreihe">
      <ak-taster art="glas" symbol="fa-backward-step" farbe="weiss" licht="bernstein" modus="tasten"
        use:taste={{ licht: tasten.zurueck.licht, gesperrt: tasten.zurueck.gesperrt, hilfe: tasten.zurueck.hilfe, beiDruck: zurueck, beiZeigen: zeigen }}></ak-taster>
      <ak-taster art="glas" symbol="fa-stop" farbe="weiss" licht="weiss" modus="tasten"
        use:taste={{ gesperrt: tasten.stopp.gesperrt, hilfe: tasten.stopp.hilfe, beiDruck: mitKlang(stoppen), beiZeigen: zeigen }}></ak-taster>
      <ak-taster art="glas" symbol="fa-play" farbe="blau" licht="blau"
        use:taste={{ an: tasten.spielen.an, licht: tasten.spielen.licht, lichtFarbe: tasten.spielen.farbe, gesperrt: tasten.spielen.gesperrt, hilfe: tasten.spielen.hilfe,
                     symbol: tasten.spielen.symbol, beiDruck: mitKlang(tasten.spielen.neuVerbinden ? quelleStarten : spielenOderPause), beiZeigen: zeigen }}></ak-taster>
      <ak-taster art="glas" symbol="fa-circle" farbe="rot" licht="rot"
        use:taste={{ an: tasten.aufnahme.an, licht: tasten.aufnahme.licht, gesperrt: tasten.aufnahme.gesperrt, hilfe: tasten.aufnahme.hilfe,
                     beiDruck: mitKlang(aufnehmen), beiZeigen: zeigen }}></ak-taster>
      <ak-taster art="glas" symbol="fa-forward-step" farbe="weiss" licht="bernstein" modus="tasten"
        use:taste={{ licht: tasten.vor.licht, gesperrt: tasten.vor.gesperrt, hilfe: tasten.vor.hilfe, symbol: "fa-forward-step", gespiegelt: tasten.vor.gespiegelt,
                     beiDruck: vor, beiZeigen: zeigen }}></ak-taster>
    </div>
    <div class="rh-betrieb ak-tastenreihe">
      <ak-taster art="glas" symbol={tasten.modus.symbol} farbe="weiss" licht={tasten.modus.farbe}
          use:taste={{ an: false, licht: tasten.modus.licht, lichtFarbe: tasten.modus.farbe, gesperrt: tasten.modus.gesperrt, hilfe: tasten.modus.hilfe,
                       symbol: tasten.modus.symbol, beiDruck: mitKlang(onmodus), beiZeigen: zeigen }}></ak-taster>
      <ak-taster art="glas" symbol={tasten.reihenfolge.symbol} farbe="weiss" licht={tasten.reihenfolge.farbe}
          use:taste={{ an: false, licht: tasten.reihenfolge.licht, lichtFarbe: tasten.reihenfolge.farbe, gesperrt: tasten.reihenfolge.gesperrt, hilfe: tasten.reihenfolge.hilfe,
                       symbol: tasten.reihenfolge.symbol, beiDruck: mitKlang(reihenfolgeWeiter), beiZeigen: zeigen }}></ak-taster>
    </div>
    <ak-dreh class="rh-bitrate-wahl" name={t("kanzel.bitrateName")} hilfe={t("kanzel.bitrateHilfe")} raster={bitrateRaster(t)} vorgabe="0"
        role="slider" aria-valuenow={stellung} wert={stellung} aria-disabled={drehFrei ? "false" : "true"} tabindex={drehFrei ? 0 : -1} style:--ak-wert="var(--led-{lage === 'frei' && bitrate.vorgabe !== null ? 'gelb' : 'gruen'})"
        oninput={gedreht} onchange={() => bitrate.anwenden()}></ak-dreh>
  </div>
</section>
