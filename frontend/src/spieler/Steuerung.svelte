<script lang="ts">
  // Modul Steuerung: alle Tasten in einer Reihe, in jeder Breite (Nutzer 20.11.2026), gleich groß und auf einer
  // Grundlinie; erst der Transport (Zurück, Stopp, Spielen oder Anhalten, Aufnahme, Weiter), mit Abstand das Seltene
  // (Original oder Zeitversatz, Reihenfolge), am Ende die Bitrate des Zeitversatzes als Drehwahl (Nutzer 17.11.2026);
  // spielt eine Folge, steht dort das Tempo (RAD-17).
  // Die Kappen leuchten nie, nur ihr Tastenlicht (Nutzer 20.11.2026). Was der Weg der Wiedergabe nicht kann, steht nicht
  // da (Webversion: ohne Aufnahme, Zeitversatz und Folgen, also ohne Aufnahme, Original oder Zeitversatz, Reihenfolge
  // und Bitrate). Zurück, Stopp und Weiter leuchten, solange sie
  // gedrückt sind; Spielen und Aufnahme folgen dem Zustand (Aufnahme blinkt rot); nach einem Fehler wird Spielen zu Neu
  // verbinden. Während der Aufnahme sind Senderwechsel und Anhalten gesperrt. Was in einem Zustand nicht gilt, bleibt
  // sichtbar und ist gesperrt, wie in HiFiPlayer.
  import type { Drehregler } from "appkern-oberflaeche/instrumente";
  import { t } from "../lib/i18n.svelte.js";
  import { aufnehmen, quelleStarten, reihenfolgeWeiter, spielenOderPause, stoppen, vor, vorSender, zurueck, zurueckSender, andereVariante } from "./aktionen";
  import { fokusSchalten } from "./fokus.svelte";
  import { bitrateAusStellung, bitrateRaster, bitrateStellung, tempoAusStellung, tempoRaster, tempoStellung, type BitrateLage, type Tasten } from "./kanzel";
  import { app } from "./app";
  import { actions } from "../lib/store.svelte.js";
  import type { Bitrate } from "./bitrate.svelte";
  import { taste } from "./taste";
  import { faehigkeiten } from "../lib/playerEngine.js";

  const kann = faehigkeiten();

  let { tasten, onmodus, bitrate, lage }: {
    tasten: Tasten;
    onmodus: () => void;
    bitrate: Bitrate;
    /** Bitratenwahl wirkt (frei), gesperrt, fest (Folge im Puffer, 128) oder gilt nicht (aus, gesperrt sichtbar) */
    lage: BitrateLage;
  } = $props();

  const drehFrei = $derived(lage === "frei" && !bitrate.wechselt);
  const stellung = $derived(lage === "fest" ? bitrateStellung(128) : bitrateStellung(bitrate.vorgabe));
  function gedreht(e: Event) {
    const wert = (e.currentTarget as Drehregler).wert;
    if (drehFrei && wert !== undefined) bitrate.vormerken(bitrateAusStellung(Math.round(wert)));
  }
</script>

