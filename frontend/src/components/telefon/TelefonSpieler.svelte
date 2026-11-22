<script>
  /**
   * Spielerleiste über der Fußleiste (Bild, Titel, Wiedergabe/Pause); antippen öffnet den Spieler als Vollbild:
   * bei Folgen Position, Spulen, 15 s zurück und 30 s vor; beim Radio voriger und nächster Sender und Stopp. Der große
   * Knopf hält nur an und setzt fort, beendet wird nur über Stopp (Nutzer 20.11.2026, wie an der Kanzel). Hinter dem
   * Vollbild liegt das Logo weichgezeichnet als Farbschein, die Bedienflächen darauf sind aus Glas (RAD-56).
   */
  import { appState } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { beschreibung } from '../../lib/telefon/medien.js';
  import Bild from './Bild.svelte';
  import PufferBalken from './PufferBalken.svelte';
  import TelefonPuffer from './TelefonPuffer.svelte';
  import { puffer } from '../../spieler/puffer.svelte';
  import { live } from '../../spieler/aktionen';
  import { naechster, vorheriger } from '../../lib/radio/abschnitte';
  import { formatTimeShort } from '../../lib/formatters.js';
  import { lack } from '../../lib/radio/anzeige';
  import { einzelnAusgeblendet } from '../../lib/radio/bedienung.svelte';
  import { podcastquelle } from '../../lib/podcasts';
  import { rasterStellen, STATUS_JE_SCHRIFT } from '../../spieler/rasterbreite';
  import { Auswahl, Geraeteliste } from 'appkern-oberflaeche';
  import { Bitrate } from '../../spieler/bitrate.svelte';
  import { BITRATEN } from '../../spieler/kanzel';
  import { faehigkeiten } from '../../lib/playerEngine.js';
  import { geraete, geraeteTexte, geraeteZeile } from '../../spieler/geraete.svelte';

  let { offen = $bindable(false), zeit = 0, dauer = 0, steuerung, bedienung } = $props();

  const info = $derived(beschreibung(appState));
  const folge = $derived(!!appState.currentEpisode);
  const spielt = $derived(appState.isPlaying && !appState.isPaused);
  const bildSrc = $derived(info?.bild || null);
  /** Name der Quelle für die Kachel ohne Logo (Kürzel und Lack wie in der Liste, RAD-100) */
  const quellName = $derived(appState.currentStation?.name || appState.currentEpisode?.podcast?.title || info?.title || '');
  /** das Bild, sobald es wirklich geladen ist: nur dann trägt es den Farbschein, sonst der Schein aus dem Akzent (RAD-90) */
  let scheinBild = $state(null);
  $effect(() => {
    const src = bildSrc;
    scheinBild = null;
    if (!src) return;
    const probe = new Image();
    probe.onload = () => { if (probe.naturalWidth >= 4) scheinBild = src; };
    probe.src = src;
    return () => { probe.onload = null; };
  });
  /** Auge und Stern unter dem Sender (RAD-94): derselbe Eintrag wie in der Liste, sonst von der Quelle geholt */
  const senderUuid = $derived(folge ? null : (appState.currentStation?.uuid ?? null));
  const eintrag = $derived(bedienung.eintragVon(senderUuid));
  $effect(() => { if (offen) void bedienung.eintragHolen(senderUuid); });
  /** Auge: erst zum nächsten Sender, dann den bisherigen ausblenden (sonst fehlt Vor die Stelle in der Liste) */
  function ausblendenUndWeiter() {
    const e = eintrag;
    if (!e) return;
    steuerung.naechster();
    void bedienung.ausblenden(e);
  }
  /** Herunterladen der laufenden Folge, nur hier im großen Spieler (RAD-102, Wahl B); in Basic die Datei des Feeds,
   *  die der Browser dann selbst öffnet (fremder Server) */
  const dateiAdresse = $derived(folge && podcastquelle.faehig.herunterladen && appState.currentEpisode?.id
    ? podcastquelle.dateiAdresse(appState.currentEpisode.id) : '');
  let ziehen = $state(null);
  /** Puffer-Liste über dem Spieler (RAD-46) */
  let pufferOffen = $state(false);
  /** Rasterdisplay der Leiste (RAD-97): Zeichenhöhe des Titels in Grundschriften, Stellen nach der Breite */
  const LEISTE_JE_SCHRIFT = 0.95;
  let titelStellen = $state(24);
  let zusatzStellen = $state(30);
  /** Geräte als Blatt von unten (RAD-18) */
  let geraeteOffen = $state(false);
  const kann = faehigkeiten();
  /** Ton des Zeitversatzes (RAD-92): Original, voll umgewandelt oder eine feste Stufe */
  const bitrate = new Bitrate();
  const tonOptionen = [
    { wert: 'original', titel: t('kanzel.bitrateOriginalName'), hinweis: t('telefon.tonOriginalHinweis') },
    { wert: 'voll', titel: t('kanzel.bitrateVollName'), hinweis: t('telefon.tonVollHinweis') },
    ...BITRATEN.map((n) => ({ wert: n, titel: t('kanzel.kbit', { n }) })),
  ];
  const pStelle = $derived(puffer.stelle ?? puffer.ende);
  const pTitel = $derived(puffer.laufend);
  const pName = (a) => puffer.benennen(a);

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
  <div class="tf-leiste">
    <button class="leiste-info" onclick={() => (offen = true)} aria-label={t('telefon.spielerOeffnen')}>
      <Bild src={bildSrc} name={quellName} symbol={folge ? 'fa-podcast' : 'fa-radio'} groesse={44} />
      <!-- Rasterdisplay wie die Anzeige der Kanzel (RAD-97, Wahl A): Titel und Sender als Punktmatrix hinter Glas -->
      <span class="ak-glas rh-display tf-raster">
        <span class="rh-display-zeile rh-display-titel" use:rasterStellen={{ jeSchrift: LEISTE_JE_SCHRIFT, melden: (n) => (titelStellen = n) }}>
          {#key titelStellen}<ak-segmente art="punkt" stellen={titelStellen} lauf="200" farbe="gruen" text={info.title}></ak-segmente>{/key}
        </span>
        <span class="rh-display-zeile" use:rasterStellen={{ jeSchrift: STATUS_JE_SCHRIFT, melden: (n) => (zusatzStellen = n) }}>
          {#key zusatzStellen}<ak-segmente art="punkt" stellen={zusatzStellen} lauf="240" farbe="gruen" text={info.artist || (folge ? '' : t('telefon.live'))}></ak-segmente>{/key}
        </span>
      </span>
    </button>
    <button class="knopf primaer tf-rund" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
      <i class="fa-solid {spielt ? 'fa-pause' : 'fa-play'}"></i>
    </button>
  </div>
{/if}

{#if offen && info}
  <div class="vollbild" role="dialog" aria-modal="true" aria-label={info.title}>
    <!-- Farbschein aus dem Logo über die ganze Fläche, Bedienflächen als Glas darauf (RAD-56, Wahl A) -->
    <div class="tf-schein" class:ohne={!scheinBild} aria-hidden="true" style:background-image={scheinBild ? `url("${scheinBild}")` : null}
      style:--lack={scheinBild ? null : lack(quellName)}></div>
    <div class="vollbild-kopf">
      <button class="kopf-knopf" onclick={() => (offen = false)} aria-label={t('telefon.spielerSchliessen')}>
        <i class="fa-solid fa-chevron-down"></i>
      </button>
    </div>
    <div class="buehne">
      <span class="tf-cover"><Bild src={bildSrc} name={quellName} symbol={folge ? 'fa-podcast' : 'fa-radio'} groesse="min(72vw, 320px, 26svh)" /></span>
      {#if !folge && puffer.aktiv && pTitel}
        <!-- zeigt der Zeitversatz den Titel unten im Kasten, steht oben nur der Sender, nichts doppelt (RAD-90) -->
        <h2>{info.artist || info.title}</h2>
      {:else}
        <h2>{info.title}</h2>
        <p class="zusatz">{info.artist || (folge ? '' : t('telefon.live'))}</p>
      {/if}
      {#if dateiAdresse}
        <!-- Herunterladen unter dem Titel, rund wie die Tasten (RAD-102, Wahl B) -->
        <div class="tf-sender-aktionen">
          <a class="rund tf-rund" href={dateiAdresse} download target="_blank" rel="noopener"
             aria-label={t('podcastAnsicht.herunterladenHilfe')} title={t('podcastAnsicht.herunterladenHilfe')}><i class="fa-solid fa-download"></i></a>
        </div>
      {/if}
      {#if eintrag}
        <!-- Auge und Stern wie in der Zeile der Liste, rund wie die Tasten (RAD-94); während einer Aufnahme bleibt der Sender -->
        <div class="tf-sender-aktionen">
          {#if einzelnAusgeblendet(eintrag)}
            <button class="rund tf-rund" type="button" onclick={() => void bedienung.einblenden(eintrag)}
                    aria-label={t('radio.einblendenVon', { name: eintrag.name })} title={t('radio.einblendenHilfe')}><i class="fa-solid fa-eye"></i></button>
          {:else}
            <button class="rund tf-rund" type="button" disabled={appState.isRecording} onclick={ausblendenUndWeiter}
                    aria-label={t('radio.ausblendenVon', { name: eintrag.name })} title={t('telefon.ausblendenWeiter')}><i class="fa-solid fa-eye-slash"></i></button>
          {/if}
          <button class="rund tf-rund" class:favorit={eintrag.favorit} type="button" aria-pressed={eintrag.favorit}
                  aria-label={eintrag.favorit ? t('telefon.favoritAus') : t('telefon.favoritAn')} title={eintrag.favorit ? t('telefon.favoritAus') : t('telefon.favoritAn')}
                  onclick={() => void bedienung.favorit(eintrag)}><i class="fa-{eintrag.favorit ? 'solid' : 'regular'} fa-star"></i></button>
        </div>
      {/if}
    </div>

    {#if folge}
      <div class="position">
        <input name="position" type="range" min="0" max={Math.max(1, Math.floor(dauer))} step="1"
          value={ziehen ?? Math.floor(zeit)} aria-label={t('telefon.abspielen')}
          oninput={(e) => (ziehen = Number(e.currentTarget.value))}
          onchange={(e) => { steuerung.springen(Number(e.currentTarget.value)); ziehen = null; }} />
        <div class="zeiten"><span>{uhr(ziehen ?? zeit)}</span><span>-{uhr(Math.max(0, dauer - (ziehen ?? zeit)))}</span></div>
      </div>
      <div class="knoepfe">
        <button class="rund tf-rund mittel" onclick={() => steuerung.zurueck(15)} aria-label={t('telefon.zurueck15')} title={t('telefon.zurueck15')}>
          <i class="fa-solid fa-rotate-left"></i><span class="tf-zahl">15</span>
        </button>
        <button class="knopf primaer tf-rund tf-gross" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
          <i class="fa-solid {spielt ? 'fa-pause' : 'fa-play'}"></i>
        </button>
        <button class="rund tf-rund mittel" onclick={() => steuerung.vor(30)} aria-label={t('telefon.vor30')} title={t('telefon.vor30')}>
          <i class="fa-solid fa-rotate-right"></i><span class="tf-zahl">30</span>
        </button>
      </div>
    {:else}
      <div class="knoepfe">
        <button class="rund tf-rund mittel" onclick={steuerung.voriger} aria-label={t('telefon.voriger')} title={t('telefon.voriger')}>
          <i class="fa-solid fa-backward-step"></i>
        </button>
        <button class="rund tf-rund mittel" onclick={steuerung.stoppen} aria-label={t('telefon.stopp')} title={t('telefon.stopp')}>
          <i class="fa-solid fa-stop"></i>
        </button>
        <button class="knopf primaer tf-rund tf-gross" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
          <i class="fa-solid {spielt ? 'fa-pause' : 'fa-play'}"></i>
        </button>
        <button class="rund tf-rund mittel" onclick={steuerung.naechster} aria-label={t('telefon.naechster')} title={t('telefon.naechster')}>
          <i class="fa-solid fa-forward-step"></i>
        </button>
      </div>
      {#if puffer.aktiv}
        <!-- Zeitversatz mit Titeln und Werbung (RAD-46, Entwurf puffer.html Zustand 6) -->
        <div class="tf-versatz">
          <div class="tf-versatz-kopf">
            <span class="tf-etikett">{t('puffer.zeitversatz')}</span>
            <!-- Ton des Zeitversatzes auch am Telefon wählbar (RAD-92): manches Telefon spielt das Original nicht -->
            <Auswahl wert={bitrate.vorgabe} optionen={tonOptionen} symbol="fa-wave-square" titel={t('kanzel.bitrateName')}
                     onwahl={(w) => { bitrate.vormerken(w); void bitrate.anwenden(); }} />
          </div>
          <PufferBalken stelle={pStelle} links={t('puffer.vorLive', { zeit: formatTimeShort(puffer.hinter) })}
            mitte={t('puffer.laengeVonMax', { laenge: formatTimeShort(puffer.ende - puffer.anfang), max: formatTimeShort(puffer.groesste) })} />
          <div class="tf-versatz-titel">
            {#if pTitel}<b>{pName(pTitel)}</b><span>{t('puffer.vonLaenge', { a: formatTimeShort(Math.max(0, pStelle - pTitel.von)), b: formatTimeShort(pTitel.bis - pTitel.von) })}</span>
            {:else}<span>{t('puffer.ohneTitel')}</span>{/if}
          </div>
          <div class="tf-versatz-knoepfe">
            <button type="button" class="knopf" aria-label={t('puffer.titelZurueckHilfe')} disabled={vorheriger(puffer.abschnitte, pStelle) === null} onclick={() => puffer.vorher()}>
              <i class="fa-solid fa-backward-step"></i>{t('puffer.titelZurueck')}</button>
            <button type="button" class="knopf" aria-label={t('puffer.titelVorHilfe')} disabled={naechster(puffer.abschnitte, pStelle) === null} onclick={() => puffer.weiter()}>
              {t('puffer.titelVor')}<i class="fa-solid fa-forward-step"></i></button>
            <button type="button" class="knopf" aria-label={t('player.goLive')} disabled={!!appState.isLive} onclick={live}><i class="fa-solid fa-tower-broadcast"></i>{t('kanzel.live')}</button>
            <button type="button" class="knopf primaer" onclick={() => (pufferOffen = true)}><i class="fa-solid fa-list-ul"></i>{t('puffer.puffer')}</button>
          </div>
        </div>
      {/if}
    {/if}
    <!-- unten nebeneinander (RAD-90): den Sender in der Liste wiederfinden (Nutzer 20.11.2026) und Geräte (RAD-18, blinkt
         ruhig, solange woanders etwas spielt) -->
    {#if !folge || kann.uebergabe}
      <div class="tf-fuss">
        {#if !folge}
          <button class="knopf tf-zur-liste" onclick={steuerung.zurListe}><i class="fa-solid fa-location-crosshairs"></i> {t('telefon.inListeZeigen')}</button>
        {/if}
        {#if kann.uebergabe}
          <button class="knopf tf-zur-liste tf-geraete" class:blinkt={geraete.spielenWoanders.length > 0} onclick={() => (geraeteOffen = true)}>
            <i class="fa-solid fa-tower-broadcast"></i>
            {geraete.spielenWoanders.length ? t('geraete.telefonKnopfSpielt', { n: geraete.spielenWoanders.length }) : t('geraete.telefonKnopf')}
          </button>
        {/if}
      </div>
    {/if}
  </div>
{/if}

{#if geraeteOffen && offen}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="tf-blatt-grund" onclick={() => (geraeteOffen = false)}></div>
  <div class="tf-blatt">
    <Geraeteliste uebergabe={geraete} zeile={geraeteZeile} texte={geraeteTexte()} telefon
                  hierSpielt={appState.isPlaying || appState.isPaused} onzu={() => (geraeteOffen = false)} />
  </div>
{/if}

{#if pufferOffen && offen}
  <TelefonPuffer onzu={() => (pufferOffen = false)} />
{/if}

<style>
  .tf-versatz { display: grid; gap: 8px; margin: 12px 0 4px; padding: 10px 12px; border-radius: 14px; background: var(--t-flaeche); }
  .tf-versatz-kopf { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .tf-etikett { font-size: var(--marke); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--t-text-2); }
  .tf-versatz-titel { display: grid; text-align: center; }
  .tf-versatz-titel b { font-size: var(--gross); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tf-versatz-titel span { font-size: var(--klein); color: var(--t-text-2); font-variant-numeric: tabular-nums; }
  .tf-versatz-knoepfe { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
  .tf-versatz-knoepfe .knopf { justify-content: center; gap: 6px; min-height: 44px; padding: 0 4px; font-size: var(--klein); }
  .tf-geraete.blinkt > i { color: var(--t-akzent); animation: tf-blinken 1.4s steps(1, end) infinite; }
  @keyframes tf-blinken { 50% { opacity: .25; } }
  @media (prefers-reduced-motion: reduce) { .tf-geraete.blinkt > i { animation: none; } }
  .tf-blatt-grund { position: fixed; inset: 0; z-index: 30; background: rgb(0 0 0 / .35); }
  .tf-blatt { position: fixed; inset: auto 0 0; z-index: 31; box-shadow: 0 -12px 30px rgb(0 0 0 / .4); }
  .tf-fuss { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 6px; }
  .tf-zur-liste { gap: 8px; min-height: 44px; padding: 0 16px; border-radius: 22px; font-size: 16px; white-space: nowrap; }
  /* Spielerleiste als kleines Gerät aus dem Material der Kanzel (RAD-97, Wahl A) */
  .tf-leiste {
    flex: none;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px 8px 12px;
    background-color: var(--rh-geraet);
    background-image: var(--rh-geraet-bild);
    color: var(--rh-geraet-tinte);
    box-shadow: var(--rh-kanzel-schatten);
  }
  /* das Rasterdisplay füllt den Platz zwischen Bild und Knopf; jede Zeile misst ihre eigene Breite */
  .tf-raster { flex: 1; min-width: 0; padding: 6px 8px; gap: 2px; }
  .tf-raster .rh-display-zeile { container-type: inline-size; }
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
  .zusatz { font-size: 15px; color: var(--t-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* Knöpfe des Appkerns (rund, knopf, primaer; RAD-97): hier nur Form und Größe, Material und Farben kommen aus der
     Vorlage (HiFi oder Klassisch) */
  .tf-rund {
    position: relative;
    width: 52px;
    height: 52px;
    flex: none;
    padding: 0;
    border-radius: 50%;
    justify-content: center;
    font-size: 20px;
  }
  .tf-rund.mittel { width: clamp(52px, 17vw, 64px); height: clamp(52px, 17vw, 64px); font-size: 24px; }
  .tf-rund.tf-gross { width: clamp(68px, 22vw, 84px); height: clamp(68px, 22vw, 84px); font-size: 32px; }
  .tf-zahl { position: absolute; left: 0; right: 0; bottom: 6px; font-size: 15px; font-weight: 700; }

  .vollbild {
    position: fixed;
    inset: 0;
    z-index: 20;
    isolation: isolate;
    display: flex;
    flex-direction: column;
    padding: var(--rahmen-sicher-oben) var(--rahmen-rand) 24px;
    background: var(--t-grund);
    color: var(--t-text);
    overflow-y: auto;
    overflow-x: hidden;
  }
  .vollbild > :not(.tf-schein) { position: relative; z-index: 1; }
  /* Farbschein: das Logo stark weichgezeichnet und gesättigt über die ganze Fläche, darüber der Grund halb deckend,
     damit Schrift in hell und dunkel lesbar bleibt; ohne Logo ein Schein aus dem Akzent */
  .tf-schein { position: fixed; inset: -20%; z-index: 0; pointer-events: none; background-size: cover; background-position: center;
    filter: blur(60px) saturate(1.8); transform: translateZ(0); }
  /* ohne Logo der Schein aus der Lackfarbe der Kachel (RAD-100) */
  .tf-schein.ohne { background-image: radial-gradient(circle at 50% 30%, var(--lack, var(--t-akzent)), transparent 70%); }
  .tf-schein::after { content: ""; position: absolute; inset: 0; background: color-mix(in srgb, var(--t-grund) 55%, transparent); }
  /* Glas auf dem Schein */
  /* Glas nur für den Kasten des Zeitversatzes; die Knöpfe darauf sind Knöpfe des Appkerns (RAD-97) */
  .vollbild .tf-versatz {
    background: color-mix(in srgb, var(--t-flaeche-2) 70%, transparent); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
  .tf-cover { display: grid; }
  .tf-cover :global(.tf-bild) { border-radius: 22px; box-shadow: 0 18px 40px -12px rgb(0 0 0 / .55); }
  .vollbild-kopf { display: flex; }
  .kopf-knopf { width: 48px; height: 48px; border: none; border-radius: 12px; background: transparent; color: var(--t-text); font-size: 22px; }
  .buehne { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; min-height: 0; text-align: center; }
  .buehne > * { flex-shrink: 0; }   /* Titel und Sender werden nie zusammengedrückt; das Bild richtet sich nach der Höhe */
  /* Titel höchstens zwei Zeilen, Sender oder Abo eine (RAD-90): nichts rutscht unter die Tasten */
  .buehne h2 { margin: 12px 0 0; font-size: 22px; font-weight: 700; overflow-wrap: anywhere; line-height: 1.25;
    display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; overflow: hidden; }
  .tf-sender-aktionen { display: flex; gap: 14px; justify-content: center; margin-top: 4px; }
  .buehne .zusatz { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-inline-size: 100%; }
  .position { margin: 16px 0 4px; }
  .position input { width: 100%; height: 32px; accent-color: var(--t-akzent); }
  .zeiten { display: flex; justify-content: space-between; font-size: 15px; color: var(--t-text-2); font-variant-numeric: tabular-nums; }
  .knoepfe { display: flex; align-items: center; justify-content: center; gap: clamp(10px, 4vw, 24px); margin: 16px 0 8px; }
</style>
