<script>
  /**
   * Telefonansicht: nur Radio und Podcasts, Spielerleiste über der Fußleiste, Spieler als Vollbild, quer die
   * Weckeransicht. Kopf, Fußleiste, Höhe und sichere Ränder kommen allein aus dem Rahmen des Appkerns (data-rahmen,
   * Klassen der Telefonansicht .mobil, .t-kopf, .t-inhalt, .t-reiter); quer zeichnet die Weckeransicht den ganzen Schirm
   * selbst. Eigenes Audio-Element (die Rechneransicht ist nicht geladen), es bleibt beim Drehen dasselbe; die
   * Wiedergabe steuert dieselbe playerEngine wie am Rechner.
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
  import Meldung from '../../schale/Meldung.svelte';

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

  // Favoriten und Abos beim Start und wieder, wenn die App nach vorn kommt (die Ansicht bleibt am Telefon und am
  // Nachttisch tagelang offen; ein einmal gescheitertes Laden bliebe sonst bis zum Neuladen leer)
  $effect(() => {
    const laden = () => {
      actions.loadFavorites();
      actions.loadPodcasts();
    };
    laden();
    const sichtbar = () => { if (document.visibilityState === 'visible') laden(); };
    document.addEventListener('visibilitychange', sichtbar);
    return () => document.removeEventListener('visibilitychange', sichtbar);
  });

  function zeitAktualisieren() {
    const r = engine.handleTimeUpdate();
    if (!r) return;
    zeit = r.currentTime;
    dauer = r.duration;
    if (appState.currentEpisode) medien.position(dauer, zeit, appState.podcastSpeed || 1);
  }

  // Vor und Zurück folgen der sichtbaren Liste des Radios (Vorgabe 7); ohne Liste (Radio noch nicht geöffnet) die Favoriten
  function favorit(schritt) {
    if (appState.stations.length) return schritt < 0 ? actions.navigatePrev() : actions.navigateNext();
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
    // auch ein direkter Strom hält nur an; weiter verbindet ihn neu ab live (playerEngine.resume)
    actions.pause();
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

<div class="rh-telefon" class:mobil={!geraet.quer} data-rahmen={geraet.quer ? undefined : 'app'}>
  {#if geraet.quer}
    <TelefonWecker {steuerung} audio={audioEl} />
  {:else}
    <div class="t-kopf mit-aktionen" data-rahmen="kopf">
      <h1>{titel}</h1>
      <span class="t-aktionen">
        <button class="rund" class:aktiv={appState.activeTab === 'wecker'}
          onclick={() => actions.navigateTo(appState.activeTab === 'wecker' ? '/radio' : '/wecker')}
          aria-label={t('telefon.wecker')} title={t('telefon.wecker')}><i class="fa-solid fa-clock"></i></button>
        <button class="rund" onclick={() => (einstellungenOffen = true)}
          aria-label={t('telefon.einstellungen')} title={t('telefon.einstellungen')}><i class="fa-solid fa-sliders"></i></button>
      </span>
    </div>

    <!-- Radio ist neu gebaut (RAD-7): eigene Rollfelder, Marken direkt; die übrigen Bereiche wachsen als Ganzes (rh-alt) -->
    <main class="t-inhalt" class:rh-alt={appState.activeTab === "podcasts" || appState.activeTab === "wecker"}
          class:tf-radio-inhalt={appState.activeTab !== "podcasts" && appState.activeTab !== "wecker"} data-rahmen="inhalt">
      {#if appState.activeTab === 'podcasts'}
        <TelefonPodcasts />
      {:else if appState.activeTab === 'wecker'}
        <TelefonWeckerListe />
      {:else}
        <TelefonRadio />
      {/if}
    </main>

    <div class="rh-alt"><TelefonSpieler bind:offen={spielerOffen} {zeit} {dauer} {steuerung} /></div>

    <nav class="t-reiter" data-rahmen="fuss">
      <button class:aktiv={appState.activeTab === 'radio'} onclick={() => actions.navigateTo('/radio')}>
        <i class="fa-solid fa-radio"></i><span class="t-reiter-name">{t('telefon.radio')}</span>
      </button>
      <button class:aktiv={appState.activeTab === 'podcasts'} onclick={() => actions.navigateTo('/podcasts')}>
        <i class="fa-solid fa-podcast"></i><span class="t-reiter-name">{t('telefon.podcasts')}</span>
      </button>
    </nav>
    <Meldung />
  {/if}

  {#if einstellungenOffen}
    <TelefonEinstellungen onschliessen={() => (einstellungenOffen = false)} />
  {/if}

  <!-- svelte-ignore a11y_media_has_caption -->
  <audio bind:this={audioEl} preload="none" ontimeupdate={zeitAktualisieren} onloadedmetadata={zeitAktualisieren}
    onended={() => engine.handleEnded()} onerror={(e) => engine.handleError(e)}></audio>
</div>

<style>
  /* quer zeichnet die Weckeransicht den ganzen Schirm; hochkant gibt der Rahmen des Appkerns Höhe und Ränder vor */
  .rh-telefon:not(.mobil) { position: fixed; inset: 0; display: flex; flex-direction: column; overflow: hidden; }
  /* Meldung über Spielerleiste und Fußleiste */
  .rh-telefon { --rh-band-unten: calc(var(--rahmen-fuss) + 84px); }
</style>