<!-- Köpfe nebeneinander (RAD-72): STEUERUNG über den Tasten, der Name des Drehreglers über dem Regler, auf einer Linie -->
<section class="rh-modul rh-m-steuerung" aria-label={t("kanzel.steuerung")}><span class="ak-etikett">{t("kanzel.steuerung")}</span>
  {#if app.playerMode === "podcast" || kann.zeitversatz}<span class="ak-etikett rh-dreh-kopf">{t(app.playerMode === "podcast" ? "kanzel.tempoName" : "kanzel.bitrateName")}</span>{/if}
  <div class="rh-steuerung">
    <div class="rh-transport ak-tastenreihe">
      <ak-taster art="glas" symbol="fa-backward-step" farbe="weiss" licht="bernstein" modus="tasten"
        use:taste={{ licht: tasten.zurueck.licht, gesperrt: tasten.zurueck.gesperrt, hilfe: tasten.zurueck.hilfe, beiDruck: zurueck, beiLang: zurueckSender }}></ak-taster>
      <ak-taster art="glas" symbol="fa-stop" farbe="weiss" licht="bernstein" modus="tasten"
        use:taste={{ gesperrt: tasten.stopp.gesperrt, hilfe: tasten.stopp.hilfe, beiDruck: stoppen }}></ak-taster>
      <ak-taster class="rh-t-gruen" art="glas" symbol="fa-play" farbe="gruen" licht="gruen"
        use:taste={{ an: tasten.spielen.an, licht: tasten.spielen.licht, lichtFarbe: tasten.spielen.farbe, gesperrt: tasten.spielen.gesperrt, hilfe: tasten.spielen.hilfe,
                     symbol: tasten.spielen.symbol, beiDruck: tasten.spielen.neuVerbinden ? quelleStarten : spielenOderPause }}></ak-taster>
      {#if kann.aufnahme}
      <ak-taster class="rh-t-rot" art="glas" symbol="fa-circle" farbe="rot" licht="rot"
        use:taste={{ an: tasten.aufnahme.an, licht: tasten.aufnahme.licht, gesperrt: tasten.aufnahme.gesperrt, hilfe: tasten.aufnahme.hilfe,
                     beiDruck: aufnehmen }}></ak-taster>
      {/if}
      <ak-taster art="glas" symbol="fa-forward-step" farbe="weiss" licht="bernstein" modus="tasten"
        use:taste={{ licht: tasten.vor.licht, gesperrt: tasten.vor.gesperrt, hilfe: tasten.vor.hilfe, symbol: "fa-forward-step", gespiegelt: tasten.vor.gespiegelt,
                     beiDruck: vor, beiLang: vorSender }}></ak-taster>
    </div>
    <div class="rh-betrieb ak-tastenreihe">
      <!-- Fokus auf den laufenden Sender ein oder aus (auch in Basic, RAD-19); dieselbe Größe wie alle Tasten der Reihe -->
      <ak-taster art="glas" symbol="fa-location-crosshairs" farbe="weiss" licht="blau"
          use:taste={{ an: false, licht: tasten.quelle.licht, lichtFarbe: tasten.quelle.varianten ? "rot" : "blau", gesperrt: tasten.quelle.gesperrt,
                       hilfe: tasten.quelle.hilfe, symbol: tasten.quelle.varianten ? "fa-layer-group" : "fa-location-crosshairs",
                       beiDruck: tasten.quelle.varianten ? andereVariante : fokusSchalten }}></ak-taster>
      {#if kann.zeitversatz}
      <ak-taster art="glas" symbol={tasten.modus.symbol} farbe="weiss" licht={tasten.modus.farbe}
          use:taste={{ an: false, licht: tasten.modus.licht, lichtFarbe: tasten.modus.farbe, gesperrt: tasten.modus.gesperrt, hilfe: tasten.modus.hilfe,
                       symbol: tasten.modus.symbol, beiDruck: onmodus }}></ak-taster>
      {/if}
      {#if kann.folgen}
      <ak-taster art="glas" symbol={tasten.reihenfolge.symbol} farbe="weiss" licht={tasten.reihenfolge.farbe}
          use:taste={{ an: false, licht: tasten.reihenfolge.licht, lichtFarbe: tasten.reihenfolge.farbe, gesperrt: tasten.reihenfolge.gesperrt, hilfe: tasten.reihenfolge.hilfe,
                       symbol: tasten.reihenfolge.symbol, beiDruck: reihenfolgeWeiter }}></ak-taster>
      {/if}
    </div>
  </div>
    {#if app.playerMode === "podcast"}
    <ak-dreh class="rh-bitrate-wahl" name={t("kanzel.tempoName")} hilfe={t("kanzel.tempoHilfe")} raster={tempoRaster()} vorgabe="1"
        role="slider" aria-valuenow={tempoStellung(app.podcastSpeed)} wert={tempoStellung(app.podcastSpeed)}
        oninput={(e: Event) => actions.setPodcastSpeed(tempoAusStellung((e.currentTarget as Drehregler).wert ?? 1))}></ak-dreh>
    {:else if kann.zeitversatz}
    <ak-dreh class="rh-bitrate-wahl" name={t("kanzel.bitrateName")} hilfe={t("kanzel.bitrateHilfe")} raster={bitrateRaster(t)} vorgabe="0"
        role="slider" aria-valuenow={stellung} wert={stellung} aria-disabled={drehFrei ? "false" : "true"} tabindex={drehFrei ? 0 : -1} style:--ak-wert="var(--led-{lage === 'frei' && bitrate.vorgabe !== null ? 'gelb' : 'gruen'})"
        oninput={gedreht} onchange={() => bitrate.anwenden()}></ak-dreh>
    {/if}
</section>
