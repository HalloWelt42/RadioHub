<script>
  /**
   * Weckeransicht (Telefon quer, Nachttisch) in zwei Layouts nach mockups/querformat.html, umschaltbar per Wischen:
   * "sonne" (D: große Uhr, darunter das Sonnenband, rechts Sender, Wecker, Knöpfe) und "uhr" (B: Uhr vollflächig,
   * unten eine schmale Leiste, die Knöpfe erst nach Antippen). Ein scharfer Wecker ist in beiden unübersehbar.
   * Nachts (nach Sonnenzeiten oder von Hand) dunkelrot auf schwarz. Hält den Bildschirm wach, löst die Wecker aus,
   * sagt die Zeit an und verbindet neu, wenn der Sender ausfällt; nur solange sie offen ist.
   */
  import { onDestroy } from 'svelte';
  import { appState, actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { api } from '../../lib/api.js';
  import { sonnenzeiten, istNacht } from '../../lib/sonne.js';
  import { naechsterWecker, faelligInMinute } from '../../lib/wecker.js';
  import { geste } from '../../lib/telefon/geste.js';
  import { Waechter, hoerbarMesser, wunsch } from '../../lib/telefon/verbindung.svelte.js';
  import { wecktonVorbereiten, wecktonAn, wecktonAus } from '../../lib/telefon/weckton.js';
  import { weckeransichtOffen } from '../../lib/telefon/wachHalten.svelte.js';
  import { weckerdaten, weckerLaden } from '../../lib/telefon/weckerdaten.svelte.js';
  import { zeit, ansagen, abbrechen, entsperren, bausteineLaden, zeitansageSchalten } from '../../lib/telefon/zeitansage.svelte.js';
  import { sperren, freigeben } from '../../lib/aktualisierung.svelte.js';
  import WeckerUhr from './WeckerUhr.svelte';
  import WeckerSonnenband from './WeckerSonnenband.svelte';

  let { steuerung, audio = null } = $props();

  // --- Einstellungen im Gerät ---------------------------------------------------------------------------------------
  const NACHT_SCHLUESSEL = 'radiohub_nachtschaltung';
  const LAYOUT_SCHLUESSEL = 'radiohub_weckerlayout';
  const LAYOUTS = ['sonne', 'uhr'];
  const lesen = (s, v) => { try { return localStorage.getItem(s) || v; } catch { return v; } };
  const schreiben = (s, w) => { try { localStorage.setItem(s, w); } catch { /* privates Fenster */ } };

  let nachtWahl = $state(lesen(NACHT_SCHLUESSEL, 'auto'));
  let layout = $state(LAYOUTS.includes(lesen(LAYOUT_SCHLUESSEL, '')) ? lesen(LAYOUT_SCHLUESSEL, '') : 'sonne');

  // ein Knopf, drei Stufen: automatisch nach Sonnenzeiten, immer Rot, immer normal
  const NACHT_FOLGE = { auto: 'an', an: 'aus', aus: 'auto' };
  const NACHT_SYMBOL = { auto: 'fa-circle-half-stroke', an: 'fa-moon', aus: 'fa-sun' };
  const NACHT_TEXT = { auto: 'nachtAuto', an: 'nachtAn', aus: 'nachtAus' };
  function nachtSetzen(wert) { nachtWahl = wert; schreiben(NACHT_SCHLUESSEL, wert); }

  function layoutWechseln(schritt) {
    const i = LAYOUTS.indexOf(layout);
    layout = LAYOUTS[(i + schritt + LAYOUTS.length) % LAYOUTS.length];
    schreiben(LAYOUT_SCHLUESSEL, layout);
  }

  // --- Zeit und abgeleitete Werte -----------------------------------------------------------------------------------
  let jetzt = $state(new Date());
  const ort = $derived(weckerdaten.ort);
  const sonne = $derived(ort.breite != null && ort.laenge != null ? sonnenzeiten(jetzt, ort.breite, ort.laenge) : null);
  const nacht = $derived(nachtWahl === 'an' || (nachtWahl === 'auto' && istNacht(jetzt, ort.breite, ort.laenge) === true));
  const naechster = $derived(naechsterWecker(weckerdaten.liste, jetzt));
  const spielt = $derived(appState.isPlaying && !appState.isPaused);
  const senderName = $derived(appState.currentStation?.name || appState.currentEpisode?.title || '');
  const zwei = (n) => String(n).padStart(2, '0');
  const hhmm = (d) => (d ? `${zwei(d.getHours())}:${zwei(d.getMinutes())}` : '--:--');
  const tagKurz = (d) => d.toLocaleDateString(undefined, { weekday: 'short' });

  // --- Wecker ---------------------------------------------------------------------------------------------------------
  let klingelt = $state(null);
  let schlummerBis = $state(null);
  let schlummerWecker = null;
  const ausgeloest = new Set();
  let anstieg = null;

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
    wunsch.spielen = true;
    const ziel = w.lautstaerke || 60;
    const schritte = Math.max(1, w.anstieg_s || 0);
    let stufe = 0;
    actions.setVolume(w.anstieg_s ? 5 : ziel);
    if (w.quelle === 'sender' && w.sender) {
      waechter.bewachen(w.sender, { wecker: true });
      await actions.playStation(w.sender);
    } else if (w.podcast_id) {
      try {
        const r = await api.getEpisodes(w.podcast_id, 1, 0, 'all');
        const folge = r.episodes?.[0];
        const abo = appState.podcasts.find((p) => p.id === w.podcast_id) || { id: w.podcast_id };
        if (folge) {
          waechter.bewachen({ ...folge, podcast: abo }, { wecker: true });
          actions.playEpisode(folge, abo);
        }
      } catch { /* Abo nicht erreichbar: der Wächter weckt mit dem Weckton */ }
      if (!waechter.ziel) waechter.bewachen({ fehlt: true }, { wecker: true });
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

  function stille() {
    clearInterval(anstieg);
    klingelt = null;
    wunsch.spielen = false;
    waechter.lassen();
    actions.stop();
  }

  function aus() {
    stille();
    schlummerBis = null;
    schlummerWecker = null;
    freigeben('schlummern');
  }

  function schlummern() {
    const w = klingelt;
    stille();
    schlummerWecker = w;
    schlummerBis = new Date(Date.now() + (w?.schlummern_min || 9) * 60000);
    sperren('schlummern');   // keine Aktualisierung, solange geschlummert wird
  }

  // --- Verbindung: neu verbinden, wenn nichts zu hören ist, obwohl etwas laufen soll ---------------------------------
  const waechter = new Waechter({
    hoerbar: hoerbarMesser(() => audio),
    starten: (ziel) => {
      if (ziel.fehlt) return null;
      return ziel.uuid ? actions.playStation(ziel) : actions.playEpisode(ziel, ziel.podcast);
    },
    ton: { an: wecktonAn, aus: wecktonAus }
  });

  // Läuft beim Öffnen schon etwas, soll es weiterlaufen
  wunsch.spielen = appState.isPlaying && !appState.isPaused;
  const zielSchluessel = $derived(appState.currentStation?.uuid ?? (appState.currentEpisode ? `folge-${appState.currentEpisode.id}` : null));
  $effect(() => {
    const soll = wunsch.spielen;
    const schluessel = zielSchluessel;
    if (klingelt) return;   // beim Wecken bewacht ausloesen selbst
    if (soll && schluessel) {
      waechter.bewachen(appState.currentStation ?? { ...appState.currentEpisode, podcast: appState.currentEpisode?.podcast });
    } else {
      waechter.lassen();
    }
  });

  function umschalten() {
    wunsch.spielen = !spielt;
    steuerung.umschalten();
  }

  // --- Zeitansage -----------------------------------------------------------------------------------------------------
  let angesagt = '';
  function zeitPruefen() {
    const schluessel = `${jetzt.getHours()}:${jetzt.getMinutes()}`;
    if (!zeit.an || klingelt || jetzt.getMinutes() % 5 !== 0 || angesagt === schluessel) return;
    if (document.visibilityState !== 'visible') return;
    angesagt = schluessel;
    ansagen({ nacht, jetzt });
  }

  // Antippen der Ziffern sagt die Zeit sofort an; ohne fertige Bausteine zucken die Ziffern nur kurz
  let zucken = $state(false);
  function zifferTipp() {
    if (zeit.bereit && !zeit.laeuft) {
      ansagen({ nacht, jetzt: new Date() });
    } else if (!zeit.laeuft) {
      zucken = true;
      setTimeout(() => { zucken = false; }, 300);
    }
  }

  // --- Gesten: Wischen wechselt das Layout, Antippen der Ziffern sagt an, sonst zeigt es im Layout "uhr" die Knöpfe ----
  let start = null;
  let klickSperre = false;
  let knoepfeBis = $state(0);
  const knoepfeSichtbar = $derived(layout === 'sonne' || jetzt.getTime() < knoepfeBis);
  const KNOEPFE_MS = 6000;

  function zeigeKnoepfe() { knoepfeBis = Date.now() + KNOEPFE_MS; jetzt = new Date(); }

  function down(e) {
    entsperren();
    start = { x: e.clientX, y: e.clientY, t: Date.now() };
    if (layout === 'uhr' && knoepfeSichtbar) zeigeKnoepfe();   // jede Berührung hält die Knöpfe offen
  }
  function up(e) {
    if (!start) return;
    const art = geste(start, { x: e.clientX, y: e.clientY, t: Date.now() });
    start = null;
    if (art === 'links' || art === 'rechts') {
      klickSperre = true;   // ein Wischen über einem Knopf löst ihn nicht aus
      setTimeout(() => { klickSperre = false; }, 0);
      layoutWechseln(art === 'links' ? 1 : -1);
    } else if (art === 'tippen' && e.target.closest('.uhr-box')) {
      zifferTipp();
    } else if (art === 'tippen' && layout === 'uhr' && !e.target.closest('button')) {
      zeigeKnoepfe();
    }
  }
  function klickFangen(e) {
    if (klickSperre) { e.stopPropagation(); e.preventDefault(); }
  }

  // --- Lebenslauf -----------------------------------------------------------------------------------------------------
  weckeransichtOffen(true);
  weckerLaden();
  bausteineLaden();
  try { wecktonVorbereiten(); } catch { /* ohne Web Audio kein Weckton */ }
  const takt = setInterval(() => {
    jetzt = new Date();
    pruefen();
    zeitPruefen();
    waechter.takt(Date.now());
  }, 1000);

  // Zeitansage und Wächter nur, solange die Weckeransicht offen und sichtbar ist
  function sichtbarkeit() {
    if (document.visibilityState !== 'visible') abbrechen();
  }
  document.addEventListener('visibilitychange', sichtbarkeit);

  onDestroy(() => {
    clearInterval(takt);
    clearInterval(anstieg);
    document.removeEventListener('visibilitychange', sichtbarkeit);
    abbrechen();
    waechter.lassen();
    freigeben('schlummern');
    weckeransichtOffen(false);
  });

  const VERBINDUNG_SYMBOL = { ok: 'fa-signal', verbindet: 'fa-rotate fa-spin', gestoert: 'fa-triangle-exclamation' };
</script>

{#snippet weckerAnzeige(gross)}
  {#if schlummerBis}
    <span class="wecker-an" class:gross title={t('telefon.schlummertBis')}><i class="fa-solid fa-bed"></i>{hhmm(schlummerBis)}</span>
  {:else if naechster}
    <span class="wecker-an" class:gross title={t('telefon.naechsterWecker')}><i class="fa-solid fa-bell"></i>{tagKurz(naechster.zeitpunkt)} {hhmm(naechster.zeitpunkt)}</span>
  {:else}
    <span class="wecker-aus" class:gross title={t('telefon.keinWeckerAktiv')} aria-label={t('telefon.keinWeckerAktiv')}><i class="fa-solid fa-bell-slash"></i></span>
  {/if}
{/snippet}

{#snippet senderAnzeige()}
  <span class="sender">
    <i class="fa-solid fa-radio" aria-hidden="true"></i>
    <span class="name">{senderName || '-'}</span>
    {#if waechter.zustand !== 'aus'}
      <i class="fa-solid {VERBINDUNG_SYMBOL[waechter.zustand]} verbindung" class:warn={waechter.zustand === 'gestoert'}
        aria-label={waechter.zustand}></i>
    {/if}
  </span>
{/snippet}

{#snippet knoepfe()}
  <div class="knoepfe">
    <button class="symbol" disabled={!senderName} onclick={umschalten}
      aria-label={spielt ? t('telefon.pause') : t('telefon.abspielen')}>
      <i class="fa-solid {spielt ? (appState.playerMode === 'direct' ? 'fa-stop' : 'fa-pause') : 'fa-play'}"></i>
    </button>
    <!-- Ansage alle 5 Minuten an oder aus; sofort ansagen: auf die Ziffern tippen -->
    <button class="symbol" class:an={zeit.an} aria-pressed={zeit.an} onclick={() => zeitansageSchalten(!zeit.an)}
      aria-label={t('telefon.zeitansageAlle5')} title={zeit.an ? t('telefon.ansageAn') : t('telefon.ansageAus')}>
      <i class="fa-solid {zeit.laeuft ? 'fa-volume-high' : zeit.an ? 'fa-comment-dots' : 'fa-comment-slash'}"></i>
    </button>
    <button class="symbol" class:an={nachtWahl !== 'aus'} onclick={() => nachtSetzen(NACHT_FOLGE[nachtWahl])}
      aria-label={t('telefon.nacht') + ': ' + t('telefon.' + NACHT_TEXT[nachtWahl])} title={t('telefon.' + NACHT_TEXT[nachtWahl])}>
      <i class="fa-solid {NACHT_SYMBOL[nachtWahl]}"></i>
    </button>
  </div>
{/snippet}

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="wecker" class:nacht onpointerdown={down} onpointerup={up} onpointercancel={() => (start = null)}
  onclickcapture={klickFangen}>
  {#if layout === 'sonne'}
    <div class="layout-sonne">
      <div class="links">
        <div class="uhr-box" class:zucken><WeckerUhr text={hhmm(jetzt)} /></div>
        <WeckerSonnenband {jetzt} {sonne} />
      </div>
      <div class="rechts">
        <div class="block">{@render senderAnzeige()}
          {#if senderName}<i class="fa-solid {spielt ? 'fa-play' : 'fa-pause'} zustand" aria-label={spielt ? t('telefon.laeuft') : t('telefon.pausiert')}></i>{/if}
        </div>
        <div class="block">{@render weckerAnzeige(true)}</div>
        {@render knoepfe()}
      </div>
    </div>
  {:else}
    <div class="layout-uhr">
      <div class="uhr-box" class:zucken><WeckerUhr text={hhmm(jetzt)} /></div>
      <div class="leiste">
        {@render senderAnzeige()}
        {@render weckerAnzeige(true)}
        <span class="sonnenzeiten">
          {#if sonne && !sonne.polar}
            <i class="fa-solid fa-sun"></i>{hhmm(sonne.aufgang)} <i class="fa-solid fa-moon"></i>{hhmm(sonne.untergang)}
          {/if}
        </span>
      </div>
      {#if knoepfeSichtbar}<div class="schwebend">{@render knoepfe()}</div>{/if}
    </div>
  {/if}

  <div class="punkte" aria-hidden="true">
    {#each LAYOUTS as l (l)}<span class:an={layout === l}></span>{/each}
  </div>

  {#if klingelt}
    <div class="klingeln" role="alertdialog" aria-label={t('telefon.klingelt')}>
      <span class="wecker-an gross"><i class="fa-solid fa-bell fa-shake"></i>{klingelt.zeit}</span>
      <button class="riesig" onclick={schlummern} aria-label={t('telefon.schlummern')} title={t('telefon.schlummern')}><i class="fa-solid fa-bed"></i></button>
      <button class="riesig aus" onclick={aus} aria-label={t('telefon.aus')} title={t('telefon.aus')}><i class="fa-solid fa-power-off"></i></button>
    </div>
  {/if}
</div>

<style>
  .wecker {
    --w-grund: var(--t-grund);
    --w-text: var(--t-text);
    --w-text-2: var(--t-text-2);
    --w-linie: var(--t-linie);
    --w-akzent: var(--t-akzent);
    --w-akzent-text: var(--t-akzent-text);
    --w-fein: var(--t-flaeche-2);
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
    padding: 12px max(env(safe-area-inset-right, 0px), 20px) 10px max(env(safe-area-inset-left, 0px), 20px);
    background: var(--w-grund);
    color: var(--w-text);
    overflow: hidden;
    touch-action: none;   /* Wischen gehört der Ansicht, nicht dem Browser */
    -webkit-user-select: none;
    user-select: none;
  }
  .wecker.nacht {
    --w-grund: #000000;
    --w-text: #c62020;
    --w-text-2: #c01c1c;
    --w-linie: #4a0b0b;
    --w-akzent: #c62020;
    --w-akzent-text: #000000;
    --w-fein: #1c0405;
  }

  /* D: große Uhr mit Sonnenband, rechts eine schmale Spalte */
  .layout-sonne { flex: 1; min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr) 220px; gap: 0 24px; }
  .layout-sonne .links { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .uhr-box { flex: 1; min-height: 0; min-width: 0; }
  .uhr-box.zucken { animation: zucken 0.3s ease-in-out; }
  @keyframes zucken { 0%, 100% { transform: translateX(0); } 30% { transform: translateX(-6px); } 70% { transform: translateX(6px); } }
  .layout-sonne .rechts { display: flex; flex-direction: column; justify-content: center; gap: 16px; padding-left: 20px;
    border-left: 1px solid var(--w-linie); min-width: 0; }
  .block { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .zustand { color: var(--w-text-2); font-size: 15px; flex: none; }

  /* B: Uhr vollflächig, unten eine schmale Leiste, Knöpfe nach Antippen */
  .layout-uhr { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .leiste { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-top: 8px;
    border-top: 1px solid var(--w-linie); font-size: 17px; color: var(--w-text-2); min-width: 0; }
  .sonnenzeiten { display: flex; align-items: center; gap: 6px; flex: none; font-variant-numeric: tabular-nums; }
  .sonnenzeiten i { margin-left: 6px; }
  .schwebend { position: absolute; top: 12px; right: max(env(safe-area-inset-right, 0px), 20px); }

  .sender { display: flex; align-items: center; gap: 8px; min-width: 0; font-size: 17px; }
  .sender .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; color: var(--w-text); }
  .sender > i:first-child { color: var(--w-text-2); flex: none; }
  .verbindung { flex: none; font-size: 15px; color: var(--w-text-2); }
  .verbindung.warn { color: var(--w-akzent); }

  /* Wecker: scharf in Akzentfarbe und fett, sonst durchgestrichene Glocke gedämpft */
  .wecker-an, .wecker-aus { display: inline-flex; align-items: center; gap: 8px; flex: none; font-variant-numeric: tabular-nums; }
  .wecker-an { color: var(--w-akzent); font-weight: 700; }
  .wecker-aus { color: var(--w-text-2); }
  .wecker-an.gross { font-size: 24px; }
  .wecker-aus.gross { font-size: 22px; }

  .knoepfe { display: flex; gap: 12px; }
  .symbol { width: 56px; height: 56px; flex: none; border: 1px solid var(--w-linie); border-radius: 50%; background: var(--w-grund);
    color: var(--w-text); font-size: 22px; display: flex; align-items: center; justify-content: center; touch-action: none; }
  .symbol.an { background: var(--w-akzent); border-color: var(--w-akzent); color: var(--w-akzent-text); }
  .symbol:disabled { opacity: 0.4; }

  .punkte { position: absolute; top: 6px; left: 50%; transform: translateX(-50%); display: flex; gap: 6px; }
  .punkte span { width: 6px; height: 6px; border-radius: 50%; background: var(--w-linie); }
  .punkte span.an { background: var(--w-text-2); }

  .klingeln { position: absolute; top: 0; right: 0; bottom: 0; width: 42%; display: flex; flex-direction: column; justify-content: center;
    gap: 14px; padding: 16px max(env(safe-area-inset-right, 0px), 20px) 16px 20px; background: var(--w-grund); border-left: 1px solid var(--w-linie); }
  .riesig { min-height: 76px; border: none; border-radius: 18px; background: var(--w-akzent); color: var(--w-akzent-text); font: inherit;
    font-size: 30px; display: flex; align-items: center; justify-content: center; }
  .riesig.aus { background: transparent; color: var(--w-text); border: 2px solid var(--w-text); }
</style>
