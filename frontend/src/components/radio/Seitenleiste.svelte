<script lang="ts">
  // Seitenleiste der Schnellfilter (Entwurf rechner.html): oben fest das Gerät der Schnellwahl mit dem Kopf (Zahl der
  // aktiven Filter, Zurücksetzen, unter 1100 Pixel Schließen), darunter rollen die Facetten mit Zahlen unter allen
  // übrigen Filtern: Länder (welche, legen die Einstellungen fest), Genres, Qualität, Codec mit Mindestbitrate, eigene
  // Bewertung, eigene Kategorien. Lange Gruppen zeigen nur die häufigsten Einträge (gewählte immer), den Rest auf Wunsch
  // (RAD-28: sonst lagen Genre, Qualität und Codec weit unten).
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import { bewertungName, landName, qualitaetName, sterneVon, zahl } from "../../lib/radio/anzeige";
  import { aktive, umschalten, zurueckgesetzt, type Schnellfilter } from "../../lib/radio/schnellfilter";
  import type { Bewertung, Facette, Facetten, Qualitaet } from "../../lib/radio/typen";
  import BitrateWahl from "./BitrateWahl.svelte";
  import Guete from "./Guete.svelte";
  import Schnellwahl from "./Schnellwahl.svelte";
  import Sterne from "./Sterne.svelte";

  let { filter, facetten, offen, onaendern, onzu }: {
    filter: Schnellfilter;
    facetten: Facetten | null;
    offen: boolean;
    onaendern: (arbeit: (f: Schnellfilter) => Schnellfilter) => void;
    onzu: () => void;
  } = $props();

  /** so viele Einträge zeigt eine Gruppe, bis man sie aufklappt */
  const OBEN = 6;
  let aufgeklappt = $state<Partial<Record<Gruppe, boolean>>>({});
  const anzahl = $derived(aktive(filter).length);

  type Gruppe = "laender" | "genres" | "qualitaet" | "bewertungen" | "kategorien";
  /** die häufigsten Einträge und gewählte (auch seltene) stehen immer da, der Rest nur aufgeklappt */
  function sichtbar(g: Gruppe, liste: Facette[]): { zeigen: Facette[]; versteckt: number } {
    if (aufgeklappt[g] || liste.length <= OBEN) return { zeigen: liste, versteckt: 0 };
    const zeigen = liste.filter((f, i) => i < OBEN || gewaehlt(g, f.wert));
    return { zeigen, versteckt: liste.length - zeigen.length };
  }
  const gewaehlt = (g: Gruppe, wert: string): boolean =>
    g === "kategorien" ? filter.kategorien.includes(Number(wert)) : (filter[g] as string[]).includes(wert);

  function waehlen(g: Gruppe, wert: string) {
    onaendern((f) => {
      if (g === "kategorien") return { ...f, kategorien: umschalten(f.kategorien, Number(wert)) };
      if (g === "qualitaet") return { ...f, qualitaet: umschalten(f.qualitaet, wert as Qualitaet) };
      if (g === "bewertungen") return { ...f, bewertungen: umschalten(f.bewertungen, wert as Bewertung) };
      return { ...f, [g]: umschalten(f[g], wert) };
    });
  }

  function gehe(e: MouseEvent, pfad: string) {
    e.preventDefault();
    actions.navigateTo(pfad);
  }
</script>

