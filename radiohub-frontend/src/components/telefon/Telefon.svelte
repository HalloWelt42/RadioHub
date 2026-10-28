<script>
  /**
   * Telefonansicht: nur Radio und Podcasts, Spielerleiste über der Fußleiste, Spieler als Vollbild, quer die
   * Weckeransicht. Eigenes Audio-Element (die Rechneransicht ist nicht geladen); die Wiedergabe steuert dieselbe
   * playerEngine wie am Rechner.
   */
  import * as engine from '../../lib/playerEngine.js';
  import { appState, actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { geraet } from '../../lib/geraet.svelte.js';
  import * as medien from '../../lib/telefon/medien.js';
  import { radioSetzen } from '../../lib/telefon/zeitansage.svelte.js';
  import { wunsch } from '../../lib/telefon/verbindung.svelte.js';
  import TelefonRadio from './TelefonRadio.svelte';
  import TelefonPodcasts from './TelefonPodcasts.svelte';
  import TelefonSpieler from './TelefonSpieler.svelte';
  import TelefonWecker from './TelefonWecker.svelte';
  import TelefonWeckerListe from './TelefonWeckerListe.svelte';
  import TelefonEinstellungen from './TelefonEinstellungen.svelte';

  let audioEl = $state();
  let zeit = $state(0);
  let dauer = $state(0);
  let spielerOffen = $state(false);
  let einstellungenOffen = $state(false);

  $effect(() => {
    if (audioEl) {
      engine.init(audioEl, appState);
      radioSetzen(audioEl);
    }
  });

  $effect(() => {
    actions.loadFavorites();
    actions.loadPodcasts();
  });

  function zeitAktualisieren() {
    const r = engine.handleTimeUpdate();
    if (!r) return;
    zeit = r.currentTime;
    dauer = r.duration;
    if (appState.currentEpisode) medien.position(dauer, zeit, appState.podcastSpeed || 1);
  }

  function favorit(schritt) {
    const liste = appState.favorites;
    if (!liste.length) return;
    const i = liste.findIndex((f) => f.uuid === appState.currentStation?.uuid);
    const ziel = liste[(i + schritt + liste.length) % liste.length];
    actions.playStation(ziel);
  }

  function abspielen() {
    wunsch.spielen = true;   // ab jetzt soll etwas zu hören sein (der Wächter der Weckeransicht verbindet neu)
    if (appState.isPaused) return actions.resume();
    if (appState.isPlaying) return;
    if (appState.currentEpisode) {
      actions.playEpisode(appState.currentEpisode, appState.currentEpisode.podcast);
    } else if (appState.currentStation) {
      actions.playStation(appState.currentStation);
    }
  }

  function pause() {
    wunsch.spielen = false;
    // Ein direkter Strom ohne Puffer lässt sich nicht anhalten, nur beenden
    if (appState.playerMode === 'direct') actions.stop();
    else actions.pause();
  }

  const steuerung = {
    abspielen,
    pause,
    umschalten: () => (appState.isPlaying && !appState.isPaused ? pause() : abspielen()),
    zurueck: (s) => engine.skip(-s),
    vor: (s) => engine.skip(s),
    springen: (sek) => { if (dauer > 0) engine.seek((sek / dauer) * 100); },
    voriger: () => favorit(-1),
    naechster: () => favorit(1)
  };

  $effect(() => {
    medien.aktualisieren(appState, steuerung);
  });

  const titel = $derived(
    appState.activeTab === 'podcasts' ? t('telefon.podcasts')
      : appState.activeTab === 'wecker' ? t('telefon.wecker') : t('telefon.radio')
  );
</script>

<div class="telefon">
  {#if geraet.quer}
    <TelefonWecker {steuerung} audio={audioEl} />
  {:else}
    <header class="kopf">
      <h1>{titel}</h1>
      <button class="kopf-knopf" class:aktiv={appState.activeTab === 'wecker'}
        onclick={() => actions.navigateTo(appState.activeTab === 'wecker' ? '/radio' : '/wecker')}
        aria-label={t('telefon.wecker')} title={t('telefon.wecker')}>
        <i class="fa-solid fa-clock"></i>
      </button>
      <button class="kopf-knopf" onclick={() => (einstellungenOffen = true)}
        aria-label={t('telefon.einstellungen')} title={t('telefon.einstellungen')}>
        <i class="fa-solid fa-sliders"></i>
      </button>
    </header>

    <main class="inhalt">
      {#if appState.activeTab === 'podcasts'}
        <TelefonPodcasts />
      {:else if appState.activeTab === 'wecker'}
        <TelefonWeckerListe />
      {:else}
        <TelefonRadio />
      {/if}
    </main>

    {#if appState.toast}
      <div class="meldung" class:fehler={appState.toast.type === 'error'} role="status">{appState.toast.message}</div>
    {/if}

    <TelefonSpieler bind:offen={spielerOffen} {zeit} {dauer} {steuerung} />

    <nav class="fuss">
      <button class:aktiv={appState.activeTab === 'radio'} onclick={() => actions.navigateTo('/radio')}>
        <i class="fa-solid fa-radio"></i><span>{t('telefon.radio')}</span>
      </button>
      <button class:aktiv={appState.activeTab === 'podcasts'} onclick={() => actions.navigateTo('/podcasts')}>
        <i class="fa-solid fa-podcast"></i><span>{t('telefon.podcasts')}</span>
      </button>
    </nav>
  {/if}

  {#if einstellungenOffen}
    <TelefonEinstellungen onschliessen={() => (einstellungenOffen = false)} />
  {/if}

  <!-- svelte-ignore a11y_media_has_caption -->
  <audio bind:this={audioEl} preload="none" ontimeupdate={zeitAktualisieren} onloadedmetadata={zeitAktualisieren}
    onended={() => engine.handleEnded()} onerror={(e) => engine.handleError(e)}></audio>
</div>

<style>
  .telefon {
    --t-grund: #121417;
    --t-flaeche: #1c2025;
    --t-flaeche-2: #272c33;
    --t-linie: #313840;
    --t-text: #f1f3f5;
    --t-text-2: #b9c1c9;
    --t-akzent: #5aa0e9;
    --t-akzent-text: #0b0d10;
    --t-fehler: #ff8a80;
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    background: var(--t-grund);
    color: var(--t-text);
    font-family: var(--hifi-font-body);
    font-size: 17px;
    line-height: 1.35;
    overflow: hidden;
    -webkit-text-size-adjust: 100%;
  }
  :global([data-theme='light']) .telefon {
    --t-grund: #f3f4f6;
    --t-flaeche: #ffffff;
    --t-flaeche-2: #e9ecef;
    --t-linie: #d5dae0;
    --t-text: #15181c;
    --t-text-2: #48515a;
    --t-akzent: #2564a8;
    --t-akzent-text: #ffffff;
    --t-fehler: #b3261e;
  }

  .kopf {
    position: sticky;
    top: 0;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: max(env(safe-area-inset-top, 0px), 1cm) 12px 8px 16px;
    background: var(--t-grund);
    border-bottom: 1px solid var(--t-linie);
    flex: none;
  }
  .kopf h1 {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: 24px;
    font-weight: 700;
    font-family: var(--hifi-font-body);
    letter-spacing: 0;
  }
  .kopf-knopf {
    width: 48px;
    height: 48px;
    flex: none;
    border: none;
    border-radius: 12px;
    background: transparent;
    color: var(--t-text);
    font-size: 20px;
  }
  .kopf-knopf.aktiv {
    background: var(--t-flaeche-2);
    color: var(--t-akzent);
  }

  .inhalt {
    flex: 1;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
  }

  .meldung {
    flex: none;
    margin: 0 12px 6px;
    padding: 10px 14px;
    border-radius: 10px;
    background: var(--t-flaeche-2);
    color: var(--t-text);
    font-size: 15px;
  }
  .meldung.fehler { color: var(--t-fehler); }

  .fuss {
    flex: none;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    background: var(--t-flaeche);
    border-top: 1px solid var(--t-linie);
  }
  .fuss button {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    min-height: 60px;
    padding: 8px 4px;
    border: none;
    background: transparent;
    color: var(--t-text-2);
    font-family: var(--hifi-font-body);
    font-size: 15px;
  }
  .fuss button i { font-size: 22px; }
  .fuss button.aktiv { color: var(--t-akzent); font-weight: 600; }
</style>
