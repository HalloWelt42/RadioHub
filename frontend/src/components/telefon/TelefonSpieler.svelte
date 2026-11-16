<script>
  /**
   * Spielerleiste über der Fußleiste (Bild, Titel, Wiedergabe/Pause); antippen öffnet den Spieler als Vollbild:
   * bei Folgen Position, Spulen, 15 s zurück und 30 s vor; beim Radio voriger und nächster Favorit.
   */
  import { appState } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { beschreibung } from '../../lib/telefon/medien.js';
  import Bild from './Bild.svelte';

  let { offen = $bindable(false), zeit = 0, dauer = 0, steuerung } = $props();

  const info = $derived(beschreibung(appState));
  const folge = $derived(!!appState.currentEpisode);
  const spielt = $derived(appState.isPlaying && !appState.isPaused);
  const bildSrc = $derived(info?.artwork?.[0]?.src || null);
  let ziehen = $state(null);

  function uhr(s) {
    if (!Number.isFinite(s) || s < 0) s = 0;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sek = Math.floor(s % 60);
    return (h ? `${h}:${String(m).padStart(2, '0')}` : `${m}`) + `:${String(sek).padStart(2, '0')}`;
  }

  $effect(() => {
    if (!info) offen = false;
  });
</script>

{#if info}
  <div class="leiste">
    <button class="leiste-info" onclick={() => (offen = true)} aria-label={t('telefon.spielerOeffnen')}>
      <Bild src={bildSrc} symbol={folge ? 'fa-podcast' : 'fa-radio'} groesse={44} />
      <span class="text">
        <span class="titel">{info.title}</span>
        <span class="zusatz">{info.artist || (folge ? '' : t('telefon.live'))}</span>
      </span>
    </button>
    <button class="rund" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
      <i class="fa-solid {spielt ? (appState.playerMode === 'direct' ? 'fa-stop' : 'fa-pause') : 'fa-play'}"></i>
    </button>
  </div>
{/if}

{#if offen && info}
  <div class="vollbild" role="dialog" aria-modal="true" aria-label={info.title}>
    <div class="vollbild-kopf">
      <button class="kopf-knopf" onclick={() => (offen = false)} aria-label={t('telefon.spielerSchliessen')}>
        <i class="fa-solid fa-chevron-down"></i>
      </button>
    </div>
    <div class="buehne">
      <Bild src={bildSrc} symbol={folge ? 'fa-podcast' : 'fa-radio'} groesse={240} />
      <h2>{info.title}</h2>
      <p class="zusatz">{info.artist || (folge ? '' : t('telefon.live'))}</p>
    </div>

    {#if folge}
      <div class="position">
        <input type="range" min="0" max={Math.max(1, Math.floor(dauer))} step="1"
          value={ziehen ?? Math.floor(zeit)} aria-label={t('telefon.abspielen')}
          oninput={(e) => (ziehen = Number(e.currentTarget.value))}
          onchange={(e) => { steuerung.springen(Number(e.currentTarget.value)); ziehen = null; }} />
        <div class="zeiten"><span>{uhr(ziehen ?? zeit)}</span><span>-{uhr(Math.max(0, dauer - (ziehen ?? zeit)))}</span></div>
      </div>
      <div class="knoepfe">
        <button class="rund mittel" onclick={() => steuerung.zurueck(15)} aria-label={t('telefon.zurueck15')} title={t('telefon.zurueck15')}>
          <i class="fa-solid fa-rotate-left"></i><span class="zahl">15</span>
        </button>
        <button class="rund gross" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
          <i class="fa-solid {spielt ? 'fa-pause' : 'fa-play'}"></i>
        </button>
        <button class="rund mittel" onclick={() => steuerung.vor(30)} aria-label={t('telefon.vor30')} title={t('telefon.vor30')}>
          <i class="fa-solid fa-rotate-right"></i><span class="zahl">30</span>
        </button>
      </div>
    {:else}
      <div class="knoepfe">
        <button class="rund mittel" onclick={steuerung.voriger} aria-label={t('telefon.voriger')} title={t('telefon.voriger')}>
          <i class="fa-solid fa-backward-step"></i>
        </button>
        <button class="rund gross" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.stopp') : t('telefon.abspielen')}>
          <i class="fa-solid {spielt ? (appState.playerMode === 'direct' ? 'fa-stop' : 'fa-pause') : 'fa-play'}"></i>
        </button>
        <button class="rund mittel" onclick={steuerung.naechster} aria-label={t('telefon.naechster')} title={t('telefon.naechster')}>
          <i class="fa-solid fa-forward-step"></i>
        </button>
      </div>
    {/if}
  </div>
{/if}

<style>
  .leiste {
    flex: none;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px 8px 12px;
    background: var(--t-flaeche);
    border-top: 1px solid var(--t-linie);
  }
  .leiste-info {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    border: none;
    background: transparent;
    color: var(--t-text);
    text-align: left;
    font: inherit;
    padding: 0;
  }
  .text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .titel { font-size: 17px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .zusatz { font-size: 15px; color: var(--t-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rund {
    position: relative;
    width: 52px;
    height: 52px;
    flex: none;
    border: none;
    border-radius: 50%;
    background: var(--t-akzent);
    color: var(--t-akzent-text);
    font-size: 20px;
  }
  .rund.mittel { width: 64px; height: 64px; background: var(--t-flaeche-2); color: var(--t-text); font-size: 24px; }
  .rund.gross { width: 84px; height: 84px; font-size: 32px; }
  .zahl { position: absolute; left: 0; right: 0; bottom: 6px; font-size: 15px; font-weight: 700; }

  .vollbild {
    position: fixed;
    inset: 0;
    z-index: 20;
    display: flex;
    flex-direction: column;
    padding: max(env(safe-area-inset-top, 0px), 1cm) 16px 24px;
    background: var(--t-grund);
    color: var(--t-text);
    overflow-y: auto;
    overflow-x: hidden;
  }
  .vollbild-kopf { display: flex; }
  .kopf-knopf { width: 48px; height: 48px; border: none; border-radius: 12px; background: transparent; color: var(--t-text); font-size: 22px; }
  .buehne { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; min-height: 0; text-align: center; }
  .buehne h2 { margin: 16px 0 0; font-size: 22px; font-weight: 700; overflow-wrap: anywhere; }
  .buehne .zusatz { white-space: normal; }
  .position { margin: 16px 0 4px; }
  .position input { width: 100%; height: 32px; accent-color: var(--t-akzent); }
  .zeiten { display: flex; justify-content: space-between; font-size: 15px; color: var(--t-text-2); font-variant-numeric: tabular-nums; }
  .knoepfe { display: flex; align-items: center; justify-content: center; gap: 28px; margin: 16px 0 8px; }
</style>
