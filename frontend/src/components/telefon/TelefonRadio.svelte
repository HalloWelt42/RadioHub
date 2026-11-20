<script lang="ts">
  // Radio am Telefon (Entwurf mockups/radio-filter/telefon.html, RAD-7) im Rahmen des Appkerns: Suche und Knopf Filter,
  // Trefferzähler mit den aktiven Filtern als Chips, die Liste seitenweise mit Logo, Land, Qualität, Varianten und
  // Favorit; die Filter als Blatt von unten mit denselben Facetten wie am Rechner. Dieselbe Senderquelle und dieselben
  // Schnellfilter in der Adresse wie am Rechner; der kleine und der große Spieler bleiben die bisherigen (Etappe 4).
  import { onMount, untrack } from "svelte";
  import { Nachladen } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { appState } from "../../lib/store.svelte.js";
  import { filterzustand, senderquelle } from "../../lib/radio";
  import { bewertungName, format, landName, qualitaetName, sterneVon, zahl } from "../../lib/radio/anzeige";
  import { Radiobedienung } from "../../lib/radio/bedienung.svelte";
  import { aktive, ohne, umschalten, zuAbfrage, zurueckgesetzt, type Chip, type Schnellfilter } from "../../lib/radio/schnellfilter";
  import type { Bewertung, Facette, Qualitaet } from "../../lib/radio/typen";
  import Band from "../radio/Band.svelte";
  import Guete from "../radio/Guete.svelte";
  import Logo from "../radio/Logo.svelte";
  import Schnellwahl from "../radio/Schnellwahl.svelte";
  import Sterne from "../radio/Sterne.svelte";
  import Suchfeld from "../radio/Suchfeld.svelte";

  const bedienung = new Radiobedienung(senderquelle);
  const liste = bedienung.liste;
  let blatt = $state(false);

  const filter = $derived(filterzustand.filter);
  const chips = $derived(aktive(filter));
  const spielend = $derived((appState.currentStation as { uuid?: string } | null)?.uuid ?? null);
  const aendern = (arbeit: (f: Schnellfilter) => Schnellfilter) => filterzustand.aendern(arbeit);

  $effect(() => {
    const abfrage = zuAbfrage(filterzustand.filter);
    untrack(() => void liste.laden(abfrage));
  });
  onMount(() => {
    filterzustand.ansicht();
    void bedienung.bestandLaden();
    const zurueck = () => { if (window.location.pathname.startsWith("/radio")) filterzustand.ausAdresse(); };
    window.addEventListener("popstate", zurueck);
    return () => window.removeEventListener("popstate", zurueck);
  });
  // Vor und Zurück (auch am Sperrbildschirm) folgen der sichtbaren Liste (Vorgabe 7)
  $effect(() => {
    (appState as { stations: unknown[] }).stations = bedienung.fuerWiedergabe();
  });
  $effect(() => {
    const uuid = spielend;
    void liste.eintraege.length;
    untrack(() => bedienung.nachbarnVorbereiten(uuid));
  });

  function chipText(c: Chip): string {
    switch (c.art) {
      case "land": return landName(c.wert);
      case "qualitaet": return `${t("radio.qualitaetTitel")} ${qualitaetName(c.wert as Qualitaet)}`;
      case "bewertung": return bewertungName(c.wert);
      case "kategorie": return liste.facetten?.kategorien.find((k) => k.wert === c.wert)?.name ?? c.wert;
      case "favoriten": return t("radio.nurFavoriten");
      case "erreichbar": return t("radio.auchNichtErreichbare");
      case "stimmen": return `${t("radio.stimmen")} ${t("radio.abZahl", { n: zahl(Number(c.wert)) })}`;
      case "bitrate": return t("radio.abKbps", { n: c.wert });
      case "codec": return c.wert === "unbekannt" ? t("radio.unbekannt") : c.wert;
      default: return c.wert;
    }
  }

  type Gruppe = "laender" | "genres" | "qualitaet" | "codecs" | "bewertungen" | "kategorien";
  const an = (g: Gruppe, w: string) => (g === "kategorien" ? filter.kategorien.includes(Number(w)) : (filter[g] as string[]).includes(w));
  function waehlen(g: Gruppe, w: string) {
    aendern((f) => {
      if (g === "kategorien") return { ...f, kategorien: umschalten(f.kategorien, Number(w)) };
      if (g === "qualitaet") return { ...f, qualitaet: umschalten(f.qualitaet, w as Qualitaet) };
      if (g === "bewertungen") return { ...f, bewertungen: umschalten(f.bewertungen, w as Bewertung) };
      return { ...f, [g]: umschalten(f[g], w) };
    });
  }
