<script lang="ts">
  // Balken des Puffers am Telefon (RAD-46): vom ältesten Ton bis live, gelb bis zur Stelle, die man hört, Titelgrenzen
  // als Striche, Werbung violett, ein gewählter Bereich rot umrandet; darunter zwei Angaben der Ansicht und "live", in
  // drei festen Spalten: keine Angabe verschiebt eine andere, wenn sie wächst (RAD-54, Entwurf Zustände 6 bis 8).
  import { t } from "../../lib/i18n.svelte.js";
  import { bei, prozent, type Abschnitt } from "../../lib/radio/abschnitte";
  import { puffer } from "../../spieler/puffer.svelte";

  let { stelle, bereich = null, links, mitte, onwahl }: { stelle: number; bereich?: { von: number; bis: number } | null; links: string; mitte: string;
    /** auf einen Abschnitt getippt (RAD-132) */
    onwahl?: (a: Abschnitt) => void } = $props();

  function getippt(e: MouseEvent): void {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const a = bei(puffer.abschnitte, puffer.anfang + ((e.clientX - r.left) / Math.max(1, r.width)) * (puffer.ende - puffer.anfang));
    if (a) onwahl?.(a);
  }
  const p = (s: number) => prozent(s, puffer.anfang, puffer.ende);
</script>

<div class="pb">
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="pb-bahn" onclick={getippt}>
    <div class="pb-balken"><span style:width="{p(stelle)}%"></span>
      {#each puffer.abschnitte.filter((a) => a.art === "werbung") as a (a.von)}<i class="pb-werbung" style:left="{p(a.von)}%" style:width="{Math.max(1, p(a.bis) - p(a.von))}%"></i>{/each}</div>
    <div class="pb-striche" aria-hidden="true">{#each puffer.abschnitte.filter((a) => a.von > puffer.anfang + 0.5) as a (a.von)}<i style:left="{p(a.von)}%"></i>{/each}</div>
    {#if bereich}<i class="pb-bereich" style:left="{p(bereich.von)}%" style:width="{p(bereich.bis) - p(bereich.von)}%"></i>{/if}
  </div>
  <div class="pb-zahlen">
    <span>{links}</span>
    <span>{mitte}</span>
    <span>{t("puffer.live")}</span>
  </div>
</div>

<style>
  .pb { display: grid; gap: 4px; }
  .pb-bahn { position: relative; padding-block: 12px; margin-block: -6px; }
  .pb-balken { position: relative; height: 12px; border-radius: 6px; overflow: hidden; background: var(--t-flaeche-2); }
  .pb-balken > span { display: block; height: 100%; background: var(--t-akzent); }
  .pb-werbung { position: absolute; top: 0; bottom: 0; background: var(--violett); }
  .pb-striche { position: absolute; inset: 8px 0; pointer-events: none; }
  .pb-striche i { position: absolute; top: 0; bottom: 0; width: 2px; margin-left: -1px; border-radius: 1px; background: var(--t-grund);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--t-text) 65%, transparent); }
  .pb-bereich { position: absolute; top: 9px; bottom: 9px; border-radius: 4px; box-shadow: 0 0 0 2px var(--rh-aufnahme); pointer-events: none; }
  .pb-zahlen { display: grid; grid-template-columns: 1fr auto 1fr; gap: 8px; font-size: var(--klein); color: var(--t-text-2); font-variant-numeric: tabular-nums; }
  .pb-zahlen > span { white-space: nowrap; }
  .pb-zahlen > span:last-child { text-align: right; }
</style>
