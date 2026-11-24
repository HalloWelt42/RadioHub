<script lang="ts">
  // Werbestellen einer Folge (Entwurf podcast-werbung.html; RAD-32): Leiste, je Stelle Zeit, Länge und Herkunft, anhören und
  // "keine Werbung" (mit Rückgängig), dazu der Fortschritt der Suche. Ohne Stellen steht hier nichts (RAD-138).
  import { t } from "../../lib/i18n.svelte.js";
  import { stelleText } from "../../lib/podcasts/anzeige";
  import type { Folge, Werbeherkunft } from "../../lib/podcasts";
  import type { Folgenwerbung } from "../../spieler/folgenwerbung.svelte";

  let { werbung: w, folge, schmal = false, onanhoeren }: {
    werbung: Folgenwerbung;
    folge: Folge;
    /** Telefon: Stellen ohne eigene Spalte für die Zeit */
    schmal?: boolean;
    /** ab einer Stelle hören (die Stelle wird dabei nicht übersprungen) */
    onanhoeren: (von: number) => void;
  } = $props();

  const SYMBOL: Record<Werbeherkunft, string> = { kapitel: "fa-list-ol", hand: "fa-hand-pointer", vergleich: "fa-code-compare", transkript: "fa-comment-dots" };
  const dauer = $derived(folge.dauer || Math.max(0, ...w.stellen.map((s) => s.bis)));
  const prozent = (x: number) => (dauer ? Math.min(100, (x / dauer) * 100) : 0);
</script>

{#if w.stellen.length || w.auftrag || w.verworfen}
<section class="rh-werbeteil" class:schmal aria-label={t("podcastAnsicht.werbung.titel")}>
  {#if w.stellen.length}
    <div class="rh-werbeleiste" role="img" aria-label={t("podcastAnsicht.werbung.leiste", { n: w.stellen.length })}>
      <span class="gehoert" style:width="{prozent(folge.stelle)}%"></span>
      {#each w.stellen as s (s.id)}<span class="werbung" style:left="{prozent(s.von)}%" style:width="{Math.max(0.8, prozent(s.bis) - prozent(s.von))}%"></span>{/each}
      <span class="kopf" style:left="{prozent(folge.stelle)}%"></span>
    </div>
  {/if}
  {#if w.auftrag}
    <div class="rh-auftrag" role="status">
      <span>{w.auftrag.was}{w.auftrag.f ? `: ${w.auftrag.f.text}` : ""}</span>
      <div class="balken"><span style:width="{w.auftrag.f ? Math.round((w.auftrag.f.schritt / Math.max(1, w.auftrag.f.gesamt)) * 100) : 5}%"></span></div>
      <span class="rh-zahl">{w.auftrag.f ? `${w.auftrag.f.schritt}/${w.auftrag.f.gesamt}` : ""}</span></div>
  {:else if w.stellen.length}
    <ol class="rh-werbestellen">
      {#each w.stellen as s, i (s.id)}
        <li>
          <span class="rh-a-nr">{String(i + 1).padStart(2, "0")}</span>
          <span class="zeit"><b>{t("podcastAnsicht.werbung.vonBis", { von: stelleText(s.von), bis: stelleText(s.bis) })}</b><span>{stelleText(s.bis - s.von)}</span></span>
          <span class="herkunft"><span><i class="fa-solid {SYMBOL[s.herkunft]}"></i>{t(`schale.werbeherkunft_${s.herkunft}`)}</span>{#if s.text}<span class="rh-still">{s.text}</span>{/if}</span>
          <span class="aktionen">
            <button class="rund" type="button" title={t("podcastAnsicht.werbung.anhoeren")} aria-label={t("podcastAnsicht.werbung.anhoeren")}
                    onclick={() => onanhoeren(s.von)}><i class="fa-solid fa-play"></i></button>
            <button class="rund" type="button" title={t("podcastAnsicht.werbung.keineWerbungHilfe")} aria-label={t("podcastAnsicht.werbung.keineWerbung")}
                    onclick={() => void w.verwerfen(s)}><i class="fa-solid fa-xmark"></i></button>
          </span>
        </li>
      {/each}
    </ol>
  {/if}
  {#if w.verworfen}
    <p class="rh-still rh-werbe-zurueck"><i class="fa-solid fa-check"></i>{t("podcastAnsicht.werbung.verworfen", { von: stelleText(w.verworfen.von) })}
      <button class="knopf still" type="button" onclick={() => void w.zurueckholen()}><i class="fa-solid fa-rotate-left"></i>{t("podcastAnsicht.werbung.rueckgaengig")}</button></p>
  {/if}
</section>
{/if}
