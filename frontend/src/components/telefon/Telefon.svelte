<script>
  /**
   * Telefonansicht: Radio, Aufnahmen (nur hören) und Podcasts, Spielerleiste über der Fußleiste, Spieler als Vollbild, quer die
   * Weckeransicht. Kopf, Fußleiste, Höhe und sichere Ränder kommen allein aus dem Rahmen des Appkerns (data-rahmen,
   * Klassen der Telefonansicht .mobil, .t-kopf, .t-inhalt, .t-reiter); quer zeichnet die Weckeransicht den ganzen Schirm
   * selbst. Das Tonelement ist das eine der Seite (spieler/tonelement.ts), es bleibt beim Drehen und beim Wechsel zum Rechner dasselbe; die
   * Wiedergabe steuert dieselbe playerEngine wie am Rechner.
   */
  import * as engine from '../../lib/playerEngine.js';
  import { appState, actions } from '../../lib/store.svelte.js';
  import { filterzustand, senderquelle } from '../../lib/radio';
  import { Radiobedienung } from '../../lib/radio/bedienung.svelte';
  import Band from '../radio/Band.svelte';
  import { tick } from 'svelte';
  import { t } from '../../lib/i18n.svelte.js';
  import { geraet } from '../../lib/geraet.svelte.js';
  import * as medien from '../../lib/telefon/medien.js';
  import { radioSetzen } from '../../lib/telefon/zeitansage.svelte.js';
  import { wunsch } from '../../lib/telefon/verbindung.svelte.js';
  import { anhaengen, tonelement } from '../../spieler/tonelement';
  import TelefonRadio from './TelefonRadio.svelte';
  import TelefonPodcasts from './podcasts/TelefonPodcasts.svelte';
  import TelefonAufnahmen from './TelefonAufnahmen.svelte';
  import TelefonSpieler from './TelefonSpieler.svelte';
  import TelefonWecker from './TelefonWecker.svelte';
  import TelefonWeckerListe from './TelefonWeckerListe.svelte';
  import TelefonEinstellungen from './TelefonEinstellungen.svelte';
  import Hinweise from '../../schale/Hinweise.svelte';
  import Meldung from '../../schale/Meldung.svelte';

  /** Was die Telefonansicht anbietet; die Webversion (RAD-4) nur Radio, ohne Wecker und ohne Daten des Backends */
  let { angebot = { podcasts: true, aufnahmen: true, wecker: true, backend: true } } = $props();
  /** eine Bedienung des Radios für die Liste und den großen Spieler (Auge und Stern, RAD-94): beide sehen denselben
   *  Stand; das Rückgängig-Band steht hier, damit es auch über dem Spieler erscheint */
  const radio = new Radiobedienung(senderquelle);

  // das eine Tonelement der Seite (bleibt beim Wechsel zwischen Rechner und Telefon bestehen, RAD-28)
  const audioEl = tonelement();
  let zeit = $state(0);
  let dauer = $state(0);
  let spielerOffen = $state(false);
  let einstellungenOffen = $state(false);

  $effect(() => {
    radioSetzen(audioEl);
    return anhaengen({ timeupdate: zeitAktualisieren, loadedmetadata: zeitAktualisieren });
  });

  // Favoriten und Abos beim Start und wieder, wenn die App nach vorn kommt (die Ansicht bleibt am Telefon und am
  // Nachttisch tagelang offen; ein einmal gescheitertes Laden bliebe sonst bis zum Neuladen leer)
  $effect(() => {
    if (!angebot.backend) return;
    const laden = () => {
      actions.loadFavorites();
      if (angebot.podcasts) actions.loadPodcasts();
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
    if (appState.isRecording) return;   // während einer Aufnahme bleibt der Sender (RAD-83)
    if (appState.stations.length) return schritt < 0 ? actions.navigatePrev() : actions.navigateNext();
    const liste = appState.favorites;
    if (!liste.length) return;
    const i = liste.findIndex((f) => f.uuid === appState.currentStation?.uuid);
    const ziel = liste[(i + schritt + liste.length) % liste.length];
    return actions.playStation(ziel);
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
    stoppen: () => { wunsch.spielen = false; actions.stop(); },
    zurueck: (s) => engine.skip(-s),
    vor: (s) => engine.skip(s),
    springen: (sek) => { if (dauer > 0) engine.seek((sek / dauer) * 100); },
    voriger: () => favorit(-1),
    naechster: () => favorit(1),
    zurListe
  };

  /** Laufenden Sender in der Liste zeigen: Spieler zu, zur Zeile rollen; steht er wegen eines Filters nicht in der
   *  Liste, sucht ihn die Liste gezielt (als Suche sichtbar, mit einem Tipp entfernbar) */
  async function zurListe(sender = appState.currentStation) {
    if (!sender) return;
    spielerOffen = false;
    if (appState.activeTab !== 'radio') actions.navigateTo('/radio');
    await tick();
    const zeile = () => document.querySelector('.tf-sender.spielt');
    if (!zeile()) {
      filterzustand.aendern((f) => ({ ...f, suche: sender.name.trim().slice(0, 100) }));
      for (let i = 0; i < 20 && !zeile(); i++) await new Promise((r) => setTimeout(r, 150));
    }
    zeile()?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }

  $effect(() => {
    medien.aktualisieren(appState, steuerung);
  });

  const titel = $derived(
    appState.activeTab === 'podcasts' ? t('telefon.podcasts')
      : appState.activeTab === 'recordings' ? t('aufnahmenAnsicht.telefon.aufnahmen')
      : appState.activeTab === 'wecker' ? t('telefon.wecker') : t('telefon.radio')
  );
</script>

<div class="rh-telefon" class:mobil={!geraet.quer || !angebot.wecker} data-rahmen={geraet.quer && angebot.wecker ? undefined : 'app'}>
  {#if geraet.quer && angebot.wecker}
    <TelefonWecker {steuerung} audio={audioEl} />
  {:else}
    <div class="t-kopf mit-aktionen" data-rahmen="kopf">
      <!-- Schriftzug klein statt des Bereichs (RAD-90, Wahl A): mit PRO oder BASIC; den Bereich zeigt die Leiste unten -->
      <div class="tf-marke">
        <h1 class="t-logo" aria-label="RadioHub {angebot.backend ? 'PRO' : 'Basic'}: {titel}">
          <span class="rh-logo" aria-hidden="true">{#each 'RadioHub'.split('') as zeichen, i (i)}<span class="rh-logo-zeichen" style:--i={i}>{zeichen}</span>{/each}</span>
          <span class={angebot.backend ? 'rh-pro' : 'rh-basic'} aria-hidden="true">{angebot.backend ? 'PRO' : 'BASIC'}</span>
        </h1>
      </div>
      <span class="t-aktionen">
        <Hinweise />
        {#if angebot.wecker}
        <button class="rund" class:aktiv={appState.activeTab === 'wecker'}
          onclick={() => actions.navigateTo(appState.activeTab === 'wecker' ? '/radio' : '/wecker')}
          aria-label={t('telefon.wecker')} title={t('telefon.wecker')}><i class="fa-solid fa-clock"></i></button>
        {/if}
        <button class="rund" onclick={() => (einstellungenOffen = true)}
          aria-label={t('telefon.einstellungen')} title={t('telefon.einstellungen')}><i class="fa-solid fa-sliders"></i></button>
      </span>
    </div>

    <!-- Radio, Aufnahmen und Podcasts sind neu gebaut (RAD-7, RAD-17, RAD-14): eigene Rollfelder, Marken direkt; nur die
         Liste der Wecker wächst noch als Ganzes (rh-alt) -->
    <main class="t-inhalt" class:rh-alt={appState.activeTab === "wecker"}
          class:tf-radio-inhalt={appState.activeTab !== "wecker"} data-rahmen="inhalt">
      {#if appState.activeTab === 'podcasts' && angebot.podcasts}
        <TelefonPodcasts />
      {:else if appState.activeTab === 'recordings' && angebot.aufnahmen}
        <TelefonAufnahmen />
      {:else if appState.activeTab === 'wecker' && angebot.wecker}
        <TelefonWeckerListe />
      {:else}
        <TelefonRadio bedienung={radio} />
      {/if}
    </main>

    <div class="rh-alt"><TelefonSpieler bind:offen={spielerOffen} {zeit} {dauer} {steuerung} bedienung={radio} /></div>
    <Band bind:inhalt={radio.band} />

    {#if angebot.podcasts}
    <nav class="t-reiter" data-rahmen="fuss">
      <button class:aktiv={appState.activeTab === 'radio'} onclick={() => actions.navigateTo('/radio')}>
        <i class="fa-solid fa-radio"></i><span class="t-reiter-name">{t('telefon.radio')}</span>
      </button>
      {#if angebot.aufnahmen}
      <button class:aktiv={appState.activeTab === 'recordings'} onclick={() => actions.navigateTo('/aufnahmen')}>
        <i class="fa-solid fa-circle-dot"></i><span class="t-reiter-name">{t('aufnahmenAnsicht.telefon.aufnahmen')}</span>
      </button>
      {/if}
      <button class:aktiv={appState.activeTab === 'podcasts'} onclick={() => actions.navigateTo('/podcasts')}>
        <i class="fa-solid fa-podcast"></i><span class="t-reiter-name">{t('telefon.podcasts')}</span>
      </button>
    </nav>
    {/if}
    <Meldung />
  {/if}

  {#if einstellungenOffen}
    <TelefonEinstellungen onschliessen={() => (einstellungenOffen = false)} angebot={{ wecker: angebot.wecker, backend: angebot.backend }} />
  {/if}

</div>

<style>
  /* quer zeichnet die Weckeransicht den ganzen Schirm; hochkant gibt der Rahmen des Appkerns Höhe und Ränder vor */
  .rh-telefon:not(.mobil) { position: fixed; inset: 0; display: flex; flex-direction: column; overflow: hidden; }
  /* Meldung über Spielerleiste und Fußleiste */
  .rh-telefon { --rh-band-unten: calc(var(--rahmen-fuss) + 84px); }
</style>
