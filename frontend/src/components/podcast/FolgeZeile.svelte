<script lang="ts">
  // Zeile einer Folge (Entwurf podcasts.html), dasselbe Raster wie die Senderzeile: Licht, Bild, Titel mit Abo und Datum,
  // Stand, Länge, Herunterladen, Gehört, Details; aufgeklappt Beschreibung und Knöpfe.
  import { t } from "../../lib/i18n.svelte.js";
  import { datumKurz, megabyte, minuten, standVon, stelleText, tageHer, textAus } from "../../lib/podcasts/anzeige";
  import type { Abo, Folge } from "../../lib/podcasts";
  import AboBild from "./AboBild.svelte";

  let { folge, abo, spielt, offen, onspielen, onvorn, onladen, ongehoert, ondetails, onabo }: {
    folge: Folge;
    abo: Abo | undefined;
    spielt: boolean;
    offen: boolean;
    onspielen: () => void;
    onvorn: () => void;
    onladen: () => void;
    ongehoert: () => void;
    ondetails: () => void;
    onabo: () => void;
  } = $props();

  const stand = $derived(standVon(folge));
  const gehoert = $derived(stand.art === "gehoert");
  const aboTitel = $derived(abo?.titel ?? folge.aboTitel ?? "");
  const tage = $derived(tageHer(folge.datum));
  const datum = $derived(tage === 0 ? t("podcastAnsicht.heute") : tage === 1 ? t("podcastAnsicht.gestern")
    : datumKurz(folge.datum));
  const beschreibung = $derived(offen ? textAus(folge.beschreibung) : "");
</script>

<article class="rh-sender rh-folge" class:spielt class:gewaehlt={offen && !spielt} class:offen class:gehoert data-folge={folge.id}>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="rh-sender-kern" onclick={onspielen}>
    <span class="led"><ak-led farbe={spielt ? "blau" : "gelb"} zustand={spielt || offen ? "an" : "aus"} groesse="klein"></ak-led></span>
    <AboBild abo={{ titel: aboTitel, bild: folge.bild }} />
    <div class="name"><b>{folge.titel}</b>
      <div class="meta"><span>{aboTitel}</span><span>{datum}</span>
        {#if folge.heruntergeladen}<span class="rh-heruntergeladen" title={t("podcastAnsicht.heruntergeladenHilfe")}><i class="fa-solid fa-circle-down"></i>{t("podcastAnsicht.heruntergeladen")}</span>{/if}</div></div>
    <div class="stand-zelle">
      {#if stand.art === "gehoert"}<span class="rh-stand fertig"><i class="fa-solid fa-check"></i>{t("podcastAnsicht.gehoert")}</span>
      {:else if stand.art === "neu"}<span class="rh-stand neu"><ak-led farbe="gruen" zustand="an" groesse="klein"></ak-led>{t("podcastAnsicht.neu")}</span>
      {:else}<span class="rh-stand"><span class="balken"><span style:width="{Math.round(stand.anteil * 100)}%"></span></span>{t("podcastAnsicht.noch", { n: minuten(stand.rest) })}</span>{/if}
    </div>
    <div class="laenge">{folge.dauer ? t("podcastAnsicht.minuten", { n: minuten(folge.dauer) }) : ""}</div>
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div class="rh-aktionen rh-folgen-aktionen" onclick={(e) => e.stopPropagation()}>
      <button class="rund" class:an={folge.heruntergeladen} type="button" aria-pressed={folge.heruntergeladen} aria-label={t("podcastAnsicht.herunterladen")}
              title={folge.heruntergeladen ? t("podcastAnsicht.heruntergeladenLoeschen", { mb: megabyte(folge.groesse) }) : t("podcastAnsicht.herunterladen")} onclick={onladen}>
        <i class="fa-solid {folge.heruntergeladen ? 'fa-circle-down' : 'fa-download'}"></i></button>
      <button class="rund" class:an={gehoert} type="button" aria-pressed={gehoert} aria-label={t("podcastAnsicht.alsGehoert")}
              title={gehoert ? t("podcastAnsicht.gehoertZuruecksetzen") : t("podcastAnsicht.alsGehoert")} onclick={ongehoert}>
        <i class="fa-solid fa-check"></i></button>
      <button class="rund" type="button" aria-expanded={offen} aria-label={t("podcastAnsicht.details")} title={t("podcastAnsicht.details")} onclick={ondetails}>
        <i class="fa-solid fa-chevron-down"></i></button>
    </div>
  </div>
  {#if offen}
    <div class="rh-detail rh-folge-detail">
      {#if beschreibung}<p>{beschreibung}</p>{/if}
      <div class="rh-detail-knoepfe">
        <button class="knopf primaer" type="button" onclick={onspielen}><i class="fa-solid fa-play"></i>
          {stand.art === "laeuft" ? t("podcastAnsicht.weiterAb", { zeit: stelleText(folge.stelle) }) : t("podcastAnsicht.hoeren")}</button>
        {#if folge.stelle && !gehoert}<button class="knopf" type="button" onclick={onvorn}><i class="fa-solid fa-backward-fast"></i>{t("podcastAnsicht.vonVorn")}</button>{/if}
        <button class="knopf" type="button" onclick={ongehoert}><i class="fa-solid {gehoert ? 'fa-rotate-left' : 'fa-check'}"></i>
          {gehoert ? t("podcastAnsicht.alsUngehoert") : t("podcastAnsicht.alsGehoert")}</button>
        <button class="knopf" type="button" onclick={onladen}><i class="fa-solid {folge.heruntergeladen ? 'fa-trash-can' : 'fa-download'}"></i>
          {folge.heruntergeladen ? t("podcastAnsicht.downloadLoeschen", { mb: megabyte(folge.groesse) }) : t("podcastAnsicht.herunterladen")}</button>
        {#if aboTitel}<a class="knopf still" href="/podcasts/{folge.aboId}" onclick={(e) => { e.preventDefault(); onabo(); }}><i class="fa-solid fa-podcast"></i>{aboTitel}</a>{/if}
      </div>
    </div>
  {/if}
</article>
