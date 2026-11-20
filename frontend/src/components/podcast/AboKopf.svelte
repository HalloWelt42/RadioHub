<script lang="ts">
  // Kopf eines gewählten Abos über der Liste (Entwurf podcasts.html): Bild, Titel, Autor, Beschreibung, Zahlen; der
  // Schalter "Neue merken" (flacher Taster wie "Nur Favoriten"), Aktualisieren, Alle merken, Abbestellen; darunter der
  // Fortschritt von "Alle merken".
  import { t } from "../../lib/i18n.svelte.js";
  import { dauerText, textAus } from "../../lib/podcasts/anzeige";
  import type { Abo, Merkauftrag } from "../../lib/podcasts";
  import AboBild from "./AboBild.svelte";

  let { abo, auftrag, arbeitet, onauto, onaktualisieren, onallemerken, onabbestellen }: {
    abo: Abo;
    auftrag: Merkauftrag;
    arbeitet: boolean;
    onauto: (an: boolean) => void;
    onaktualisieren: () => void;
    onallemerken: () => void;
    onabbestellen: () => void;
  } = $props();

  const merktHier = $derived(auftrag.laeuft && auftrag.aboId === abo.id);
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
      <span>{t("podcastAnsicht.gemerktKopf", { n: abo.geladen })}</span><span>{t("podcastAnsicht.zusammen", { zeit: dauerText(abo.dauerGesamt) })}</span>
    </div>
  </div>
  <ak-taster art="flach" beschriftung={t("podcastAnsicht.neueMerken")} farbe="gruen" an={abo.autoLaden || undefined} hilfe={t("podcastAnsicht.neueMerkenHilfe")}
             oninput={(e: Event) => onauto(!!(e.currentTarget as HTMLElement & { an?: boolean }).an)}></ak-taster>
  <div class="rh-detail-knoepfe rh-abo-knoepfe">
    <button class="knopf" type="button" disabled={arbeitet} onclick={onaktualisieren}><i class="fa-solid fa-rotate" class:fa-spin={arbeitet}></i>{t("podcastAnsicht.aktualisieren")}</button>
    <button class="knopf" type="button" disabled={auftrag.laeuft} onclick={onallemerken}><i class="fa-solid fa-download"></i>{t("podcastAnsicht.alleMerken")}</button>
    <button class="knopf" type="button" onclick={onabbestellen}><i class="fa-solid fa-trash-can"></i>{t("podcastAnsicht.abbestellen")}</button>
  </div>
  {#if merktHier}
    <div class="rh-auftrag">
      <ak-led farbe="gruen" zustand={auftrag.angehalten ? "an" : "blinkt"} groesse="klein"></ak-led>
      <span>{t("podcastAnsicht.merkeVon", { fertig: auftrag.fertig, gesamt: auftrag.gesamt })}{#if auftrag.fehler}, {t("podcastAnsicht.merkenFehler", { n: auftrag.fehler })}{/if}</span>
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
