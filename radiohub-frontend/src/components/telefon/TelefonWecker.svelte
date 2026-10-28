<script>
  /**
   * Weckeransicht (Telefon quer, Nachttisch): links die Uhr mit Datum, rechts was läuft, der nächste Wecker und
   * Sonnenauf- und -untergang. Nachts (nach Sonnenzeiten oder von Hand) dunkelrot auf schwarz. Hält den Bildschirm
   * wach und löst die Wecker aus, solange sie offen ist; Web-Apps werden im Hintergrund nicht geweckt.
   */
  import { onDestroy } from 'svelte';
  import '@fontsource/chakra-petch/700.css';
  import { appState, actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { api } from '../../lib/api.js';
  import { sonnenzeiten, istNacht } from '../../lib/sonne.js';
  import { naechsterWecker, faelligInMinute } from '../../lib/wecker.js';
  import { beschreibung } from '../../lib/telefon/medien.js';
  import { weckeransichtOffen } from '../../lib/telefon/wachHalten.svelte.js';
  import { weckerdaten, weckerLaden } from '../../lib/telefon/weckerdaten.svelte.js';
  import { zeit, ansagen, abbrechen, entsperren, bausteineLaden, zeitansageSchalten } from '../../lib/telefon/zeitansage.svelte.js';
  import { sperren, freigeben } from '../../lib/aktualisierung.svelte.js';

  let { steuerung } = $props();

  const NACHT_SCHLUESSEL = 'radiohub_nachtschaltung';
  let jetzt = $state(new Date());

  // Uhr: Chakra Petch fett, so groß wie die linke Fläche erlaubt. Jede Ziffer steht in einer Zelle von der Breite der
  // breitesten Ziffer, der Doppelpunkt in seiner eigenen; so wackelt nichts, wenn die Zahlen wechseln.
  const UHR_SCHRIFT = '700 100px "Chakra Petch"';
  const UHR_STRECKUNG = 1.6; // Ziffern in der Höhe gestreckt (Nutzer: "knapp 1,6-fache Höhe")
  let uhrFlaeche = $state(null);
  let datumZeile = $state(null);
  let zifferBreite = $state(0.6);
  let doppelpunktBreite = $state(0.3);
  let uhrGroesse = $state(80);

  function uhrAnpassen() {
    if (!uhrFlaeche) return;
    const breite = uhrFlaeche.clientWidth;
    const hoehe = uhrFlaeche.clientHeight - (datumZeile?.offsetHeight ?? 0) - 8;
    uhrGroesse = Math.max(24, Math.floor(Math.min(breite / (4 * zifferBreite + doppelpunktBreite), hoehe / UHR_STRECKUNG)));
  }

  async function uhrVermessen() {
    try { await document.fonts.load(UHR_SCHRIFT, '0123456789:'); } catch { /* Ersatzschrift misst dann */ }
    const ctx = document.createElement('canvas').getContext('2d');
    ctx.font = UHR_SCHRIFT;
    zifferBreite = Math.max(...'0123456789'.split('').map((z) => ctx.measureText(z).width)) / 100;
    doppelpunktBreite = ctx.measureText(':').width / 100;
    uhrAnpassen();
  }

  $effect(() => {
    if (!uhrFlaeche) return;
    uhrVermessen();
    const beobachter = new ResizeObserver(uhrAnpassen);
    beobachter.observe(uhrFlaeche);
    return () => beobachter.disconnect();
  });
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
  bausteineLaden();
  let angesagt = '';
  const takt = setInterval(() => { jetzt = new Date(); pruefen(); zeitPruefen(); }, 1000);

  // Die Zeitansage gibt es nur, solange die Weckeransicht offen und sichtbar ist
  function sichtbarkeit() {
    if (document.visibilityState !== 'visible') abbrechen();
  }
  document.addEventListener('visibilitychange', sichtbarkeit);

  onDestroy(() => {
    clearInterval(takt);
    clearInterval(anstieg);
    document.removeEventListener('visibilitychange', sichtbarkeit);
    abbrechen();
    freigeben('schlummern');
    weckeransichtOffen(false);
  });

  /** Alle 5 Minuten zur vollen Minute, nicht während der Wecker klingelt. */
  function zeitPruefen() {
    const schluessel = `${jetzt.getHours()}:${jetzt.getMinutes()}`;
    if (!zeit.an || klingelt || jetzt.getMinutes() % 5 !== 0 || angesagt === schluessel) return;
    if (document.visibilityState !== 'visible') return;
    angesagt = schluessel;
    ansagen({ nacht, jetzt });
  }

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
      freigeben('schlummern');
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
    abbrechen();
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
    freigeben('schlummern');
    actions.stop();
  }

  function schlummern() {
    const w = klingelt;
    clearInterval(anstieg);
    klingelt = null;
    actions.stop();
    schlummerWecker = w;
    schlummerBis = new Date(Date.now() + (w?.schlummern_min || 9) * 60000);
    sperren('schlummern');   // keine Aktualisierung, solange geschlummert wird
  }
