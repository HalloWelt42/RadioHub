<script lang="ts">
  // Abonnieren (Entwurf podcasts.html): Suche im Verzeichnis anstelle der Liste; schon abonnierte zeigen das, die übrigen
  // einen Knopf Abonnieren. Eine Adresse eines Feeds abonniert direkt. Woher ein Treffer stammt, steht nicht da: die
  // Namen der Verzeichnisse sind fremde Marken.
  import { t } from "../../lib/i18n.svelte.js";
  import type { Fundstueck, Podcastquelle } from "../../lib/podcasts";
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

  let text = $state("");
  let treffer = $state<Fundstueck[] | null>(null);
  let sucht = $state(false);
  let fehler = $state("");
  let arbeitet = $state<string | null>(null);
  let abbruch: AbortController | null = null;
  const istFeed = $derived(/^https?:\/\/\S+$/i.test(text.trim()));

  /** das Suchfeld meldet nach kurzer Pause (wie beim Radio); eine Adresse eines Feeds sucht nicht, sie abonniert direkt */
  function gesucht(s: string) {
    text = s;
    if (s.length < 2 || istFeed) { abbruch?.abort(); treffer = null; sucht = false; return; }
    void suchen(s);
  }

  async function suchen(s: string) {
    abbruch?.abort();
    const meiner = (abbruch = new AbortController());
    sucht = true;
    fehler = "";
    try {
      const r = await quelle.suchen(s, meiner.signal);
      if (meiner === abbruch) treffer = r;
    } catch (f) {
      if ((f as Error).name !== "AbortError") fehler = (f as Error).message;
    } finally {
      if (meiner === abbruch) sucht = false;
    }
  }

  async function abonnieren(feed: string, titel: string) {
    arbeitet = feed;
    try {
      await onabonnieren(feed, titel);
    } finally {
      arbeitet = null;
    }
  }
</script>

<section class="rh-verzeichnis">
  <div class="rh-verzeichnis-kopf">
    <h2><i class="fa-solid fa-plus"></i>{t("podcastAnsicht.abonnieren")}</h2>
    <Suchfeld wert={text} gedaechtnis={verlauf} name="verzeichnis-suche" platzhalter={t("podcastAnsicht.verzeichnisSuchen")}
              beschriftung={t("podcastAnsicht.verzeichnisSuchen")} hilfe={t("podcastAnsicht.verzeichnisHinweis")} onsuche={gesucht} sofortFokus />
    <button class="knopf" type="button" onclick={onzu}><i class="fa-solid fa-arrow-left"></i>{t("podcastAnsicht.zurueckZuDenFolgen")}</button>
  </div>
  {#if istFeed}
    <article class="rh-sender rh-fund"><div class="rh-sender-kern rh-fund-kern">
      <AboBild abo={{ titel: text.trim(), bild: "" }} />
      <div class="name"><b>{text.trim()}</b></div>
      <button class="knopf primaer" type="button" disabled={arbeitet !== null} onclick={() => abonnieren(text.trim(), text.trim())}>
        <i class="fa-solid fa-plus"></i>{t("podcastAnsicht.feedAbonnieren")}</button>
    </div></article>
  {:else if sucht && !treffer}
    <div class="rh-ohne-treffer"><i class="fa-solid fa-spinner fa-spin"></i><b>{t("podcastAnsicht.laedt")}</b></div>
  {:else if fehler}
    <div class="rh-ohne-treffer"><i class="fa-solid fa-triangle-exclamation"></i><b>{fehler}</b></div>
  {:else if treffer}
    {#each treffer as f (f.feed)}
      <article class="rh-sender rh-fund"><div class="rh-sender-kern rh-fund-kern">
        <AboBild abo={{ titel: f.titel, bild: "" }} />
        <div class="name"><b>{f.titel}</b><div class="meta">{#if f.autor}<span>{f.autor}</span>{/if}</div></div>
        {#if abonniert(f.feed)}
          <span class="rh-stand fertig"><i class="fa-solid fa-check"></i>{t("podcastAnsicht.abonniert")}</span>
        {:else}
          <button class="knopf primaer" type="button" disabled={arbeitet !== null} onclick={() => abonnieren(f.feed, f.titel)}>
            <i class="fa-solid {arbeitet === f.feed ? 'fa-spinner fa-spin' : 'fa-plus'}"></i>{t("podcastAnsicht.abonnieren")}</button>
        {/if}
      </div></article>
    {:else}
      <div class="rh-ohne-treffer"><i class="fa-solid fa-magnifying-glass"></i><b>{t("podcastAnsicht.nichtsGefunden")}</b><span>{t("podcastAnsicht.nichtsGefundenHilfe")}</span></div>
    {/each}
  {/if}
  <p class="rh-still">{t("podcastAnsicht.verzeichnisHinweis")}</p>
</section>