{#snippet facette(g: Gruppe, f: Facette)}
  {@const kennung = g === "laender" || g === "qualitaet" || g === "bewertungen"}
  <label class="rh-facette" class:ohne-kennung={!kennung}>
    <input type="checkbox" checked={gewaehlt(g, f.wert)} onchange={() => waehlen(g, f.wert)} />
    {#if g === "laender"}<span class="rh-kennung">{f.wert}</span>
    {:else if g === "qualitaet"}<Guete stufe={f.wert as Qualitaet} />
    {:else if g === "bewertungen"}
      {#if sterneVon(f.wert)}<Sterne n={sterneVon(f.wert)} />{:else}<span class="rh-kennung" title={bewertungName(f.wert)}><i class="fa-solid {f.wert === 'werbung' ? 'fa-rectangle-ad' : 'fa-tag'}"></i></span>{/if}
    {/if}
    <span>{g === "laender" ? landName(f.wert, f.name) : g === "qualitaet" ? qualitaetName(f.wert as Qualitaet) : g === "bewertungen" ? bewertungName(f.wert) : f.name}</span>
    <span class="rh-zahl">{zahl(f.anzahl)}</span>
  </label>
{/snippet}

{#snippet gruppe(g: Gruppe, liste: Facette[])}
  {@const s = sichtbar(g, liste)}
  <div class="rh-facetten">{#each s.zeigen as f (f.wert)}{@render facette(g, f)}{/each}</div>
  {#if s.versteckt || aufgeklappt[g]}
    {#if liste.length > OBEN}
      <button class="knopf still rh-mehr" type="button" aria-expanded={!!aufgeklappt[g]} onclick={() => (aufgeklappt = { ...aufgeklappt, [g]: !aufgeklappt[g] })}>
        {aufgeklappt[g] ? t("radio.wenigerZeigen") : t("radio.alleZeigen", { n: liste.length })}</button>
    {/if}
  {/if}
{/snippet}

<aside class="rh-filter" class:offen id="rh-filter" aria-label={t("radio.schnellfilter")}>
  <div class="rh-filter-oben">
    <Schnellwahl {filter} {onaendern}>
      {#snippet kopf()}
        <div class="rh-schnellwahl-kopf">
          <span class="ak-etikett">{t("radio.schnellfilter")}</span>
          <!-- Zurücksetzen trägt die Zahl der aktiven Filter als Leuchtziffer -->
          <button class="rh-kopf-taste" type="button" disabled={!anzahl} aria-label="{t('radio.alleZuruecksetzen')} ({t('radio.aktiv', { n: anzahl })})"
                  title="{t('radio.alleZuruecksetzen')} ({t('radio.aktiv', { n: anzahl })})" onclick={() => onaendern(zurueckgesetzt)}>
            <i class="fa-solid fa-rotate-left"></i><span class="rh-leuchtzahl" class:an={anzahl > 0}>{anzahl}</span></button>
          <button class="rh-kopf-taste rh-filter-zu" type="button" aria-label={t("radio.filterSchliessen")} title={t("radio.schliessen")} onclick={onzu}>
            <i class="fa-solid fa-xmark"></i></button>
        </div>
      {/snippet}
    </Schnellwahl>
  </div>
  <div class="rh-filter-rollt">
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.laender")}</h3>
        <a href="/einstellungen/radio/laender" title={t("radio.laenderWaehlenHilfe")} onclick={(e) => gehe(e, "/einstellungen/radio/laender")}>{t("radio.laenderWaehlen")}</a></div>
      {@render gruppe("laender", facetten?.laender ?? [])}
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.genres")}</h3></div>
      {@render gruppe("genres", facetten?.genres ?? [])}
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.qualitaetTitel")}</h3><span class="rh-still" title={t("radio.gemessenHilfe")}>{t("radio.gemessen")}</span></div>
      {@render gruppe("qualitaet", facetten?.qualitaet ?? [])}
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.codecUndBitrate")}</h3></div>
      <div class="rh-chips-wahl rh-chips-zwei">
        {#each facetten?.codecs ?? [] as f (f.wert)}
          {@const an = filter.codecs.includes(f.wert)}
          <button type="button" class="chip wahl" class:an aria-pressed={an}
                  onclick={() => onaendern((x) => ({ ...x, codecs: umschalten(x.codecs, f.wert) }))}>{f.wert === "unbekannt" ? t("radio.unbekannt") : f.wert}<span class="rh-zahl">{zahl(f.anzahl)}</span></button>
        {/each}
      </div>
      <BitrateWahl {filter} {onaendern} />
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.eigeneBewertung")}</h3></div>
      {#if facetten?.bewertungen.length}
        {@render gruppe("bewertungen", facetten.bewertungen)}
      {:else}
        <p class="rh-leer-facette">{t("radio.keineBewertungen")}</p>
      {/if}
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.eigeneKategorien")}</h3>
        <a href="/einstellungen/radio/kategorien" onclick={(e) => gehe(e, "/einstellungen/radio/kategorien")}>{t("radio.verwalten")}</a></div>
      {#if facetten?.kategorien.length}
        {@render gruppe("kategorien", facetten.kategorien)}
      {:else}
        <p class="rh-leer-facette">{t("radio.keineKategorien")}</p>
      {/if}
    </section>
  </div>
</aside>