</script>

{#snippet chipwahl(g: Gruppe, werte: Facette[])}
  <div class="t-chipwahl">
    {#each werte as f (f.wert)}
      <button type="button" class="chip wahl" class:an={an(g, f.wert)} aria-pressed={an(g, f.wert)} onclick={() => waehlen(g, f.wert)}>
        {#if g === "qualitaet"}<Guete stufe={f.wert as Qualitaet} />{qualitaetName(f.wert as Qualitaet)}
        {:else if g === "bewertungen"}{#if sterneVon(f.wert)}<Sterne n={sterneVon(f.wert)} />{:else if f.wert === "werbung"}<i class="fa-solid fa-rectangle-ad"></i>{/if}{bewertungName(f.wert)}
        {:else if g === "laender"}{landName(f.wert, f.name)}
        {:else if g === "codecs" && f.wert === "unbekannt"}{t("radio.unbekannt")}
        {:else}{f.name}{/if}<span class="rh-zahl">{zahl(f.anzahl)}</span></button>
    {/each}
  </div>
{/snippet}

<div class="tf-radio">
  <div class="t-suche">
    <Suchfeld wert={filter.suche} onsuche={(s) => aendern((f) => ({ ...f, suche: s }))} />
    <button class="knopf" type="button" aria-expanded={blatt} onclick={() => (blatt = true)}><i class="fa-solid fa-sliders"></i>{t("radio.filter")}<span class="pille">{chips.length}</span></button>
  </div>
  <div class="t-chips">
    <span class="t-treffer" title={t("radio.trefferHilfe")}><ak-segmente art="7" stellen="5" farbe="gruen" text={liste.gesamt === null ? "-----" : zahl(liste.gesamt)}></ak-segmente>{t("radio.treffer")}</span>
    {#each chips as c (`${c.art}:${c.wert}`)}
      <span class="chip">{chipText(c)}<button type="button" aria-label={t("radio.filterEntfernen")} onclick={() => aendern((f) => ohne(f, c))}><i class="fa-solid fa-xmark"></i></button></span>
    {/each}
  </div>
  <div class="tf-liste">
    {#if bedienung.bestand?.ausgeblendet}
      <p class="rh-hinweis t-hinweis"><ak-led farbe="bernstein" zustand="an" groesse="klein"></ak-led><span><b>{zahl(bedienung.bestand.ausgeblendet)}</b> {t("radio.telefon.durchRegelnAus")}</span></p>
    {/if}
    {#if !liste.geladen}
      <p class="tf-hinweis">{t("telefon.laden")}</p>
    {:else if liste.fehler && !liste.eintraege.length}
      <p class="tf-hinweis">{t("telefon.fehler")}</p>
    {:else if !liste.eintraege.length}
      <p class="tf-hinweis">{filter.nurFavoriten && chips.length === 1 ? t("telefon.keineFavoriten") : t("telefon.keineTreffer")}</p>
      {#if chips.length}<button class="knopf" type="button" onclick={() => aendern(zurueckgesetzt)}>{t("radio.alleZuruecksetzen")}</button>{/if}
    {:else}
      {#each liste.eintraege as e (e.uuid)}
        {@const spielt = spielend === e.uuid}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <div class="tf-sender" class:spielt onclick={() => void bedienung.spielen(e)}>
          <Logo uuid={e.uuid} name={e.name} logo={e.logo} />
          <div><b>{e.name}</b>
            <div class="tf-meta">{#if e.land}<span class="rh-kennung">{e.land}</span>{/if}<Guete stufe={e.qualitaet} /><span>{format(e)}</span>
              {#if e.varianten > 1}<span class="t-var"><i class="fa-solid fa-layer-group"></i>{t("radio.variantenZahl", { n: e.varianten })}</span>{/if}</div>
            {#if spielt}<div class="t-titel"><i class="fa-solid fa-volume-high"></i>{appState.streamTitle || t("radio.spielt")}</div>{/if}
          </div>
          <button class="rund" class:favorit={e.favorit} type="button" aria-pressed={e.favorit} aria-label={e.favorit ? t("telefon.favoritAus") : t("telefon.favoritAn")}
                  title={e.favorit ? t("telefon.favoritAus") : t("telefon.favoritAn")} onclick={(ev) => { ev.stopPropagation(); void bedienung.favorit(e); }}>
            <i class="fa-{e.favorit ? 'solid' : 'regular'} fa-star"></i></button>
        </div>
      {/each}
      <Nachladen geladen={liste.eintraege.length} gesamt={liste.gesamt} laedt={liste.laedtMehr} fehler={liste.fehler} onmehr={() => void liste.mehr()} einheit={t("radio.geladen")} />
    {/if}
  </div>
</div>

{#if blatt}
  <button class="t-schleier" type="button" aria-label={t("radio.filterSchliessen")} onclick={() => (blatt = false)}></button>
  <div class="t-blatt" role="dialog" aria-label={t("radio.filter")}>
    <div class="t-blatt-kopf"><h2>{t("radio.filter")}</h2>
      <button class="knopf still" type="button" disabled={!chips.length} onclick={() => aendern(zurueckgesetzt)}>{t("radio.telefon.zuruecksetzen")}</button>
      <button class="rund" type="button" aria-label={t("radio.schliessen")} onclick={() => (blatt = false)}><i class="fa-solid fa-xmark"></i></button></div>
    <div class="t-blatt-rollt">
      <Schnellwahl {filter} onaendern={aendern} />
      <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>{t("radio.laender")}</h3></div>{@render chipwahl("laender", liste.facetten?.laender ?? [])}</section>
      <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>{t("radio.genres")}</h3></div>{@render chipwahl("genres", liste.facetten?.genres ?? [])}</section>
      <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>{t("radio.qualitaetTitel")}</h3><span class="rh-still">{t("radio.gemessen")}</span></div>{@render chipwahl("qualitaet", liste.facetten?.qualitaet ?? [])}</section>
      <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>{t("radio.codec")}</h3></div>{@render chipwahl("codecs", liste.facetten?.codecs ?? [])}</section>
      <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>{t("radio.eigeneBewertung")}</h3></div>
        {#if liste.facetten?.bewertungen.length}{@render chipwahl("bewertungen", liste.facetten.bewertungen)}{:else}<p class="rh-leer-facette">{t("radio.keineBewertungen")}</p>{/if}</section>
      <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>{t("radio.eigeneKategorien")}</h3></div>
        {#if liste.facetten?.kategorien.length}{@render chipwahl("kategorien", liste.facetten.kategorien)}{:else}<p class="rh-leer-facette">{t("radio.keineKategorien")}</p>{/if}</section>
    </div>
    <div class="t-blatt-fuss"><button class="knopf primaer" type="button" onclick={() => (blatt = false)}><i class="fa-solid fa-check"></i>
      {t("radio.telefon.zeigen", { n: liste.gesamt === null ? "-" : zahl(liste.gesamt) })}</button></div>
  </div>
{/if}
<Band bind:inhalt={bedienung.band} />
