<script lang="ts">
  // Kopf eines gewählten Abos über der Liste (Entwurf podcasts.html): Bild, Titel, Autor, Beschreibung, Zahlen; der
  // Schalter "Neue herunterladen" (flacher Taster wie "Nur Favoriten"), Aktualisieren, Alle herunterladen, Anheften,
  // Abbestellen; darunter der Fortschritt von "Alle herunterladen".
  import { t } from "../../lib/i18n.svelte.js";
  import { dauerText, textAus } from "../../lib/podcasts/anzeige";
  import type { Abo, Ladeauftrag } from "../../lib/podcasts";
  import AboBild from "./AboBild.svelte";

  let { abo, auftrag, arbeitet, onauto, onaktualisieren, onalleladen, onanheften, onabbestellen }: {
    abo: Abo;
    auftrag: Ladeauftrag;
    arbeitet: boolean;
    onauto: (an: boolean) => void;
    onaktualisieren: () => void;
    onalleladen: () => void;
    onanheften: () => void;
    onabbestellen: () => void;
  } = $props();

  const laedtHier = $derived(auftrag.laeuft && auftrag.aboId === abo.id);
  const beschreibung = $derived(textAus(abo.beschreibung));
</script>

<section class="rh-abo-kopf">
  <AboBild {abo} gross />
  <div class="rh-abo-text">
    <h2>{abo.titel}</h2>
    {#if abo.autor}<p class="rh-still">{abo.autor}</p>{/if}
    {#if beschreibung}<p class="rh-abo-beschreibung">{beschreibung}</p>{/if}
    <div class="rh-abo-zahlen">
      <span>{t("podcastAnsicht.folgenZahl", { n: abo.folgen })}</span><span>{t("podcastAnsicht.ungehoertKopf", { n: abo.ungehoert })}</span>
      <span>{t("podcastAnsicht.heruntergeladenKopf", { n: abo.heruntergeladen })}</span><span>{t("podcastAnsicht.zusammen", { zeit: dauerText(abo.dauerGesamt) })}</span>
    </div>
  </div>
  <ak-taster art="flach" beschriftung={t("podcastAnsicht.neueLaden")} farbe="gruen" an={abo.autoLaden || undefined} hilfe={t("podcastAnsicht.neueLadenHilfe")}
             oninput={(e: Event) => onauto(!!(e.currentTarget as HTMLElement & { an?: boolean }).an)}></ak-taster>
  <div class="rh-detail-knoepfe rh-abo-knoepfe">
    <button class="knopf" type="button" disabled={arbeitet} onclick={onaktualisieren}><i class="fa-solid fa-rotate" class:fa-spin={arbeitet}></i>{t("podcastAnsicht.aktualisieren")}</button>
    <button class="knopf" type="button" disabled={auftrag.laeuft} onclick={onalleladen}><i class="fa-solid fa-download"></i>{t("podcastAnsicht.alleLaden")}</button>
    <button class="knopf" type="button" aria-pressed={abo.angeheftet} title={abo.angeheftet ? t("podcastAnsicht.loesenHilfe") : t("podcastAnsicht.anheftenHilfe")} onclick={onanheften}>
      <i class="fa-solid fa-thumbtack" class:rh-angeheftet={abo.angeheftet}></i>{abo.angeheftet ? t("podcastAnsicht.loesen") : t("podcastAnsicht.anheften")}</button>
    <button class="knopf" type="button" onclick={onabbestellen}><i class="fa-solid fa-trash-can"></i>{t("podcastAnsicht.abbestellen")}</button>
  </div>
  {#if laedtHier}
    <div class="rh-auftrag">
      <ak-led farbe="gruen" zustand={auftrag.angehalten ? "an" : "blinkt"} groesse="klein"></ak-led>
      <span>{t("podcastAnsicht.ladeVon", { fertig: auftrag.fertig, gesamt: auftrag.gesamt })}{#if auftrag.fehler}, {t("podcastAnsicht.ladenFehlgeschlagen", { n: auftrag.fehler })}{/if}</span>
      <div class="balken"><span style:width="{Math.round((auftrag.fertig / Math.max(1, auftrag.gesamt)) * 100)}%"></span></div>
      {#if auftrag.angehalten}
        <button class="knopf" type="button" onclick={() => auftrag.fortsetzen()}><i class="fa-solid fa-play"></i>{t("podcastAnsicht.fortsetzen")}</button>
      {:else}
        <button class="knopf" type="button" onclick={() => auftrag.anhalten()}><i class="fa-solid fa-pause"></i>{t("podcastAnsicht.anhalten")}</button>
      {/if}
      <button class="rund" type="button" aria-label={t("podcastAnsicht.abbrechen")} title={t("podcastAnsicht.abbrechen")} onclick={() => auftrag.abbrechen()}><i class="fa-solid fa-xmark"></i></button>
    </div>
  {/if}
</section>
