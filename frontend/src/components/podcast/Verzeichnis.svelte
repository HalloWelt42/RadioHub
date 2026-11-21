<script lang="ts">
  // Abonnieren (Entwurf podcasts.html): Suche im Verzeichnis anstelle der Liste; schon abonnierte zeigen das, die übrigen
  // einen Knopf Abonnieren. Eine Adresse eines Feeds abonniert direkt. Woher ein Treffer stammt, steht nicht da: die
  // Namen der Verzeichnisse sind fremde Marken.
  import { untrack } from "svelte";
  import { t } from "../../lib/i18n.svelte.js";
  import { Verzeichnissuche, type Podcastquelle } from "../../lib/podcasts";
  import { Suchverlauf } from "../../lib/radio/suchverlauf";
  import Suchfeld from "../radio/Suchfeld.svelte";
  import AboBild from "./AboBild.svelte";

  const verlauf = new Suchverlauf("radiohub_podcast_verzeichnis");

  let { quelle, abonniert, onabonnieren, onzu }: {
    quelle: Podcastquelle;
    abonniert: (feed: string) => boolean;
    onabonnieren: (feed: string, titel: string) => Promise<void>;
    onzu: () => void;
  } = $props();

  // die Quelle wechselt nie; die Suche hält die beim Öffnen
  const suche = new Verzeichnissuche(untrack(() => quelle));
  const abonnieren = (feed: string, titel: string) => suche.abonnieren(feed, () => onabonnieren(feed, titel));
</script>

<section class="rh-verzeichnis">
  <div class="rh-verzeichnis-kopf">
    <h2><i class="fa-solid fa-plus"></i>{t("podcastAnsicht.abonnieren")}</h2>
    <Suchfeld wert={suche.text} gedaechtnis={verlauf} name="verzeichnis-suche" platzhalter={t("podcastAnsicht.verzeichnisSuchen")}
              beschriftung={t("podcastAnsicht.verzeichnisSuchen")} hilfe={t("podcastAnsicht.verzeichnisHinweis")} onsuche={(s) => suche.gesucht(s)} sofortFokus />
    <button class="knopf" type="button" onclick={onzu}><i class="fa-solid fa-arrow-left"></i>{t("podcastAnsicht.zurueckZuDenFolgen")}</button>
  </div>
  {#if suche.istFeed}
    <article class="rh-sender rh-fund"><div class="rh-sender-kern rh-fund-kern">
      <AboBild abo={{ titel: suche.text.trim(), bild: "" }} />
      <div class="name"><b>{suche.text.trim()}</b></div>
      <button class="knopf primaer" type="button" disabled={suche.arbeitet !== null} onclick={() => abonnieren(suche.text.trim(), suche.text.trim())}>
        <i class="fa-solid fa-plus"></i>{t("podcastAnsicht.feedAbonnieren")}</button>
    </div></article>
  {:else if suche.sucht && !suche.treffer}
    <div class="rh-ohne-treffer"><i class="fa-solid fa-spinner fa-spin"></i><b>{t("podcastAnsicht.laedt")}</b></div>
  {:else if suche.fehler}
    <div class="rh-ohne-treffer"><i class="fa-solid fa-triangle-exclamation"></i><b>{suche.fehler}</b></div>
  {:else if suche.treffer}
    {#each suche.treffer as f (f.feed)}
      <article class="rh-sender rh-fund"><div class="rh-sender-kern rh-fund-kern">
        <AboBild abo={{ titel: f.titel, bild: "" }} />
        <div class="name"><b>{f.titel}</b><div class="meta">{#if f.autor}<span>{f.autor}</span>{/if}</div></div>
        {#if abonniert(f.feed)}
          <span class="rh-stand fertig"><i class="fa-solid fa-check"></i>{t("podcastAnsicht.abonniert")}</span>
        {:else}
          <button class="knopf primaer" type="button" disabled={suche.arbeitet !== null} onclick={() => abonnieren(f.feed, f.titel)}>
            <i class="fa-solid {suche.arbeitet === f.feed ? 'fa-spinner fa-spin' : 'fa-plus'}"></i>{t("podcastAnsicht.abonnieren")}</button>
        {/if}
      </div></article>
    {:else}
      <div class="rh-ohne-treffer"><i class="fa-solid fa-magnifying-glass"></i><b>{t("podcastAnsicht.nichtsGefunden")}</b><span>{t("podcastAnsicht.nichtsGefundenHilfe")}</span></div>
    {/each}
  {/if}
  <p class="rh-still">{t("podcastAnsicht.verzeichnisHinweis")}</p>
</section>
