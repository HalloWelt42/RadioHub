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
  import { Geraeteliste } from 'appkern-oberflaeche';
  import { faehigkeiten } from '../../lib/playerEngine.js';
  import { geraete, geraeteTexte, geraeteZeile } from '../../spieler/geraete.svelte';

  let { offen = $bindable(false), zeit = 0, dauer = 0, steuerung } = $props();

  const info = $derived(beschreibung(appState));
  const folge = $derived(!!appState.currentEpisode);
  const spielt = $derived(appState.isPlaying && !appState.isPaused);
  const bildSrc = $derived(info?.artwork?.[0]?.src || null);
  let ziehen = $state(null);
  /** Puffer-Liste über dem Spieler (RAD-46) */
  let pufferOffen = $state(false);
  /** Geräte als Blatt von unten (RAD-18) */
  let geraeteOffen = $state(false);
  const kann = faehigkeiten();
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
      <Bild src={bildSrc} symbol={folge ? 'fa-podcast' : 'fa-radio'} groesse={44} />
      <span class="tf-text">
        <span class="tf-titel">{info.title}</span>
        <span class="zusatz">{info.artist || (folge ? '' : t('telefon.live'))}</span>
      </span>
    </button>
    <button class="tf-rund" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
      <i class="fa-solid {spielt ? 'fa-pause' : 'fa-play'}"></i>
    </button>
  </div>
{/if}

