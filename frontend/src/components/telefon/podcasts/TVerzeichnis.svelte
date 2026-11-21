<script lang="ts">
  // Abonnieren am Telefon (Entwurf telefon-podcasts.html, Zustand 6): Suche im Verzeichnis oder Adresse eines Feeds,
  // Treffer mit Plus oder "abonniert". Dieselbe Suche wie am Rechner (lib/podcasts/verzeichnissuche).
  import { untrack } from "svelte";
  import { t } from "../../../lib/i18n.svelte.js";
  import { Verzeichnissuche, type Podcastquelle } from "../../../lib/podcasts";
  import { Suchverlauf } from "../../../lib/radio/suchverlauf";
  import AboBild from "../../podcast/AboBild.svelte";
  import Suchfeld from "../../radio/Suchfeld.svelte";

  const verlauf = new Suchverlauf("radiohub_podcast_verzeichnis");

  let { quelle, abonniert, onabonnieren, onzurueck }: {
    quelle: Podcastquelle;
    abonniert: (feed: string) => boolean;
    onabonnieren: (feed: string, titel: string) => Promise<void>;
    onzurueck: () => void;
  } = $props();

  // die Quelle wechselt nie; die Suche hält die beim Öffnen
  const suche = new Verzeichnissuche(untrack(() => quelle));
  const abonnieren = (feed: string, titel: string) => suche.abonnieren(feed, () => onabonnieren(feed, titel));
</script>

<div class="t-kopf-zurueck tf-a-kopf">
  <button class="rund" type="button" aria-label={t("podcastAnsicht.telefon.zurueck")} title={t("podcastAnsicht.telefon.zurueck")} onclick={onzurueck}><i class="fa-solid fa-chevron-left"></i></button>
  <div><b>{t("podcastAnsicht.telefon.abonnierenTitel")}</b><span class="rh-still">{t("podcastAnsicht.telefon.abonnierenHilfe")}</span></div>
</div>
<div class="t-suche tp-suche">
  <Suchfeld wert={suche.text} gedaechtnis={verlauf} name="verzeichnis-suche" platzhalter={t("podcastAnsicht.verzeichnisSuchen")}
            beschriftung={t("podcastAnsicht.verzeichnisSuchen")} hilfe={t("podcastAnsicht.verzeichnisHinweis")} onsuche={(s) => suche.gesucht(s)} sofortFokus />
</div>
<div class="tf-liste">
  {#if suche.istFeed}
    <div class="tf-sender tp-abo"><AboBild abo={{ titel: suche.text.trim(), bild: "" }} /><div><b>{suche.text.trim()}</b></div>
      <span class="tf-aktionen"><button class="rund" type="button" disabled={suche.arbeitet !== null} aria-label={t("podcastAnsicht.feedAbonnieren")}
              title={t("podcastAnsicht.feedAbonnieren")} onclick={() => void abonnieren(suche.text.trim(), suche.text.trim())}><i class="fa-solid fa-plus"></i></button></span></div>
  {:else if suche.sucht && !suche.treffer}
    <p class="tf-hinweis">{t("podcastAnsicht.laedt")}</p>
  {:else if suche.fehler}
    <p class="tf-hinweis">{suche.fehler}</p>
  {:else if suche.treffer}
    {#each suche.treffer as f (f.feed)}
      <div class="tf-sender tp-abo"><AboBild abo={{ titel: f.titel, bild: "" }} />
        <div><b>{f.titel}</b>{#if f.autor}<div class="tf-meta"><span>{f.autor}</span></div>{/if}</div>
        {#if abonniert(f.feed)}
          <span class="tp-abonniert"><i class="fa-solid fa-check"></i>{t("podcastAnsicht.abonniert")}</span>
        {:else}
          <span class="tf-aktionen"><button class="rund" type="button" disabled={suche.arbeitet !== null} aria-label={t("podcastAnsicht.abonnieren")} title={t("podcastAnsicht.abonnieren")}
                  onclick={() => void abonnieren(f.feed, f.titel)}><i class="fa-solid {suche.arbeitet === f.feed ? 'fa-spinner fa-spin' : 'fa-plus'}"></i></button></span>
        {/if}
      </div>
    {:else}
      <p class="tf-hinweis">{t("podcastAnsicht.nichtsGefunden")}: {t("podcastAnsicht.nichtsGefundenHilfe")}</p>
    {/each}
  {/if}
  <p class="tf-hinweis">{t("podcastAnsicht.verzeichnisHinweis")}</p>
</div>
