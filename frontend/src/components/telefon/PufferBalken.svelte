<script lang="ts">
  // Balken des Puffers am Telefon (RAD-46): vom ältesten Ton bis live, gelb bis zur Stelle, die man hört, Titelgrenzen
  // als Striche, Werbung violett, ein gewählter Bereich rot umrandet; darunter Abstand zu live, Länge und "live".
  import { t } from "../../lib/i18n.svelte.js";
  import { formatTimeShort } from "../../lib/formatters.js";
  import { prozent } from "../../lib/radio/abschnitte";
  import { puffer } from "../../spieler/puffer.svelte";

  let { stelle, bereich = null }: { stelle: number; bereich?: { von: number; bis: number } | null } = $props();

  const p = (s: number) => prozent(s, puffer.anfang, puffer.ende);
</script>

<div class="pb">
  <div class="pb-bahn">
    <div class="pb-balken"><span style:width="{p(stelle)}%"></span>
      {#each puffer.abschnitte.filter((a) => a.art === "werbung") as a (a.von)}<i class="pb-werbung" style:left="{p(a.von)}%" style:width="{Math.max(1, p(a.bis) - p(a.von))}%"></i>{/each}</div>
    <div class="pb-striche" aria-hidden="true">{#each puffer.abschnitte.filter((a) => a.von > puffer.anfang + 0.5) as a (a.von)}<i style:left="{p(a.von)}%"></i>{/each}</div>
    {#if bereich}<i class="pb-bereich" style:left="{p(bereich.von)}%" style:width="{p(bereich.bis) - p(bereich.von)}%"></i>{/if}
  </div>
  <div class="pb-zahlen">
    <span>{puffer.ende - stelle > 1 ? t("puffer.vorLive", { zeit: formatTimeShort(puffer.ende - stelle) }) : ""}</span>
    <span>{formatTimeShort(puffer.ende - puffer.anfang)}</span>
    <span>{t("puffer.live")}</span>
  </div>
</div>

<style>
  .pb { display: grid; gap: 4px; }
  .pb-bahn { position: relative; padding-block: 6px; }
  .pb-balken { position: relative; height: 12px; border-radius: 6px; overflow: hidden; background: var(--t-flaeche-2); }
  .pb-balken > span { display: block; height: 100%; background: var(--t-akzent); }
  .pb-werbung { position: absolute; top: 0; bottom: 0; background: var(--violett); }
  .pb-striche { position: absolute; inset: 2px 0; pointer-events: none; }
  .pb-striche i { position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; border-radius: 1px; background: var(--t-grund);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--t-text) 65%, transparent); }
  .pb-bereich { position: absolute; top: 3px; bottom: 3px; border-radius: 4px; box-shadow: 0 0 0 2px var(--led-rot); pointer-events: none; }
  .pb-zahlen { display: flex; justify-content: space-between; font-size: 15px; color: var(--t-text-2); font-variant-numeric: tabular-nums; }
</style>
