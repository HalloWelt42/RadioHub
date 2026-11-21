<script>
  import { untrack } from 'svelte';
  /** Wecker am Telefon (/wecker): Liste mit Schalter, Bearbeiten (Uhrzeit, Tage, Sender oder neueste Folge, Lautstärke). */
  import { appState } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { weckerdaten, weckerLaden, weckerSpeichern, weckerLoeschen } from '../../lib/telefon/weckerdaten.svelte.js';
  import { WECKTOENE, VORGABE } from '../../lib/telefon/wecktoene.js';
  import { wecktonAn, wecktonAus } from '../../lib/telefon/weckton.js';
  import { weckerablage } from '$ziel/telefon';

  let entwurf = $state(null);
  let meldung = $state('');
  // Hörprobe des Wecktons im Entwurf: läuft, bis angehalten, ein anderer Ton gewählt oder die Bearbeitung geschlossen wird
  let probe = $state(false);
  const tageKurz = $derived(t('telefon.tageKurz').split(','));
  const STUNDEN = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
  const MINUTEN = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'));

  // Sender zur Wahl: die Favoriten, abspielbar (woher, sagt das Bauziel)
  let favoriten = $state([]);
  $effect(() => {
    weckerLaden();
    weckerablage.sender().then((s) => (favoriten = s)).catch(() => (favoriten = []));
  });


  function neu() {
    const sender = favoriten[0] || null;
    entwurf = { aktiv: true, stunde: '07', minute: '00', tage: [1, 2, 3, 4, 5],
                quelle: sender || !weckerablage.faehig.podcast ? 'sender' : 'podcast',
                sender_uuid: sender?.uuid || '', podcast_id: appState.podcasts[0]?.id || null, lautstaerke: 60, anstieg_s: 60,
                schlummern_min: 9, weckton: VORGABE };
    meldung = '';
  }

  function bearbeiten(w) {
    const [stunde, minute] = w.zeit.split(':');
    entwurf = { ...w, stunde, minute, tage: [...w.tage], sender_uuid: w.sender?.uuid || '', weckton: w.weckton || VORGABE };
    meldung = '';
  }

  function tag(nr) {
    entwurf.tage = entwurf.tage.includes(nr) ? entwurf.tage.filter((x) => x !== nr) : [...entwurf.tage, nr].sort();
  }

  function senderZu(uuid, alt) {
    const s = favoriten.find((f) => f.uuid === uuid) || (alt?.uuid === uuid ? alt : null);
    return s ? { uuid: s.uuid, name: s.name, url: s.url, url_resolved: s.url_resolved, favicon: s.favicon } : null;
  }

  async function sichern() {
    const e = entwurf;
    try {
      await weckerSpeichern({ id: e.id, aktiv: e.aktiv, zeit: `${e.stunde}:${e.minute}`, tage: e.tage, quelle: e.quelle,
        sender: e.quelle === 'sender' ? senderZu(e.sender_uuid, e.sender) : null,
        podcast_id: e.quelle === 'podcast' ? Number(e.podcast_id) : null,
        lautstaerke: Number(e.lautstaerke), anstieg_s: Number(e.anstieg_s), schlummern_min: Number(e.schlummern_min),
        weckton: e.weckton });
      entwurf = null;
    } catch (f) {
      meldung = f.message || t('telefon.fehler');
    }
  }

  function probeSchalten() {
    if (probe) { wecktonAus(); probe = false; return; }
    try { wecktonAn(entwurf.weckton, Number(entwurf.lautstaerke) / 100); probe = true; } catch { /* ohne Web Audio keine Hörprobe */ }
  }

  // ein anderer Ton oder eine andere Lautstärke klingt sofort; ohne Entwurf ist die Probe aus
  $effect(() => {
    const e = entwurf;
    if (!e) { untrack(() => { if (probe) { wecktonAus(); probe = false; } }); return; }
    const id = e.weckton, laut = Number(e.lautstaerke) / 100;
    untrack(() => { if (probe) wecktonAn(id, laut); });
  });
  $effect(() => () => untrack(() => { if (probe) wecktonAus(); }));

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
  <p class="tf-hinweis">{t('telefon.weckerHinweis')}</p>

  {#if entwurf}
    <section class="form">
      <span class="beschriftung">{t('telefon.uhrzeit')}</span>
      <div class="tf-zeit">
        <select name="wecker-stunde" bind:value={entwurf.stunde} aria-label={t('telefon.uhrzeit')}>
          {#each STUNDEN as h}<option value={h}>{h}</option>{/each}
        </select>
        <span>:</span>
        <select name="wecker-minute" bind:value={entwurf.minute} aria-label={t('telefon.uhrzeit')}>
          {#each MINUTEN as m}<option value={m}>{m}</option>{/each}
        </select>
      </div>

      <span class="beschriftung">{t('telefon.tage')}</span>
      <div class="tage">
        {#each tageKurz as name, i}
          <button class:tf-an={entwurf.tage.includes(i + 1)} aria-pressed={entwurf.tage.includes(i + 1)} onclick={() => tag(i + 1)}>{name}</button>
        {/each}
      </div>

      <span class="beschriftung">{t('telefon.quelle')}</span>
      {#if weckerablage.faehig.podcast}
      <div class="tf-wahl">
        <button class:tf-an={entwurf.quelle === 'sender'} onclick={() => (entwurf.quelle = 'sender')}>{t('telefon.sender')}</button>
        <button class:tf-an={entwurf.quelle === 'podcast'} onclick={() => (entwurf.quelle = 'podcast')}>{t('telefon.folge')}</button>
      </div>
      {/if}
      {#if entwurf.quelle === 'sender'}
        <select name="wecker-sender" bind:value={entwurf.sender_uuid} aria-label={t('telefon.senderWaehlen')}>
          {#if entwurf.sender && !favoriten.some((f) => f.uuid === entwurf.sender.uuid)}
            <option value={entwurf.sender.uuid}>{entwurf.sender.name}</option>
          {/if}
          {#each favoriten as f (f.uuid)}<option value={f.uuid}>{f.name}</option>{/each}
        </select>
        {#if !favoriten.length && !entwurf.sender}<p class="tf-hinweis">{t('telefon.keineFavoriten')}</p>{/if}
      {:else}
        <select name="wecker-abo" bind:value={entwurf.podcast_id} aria-label={t('telefon.aboWaehlen')}>
          {#each appState.podcasts as p (p.id)}<option value={p.id}>{p.title}</option>{/each}
        </select>
      {/if}

      <span class="beschriftung">{t('telefon.weckton')}</span>
      <div class="tonwahl">
        <select name="wecker-weckton" bind:value={entwurf.weckton} aria-label={t('telefon.weckton')}>
          {#each WECKTOENE as id (id)}<option value={id}>{t(`telefon.ton_${id}`)}</option>{/each}
        </select>
        <button class="probe" class:tf-an={probe} aria-pressed={probe} onclick={probeSchalten}
                aria-label={probe ? t('telefon.tonAnhalten') : t('telefon.tonAnhoeren')} title={probe ? t('telefon.tonAnhalten') : t('telefon.tonAnhoeren')}>
          <i class="fa-solid {probe ? 'fa-stop' : 'fa-play'}"></i></button>
      </div>
      <p class="tf-klein">{t('telefon.wecktonHinweis')}</p>

      <label class="regler"><span>{t('telefon.lautstaerke')}: {entwurf.lautstaerke} %</span>
        <input name="wecker-lautstaerke" type="range" min="5" max="100" step="5" bind:value={entwurf.lautstaerke} /></label>
      <label class="regler"><span>{t('telefon.anstieg')}: {entwurf.anstieg_s}</span>
        <input name="wecker-anstieg" type="range" min="0" max="600" step="15" bind:value={entwurf.anstieg_s} /></label>
      <label class="regler"><span>{t('telefon.schlummerdauer')}: {entwurf.schlummern_min}</span>
        <input name="wecker-schlummern" type="range" min="1" max="60" step="1" bind:value={entwurf.schlummern_min} /></label>

      {#if meldung}<p class="tf-hinweis tf-fehler">{meldung}</p>{/if}
      <div class="tf-wahl">
        <button onclick={() => (entwurf = null)}>{t('telefon.abbrechen')}</button>
        <button class="tf-an" onclick={sichern}>{t('telefon.speichern')}</button>
      </div>
      {#if entwurf.id}
        <button class="loeschen" onclick={async () => { await weckerLoeschen(entwurf.id); entwurf = null; }}>{t('telefon.loeschen')}</button>
      {/if}
    </section>
  {:else}
    {#if !weckerdaten.liste.length}<p class="tf-hinweis">{t('telefon.keineWecker')}</p>{/if}
    <ul class="liste">
      {#each weckerdaten.liste as w (w.id)}
        <li class="tf-zeile">
          <button class="tf-haupt" onclick={() => bearbeiten(w)}>
            <span class="uhr" class:tf-aus={!w.aktiv}>{w.zeit}</span>
            <span class="tf-text">
              <span class="tage-text">{w.tage.map((n) => tageKurz[n - 1]).join(' ')}</span>
              <span class="zusatz">{quelleText(w)}</span>
            </span>
          </button>
          <span class="tf-schalter">
            <input name="wecker-aktiv-{w.id}" type="checkbox" checked={w.aktiv} onchange={() => umschalten(w)} aria-label="{t('telefon.aktiv')} {w.zeit}" /></span>
        </li>
      {/each}
    </ul>
    <button class="tf-gross" onclick={neu}><i class="fa-solid fa-plus"></i> {t('telefon.neuerWecker')}</button>
  {/if}
</div>

<style>
  .wecker { padding: 8px 0 16px; }
  .tf-hinweis { margin: 8px 0; color: var(--t-text-2); font-size: 15px; }
  .tf-hinweis.tf-fehler { color: var(--t-fehler); }
  .liste { list-style: none; margin: 0; padding: 0; }
  .tf-zeile { display: flex; align-items: center; border-bottom: 1px solid var(--rand); }
  .tf-haupt { flex: 1; min-width: 0; display: flex; align-items: center; gap: 16px; min-height: 72px; padding: 8px 8px 8px 0;
    border: none; background: transparent; color: var(--t-text); text-align: left; font: inherit; }
  .uhr { font-size: 32px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .uhr.tf-aus { color: var(--t-text-2); }
  .tf-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .tage-text { font-size: 15px; }
  .zusatz { font-size: 15px; color: var(--t-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tf-schalter { padding: 0; }
  .tf-schalter input { width: 28px; height: 28px; accent-color: var(--t-akzent); }
  .form { display: flex; flex-direction: column; gap: 8px; padding: 8px 0; }
  .beschriftung { margin-top: 8px; font-size: 15px; color: var(--t-text-2); }
  .tf-zeit { display: flex; align-items: center; gap: 8px; font-size: 28px; }
  select, .tf-wahl button, .tage button, .loeschen, .tf-gross, .probe {
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
  .tf-zeit select { width: 88px; font-size: 24px; text-align: center; }
  .tage { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
  .tage button { padding: 0; font-size: 15px; }
  .tf-wahl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .tf-wahl button.tf-an, .tage button.tf-an { background: var(--t-akzent-flaeche); border-color: var(--t-akzent-flaeche); color: var(--t-akzent-text); font-weight: 600; }
  .tonwahl { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; }
  .probe { aspect-ratio: 1; display: grid; place-items: center; padding: 0; }
  .probe.tf-an { background: var(--t-akzent-flaeche); border-color: var(--t-akzent-flaeche); color: var(--t-akzent-text); }
  .tf-klein { margin: 0; font-size: 15px; color: var(--t-text-2); overflow-wrap: anywhere; }
  .regler { display: flex; flex-direction: column; gap: 4px; font-size: 15px; color: var(--t-text-2); margin-top: 8px; }
  .regler input { width: 100%; height: 32px; accent-color: var(--t-akzent); }
  .loeschen { color: var(--t-fehler); }
  .tf-gross { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; margin: 16px 0; }
</style>
