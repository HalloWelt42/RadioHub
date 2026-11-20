<script lang="ts">
  // Seitenleiste der Schnellfilter (Entwurf rechner.html): oben fest das Gerät der Schnellwahl mit dem Kopf (Zahl der
  // aktiven Filter, Zurücksetzen, unter 1100 Pixel Schließen), darunter rollen die Facetten mit Zahlen unter allen
  // übrigen Filtern: Länder (welche, legen die Einstellungen fest), Genres, Qualität, Codec, eigene Bewertung, eigene
  // Kategorien.
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import { bewertungName, landName, qualitaetName, sterneVon, zahl } from "../../lib/radio/anzeige";
  import { aktive, umschalten, zurueckgesetzt, type Schnellfilter } from "../../lib/radio/schnellfilter";
  import type { Bewertung, Facette, Facetten, Qualitaet } from "../../lib/radio/typen";
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

  const GENRES_OBEN = 12;
  let alleGenres = $state(false);
  const anzahl = $derived(aktive(filter).length);
  // gewählte Genres stehen immer oben, auch wenn sie selten sind
  const genresOben = $derived((facetten?.genres ?? []).filter((g, i) => i < GENRES_OBEN || filter.genres.includes(g.wert)));
  const genresMehr = $derived((facetten?.genres ?? []).filter((g, i) => i >= GENRES_OBEN && !filter.genres.includes(g.wert)));

  type Gruppe = "laender" | "genres" | "qualitaet" | "bewertungen" | "kategorien";
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
      <div class="rh-facetten">{#each facetten?.laender ?? [] as f (f.wert)}{@render facette("laender", f)}{/each}</div>
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.genres")}</h3></div>
      <div class="rh-facetten">
        {#each genresOben as f (f.wert)}{@render facette("genres", f)}{/each}
        {#if alleGenres}{#each genresMehr as f (f.wert)}{@render facette("genres", f)}{/each}{/if}
      </div>
      {#if genresMehr.length}
        <button class="knopf still rh-mehr" type="button" onclick={() => (alleGenres = !alleGenres)}>
          {alleGenres ? t("radio.wenigerZeigen") : t("radio.alleZeigen", { n: genresOben.length + genresMehr.length })}</button>
      {/if}
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.qualitaetTitel")}</h3><span class="rh-still" title={t("radio.gemessenHilfe")}>{t("radio.gemessen")}</span></div>
      <div class="rh-facetten">{#each facetten?.qualitaet ?? [] as f (f.wert)}{@render facette("qualitaet", f)}{/each}</div>
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.codec")}</h3></div>
      <div class="rh-chips-wahl">
        {#each facetten?.codecs ?? [] as f (f.wert)}
          {@const an = filter.codecs.includes(f.wert)}
          <button type="button" class="chip wahl" class:an aria-pressed={an}
                  onclick={() => onaendern((x) => ({ ...x, codecs: umschalten(x.codecs, f.wert) }))}>{f.wert === "unbekannt" ? t("radio.unbekannt") : f.wert}<span class="rh-zahl">{zahl(f.anzahl)}</span></button>
        {/each}
      </div>
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.eigeneBewertung")}</h3></div>
      {#if facetten?.bewertungen.length}
        <div class="rh-facetten">{#each facetten.bewertungen as f (f.wert)}{@render facette("bewertungen", f)}{/each}</div>
      {:else}
        <p class="rh-leer-facette">{t("radio.keineBewertungen")}</p>
      {/if}
    </section>
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("radio.eigeneKategorien")}</h3>
        <a href="/einstellungen/radio/kategorien" onclick={(e) => gehe(e, "/einstellungen/radio/kategorien")}>{t("radio.verwalten")}</a></div>
      {#if facetten?.kategorien.length}
        <div class="rh-facetten">{#each facetten.kategorien as f (f.wert)}{@render facette("kategorien", f)}{/each}</div>
      {:else}
        <p class="rh-leer-facette">{t("radio.keineKategorien")}</p>
      {/if}
    </section>
  </div>
</aside>