{#if offen && info}
  <div class="vollbild" role="dialog" aria-modal="true" aria-label={info.title}>
    <!-- Farbschein aus dem Logo über die ganze Fläche, Bedienflächen als Glas darauf (RAD-56, Wahl A) -->
    <div class="tf-schein" class:ohne={!bildSrc} aria-hidden="true" style:background-image={bildSrc ? `url("${bildSrc}")` : null}></div>
    <div class="vollbild-kopf">
      <button class="kopf-knopf" onclick={() => (offen = false)} aria-label={t('telefon.spielerSchliessen')}>
        <i class="fa-solid fa-chevron-down"></i>
      </button>
    </div>
    <div class="buehne">
      <span class="tf-cover"><Bild src={bildSrc} symbol={folge ? 'fa-podcast' : 'fa-radio'} groesse="min(72vw, 320px)" /></span>
      <h2>{info.title}</h2>
      <p class="zusatz">{info.artist || (folge ? '' : t('telefon.live'))}</p>
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
        <button class="tf-rund mittel" onclick={() => steuerung.zurueck(15)} aria-label={t('telefon.zurueck15')} title={t('telefon.zurueck15')}>
          <i class="fa-solid fa-rotate-left"></i><span class="tf-zahl">15</span>
        </button>
        <button class="tf-rund tf-gross" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
          <i class="fa-solid {spielt ? 'fa-pause' : 'fa-play'}"></i>
        </button>
        <button class="tf-rund mittel" onclick={() => steuerung.vor(30)} aria-label={t('telefon.vor30')} title={t('telefon.vor30')}>
          <i class="fa-solid fa-rotate-right"></i><span class="tf-zahl">30</span>
        </button>
      </div>
    {:else}
      <div class="knoepfe">
        <button class="tf-rund mittel" onclick={steuerung.voriger} aria-label={t('telefon.voriger')} title={t('telefon.voriger')}>
          <i class="fa-solid fa-backward-step"></i>
        </button>
        <button class="tf-rund mittel" onclick={steuerung.stoppen} aria-label={t('telefon.stopp')} title={t('telefon.stopp')}>
          <i class="fa-solid fa-stop"></i>
        </button>
        <button class="tf-rund tf-gross" onclick={steuerung.umschalten} aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
          <i class="fa-solid {spielt ? 'fa-pause' : 'fa-play'}"></i>
        </button>
        <button class="tf-rund mittel" onclick={steuerung.naechster} aria-label={t('telefon.naechster')} title={t('telefon.naechster')}>
          <i class="fa-solid fa-forward-step"></i>
        </button>
      </div>
      {#if puffer.aktiv}
        <!-- Zeitversatz mit Titeln und Werbung (RAD-46, Entwurf puffer.html Zustand 6) -->
        <div class="tf-versatz">
          <span class="tf-etikett">{t('puffer.zeitversatz')}</span>
          <PufferBalken stelle={pStelle} links={t('puffer.vorLive', { zeit: formatTimeShort(puffer.hinter) })}
            mitte={t('puffer.laengeVonMax', { laenge: formatTimeShort(puffer.ende - puffer.anfang), max: formatTimeShort(puffer.groesste) })} />
          <div class="tf-versatz-titel">
            {#if pTitel}<b>{pName(pTitel)}</b><span>{t('puffer.vonLaenge', { a: formatTimeShort(Math.max(0, pStelle - pTitel.von)), b: formatTimeShort(pTitel.bis - pTitel.von) })}</span>
            {:else}<span>{t('puffer.ohneTitel')}</span>{/if}
          </div>
          <div class="tf-versatz-knoepfe">
            <button type="button" aria-label={t('puffer.titelZurueckHilfe')} disabled={vorheriger(puffer.abschnitte, pStelle) === null} onclick={() => puffer.vorher()}>
              <i class="fa-solid fa-backward-step"></i>{t('puffer.titelZurueck')}</button>
            <button type="button" aria-label={t('puffer.titelVorHilfe')} disabled={naechster(puffer.abschnitte, pStelle) === null} onclick={() => puffer.weiter()}>
              {t('puffer.titelVor')}<i class="fa-solid fa-forward-step"></i></button>
            <button type="button" aria-label={t('player.goLive')} disabled={!!appState.isLive} onclick={live}><i class="fa-solid fa-tower-broadcast"></i>{t('kanzel.live')}</button>
            <button type="button" class="tf-primaer" onclick={() => (pufferOffen = true)}><i class="fa-solid fa-list-ul"></i>{t('puffer.puffer')}</button>
          </div>
        </div>
      {/if}
      <!-- den laufenden Sender in der Liste wiederfinden (Nutzer 20.11.2026) -->
      <button class="tf-zur-liste" onclick={steuerung.zurListe}><i class="fa-solid fa-location-crosshairs"></i> {t('telefon.inListeZeigen')}</button>
    {/if}
    {#if kann.uebergabe}
      <!-- Übergabe zwischen Geräten (RAD-18): blinkt ruhig, solange woanders etwas spielt -->
      <button class="tf-zur-liste tf-geraete" class:blinkt={geraete.spielenWoanders.length > 0} onclick={() => (geraeteOffen = true)}>
        <i class="fa-solid fa-tower-broadcast"></i>
        {geraete.spielenWoanders.length ? t('geraete.telefonKnopfSpielt', { n: geraete.spielenWoanders.length }) : t('geraete.telefonKnopf')}
      </button>
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
  .tf-etikett { font-size: var(--marke); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--t-text-2); }
  .tf-versatz-titel { display: grid; text-align: center; }
  .tf-versatz-titel b { font-size: var(--gross); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tf-versatz-titel span { font-size: var(--klein); color: var(--t-text-2); font-variant-numeric: tabular-nums; }
  .tf-versatz-knoepfe { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
  .tf-versatz-knoepfe button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px; padding: 0 4px;
    border: 1px solid var(--rand); border-radius: 10px; background: var(--t-flaeche-2); color: var(--t-text); font: inherit; font-size: var(--klein); }
  .tf-versatz-knoepfe button:disabled { opacity: .45; }
  .tf-versatz-knoepfe .tf-primaer { background: var(--t-akzent-flaeche); color: var(--t-akzent-text); font-weight: 700; }
  .tf-geraete.blinkt > i { color: var(--t-akzent); animation: tf-blinken 1.4s steps(1, end) infinite; }
  @keyframes tf-blinken { 50% { opacity: .25; } }
  @media (prefers-reduced-motion: reduce) { .tf-geraete.blinkt > i { animation: none; } }
  .tf-blatt-grund { position: fixed; inset: 0; z-index: 30; background: rgb(0 0 0 / .35); }
  .tf-blatt { position: fixed; inset: auto 0 0; z-index: 31; box-shadow: 0 -12px 30px rgb(0 0 0 / .4); }
  .tf-zur-liste { align-self: center; display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 18px; margin-top: 6px;
    border: 1px solid var(--rand); border-radius: 22px; background: var(--t-flaeche); color: var(--t-text); font-size: 16px; }
  .tf-leiste {
    flex: none;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px 8px 12px;
    background: var(--t-flaeche);
    border-top: 1px solid var(--rand);
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
  .tf-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .tf-titel { font-size: 17px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .zusatz { font-size: 15px; color: var(--t-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tf-rund {
    position: relative;
    width: 52px;
    height: 52px;
    flex: none;
    border: none;
    border-radius: 50%;
    background: var(--t-akzent-flaeche);
    color: var(--t-akzent-text);
    font-size: 20px;
  }
  .tf-rund.mittel { width: clamp(52px, 17vw, 64px); height: clamp(52px, 17vw, 64px); background: var(--t-flaeche-2); color: var(--t-text); font-size: 24px; }
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
  .tf-schein.ohne { background-image: radial-gradient(circle at 50% 30%, var(--t-akzent), transparent 70%); }
  .tf-schein::after { content: ""; position: absolute; inset: 0; background: color-mix(in srgb, var(--t-grund) 55%, transparent); }
  /* Glas auf dem Schein */
  .vollbild :is(.tf-versatz, .tf-zur-liste, .tf-rund.mittel) {
    background: color-mix(in srgb, var(--t-grund) 45%, transparent); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
  .vollbild .tf-versatz-knoepfe button:not(.tf-primaer) { background: color-mix(in srgb, var(--t-grund) 35%, transparent); }
  .tf-cover { display: grid; }
  .tf-cover :global(.tf-bild) { border-radius: 22px; box-shadow: 0 18px 40px -12px rgb(0 0 0 / .55); }
  .vollbild-kopf { display: flex; }
  .kopf-knopf { width: 48px; height: 48px; border: none; border-radius: 12px; background: transparent; color: var(--t-text); font-size: 22px; }
  .buehne { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; min-height: 0; text-align: center; }
  .buehne h2 { margin: 16px 0 0; font-size: 24px; font-weight: 700; overflow-wrap: anywhere; }
  .buehne .zusatz { white-space: normal; }
  .position { margin: 16px 0 4px; }
  .position input { width: 100%; height: 32px; accent-color: var(--t-akzent); }
  .zeiten { display: flex; justify-content: space-between; font-size: 15px; color: var(--t-text-2); font-variant-numeric: tabular-nums; }
  .knoepfe { display: flex; align-items: center; justify-content: center; gap: clamp(10px, 4vw, 24px); margin: 16px 0 8px; }
</style>
