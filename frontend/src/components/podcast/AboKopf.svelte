<script lang="ts">
  // Kopf eines gewählten Abos über der Liste (Entwurf podcasts.html): Bild, Titel, Autor, Beschreibung, Zahlen; der
  // Schalter "Neue speichern" (flacher Taster wie "Nur Favoriten"), Aktualisieren, Alle speichern, Anheften,
  // Abbestellen; darunter der Fortschritt von "Alle speichern" (in der Kellerwolke).
  import Schalter from "../radio/Schalter.svelte";
  import { t } from "../../lib/i18n.svelte.js";
  import { dauerText, textAus } from "../../lib/podcasts/anzeige";
  import type { Abo, Speicherauftrag } from "../../lib/podcasts";
  import AboBild from "./AboBild.svelte";
  import Langtext from "../radio/Langtext.svelte";

  let { abo, auftrag, arbeitet, kannSpeichern, onauto, onaktualisieren, onallespeichern, onanheften, onabbestellen, onwerbung }: {
    abo: Abo;
    auftrag: Speicherauftrag;
    kannSpeichern: boolean;
    arbeitet: boolean;
    onauto: (an: boolean) => void;
    onaktualisieren: () => void;
    onallespeichern: () => void;
    onanheften: () => void;
    onabbestellen: () => void;
    /** Schalter der Werbung (RAD-32): überspringen, neue Folgen prüfen */
    onwerbung: (teil: { ueberspringen?: boolean; pruefen?: boolean }) => void;
  } = $props();

  const speichertHier = $derived(auftrag.laeuft && auftrag.aboId === abo.id);
  const beschreibung = $derived(textAus(abo.beschreibung));
</script>

<section class="rh-abo-kopf">
  <AboBild {abo} gross />
  <div class="rh-abo-text">
    <div class="rh-abo-titel"><h2>{abo.titel}</h2>
      {#if kannSpeichern && abo.folgen}
        <!-- Vollständigkeit der gespeicherten Folgen (RAD-23, nur im großen Kopf) -->
        <span class="rh-vollstaendig" class:fertig={abo.gespeichert >= abo.folgen} title={t("podcastAnsicht.vollstaendigHilfe", { n: abo.gespeichert, von: abo.folgen })}>
          <i class="fa-solid {abo.gespeichert >= abo.folgen ? 'fa-circle-check' : 'fa-cloud'}"></i>
          <b>{abo.gespeichert}/{abo.folgen}</b>{t("podcastAnsicht.gespeichert")}
          <span class="balken"><span style:width="{Math.min(100, Math.round((abo.gespeichert / abo.folgen) * 100))}%"></span></span>
        </span>
      {/if}
    </div>
    {#if abo.autor}<p class="rh-still">{abo.autor}</p>{/if}
    {#if beschreibung}<Langtext text={beschreibung} klasse="rh-abo-beschreibung" />{/if}
    <div class="rh-abo-zahlen">
      <span>{t(abo.folgen === 1 ? "podcastAnsicht.folgenZahlEins" : "podcastAnsicht.folgenZahl", { n: abo.folgen })}</span><span>{t("podcastAnsicht.ungehoertKopf", { n: abo.ungehoert })}</span>
<span>{t("podcastAnsicht.zusammen", { zeit: dauerText(abo.dauerGesamt) })}</span>
      {#if abo.werbungFolgen}<span class="rh-werbemarke-text"><i class="fa-solid fa-rectangle-ad"></i>{abo.werbungFolgen === 1 ? t("podcastAnsicht.werbung.aboZahlEins") : t("podcastAnsicht.werbung.aboZahl", { n: abo.werbungFolgen })}</span>{/if}
    </div>
  </div>
  {#if kannSpeichern}
    <ak-taster art="flach" beschriftung={t("podcastAnsicht.neueSpeichern")} farbe="gruen" an={abo.autoLaden || undefined} hilfe={t("podcastAnsicht.neueSpeichernHilfe")}
               oninput={(e: Event) => onauto(!!(e.currentTarget as HTMLElement & { an?: boolean }).an)}></ak-taster>
  {/if}
  <div class="rh-detail-knoepfe rh-abo-knoepfe">
    <button class="knopf" type="button" disabled={arbeitet} onclick={onaktualisieren}><i class="fa-solid fa-rotate" class:fa-spin={arbeitet}></i>{t("podcastAnsicht.aktualisieren")}</button>
    <Schalter an={abo.werbungUeberspringen} farbe="bernstein" text={t("podcastAnsicht.werbung.aboUeberspringen")} hilfe={t("podcastAnsicht.werbung.aboUeberspringenHilfe")}
              onwechsel={(an) => onwerbung({ ueberspringen: an })} />
    <Schalter an={abo.werbungPruefen} farbe="bernstein" text={t("podcastAnsicht.werbung.aboPruefen")} hilfe={t("podcastAnsicht.werbung.aboPruefenHilfe")}
              onwechsel={(an) => onwerbung({ pruefen: an })} />
    {#if kannSpeichern}<button class="knopf" type="button" disabled={auftrag.laeuft} onclick={onallespeichern}><i class="fa-solid fa-cloud-arrow-up"></i>{t("podcastAnsicht.alleSpeichern")}</button>{/if}
    <button class="knopf" type="button" aria-pressed={abo.angeheftet} title={abo.angeheftet ? t("podcastAnsicht.loesenHilfe") : t("podcastAnsicht.anheftenHilfe")} onclick={onanheften}>
      <i class="fa-solid fa-thumbtack" class:rh-angeheftet={abo.angeheftet}></i>{abo.angeheftet ? t("podcastAnsicht.loesen") : t("podcastAnsicht.anheften")}</button>
    <button class="knopf" type="button" onclick={onabbestellen}><i class="fa-solid fa-trash-can"></i>{t("podcastAnsicht.abbestellen")}</button>
  </div>
  {#if speichertHier}
    <div class="rh-auftrag">
      <span>{t("podcastAnsicht.speichereVon", { fertig: auftrag.fertig, gesamt: auftrag.gesamt })}{#if auftrag.fehler}, {t("podcastAnsicht.speichernFehler", { n: auftrag.fehler })}{/if}</span>
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
