<script>
  /**
   * Podcasts am Telefon: /podcasts (Abos und gemerkte Folgen), /podcasts/gemerkt, /podcasts/<abo> (Folgen mit
   * Filter neu, ungehört, gemerkt), /podcasts/<abo>/<folge> (eine Folge). Die Hörposition merkt sich die Wiedergabe.
   */
  import { appState, actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { api } from '../../lib/api.js';
  import Bild from './Bild.svelte';

  const SEITE = 40;
  const FILTER = [['all', 'neu'], ['unplayed', 'ungehoert'], ['downloaded', 'gemerktKurz']];

  let filter = $state('all');
  let folgen = $state([]);
  let gesamt = $state(0);
  let laedt = $state(false);
  let fehler = $state(false);
  let folge = $state(null);

  const segs = $derived(appState.routeSegments || []);
  const gemerkt = $derived(segs[0] === 'gemerkt');
  const aboId = $derived(!gemerkt && segs[0] ? Number(segs[0]) : null);
  const folgeId = $derived(aboId && segs[1] ? Number(segs[1]) : null);
  const abo = $derived(appState.podcasts.find((p) => p.id === aboId) || null);

  async function laden(neu = true) {
    if (!aboId && !gemerkt) return;
    laedt = true;
    try {
      const ab = neu ? 0 : folgen.length;
      const r = gemerkt
        ? await api.getAllEpisodes({ limit: SEITE, offset: ab, filterStatus: 'downloaded' })
        : await api.getEpisodes(aboId, SEITE, ab, filter);
      folgen = neu ? r.episodes : [...folgen, ...r.episodes];
      gesamt = r.total;
      fehler = false;
    } catch {
      fehler = true;
    } finally {
      laedt = false;
    }
  }

  $effect(() => {
    aboId; gemerkt; filter;
    folgen = [];
    laden(true);
  });

  $effect(() => {
    folge = null;
    if (!folgeId) return;
    api.fetch(`/api/podcasts/episodes/${folgeId}`).then((f) => { folge = f; }).catch(() => { folge = null; });
  });

  function aboVon(f) {
    return appState.podcasts.find((p) => p.id === f.podcast_id) || { id: f.podcast_id, title: f.podcast_title };
  }

  function spielen(f) {
    const liste = folgen.length ? folgen : [f];
    actions.playEpisodeFromList(f, aboVon(f), liste);
  }

  function datum(wert) {
    if (!wert) return '';
    const d = new Date(wert.replace(' ', 'T'));
    return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function minuten(s) {
    return s > 0 ? `${Math.round(s / 60)} ${t('telefon.min')}` : '';
  }

  function rest(f) {
    if (f.is_played) return t('telefon.gehoert');
    if (f.resume_position > 0 && f.duration > 0) return `${Math.round(f.resume_position / f.duration * 100)} %`;
    return '';
  }

  function text(html) {
    // DOMParser lädt keine Bilder und führt nichts aus (anders als innerHTML im Dokument)
    return (new DOMParser().parseFromString(html || '', 'text/html').body.textContent || '').trim();
  }
</script>

<div class="podcasts">
  {#if folgeId}
    <button class="zurueck" onclick={() => actions.navigateTo(`/podcasts/${aboId}`)}>
      <i class="fa-solid fa-chevron-left"></i> {abo?.title || t('telefon.zurueck')}
    </button>
    {#if folge}
      <article class="folge">
        <Bild src={folge.image_url || folge.podcast_image_url ? api.getEpisodeImageUrl(folge.id) : null} symbol="fa-podcast" groesse={120} />
        <h2>{folge.title}</h2>
        <p class="zusatz">{[datum(folge.published_at), minuten(folge.duration), rest(folge)].filter(Boolean).join(' · ')}</p>
        <button class="gross" onclick={() => spielen(folge)}><i class="fa-solid fa-play"></i> {t('telefon.abspielen')}</button>
        <p class="beschreibung">{text(folge.description)}</p>
      </article>
    {:else}
      <p class="hinweis">{t('telefon.laden')}</p>
    {/if}
  {:else if aboId || gemerkt}
    <button class="zurueck" onclick={() => actions.navigateTo('/podcasts')}>
      <i class="fa-solid fa-chevron-left"></i> {t('telefon.abos')}
    </button>
    <h2 class="titel">{gemerkt ? t('telefon.gemerkt') : abo?.title || ''}</h2>
    {#if !gemerkt}
      <div class="filter" role="tablist">
        {#each FILTER as [wert, text]}
          <button role="tab" aria-selected={filter === wert} class:an={filter === wert} onclick={() => (filter = wert)}>
            {t('telefon.' + text)}
          </button>
        {/each}
      </div>
    {/if}
    {#if fehler}
      <p class="hinweis">{t('telefon.fehler')}</p>
    {:else if !folgen.length && !laedt}
      <p class="hinweis">{gemerkt ? t('telefon.keineGemerkt') : t('telefon.keineFolgen')}</p>
    {/if}
    <ul class="liste">
      {#each folgen as f (f.id)}
        <li class="zeile" class:laeuft={appState.currentEpisode?.id === f.id}>
          <button class="haupt" onclick={() => spielen(f)}>
            <span class="text">
              <span class="name">{f.title}</span>
              <span class="zusatz">
                {[gemerkt ? f.podcast_title : '', datum(f.published_at), minuten(f.duration), rest(f)].filter(Boolean).join(' · ')}
                {#if f.is_downloaded}<i class="fa-solid fa-circle-down gemerkt" title={t('telefon.gemerktKurz')}></i>{/if}
              </span>
            </span>
          </button>
          <button class="mehr" onclick={() => actions.navigateTo(`/podcasts/${f.podcast_id}/${f.id}`)}
            aria-label={f.title}><i class="fa-solid fa-chevron-right"></i></button>
        </li>
      {/each}
    </ul>
    {#if folgen.length < gesamt}
      <button class="gross leise" disabled={laedt} onclick={() => laden(false)}>{laedt ? t('telefon.laden') : t('telefon.mehr')}</button>
    {/if}
  {:else}
    <ul class="liste">
      <li class="zeile">
        <button class="haupt" onclick={() => actions.navigateTo('/podcasts/gemerkt')}>
          <Bild symbol="fa-circle-down" />
          <span class="text"><span class="name">{t('telefon.gemerkt')}</span></span>
          <i class="fa-solid fa-chevron-right pfeil"></i>
        </button>
      </li>
      {#each appState.podcasts as p (p.id)}
        <li class="zeile">
          <button class="haupt" onclick={() => actions.navigateTo(`/podcasts/${p.id}`)}>
            <Bild src={p.image_url ? api.getPodcastImageUrl(p.id) : null} symbol="fa-podcast" />
            <span class="text">
              <span class="name">{p.title}</span>
              {#if p.unplayed_count}<span class="zusatz">{p.unplayed_count} {t('telefon.ungehoert').toLowerCase()}</span>{/if}
            </span>
            <i class="fa-solid fa-chevron-right pfeil"></i>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .podcasts { padding: 4px 0 16px; }
  .hinweis { margin: 16px; color: var(--t-text-2); font-size: 15px; }
  .zurueck {
    display: flex;
    align-items: center;
    gap: 8px;
    max-width: 100%;
    min-height: 48px;
    padding: 0 16px;
    border: none;
    background: transparent;
    color: var(--t-akzent);
    font: inherit;
    font-size: 17px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .titel { margin: 0 16px 8px; font-size: 20px; font-weight: 700; overflow-wrap: anywhere; }
  .filter {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
    margin: 0 12px 8px;
  }
  .filter button {
    min-height: 44px;
    border: 1px solid var(--t-linie);
    border-radius: 22px;
    background: transparent;
    color: var(--t-text);
    font: inherit;
    font-size: 15px;
  }
  .filter button.an { background: var(--t-akzent); border-color: var(--t-akzent); color: var(--t-akzent-text); font-weight: 600; }
  .liste { list-style: none; margin: 0; padding: 0; }
  .zeile { display: flex; align-items: stretch; border-bottom: 1px solid var(--t-linie); }
  .haupt {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 68px;
    padding: 8px 8px 8px 16px;
    border: none;
    background: transparent;
    color: var(--t-text);
    text-align: left;
    font: inherit;
  }
  .text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .name { font-size: 17px; font-weight: 600; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
  .zusatz { font-size: 15px; color: var(--t-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .gemerkt { margin-left: 6px; color: var(--t-akzent); }
  .laeuft .name { color: var(--t-akzent); }
  .pfeil { color: var(--t-text-2); flex: none; }
  .mehr { width: 52px; flex: none; border: none; background: transparent; color: var(--t-text-2); font-size: 17px; }
  .gross {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    width: calc(100% - 32px);
    min-height: 52px;
    margin: 12px 16px;
    border: none;
    border-radius: 14px;
    background: var(--t-akzent);
    color: var(--t-akzent-text);
    font: inherit;
    font-size: 17px;
    font-weight: 600;
  }
  .gross.leise { background: var(--t-flaeche-2); color: var(--t-text); }
  .folge { display: flex; flex-direction: column; align-items: center; padding: 8px 0; }
  .folge h2 { margin: 12px 16px 4px; font-size: 20px; text-align: center; overflow-wrap: anywhere; }
  .folge .zusatz { white-space: normal; text-align: center; margin: 0 16px; }
  .beschreibung { align-self: stretch; margin: 4px 16px; color: var(--t-text-2); font-size: 15px; white-space: pre-line; overflow-wrap: anywhere; -webkit-user-select: text; user-select: text; }
</style>
