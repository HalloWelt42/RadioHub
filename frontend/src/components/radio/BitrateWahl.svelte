<script lang="ts">
  // Mindestbitrate als Leuchtbalken (RAD-28: aus dem Gerät der Schnellwahl in die Gruppe Codec, weil sie seltener
  // gebraucht wird als Favoriten und Beliebtheit). Am Rechner in der Seitenleiste, am Telefon im Filterblatt.
  import type { Schieber } from "appkern-oberflaeche/instrumente";
  import { t } from "../../lib/i18n.svelte.js";
  import { BITRATE_STUFEN, type Schnellfilter } from "../../lib/radio/schnellfilter";

  let { filter, onaendern }: {
    filter: Schnellfilter;
    onaendern: (arbeit: (f: Schnellfilter) => Schnellfilter) => void;
  } = $props();

  let bitrate = $state<Schieber>();
  const raster = $derived([t("radio.alle"), ...BITRATE_STUFEN.slice(1).map(String)].join("|"));
  const stufe = (wert: number) => Math.max(0, (BITRATE_STUFEN as readonly number[]).indexOf(wert));
  // Zustand in das Instrument (nach Zurücksetzen, Chip, Adresse)
  $effect(() => { const i = stufe(filter.bitrate); if (bitrate && bitrate.wert !== i) bitrate.wert = i; });
</script>

<ak-schieber bind:this={bitrate} class="rh-bitratewahl" art="balken" leuchte="gruen" segmente="5" name={t("radio.mindestbitrate")}
             hilfe={t("radio.mindestbitrateHilfe")} {raster} wert={stufe(filter.bitrate)}
             oninput={() => onaendern((f) => ({ ...f, bitrate: BITRATE_STUFEN[bitrate?.wert ?? 0] ?? 0 }))}></ak-schieber>
