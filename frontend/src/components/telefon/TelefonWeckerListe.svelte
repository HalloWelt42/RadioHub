<script>
  import { untrack } from 'svelte';
  /** Wecker am Telefon (/wecker): Liste mit Schalter, Bearbeiten (Uhrzeit, Tage, Sender oder neueste Folge, Lautstärke). */
  import { appState } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { weckerdaten, weckerLaden, weckerSpeichern, weckerLoeschen } from '../../lib/telefon/weckerdaten.svelte.js';
  import { sperren, freigeben } from '../../lib/aktualisierung.svelte.js';

  let entwurf = $state(null);
  let meldung = $state('');
  const tageKurz = $derived(t('telefon.tageKurz').split(','));
  const STUNDEN = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
  const MINUTEN = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'));

  $effect(() => { weckerLaden(); });

  // Offene Bearbeitung hält eine Aktualisierung auf
  $effect(() => {
    const offen = !!entwurf;
    untrack(() => (offen ? sperren('wecker-bearbeiten') : freigeben('wecker-bearbeiten')));
    return () => untrack(() => freigeben('wecker-bearbeiten'));
  });

  function neu() {
    const sender = appState.favorites[0] || null;
    entwurf = { aktiv: true, stunde: '07', minute: '00', tage: [1, 2, 3, 4, 5], quelle: sender ? 'sender' : 'podcast',
                sender_uuid: sender?.uuid || '', podcast_id: appState.podcasts[0]?.id || null, lautstaerke: 60, anstieg_s: 60,
                schlummern_min: 9 };
    meldung = '';
  }

  function bearbeiten(w) {
    const [stunde, minute] = w.zeit.split(':');
    entwurf = { ...w, stunde, minute, tage: [...w.tage], sender_uuid: w.sender?.uuid || '' };
    meldung = '';
  }

  function tag(nr) {
    entwurf.tage = entwurf.tage.includes(nr) ? entwurf.tage.filter((x) => x !== nr) : [...entwurf.tage, nr].sort();
  }

  function senderZu(uuid, alt) {
    const s = appState.favorites.find((f) => f.uuid === uuid) || (alt?.uuid === uuid ? alt : null);
    return s ? { uuid: s.uuid, name: s.name, url: s.url, url_resolved: s.url_resolved, favicon: s.favicon } : null;
  }

  async function sichern() {
    const e = entwurf;
    try {
      await weckerSpeichern({ id: e.id, aktiv: e.aktiv, zeit: `${e.stunde}:${e.minute}`, tage: e.tage, quelle: e.quelle,
        sender: e.quelle === 'sender' ? senderZu(e.sender_uuid, e.sender) : null,
        podcast_id: e.quelle === 'podcast' ? Number(e.podcast_id) : null,
        lautstaerke: Number(e.lautstaerke), anstieg_s: Number(e.anstieg_s), schlummern_min: Number(e.schlummern_min) });
      entwurf = null;
    } catch (f) {
      meldung = f.message || t('telefon.fehler');
    }
  }

  async function umschalten(w) {
    await weckerSpeichern({ ...w, aktiv: !w.aktiv });
  }

  function quelleText(w) {
    if (w.quelle === 'sender') return w.sender?.name || t('telefon.sender');
    const p = appState.podcasts.find((x) => x.id === w.podcast_id);
    return `${t('telefon.folge')}: ${p?.title || ''}`;
  }
</script>

