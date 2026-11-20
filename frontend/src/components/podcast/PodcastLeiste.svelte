<script lang="ts">
  // Seitenleiste der Podcasts (Entwurf podcasts.html): oben eine schlichte Wahl (alle, ungehört, gemerkt), darunter die
  // Abos als Facetten mit der Zahl ungehörter Folgen, mehrere wählbar; Reihenfolge per Ziehen an der Griffleiste.
  import { t } from "../../lib/i18n.svelte.js";
  import { FOLGENWAHL, type Folgenwahl } from "../../lib/podcasts";
  import type { Abo } from "../../lib/podcasts";
  import AboBild from "./AboBild.svelte";

  let { abos, gewaehlt, wahl, offen, onwahl, onabos, onordnen, onabonnieren, onzu }: {
    abos: Abo[];
    gewaehlt: number[];
    wahl: Folgenwahl;
    offen: boolean;
    onwahl: (w: Folgenwahl) => void;
    onabos: (ids: number[]) => void;
    onordnen: (ids: number[]) => void;
    onabonnieren: () => void;
    onzu: () => void;
  } = $props();

  const alleUngehoert = $derived(abos.reduce((s, a) => s + a.ungehoert, 0));
  let gezogen = $state<number | null>(null);

  function umschalten(id: number) {
    onabos(gewaehlt.includes(id) ? gewaehlt.filter((x) => x !== id) : [...gewaehlt, id]);
  }

  function abgelegt(ziel: number) {
    if (gezogen === null || gezogen === ziel) return;
    const ids = abos.map((a) => a.id).filter((id) => id !== gezogen);
    ids.splice(ids.indexOf(ziel), 0, gezogen);
    gezogen = null;
    onordnen(ids);
  }
</script>

<aside class="rh-filter" class:offen id="rh-podcast-leiste" aria-label={t("podcastAnsicht.abosUndFilter")}>
  <div class="rh-filter-oben rh-folgen-wahl">
    <div class="segment" role="group" aria-label={t("podcastAnsicht.welcheFolgen")}>
      {#each FOLGENWAHL as w (w)}
        <button type="button" class:aktiv={wahl === w} aria-pressed={wahl === w} title={w === "gemerkt" ? t("podcastAnsicht.gemerktHilfe") : undefined}
                onclick={() => onwahl(w)}>{t(`podcastAnsicht.wahl_${w}`)}</button>
      {/each}
    </div>
    <button class="rh-kopf-taste rh-filter-zu" type="button" aria-label={t("radio.schliessen")} title={t("radio.schliessen")} onclick={onzu}>
      <i class="fa-solid fa-xmark"></i></button>
  </div>
  <div class="rh-filter-rollt">
    <section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>{t("podcastAnsicht.abos")}</h3>
        <a href="/podcasts?verzeichnis=1" title={t("podcastAnsicht.abonnierenHilfe")} onclick={(e) => { e.preventDefault(); onabonnieren(); }}>{t("podcastAnsicht.abonnieren")}</a></div>
      {#if abos.length}
        <div class="rh-facetten rh-abos">
          <label class="rh-facette ohne-kennung">
            <input type="checkbox" checked={!gewaehlt.length} onchange={() => onabos([])} />
            <span>{t("podcastAnsicht.alleAbos")}</span><span class="rh-zahl" title={t("podcastAnsicht.ungehoert")}>{alleUngehoert || ""}</span>
          </label>
          {#each abos as a (a.id)}
            <label class="rh-facette rh-abo" class:gezogen={gezogen === a.id} title={a.autor} draggable="true"
                   ondragstart={(e) => { gezogen = a.id; e.dataTransfer?.setData("text/plain", String(a.id)); }}
                   ondragover={(e) => e.preventDefault()} ondrop={(e) => { e.preventDefault(); abgelegt(a.id); }} ondragend={() => (gezogen = null)}>
              <span class="rh-griff" aria-hidden="true"><i class="fa-solid fa-grip-vertical"></i></span>
              <input type="checkbox" checked={gewaehlt.includes(a.id)} onchange={() => umschalten(a.id)} />
              <AboBild abo={a} klein />
              <span class="rh-abo-name">{a.titel}{#if a.autoLaden} <i class="fa-solid fa-cloud-arrow-down rh-auto" title={t("podcastAnsicht.autoHilfe")}></i>{/if}</span>
              <span class="rh-zahl" title={t("podcastAnsicht.ungehoert")}>{a.ungehoert || ""}</span>
            </label>
          {/each}
        </div>
        <p class="rh-still rh-abos-hinweis"><i class="fa-solid fa-grip-vertical"></i>{t("podcastAnsicht.ordnenHinweis")}</p>
      {:else}
        <p class="rh-leer-facette">{t("podcastAnsicht.keineAbos")}</p>
      {/if}
    </section>
  </div>
</aside>
