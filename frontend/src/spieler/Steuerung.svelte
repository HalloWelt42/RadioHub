<script lang="ts">
  // Modul Steuerung: Tastenreihe aus Glastastern, alle gleich hoch, Tastenlicht in der Kappe (Merkmal licht).
  // Zurück, Stopp, Spielen oder Anhalten, Aufnahme, Weiter; bei Sendern Original oder Zeitversatz, bei Folgen und
  // Aufnahmen die Reihenfolge (beide immer da, gesperrt, wo sie nicht gelten, wie in HiFiPlayer). Zurück, Stopp und Weiter leuchten, solange sie gedrückt sind; Spielen und Aufnahme
  // folgen dem Zustand (Aufnahme blinkt rot). Während der Aufnahme sind Senderwechsel und Anhalten gesperrt.
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import { aufnehmen, reihenfolgeWeiter, spielenOderAnhalten, stoppen, vor, zurueck } from "./aktionen";
  import type { Tasten } from "./kanzel";
  import { taste } from "./taste";

  let { tasten, onmodus }: { tasten: Tasten; onmodus: () => void } = $props();

  /** Bedienung mit Klang (Senderwechsel ohne, wie bisher) */
  const mitKlang = (tun: () => void) => () => { tun(); sfx.click(); };
  const zeigen = () => sfx.hover();
</script>

<section class="rh-modul rh-m-steuerung" aria-label={t("kanzel.steuerung")}><span class="ak-etikett">{t("kanzel.steuerung")}</span>
  <div class="rh-steuerung ak-tastenreihe">
    <ak-taster art="glas" symbol="fa-backward-step" farbe="weiss" licht="bernstein" modus="tasten"
      use:taste={{ licht: tasten.zurueck.licht, gesperrt: tasten.zurueck.gesperrt, hilfe: tasten.zurueck.hilfe, beiDruck: zurueck, beiZeigen: zeigen }}></ak-taster>
    <ak-taster art="glas" symbol="fa-stop" farbe="weiss" licht="weiss" modus="tasten"
      use:taste={{ gesperrt: tasten.stopp.gesperrt, hilfe: tasten.stopp.hilfe, beiDruck: mitKlang(stoppen), beiZeigen: zeigen }}></ak-taster>
    <ak-taster art="glas" symbol="fa-play" farbe="blau" licht="blau"
      use:taste={{ an: tasten.spielen.an, licht: tasten.spielen.licht, gesperrt: tasten.spielen.gesperrt, hilfe: tasten.spielen.hilfe, symbol: tasten.spielen.symbol,
                   beiDruck: mitKlang(spielenOderAnhalten), beiZeigen: zeigen }}></ak-taster>
    <ak-taster art="glas" symbol="fa-circle" farbe="rot" licht="rot"
      use:taste={{ an: tasten.aufnahme.an, licht: tasten.aufnahme.licht, gesperrt: tasten.aufnahme.gesperrt, hilfe: tasten.aufnahme.hilfe,
                   beiDruck: mitKlang(aufnehmen), beiZeigen: zeigen }}></ak-taster>
    <ak-taster art="glas" symbol="fa-forward-step" farbe="weiss" licht="bernstein" modus="tasten"
      use:taste={{ licht: tasten.vor.licht, gesperrt: tasten.vor.gesperrt, hilfe: tasten.vor.hilfe, symbol: "fa-forward-step", gespiegelt: tasten.vor.gespiegelt,
                   beiDruck: vor, beiZeigen: zeigen }}></ak-taster>
    <ak-taster art="glas" symbol={tasten.modus.symbol} farbe="weiss" licht={tasten.modus.farbe}
      use:taste={{ an: false, licht: tasten.modus.licht, lichtFarbe: tasten.modus.farbe, gesperrt: tasten.modus.gesperrt, hilfe: tasten.modus.hilfe,
                   symbol: tasten.modus.symbol, beiDruck: mitKlang(onmodus), beiZeigen: zeigen }}></ak-taster>
    <ak-taster art="glas" symbol={tasten.reihenfolge.symbol} farbe="weiss" licht={tasten.reihenfolge.farbe}
      use:taste={{ an: false, licht: tasten.reihenfolge.licht, lichtFarbe: tasten.reihenfolge.farbe, gesperrt: tasten.reihenfolge.gesperrt, hilfe: tasten.reihenfolge.hilfe,
                   symbol: tasten.reihenfolge.symbol, beiDruck: mitKlang(reihenfolgeWeiter), beiZeigen: zeigen }}></ak-taster>
  </div>
</section>