<div class="wecker">
  <p class="hinweis">{t('telefon.weckerHinweis')}</p>

  {#if entwurf}
    <section class="form">
      <span class="beschriftung">{t('telefon.uhrzeit')}</span>
      <div class="zeit">
        <select bind:value={entwurf.stunde} aria-label={t('telefon.uhrzeit')}>
          {#each STUNDEN as h}<option value={h}>{h}</option>{/each}
        </select>
        <span>:</span>
        <select bind:value={entwurf.minute} aria-label={t('telefon.uhrzeit')}>
          {#each MINUTEN as m}<option value={m}>{m}</option>{/each}
        </select>
      </div>

      <span class="beschriftung">{t('telefon.tage')}</span>
      <div class="tage">
        {#each tageKurz as name, i}
          <button class:an={entwurf.tage.includes(i + 1)} aria-pressed={entwurf.tage.includes(i + 1)} onclick={() => tag(i + 1)}>{name}</button>
        {/each}
      </div>

      <span class="beschriftung">{t('telefon.quelle')}</span>
      <div class="wahl">
        <button class:an={entwurf.quelle === 'sender'} onclick={() => (entwurf.quelle = 'sender')}>{t('telefon.sender')}</button>
        <button class:an={entwurf.quelle === 'podcast'} onclick={() => (entwurf.quelle = 'podcast')}>{t('telefon.folge')}</button>
      </div>
      {#if entwurf.quelle === 'sender'}
        <select bind:value={entwurf.sender_uuid} aria-label={t('telefon.senderWaehlen')}>
          {#if entwurf.sender && !appState.favorites.some((f) => f.uuid === entwurf.sender.uuid)}
            <option value={entwurf.sender.uuid}>{entwurf.sender.name}</option>
          {/if}
          {#each appState.favorites as f (f.uuid)}<option value={f.uuid}>{f.name}</option>{/each}
        </select>
      {:else}
        <select bind:value={entwurf.podcast_id} aria-label={t('telefon.aboWaehlen')}>
          {#each appState.podcasts as p (p.id)}<option value={p.id}>{p.title}</option>{/each}
        </select>
      {/if}

      <label class="regler"><span>{t('telefon.lautstaerke')}: {entwurf.lautstaerke} %</span>
        <input type="range" min="5" max="100" step="5" bind:value={entwurf.lautstaerke} /></label>
      <label class="regler"><span>{t('telefon.anstieg')}: {entwurf.anstieg_s}</span>
        <input type="range" min="0" max="300" step="15" bind:value={entwurf.anstieg_s} /></label>

      {#if meldung}<p class="hinweis fehler">{meldung}</p>{/if}
      <div class="wahl">
        <button onclick={() => (entwurf = null)}>{t('telefon.abbrechen')}</button>
        <button class="an" onclick={sichern}>{t('telefon.speichern')}</button>
      </div>
      {#if entwurf.id}
        <button class="loeschen" onclick={async () => { await weckerLoeschen(entwurf.id); entwurf = null; }}>{t('telefon.loeschen')}</button>
      {/if}
    </section>
  {:else}
    {#if !weckerdaten.liste.length}<p class="hinweis">{t('telefon.keineWecker')}</p>{/if}
    <ul class="liste">
      {#each weckerdaten.liste as w (w.id)}
        <li class="zeile">
          <button class="haupt" onclick={() => bearbeiten(w)}>
            <span class="uhr" class:aus={!w.aktiv}>{w.zeit}</span>
            <span class="text">
              <span class="tage-text">{w.tage.map((n) => tageKurz[n - 1]).join(' ')}</span>
              <span class="zusatz">{quelleText(w)}</span>
            </span>
          </button>
          <span class="schalter">
            <input type="checkbox" checked={w.aktiv} onchange={() => umschalten(w)} aria-label="{t('telefon.aktiv')} {w.zeit}" /></span>
        </li>
      {/each}
    </ul>
    <button class="gross" onclick={neu}><i class="fa-solid fa-plus"></i> {t('telefon.neuerWecker')}</button>
  {/if}
</div>

<style>
  .wecker { padding: 8px 0 16px; }
  .hinweis { margin: 8px 16px; color: var(--t-text-2); font-size: 15px; }
  .hinweis.fehler { color: var(--t-fehler); }
  .liste { list-style: none; margin: 0; padding: 0; }
  .zeile { display: flex; align-items: center; border-bottom: 1px solid var(--t-linie); }
  .haupt { flex: 1; min-width: 0; display: flex; align-items: center; gap: 16px; min-height: 72px; padding: 8px 8px 8px 16px;
    border: none; background: transparent; color: var(--t-text); text-align: left; font: inherit; }
  .uhr { font-size: 32px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .uhr.aus { color: var(--t-text-2); }
  .text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .tage-text { font-size: 15px; }
  .zusatz { font-size: 15px; color: var(--t-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .schalter { padding: 0 16px; }
  .schalter input { width: 28px; height: 28px; accent-color: var(--t-akzent); }
  .form { display: flex; flex-direction: column; gap: 8px; padding: 8px 16px; }
  .beschriftung { margin-top: 8px; font-size: 15px; color: var(--t-text-2); }
  .zeit { display: flex; align-items: center; gap: 8px; font-size: 28px; }
  select, .wahl button, .tage button, .loeschen, .gross {
    min-height: 48px;
    border: 1px solid var(--t-linie);
    border-radius: 12px;
    background: var(--t-flaeche);
    color: var(--t-text);
    font: inherit;
    font-size: 17px;
    padding: 0 10px;
    min-width: 0;
  }
  .zeit select { width: 88px; font-size: 24px; text-align: center; }
  .tage { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
  .tage button { padding: 0; font-size: 15px; }
  .wahl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .wahl button.an, .tage button.an { background: var(--t-akzent); border-color: var(--t-akzent); color: var(--t-akzent-text); font-weight: 600; }
  .regler { display: flex; flex-direction: column; gap: 4px; font-size: 15px; color: var(--t-text-2); margin-top: 8px; }
  .regler input { width: 100%; height: 32px; accent-color: var(--t-akzent); }
  .loeschen { color: var(--t-fehler); }
  .gross { display: flex; align-items: center; justify-content: center; gap: 10px; width: calc(100% - 32px); margin: 16px; }
</style>
