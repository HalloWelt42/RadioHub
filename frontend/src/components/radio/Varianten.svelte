<script lang="ts">
  // Varianten eines Senders (gleiche Stream-Adresse oder gleicher Name im selben Land): alle sichtbaren, die beste vorn
  // mit grüner Leuchte; jede lässt sich direkt hören.
  import { t } from "../../lib/i18n.svelte.js";
  import { senderquelle } from "../../lib/radio";
  import { format, zahl } from "../../lib/radio/anzeige";
  import type { SenderEintrag } from "../../lib/radio/typen";
  import Guete from "./Guete.svelte";

  let { eintrag, spielt, onspielen }: { eintrag: SenderEintrag; spielt: string | null; onspielen: (e: SenderEintrag) => void } = $props();

  let liste = $state<SenderEintrag[] | null>(null);
  let fehler = $state("");

  $effect(() => {
    const uuid = eintrag.uuid;
    let aktuell = true;
    senderquelle.varianten(uuid).then((v) => { if (aktuell) liste = v; }).catch((f: Error) => { if (aktuell) fehler = f.message; });
    return () => { aktuell = false; };
  });
</script>

<div class="rh-varianten" role="list" aria-label={t("radio.variantenVon", { name: eintrag.name })}>
  {#if fehler}
    <div class="rh-variante" role="listitem"><span></span><span>{fehler}</span></div>
  {:else if !liste}
    <div class="rh-variante" role="listitem"><span></span><span class="rh-still">{t("radio.laedt")}</span></div>
  {:else}
    {#each liste as v, i (v.uuid)}
      <div class="rh-variante" role="listitem">
        <ak-led farbe={spielt === v.uuid ? "blau" : i === 0 ? "gruen" : "gelb"} zustand={spielt === v.uuid || i === 0 ? "an" : "aus"} groesse="klein"></ak-led>
        <span><b>{v.kbps ? `${v.codec} ${zahl(v.kbps)} kbit/s` : format(v)}</b> · {v.hls ? t("radio.hls") : v.name}{#if i === 0} <span class="stand-pille fertig">{t("radio.besteVariante")}</span>{/if}</span>
        <span class="rh-guete-text"><Guete stufe={v.qualitaet} /></span>
        <span class="stimmen-v rh-zahl"><i class="fa-solid fa-thumbs-up"></i> {zahl(v.stimmen)}</span>
        <button class="knopf" type="button" onclick={() => onspielen(v)}><i class="fa-solid fa-play"></i>{t("radio.hoeren")}</button>
      </div>
    {/each}
  {/if}
</div>
