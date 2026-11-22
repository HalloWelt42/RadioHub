<script lang="ts">
  // Gerät der Schnellwahl (Entwurf rechner.html, Seitenleiste oben fest; am Telefon oben im Filterblatt): Schalter
  // Nur Favoriten und Nur erreichbare, Drehwahl Beliebtheit (die Mindestbitrate steht seit RAD-28 in der Gruppe Codec). Am Rechner mit dem Kopf der
  // Schnellfilter im Gerät. Die Instrumente melden Bedienung über "input"; gesetzte Werte (Chip entfernt) melden nichts.
  import type { Snippet } from "svelte";
  import type { Drehregler } from "appkern-oberflaeche/instrumente";
  import Schalter from "../bausteine/Schalter.svelte";
  import { t } from "../../lib/i18n.svelte.js";
  import { zahl } from "../../lib/radio/anzeige";
  import { STIMMEN_STUFEN, type Schnellfilter } from "../../lib/radio/schnellfilter";

  let { filter, onaendern, kopf }: {
    filter: Schnellfilter;
    onaendern: (arbeit: (f: Schnellfilter) => Schnellfilter) => void;
    kopf?: Snippet;
  } = $props();

  let stimmen = $state<Drehregler>();

  const stimmenRaster = $derived([t("radio.alle"), ...STIMMEN_STUFEN.slice(1).map((n) => t("radio.abZahl", { n: zahl(n) }))].join("|"));
  const stufe = (stufen: readonly number[], wert: number) => Math.max(0, stufen.indexOf(wert));

  // Zustand in die Instrumente (nach Zurücksetzen, Chip, Adresse)
  $effect(() => { const i = stufe(STIMMEN_STUFEN, filter.stimmen); if (stimmen && stimmen.wert !== i) stimmen.wert = i; });
</script>

<div class="ak-geraet rh-schnellwahl" data-bauform="inspektor">
  <span class="ak-schraube lo" style="--dreh:22deg"></span><span class="ak-schraube ro" style="--dreh:64deg"></span><span class="ak-schraube lu" style="--dreh:-18deg"></span><span class="ak-schraube ru" style="--dreh:41deg"></span>
  {@render kopf?.()}
  <div class="rh-schnellwahl-oben">
    <div class="rh-schnellwahl-taster">
      <Schalter an={filter.nurFavoriten} text={t("radio.nurFavoriten")} farbe="gelb" hilfe={t("radio.nurFavoritenHilfe")}
                onwechsel={(an) => onaendern((f) => ({ ...f, nurFavoriten: an }))} />
      <Schalter an={filter.nurErreichbar} text={t("radio.erreichbare")} farbe="gruen" hilfe={t("radio.nurErreichbareHilfe")}
                onwechsel={(an) => onaendern((f) => ({ ...f, nurErreichbar: an }))} />
    </div>
    {#key stimmenRaster}
      <ak-dreh bind:this={stimmen} name={t("radio.stimmen")} hilfe={t("radio.stimmenHilfe")} raster={stimmenRaster}
               wert={stufe(STIMMEN_STUFEN, filter.stimmen)} vorgabe="0"
               oninput={() => onaendern((f) => ({ ...f, stimmen: STIMMEN_STUFEN[stimmen?.wert ?? 0] ?? 0 }))}></ak-dreh>
    {/key}
  </div>
</div>
