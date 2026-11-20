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

  let { eintrag: e, spielt, aufnahme, titel, offen, fokus, variantenOffen, spielend, kategorien,
        onspielen, ondetails, onvarianten, onfavorit, onausblenden, onaendern }: {
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
    onspielen: (e: SenderEintrag) => void;
    ondetails: () => void;
    onvarianten: () => void;
    onfavorit: () => void;
    onausblenden: () => void;
    onaendern: (teil: Partial<SenderEintrag>) => void;
  } = $props();

  const mehrere = $derived(e.varianten > 1);
  const led = $derived(spielt && aufnahme ? { farbe: "rot", zustand: "blinkt" } as const
    : spielt ? { farbe: "blau", zustand: "an" } as const : { farbe: "gelb", zustand: offen ? "an" : "aus" } as const);

  function halt(ev: Event, arbeit: () => void) {
    ev.stopPropagation();
    arbeit();
  }
</script>

{#snippet variantenKnopf(schmal: boolean)}
  <button class="knopf rh-varianten-knopf" class:rh-varianten-knopf-schmal={schmal} type="button" aria-expanded={variantenOffen}
          title={t("radio.variantenHilfe", { n: e.varianten })} onclick={(ev) => halt(ev, onvarianten)}>
    <i class="fa-solid fa-layer-group"></i><span><span class="rh-zahl">{e.varianten}</span> {t("radio.varianten")}</span></button>
{/snippet}

<article class="rh-sender" class:spielt class:aufnahme={spielt && aufnahme} class:gewaehlt={!spielt && offen} class:offen class:fokus data-uuid={e.uuid}>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="rh-sender-kern" onclick={() => onspielen(e)}>
    <span class="led"><ak-led farbe={led.farbe} zustand={led.zustand} groesse="klein" hilfe={spielt ? t("radio.spielt") : offen ? t("radio.gewaehlt") : t("radio.bereit")}></ak-led></span>
    <Logo uuid={e.uuid} name={e.name} logo={e.logo} />
    <div class="name"><b>{e.name}</b>
      <div class="meta">{#if e.land}<span class="rh-kennung">{e.land}</span>{/if}<span>{ort(e)}</span>
        {#if spielt && titel}<span class="rh-titel"><i class="fa-solid fa-volume-high"></i>{titel}</span>{/if}
        {#if mehrere}{@render variantenKnopf(true)}{/if}
      </div>
    </div>
    <div class="genres">{#each e.genres as g (g)}<span class="rh-genre">{g}</span>{/each}</div>
    <div class="guete-zelle"><Guete stufe={e.qualitaet} /><b>{qualitaetName(e.qualitaet)}</b><span>{format(e)}</span></div>
    <div class="stimmen">
      <button class="rund rh-auge-schmal" type="button" title={t("radio.ausblendenHilfe")} aria-label={t("radio.ausblendenVon", { name: e.name })}
              onclick={(ev) => halt(ev, onausblenden)}><i class="fa-solid fa-eye-slash"></i></button>
      <span title={t("radio.stimmenHilfeZeile")}><i class="fa-solid fa-thumbs-up"></i>{zahl(e.stimmen)}</span>
    </div>
    <div class="rh-aktionen">
      <span class="rh-varianten-zelle">{#if mehrere}{@render variantenKnopf(false)}{:else}<span class="rh-platz"></span>{/if}</span>
      <button class="rund" class:favorit={e.favorit} type="button" aria-pressed={e.favorit} aria-label={t("radio.favorit")}
              title={e.favorit ? t("radio.ausFavoriten") : t("radio.zuFavoriten")} onclick={(ev) => halt(ev, onfavorit)}>
        <i class="fa-{e.favorit ? 'solid' : 'regular'} fa-star"></i></button>
      <span class="auge-zelle"><button class="rund" type="button" title={t("radio.ausblendenHilfe")} aria-label={t("radio.ausblendenVon", { name: e.name })}
              onclick={(ev) => halt(ev, onausblenden)}><i class="fa-solid fa-eye-slash"></i></button></span>
      <button class="rund" type="button" aria-expanded={offen} title={t("radio.details")} aria-label={t("radio.detailsZu", { name: e.name })}
              onclick={(ev) => halt(ev, ondetails)}><i class="fa-solid fa-chevron-down"></i></button>
    </div>
  </div>
  {#if mehrere && variantenOffen}<Varianten eintrag={e} spielt={spielend} {onspielen} />{/if}
  {#if offen}<SenderDetail eintrag={e} {kategorien} {spielt} {onaendern} onvarianten={onvarianten} onneustart={onspielen} />{/if}
</article>
