<script lang="ts">
  // Tasten der Werbung in der Tastenreihe einer Folge (RAD-138): Überspringen mit Licht (gilt für das Abo), der Rest als Symbole.
  import { t } from "../../lib/i18n.svelte.js";
  import { stelleText } from "../../lib/podcasts/anzeige";
  import type { Abo, Folge } from "../../lib/podcasts";
  import type { Folgenwerbung } from "../../spieler/folgenwerbung.svelte";
  import Schalter from "../bausteine/Schalter.svelte";

  let { werbung: w, folge, abo, spielt }: { werbung: Folgenwerbung; folge: Folge; abo: Abo | undefined; spielt: boolean } = $props();
  const stand = $derived(w.stellen.length === 1 ? t("podcastAnsicht.werbung.zusammenEins", { zeit: stelleText(w.summe) })
    : w.stellen.length ? t("podcastAnsicht.werbung.zusammen", { n: w.stellen.length, zeit: stelleText(w.summe) }) : t("podcastAnsicht.werbung.keine"));
  const markieren = $derived(w.beginn === null ? t("podcastAnsicht.werbung.beginnt") : t("podcastAnsicht.werbung.endet", { von: stelleText(w.beginn) }));
</script>

{#if abo}<Schalter an={abo.werbungUeberspringen} farbe="bernstein" symbol="fa-rectangle-ad" text={t("podcastAnsicht.werbung.ueberspringen")}
          hilfe={`${t("podcastAnsicht.werbung.ueberspringenHilfe")}. ${stand}`} onwechsel={(an) => void w.ueberspringen(an)} />{/if}
{#if w.quellen.length}
  <button class="rund" type="button" disabled={!!w.auftrag} title={t("podcastAnsicht.werbung.suchen")} aria-label={t("podcastAnsicht.werbung.suchen")} onclick={() => void w.suchen()}>
    <i class="fa-solid {w.auftrag ? 'fa-circle-notch fa-spin' : 'fa-magnifying-glass'}"></i></button>
{/if}
{#if spielt}
  <button class="rund" class:an={w.beginn !== null} type="button" title={markieren} aria-label={markieren} onclick={w.markieren}>
    <i class="fa-solid {w.beginn === null ? 'fa-flag' : 'fa-flag-checkered'}"></i></button>
{/if}
{#if folge.gespeichert && w.stellen.length}
  <button class="rund" type="button" disabled={!!w.auftrag} title={t("podcastAnsicht.werbung.ohneSpeichern")} aria-label={t("podcastAnsicht.werbung.ohneSpeichern")} onclick={() => void w.ohneWerbung()}>
    <i class="fa-solid fa-scissors"></i></button>
{/if}
