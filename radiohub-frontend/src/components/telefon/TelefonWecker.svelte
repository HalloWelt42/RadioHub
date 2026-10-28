<script>
  /**
   * Weckeransicht (Telefon quer, Nachttisch): links die Uhr mit Datum, rechts was läuft, der nächste Wecker und
   * Sonnenauf- und -untergang. Nachts (nach Sonnenzeiten oder von Hand) dunkelrot auf schwarz. Hält den Bildschirm
   * wach und löst die Wecker aus, solange sie offen ist; Web-Apps werden im Hintergrund nicht geweckt.
   */
  import { onDestroy } from 'svelte';
  import { appState, actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { api } from '../../lib/api.js';
  import { sonnenzeiten, istNacht } from '../../lib/sonne.js';
  import { naechsterWecker, faelligInMinute } from '../../lib/wecker.js';
  import { beschreibung } from '../../lib/telefon/medien.js';
  import { weckeransichtOffen } from '../../lib/telefon/wachHalten.svelte.js';
  import { weckerdaten, weckerLaden } from '../../lib/telefon/weckerdaten.svelte.js';

  let { steuerung } = $props();

  const NACHT_SCHLUESSEL = 'radiohub_nachtschaltung';
  let jetzt = $state(new Date());
  let nachtWahl = $state(lesen());
  let klingelt = $state(null);
  let schlummerBis = $state(null);
  let schlummerWecker = null;
  const ausgeloest = new Set();
  let anstieg = null;

  function lesen() {
    try { return localStorage.getItem(NACHT_SCHLUESSEL) || 'auto'; } catch { return 'auto'; }
  }

  function nachtSetzen(wert) {
    nachtWahl = wert;
    try { localStorage.setItem(NACHT_SCHLUESSEL, wert); } catch { /* privates Fenster */ }
  }

  weckeransichtOffen(true);
  weckerLaden();
  const takt = setInterval(() => { jetzt = new Date(); pruefen(); }, 1000);

  onDestroy(() => {
    clearInterval(takt);
    clearInterval(anstieg);
    weckeransichtOffen(false);
  });

  const ort = $derived(weckerdaten.ort);
  const sonne = $derived(ort.breite != null && ort.laenge != null ? sonnenzeiten(jetzt, ort.breite, ort.laenge) : null);
  const nacht = $derived(nachtWahl === 'an' || (nachtWahl === 'auto' && istNacht(jetzt, ort.breite, ort.laenge) === true));
  const naechster = $derived(naechsterWecker(weckerdaten.liste, jetzt));
  const info = $derived(beschreibung(appState));
  const spielt = $derived(appState.isPlaying && !appState.isPaused);

  const zweistellig = (n) => String(n).padStart(2, '0');
  const hhmm = (d) => (d ? `${zweistellig(d.getHours())}:${zweistellig(d.getMinutes())}` : '--:--');
  const datum = $derived(jetzt.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' }));

  function quelleText(w) {
    if (!w) return '';
    if (w.quelle === 'sender') return w.sender?.name || '';
    const p = appState.podcasts.find((x) => x.id === w.podcast_id);
    return `${t('telefon.folge')}: ${p?.title || ''}`;
  }

  function pruefen() {
    if (klingelt) return;
    if (schlummerBis && jetzt >= schlummerBis) {
      const w = schlummerWecker;
      schlummerBis = null;
      schlummerWecker = null;
      if (w) ausloesen(w);
      return;
    }
    for (const w of weckerdaten.liste) {
      const schluessel = `${w.id}-${jetzt.toDateString()}-${w.zeit}`;
      if (!ausgeloest.has(schluessel) && faelligInMinute(w, jetzt)) {
        ausgeloest.add(schluessel);
        ausloesen(w);
        return;
      }
    }
  }

  async function ausloesen(w) {
    klingelt = w;
    const ziel = w.lautstaerke || 60;
    const schritte = Math.max(1, w.anstieg_s || 0);
    let stufe = 0;
    actions.setVolume(w.anstieg_s ? 5 : ziel);
    if (w.quelle === 'sender' && w.sender) {
      await actions.playStation(w.sender);
    } else if (w.podcast_id) {
      try {
        const r = await api.getEpisodes(w.podcast_id, 1, 0, 'all');
        const folge = r.episodes?.[0];
        const abo = appState.podcasts.find((p) => p.id === w.podcast_id) || { id: w.podcast_id };
        if (folge) actions.playEpisode(folge, abo);
      } catch { /* Abo nicht erreichbar */ }
    }
    clearInterval(anstieg);
    if (w.anstieg_s) {
      anstieg = setInterval(() => {
        stufe += 1;
        actions.setVolume(Math.round(5 + (ziel - 5) * Math.min(1, stufe / schritte)));
        if (stufe >= schritte) clearInterval(anstieg);
      }, 1000);
    }
  }

  function aus() {
    clearInterval(anstieg);
    klingelt = null;
    schlummerBis = null;
    schlummerWecker = null;
    actions.stop();
  }

  function schlummern() {
    const w = klingelt;
    clearInterval(anstieg);
    klingelt = null;
    actions.stop();
    schlummerWecker = w;
    schlummerBis = new Date(Date.now() + (w?.schlummern_min || 9) * 60000);
  }
</script>

<div class="wecker" class:nacht>
  <div class="links">
    <div class="uhr">{hhmm(jetzt)}</div>
    <div class="datum">{datum}</div>
  </div>

  <div class="rechts">
    {#if klingelt}
      <div class="klingeln">
        <p class="gross-text">{t('telefon.klingelt')} {klingelt.zeit}</p>
        <button class="riesig" onclick={schlummern}><i class="fa-solid fa-bed"></i> {t('telefon.schlummern')}</button>
        <button class="riesig aus" onclick={aus}><i class="fa-solid fa-power-off"></i> {t('telefon.aus')}</button>
      </div>
    {:else}
      <div class="block spielt-block">
        <div class="text">
          <span class="titel">{info ? info.title : t('telefon.nichtsLaeuft')}</span>
          {#if info}<span class="zusatz">{info.artist ? `${info.artist} · ` : ''}{spielt ? t('telefon.laeuft') : t('telefon.pausiert')}</span>{/if}
        </div>
        {#if info}
          <button class="rund" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
            <i class="fa-solid {spielt ? (appState.playerMode === 'direct' ? 'fa-stop' : 'fa-pause') : 'fa-play'}"></i>
          </button>
        {/if}
      </div>

      <div class="block">
        <span class="beschriftung">{schlummerBis ? t('telefon.schlummertBis') : t('telefon.naechsterWecker')}</span>
        {#if schlummerBis}
          <span class="wert">{hhmm(schlummerBis)}</span>
        {:else if naechster}
          <span class="wert">{naechster.zeitpunkt.toLocaleDateString(undefined, { weekday: 'short' })} {hhmm(naechster.zeitpunkt)}</span>
          <span class="zusatz">{quelleText(naechster.wecker)}</span>
        {:else}
          <span class="zusatz">{t('telefon.keinWeckerAktiv')}</span>
        {/if}
      </div>

      <div class="block sonne">
        {#if sonne && !sonne.polar}
          <span><i class="fa-solid fa-sun"></i> {t('telefon.aufgang')} {hhmm(sonne.aufgang)}</span>
          <span><i class="fa-solid fa-moon"></i> {t('telefon.untergang')} {hhmm(sonne.untergang)}</span>
        {:else if !sonne}
          <span class="zusatz">{t('telefon.ortFehlt')}</span>
        {/if}
      </div>

      <div class="nachtwahl" role="group" aria-label={t('telefon.nacht')}>
        {#each [['auto', 'nachtAuto'], ['an', 'nachtAn'], ['aus', 'nachtAus']] as [wert, text]}
          <button class:an={nachtWahl === wert} aria-pressed={nachtWahl === wert} onclick={() => nachtSetzen(wert)}>{t('telefon.' + text)}</button>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .wecker {
    --w-grund: var(--t-grund);
    --w-text: var(--t-text);
    --w-text-2: var(--t-text-2);
    --w-linie: var(--t-linie);
    --w-akzent: var(--t-akzent);
    --w-akzent-text: var(--t-akzent-text);
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
    gap: 16px;
    padding: 12px max(env(safe-area-inset-right, 0px), 16px) 12px max(env(safe-area-inset-left, 0px), 16px);
    background: var(--w-grund);
    color: var(--w-text);
    overflow: hidden;
  }
  .wecker.nacht {
    --w-grund: #000000;
    --w-text: #c62020;
    --w-text-2: #c01c1c;
    --w-linie: #4a0b0b;
    --w-akzent: #c62020;
    --w-akzent-text: #000000;
  }
  .links { display: flex; flex-direction: column; justify-content: center; align-items: center; min-width: 0; }
  .uhr { font-size: min(34vh, 17vw); font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
  .datum { margin-top: 8px; font-size: 20px; color: var(--w-text-2); text-align: center; }
  .rechts { display: flex; flex-direction: column; justify-content: center; gap: 10px; min-width: 0; overflow-y: auto; }
  .block { display: flex; flex-direction: column; gap: 2px; padding-bottom: 8px; border-bottom: 1px solid var(--w-linie); min-width: 0; }
  .spielt-block { flex-direction: row; align-items: center; gap: 10px; }
  .text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .titel { font-size: 19px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .zusatz, .beschriftung { font-size: 15px; color: var(--w-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sonne .zusatz { white-space: normal; }
  .wert { font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .sonne { flex-direction: row; flex-wrap: wrap; gap: 4px 16px; font-size: 17px; }
  .rund { width: 52px; height: 52px; flex: none; border: none; border-radius: 50%; background: var(--w-akzent); color: var(--w-akzent-text); font-size: 20px; }
  .nachtwahl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
  .nachtwahl button { min-height: 44px; border: 1px solid var(--w-linie); border-radius: 22px; background: transparent; color: var(--w-text); font: inherit; font-size: 15px; }
  .nachtwahl button.an { background: var(--w-akzent); border-color: var(--w-akzent); color: var(--w-akzent-text); font-weight: 600; }
  .klingeln { display: flex; flex-direction: column; gap: 12px; }
  .gross-text { margin: 0; font-size: 24px; font-weight: 700; }
  .riesig { min-height: 72px; border: none; border-radius: 18px; background: var(--w-akzent); color: var(--w-akzent-text); font: inherit; font-size: 24px; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 12px; }
  .riesig.aus { background: transparent; color: var(--w-text); border: 2px solid var(--w-text); }
</style>