</script>

<div class="wecker" class:nacht onpointerdown={entsperren}>
  <div class="links" bind:this={uhrFlaeche}>
    <div class="uhr" style:font-size="{uhrGroesse}px" style:--streckung={UHR_STRECKUNG}>
      {#each hhmm(jetzt).split('') as zeichen, i (i)}
        <span class="zeichen" style:width="{zeichen === ':' ? doppelpunktBreite : zifferBreite}em">{zeichen}</span>
      {/each}
    </div>
    <div class="datum" bind:this={datumZeile}>{datum}</div>
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
          <span class="titel">{info ? info.title : '-'}</span>
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
          <span class="wert">-</span>
        {/if}
      </div>

      {#if sonne && !sonne.polar}
        <div class="block sonne">
          <span><i class="fa-solid fa-sun"></i> {t('telefon.aufgang')} {hhmm(sonne.aufgang)}</span>
          <span><i class="fa-solid fa-moon"></i> {t('telefon.untergang')} {hhmm(sonne.untergang)}</span>
        </div>
      {/if}

      <div class="ansage">
        <button class="ansage-jetzt" disabled={!zeit.bereit || zeit.laeuft}
          onclick={() => ansagen({ nacht, jetzt: new Date() })}
          title={zeit.bereit ? t('telefon.zeitAnsagen') : t('telefon.zeitansageFehlt')}>
          <i class="fa-solid {zeit.laeuft ? 'fa-volume-high' : 'fa-comment-dots'}"></i> {t('telefon.zeitAnsagen')}
        </button>
        <button class="ansage-schalter" class:an={zeit.an} aria-pressed={zeit.an} onclick={() => zeitansageSchalten(!zeit.an)}
          title={t('telefon.zeitansageAlle5')}>
          <i class="fa-solid fa-clock-rotate-left"></i> {zeit.an ? t('telefon.ansageAn') : t('telefon.ansageAus')}
        </button>
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
  .links { height: 100%; }
  .uhr { font-family: 'Chakra Petch', var(--hifi-font-body); font-weight: 700; line-height: 1; letter-spacing: 0; white-space: nowrap; display: flex;
    /* gestreckt ohne die Breite zu ändern; der Rand hält den Platz frei, den die Streckung oben und unten braucht */
    transform: scaleY(var(--streckung)); margin: calc((var(--streckung) - 1) * 0.5em) 0; }
  .zeichen { display: inline-block; text-align: center; }
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
  .ansage { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr); gap: 6px; }
  .ansage button { min-height: 48px; border: 1px solid var(--w-linie); border-radius: 24px; background: transparent; color: var(--w-text);
    font: inherit; font-size: 17px; display: flex; align-items: center; justify-content: center; gap: 8px; white-space: nowrap; overflow: hidden; }
  .ansage .ansage-jetzt { background: var(--w-akzent); border-color: var(--w-akzent); color: var(--w-akzent-text); font-weight: 600; }
  .ansage .ansage-jetzt:disabled { background: transparent; color: var(--w-text-2); border-color: var(--w-linie); }
  .ansage .ansage-schalter.an { border-color: var(--w-text); font-weight: 600; }
  .gross-text { margin: 0; font-size: 24px; font-weight: 700; }
  .riesig { min-height: 72px; border: none; border-radius: 18px; background: var(--w-akzent); color: var(--w-akzent-text); font: inherit; font-size: 24px; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 12px; }
  .riesig.aus { background: transparent; color: var(--w-text); border: 2px solid var(--w-text); }
</style>
