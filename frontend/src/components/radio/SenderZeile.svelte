<script lang="ts">
  // Ein Sender der Liste am Rechner (Entwurf rechner.html): Leuchte (blau spielt, rot bei Aufnahme, gelb gewählt), Logo,
  // Name mit Land und Ort (beim spielenden der laufende Titel), Genres, Qualitätsleiste, Stimmen, dann Varianten,
  // Favorit, Auge und Details. Ein Klick auf die Zeile spielt; aufgeklappt folgen Varianten und Details.
  import { t } from "../../lib/i18n.svelte.js";
  import { format, ort, qualitaetName, zahl } from "../../lib/radio/anzeige";
  import type { Kategorie } from "../../lib/radio/quelle";
  import type { SenderEintrag } from "../../lib/radio/typen";
  import Guete from "./Guete.svelte";
  import Logo from "./Logo.svelte";
  import SenderDetail from "./SenderDetail.svelte";
  import Varianten from "./Varianten.svelte";
  import { einzelnAusgeblendet } from "../../lib/radio/bedienung.svelte";
  import { werbende } from "../../lib/radio/werbende.svelte";

  let { eintrag: e, spielt, aufnahme, titel, offen, fokus, variantenOffen, spielend, kategorien,
        onspielen, ondetails, onvarianten, onfavorit, onausblenden, oneinblenden, onaendern }: {
    eintrag: SenderEintrag;
    spielt: boolean;
    aufnahme: boolean;
    titel: string | null;
    offen: boolean;
    fokus: boolean;
    variantenOffen: boolean;
    /** Kennung des gerade spielenden Senders (für die Varianten) */
    spielend: string | null;
    kategorien: Kategorie[];
    /** `zeile`: gespielt aus den Varianten dieser Zeile */
    onspielen: (e: SenderEintrag, zeile?: SenderEintrag) => void;
    ondetails: () => void;
    onvarianten: () => void;
    onfavorit: () => void;
    onausblenden: () => void;
    /** ausgeblendet, aber als Favorit sichtbar: wieder einblenden */
    oneinblenden: () => void;
    onaendern: (teil: Partial<SenderEintrag>) => void;
  } = $props();

  const mehrere = $derived(e.varianten > 1);
  const ausgeblendet = $derived(einzelnAusgeblendet(e));
  const led = $derived(spielt && aufnahme ? { farbe: "rot", zustand: "blinkt" } as const
    : spielt ? { farbe: "blau", zustand: "an" } as const : { farbe: "gelb", zustand: offen ? "an" : "aus" } as const);

  function halt(ev: Event, arbeit: () => void) {
    ev.stopPropagation();
    arbeit();
  }
</script>

{#snippet variantenKnopf(schmal: boolean)}
  <button class="knopf rh-varianten-knopf" class:rh-varianten-knopf-schmal={schmal} class:aktiv={variantenOffen} type="button" aria-expanded={variantenOffen} aria-pressed={variantenOffen}
          title={t("radio.variantenHilfe", { n: e.varianten })} onclick={(ev) => halt(ev, onvarianten)}>
    <i class="fa-solid fa-layer-group"></i><span><span class="rh-zahl">{e.varianten}</span> {t("radio.varianten")}</span></button>
{/snippet}

{#snippet minusKnopf(klasse: string)}
  {#if ausgeblendet}
    <button class="rund {klasse}" type="button" title={t("radio.einblendenHilfe")} aria-label={t("radio.einblendenVon", { name: e.name })}
            onclick={(ev) => halt(ev, oneinblenden)}><i class="fa-solid fa-eye"></i></button>
  {:else}
    <button class="rund {klasse}" type="button" title={t("radio.ausblendenHilfe")} aria-label={t("radio.ausblendenVon", { name: e.name })}
            onclick={(ev) => halt(ev, onausblenden)}><i class="fa-solid fa-minus"></i></button>
  {/if}
{/snippet}

<article class="rh-sender" class:rh-ausgeblendet={ausgeblendet} class:spielt class:aufnahme={spielt && aufnahme} class:gewaehlt={!spielt && offen} class:offen class:fokus data-uuid={e.uuid}>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="rh-sender-kern" onclick={() => onspielen(e)}>
    <span class="led"><ak-led farbe={led.farbe} zustand={led.zustand} groesse="klein" hilfe={spielt ? t("radio.spielt") : offen ? t("radio.gewaehlt") : t("radio.bereit")}></ak-led></span>
    <Logo uuid={e.uuid} name={e.name} logo={e.logo} />
    <div class="name"><b title={e.name}>{e.name}</b>
      <div class="meta">{#if e.land}<span class="rh-kennung">{e.land}</span>{/if}<span>{ort(e)}</span>
        {#if spielt && titel}<span class="rh-titel"><i class="fa-solid fa-volume-high"></i>{titel}</span>{/if}
        {#if werbende.von(e.uuid)}{@const w = werbende.von(e.uuid)}<span class="rh-werbemarke-text" title={t(w?.ueberspringen ? "radio.werbungMarkeHilfe" : "radio.werbungMarkeAusHilfe", { n: w?.spots ?? 0 })}><i class="fa-solid fa-rectangle-ad"></i>{t("radio.werbungMarke")}</span>{/if}
        {#if ausgeblendet}<span class="rh-ausgeblendet-marke" title={t("radio.ausgeblendetFavoritHilfe")}><i class="fa-solid fa-eye-slash"></i>{t("radio.ausgeblendetFavorit")}</span>{/if}
        {#if mehrere}{@render variantenKnopf(true)}{/if}
      </div>
    </div>
    <div class="genres">{#each e.genres as g (g)}<span class="rh-genre">{g}</span>{/each}</div>
    <div class="guete-zelle"><Guete stufe={e.qualitaet} /><b>{qualitaetName(e.qualitaet)}</b><span>{format(e)}</span></div>
    <div class="stimmen">
      {@render minusKnopf("rh-auge-schmal")}
      <span title={t("radio.stimmenHilfeZeile")}><i class="fa-solid fa-thumbs-up"></i>{zahl(e.stimmen)}</span>
    </div>
    <div class="rh-aktionen">
      <span class="rh-varianten-zelle">{#if mehrere}{@render variantenKnopf(false)}{:else}<span class="rh-platz"></span>{/if}</span>
      <button class="rund" class:favorit={e.favorit} type="button" aria-pressed={e.favorit} aria-label={t("radio.favorit")}
              title={e.favorit ? t("radio.ausFavoriten") : t("radio.zuFavoriten")} onclick={(ev) => halt(ev, onfavorit)}>
        <i class="fa-{e.favorit ? 'solid' : 'regular'} fa-star"></i></button>
      <span class="auge-zelle">{@render minusKnopf("")}</span>
      <button class="rund" type="button" aria-expanded={offen} title={t("radio.details")} aria-label={t("radio.detailsZu", { name: e.name })}
              onclick={(ev) => halt(ev, ondetails)}><i class="fa-solid fa-chevron-down"></i></button>
    </div>
  </div>
  {#if mehrere && variantenOffen}<Varianten eintrag={e} spielt={spielend} onspielen={(v) => onspielen(v, e)} />{/if}
  {#if offen}<SenderDetail eintrag={e} {kategorien} {spielt} {onaendern} onneustart={onspielen} />{/if}
</article>
