<script>
  /**
   * Weckeransicht (Telefon quer, Nachttisch) in den Gestaltungen des Katalogs (mockups/weckansicht/katalog.html, RAD-15),
   * geblättert per Seitenwischen (weckansicht/gestaltungen.ts). Diese Datei rechnet den Zustand (Weckbild) und hält die
   * Aktionen; die Gestaltungen zeichnen nur, je in Hell, Dunkel und Nacht (nachts nach Sonnenzeiten oder von Hand Rot auf
   * Schwarz). Beim Klingeln ordnet sich jede Gestaltung neu an, nichts verdeckt etwas, und Radio oder Weckton lassen
   * sich jederzeit wechseln. Hält den Bildschirm wach, löst die Wecker aus,
   * sagt die Zeit an (nach dem Zeitplan der Einstellungen) und verbindet neu, wenn der Sender ausfällt; nur solange
   * sie offen ist. Solange die Tonausgabe entsperrt ist, wartet eine neue Fassung, denn nach dem Neuladen wäre sie
   * bis zum nächsten Tippen wieder gesperrt.
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
  import { ansageFaellig } from '../../lib/telefon/zeitplan.js';
  import { ton, loslassen } from '../../lib/telefon/tonkontext.svelte.js';
  import { sperren, freigeben } from '../../lib/aktualisierung.svelte.js';
  import '@fontsource/chakra-petch/500.css';
  import '@fontsource/chakra-petch/700.css';
  import '../../stil/weckansicht.css';
  import Buehne from './weckansicht/Buehne.svelte';
  import { GESTALTUNGEN, gestaltungVon, naechste } from './weckansicht/gestaltungen';

  let { steuerung, audio = null } = $props();

  // --- Einstellungen im Gerät ---------------------------------------------------------------------------------------
  const NACHT_SCHLUESSEL = 'radiohub_nachtschaltung';
  const LAYOUT_SCHLUESSEL = 'radiohub_weckerlayout';
  const lesen = (s, v) => { try { return localStorage.getItem(s) || v; } catch { return v; } };
  const schreiben = (s, w) => { try { localStorage.setItem(s, w); } catch { /* privates Fenster */ } };

  let nachtWahl = $state(lesen(NACHT_SCHLUESSEL, 'auto'));
  // gemerkt wird die Kennung; das Objekt kommt immer aus der Liste (ein $state-Proxy wäre nicht dasselbe Objekt)
  let gestaltungId = $state(gestaltungVon(lesen(LAYOUT_SCHLUESSEL, '')).id);
  const gestaltung = $derived(gestaltungVon(gestaltungId));

  // ein Knopf, drei Stufen: automatisch nach Sonnenzeiten, immer Rot, immer normal
  const NACHT_FOLGE = { auto: 'an', an: 'aus', aus: 'auto' };
  function nachtSetzen(wert) { nachtWahl = wert; schreiben(NACHT_SCHLUESSEL, wert); }

  function layoutWechseln(schritt) {
    gestaltungId = naechste(gestaltung, schritt).id;
    schreiben(LAYOUT_SCHLUESSEL, gestaltungId);
  }

  // Hell oder Dunkel wie die App (der Appkern setzt data-theme an der Wurzel); nachts gilt die Nachtschaltung
  let appDunkel = $state(document.documentElement.dataset.theme === 'dunkel');
  const themaBeobachter = new MutationObserver(() => { appDunkel = document.documentElement.dataset.theme === 'dunkel'; });
  themaBeobachter.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  // --- Zeit und abgeleitete Werte -----------------------------------------------------------------------------------
  let jetzt = $state(new Date());
  const ort = $derived(weckerdaten.ort);
  const sonne = $derived(ort.breite != null && ort.laenge != null ? sonnenzeiten(jetzt, ort.breite, ort.laenge) : null);
  const nacht = $derived(nachtWahl === 'an' || (nachtWahl === 'auto' && istNacht(jetzt, ort.breite, ort.laenge) === true));
  const naechster = $derived(naechsterWecker(weckerdaten.liste, jetzt));
  const spielt = $derived(appState.isPlaying && !appState.isPaused);
  // eingestellter Sender: was gerade gewählt ist, sonst der zuletzt gehörte (im Gerät gemerkt), sonst der des nächsten
  // Weckers; so steht auch nach dem Öffnen oder einer neuen Fassung immer ein Sender da
  const LETZTER_SENDER = 'radiohub.weckeransicht.sender';
  let letzterSender = $state(lesenJson(LETZTER_SENDER));
  function lesenJson(schluessel) {
    try { return JSON.parse(localStorage.getItem(schluessel) || 'null'); } catch { return null; }
  }
  $effect(() => {
    const s = appState.currentStation;
    if (!s?.uuid) return;
    letzterSender = s;
    try { localStorage.setItem(LETZTER_SENDER, JSON.stringify(s)); } catch { /* ohne Speicher eben nur bis zum Neuladen */ }
  });
  const eingestellt = $derived(appState.currentStation || letzterSender
    || (naechster?.wecker?.quelle === 'sender' ? naechster.wecker.sender : null));
  const senderName = $derived(appState.currentStation?.name || appState.currentEpisode?.title || eingestellt?.name || '');
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

  // beim Klingeln: womit geweckt wird; "weckton" ist die Wahl der Person, der Wächter springt mit dem Weckton auch selbst ein
  let quelleWahl = $state('radio');

  async function ausloesen(w) {
    abbrechen();
    klingelt = w;
    quelleWahl = 'radio';
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
    quelleWahl = 'radio';
    wunsch.spielen = false;
    waechter.lassen();
    wecktonAus();
    actions.stop();
  }

  /** Beim Klingeln zwischen Radio (oder Podcast) und Weckton wechseln, jederzeit und in beide Richtungen */
  function weckquelle(q) {
    if (!klingelt || q === bildQuelle) return;
    if (q === 'weckton') {
      quelleWahl = 'weckton';
      waechter.lassen();
      actions.stop();
      wecktonAn();
    } else {
      quelleWahl = 'radio';
      wecktonAus();
      const w = klingelt;
      if (w.quelle === 'sender' && w.sender) {
        waechter.bewachen(w.sender, { wecker: true });
        actions.playStation(w.sender);
      } else {
        ausloesen(w);
      }
    }
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
    if (!spielt && !appState.currentStation && !appState.currentEpisode && eingestellt) {
      actions.playStation(eingestellt);
      return;
    }
    steuerung.umschalten();
  }

  // --- Zeitansage -----------------------------------------------------------------------------------------------------
  // von selbst nach dem Zeitplan (Einstellungen am Telefon); ein Tipp auf die Ziffern sagt immer an
  let angesagt = '';
  function zeitPruefen() {
    const schluessel = `${jetzt.getHours()}:${jetzt.getMinutes()}`;
    if (angesagt === schluessel || document.visibilityState !== 'visible') return;
    if (!ansageFaellig(zeit, jetzt, { weckerScharf: !!naechster, schlummert: !!schlummerBis, klingelt: !!klingelt })) return;
    angesagt = schluessel;
    ansagen({ nacht, jetzt });
  }

  // Ansage-Knopf: ist die Tonausgabe gesperrt (etwa nach dem Neuladen), gibt der erste Tipp nur den Ton frei
  let tonWarGesperrt = false;
  function ansageKnopf() {
    if (zeit.an && tonWarGesperrt) { entsperren(); return; }
    zeitansageSchalten(!zeit.an);
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
  const knoepfeSichtbar = $derived(!gestaltung.tastenNachTippen || jetzt.getTime() < knoepfeBis);
  const KNOEPFE_MS = 6000;

  function zeigeKnoepfe() { knoepfeBis = Date.now() + KNOEPFE_MS; jetzt = new Date(); }

  function down(e) {
    tonWarGesperrt = !ton.laeuft;
    entsperren();   // mit der Maus zählt schon das Drücken als Geste
    start = { x: e.clientX, y: e.clientY, t: Date.now() };
    if (gestaltung.tastenNachTippen && knoepfeSichtbar) zeigeKnoepfe();   // jede Berührung hält die Knöpfe offen
  }
  function up(e) {
    entsperren();   // mit dem Finger erst das Loslassen
    if (!start) return;
    const art = geste(start, { x: e.clientX, y: e.clientY, t: Date.now() });
    start = null;
    if (art === 'links' || art === 'rechts') {
      klickSperre = true;   // ein Wischen über einem Knopf löst ihn nicht aus
      setTimeout(() => { klickSperre = false; }, 0);
      layoutWechseln(art === 'links' ? 1 : -1);
    } else if (art === 'tippen' && !e.target.closest('button') && gestaltung.tastenNachTippen && !knoepfeSichtbar) {
      zeigeKnoepfe();   // erst die Tasten zeigen, das nächste Tippen auf die Uhr sagt an
    } else if (art === 'tippen' && !e.target.closest('button') && e.target.closest('.uhr-box')) {
      zifferTipp();
    }
  }
  function klickFangen(e) {
    if (klickSperre) { e.stopPropagation(); e.preventDefault(); }
  }

  // --- Lebenslauf -----------------------------------------------------------------------------------------------------
  weckeransichtOffen(true);
  weckerLaden();
  entsperren();   // ohne Geste bleibt der Ton gesperrt, bis getippt wird; die Ansicht zeigt das am Ansage-Knopf
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

  $effect(() => {
    if (ton.laeuft) sperren('tonausgabe');
    else freigeben('tonausgabe');
  });

  onDestroy(() => {
    clearInterval(takt);
    clearInterval(anstieg);
    document.removeEventListener('visibilitychange', sichtbarkeit);
    abbrechen();
    loslassen();
    waechter.lassen();
    freigeben('schlummern');
    freigeben('tonausgabe');
    weckeransichtOffen(false);
    themaBeobachter.disconnect();
  });

  // --- Weckbild: was jede Gestaltung zeigt (weckansicht/typen.ts) ---------------------------------------------------
  const bildQuelle = $derived(quelleWahl === 'weckton' || waechter.ersatzton ? 'weckton' : 'radio');
  /** kurzer Name für grobe Anzeigen: ein kurzer Teil des Namens ("DLF" aus "Deutschlandfunk | DLF | AAC 192k"), sonst das erste Wort */
  function kurzName(name) {
    const teile = (name || '').split(/\s*[|/·-]\s*/).map((s) => s.trim()).filter(Boolean);
    const kurz = teile.find((s) => s.length <= 6 && !/\d/.test(s)) ?? (teile[0] || '').split(/\s+/)[0] ?? '';
    return kurz.slice(0, 12).toUpperCase();
  }
  const datumKurz = (d) => `${tagKurz(d).replace('.', '').toUpperCase()} ${zwei(d.getDate())}.${zwei(d.getMonth() + 1)}.`;
  const bild = $derived({
    zeit: hhmm(jetzt),
    jetzt,
    datum: datumKurz(jetzt),
    modus: nacht ? 'nacht' : gestaltung.immerDunkel || appDunkel ? 'dunkel' : 'hell',
    lage: klingelt ? 'klingelt' : schlummerBis ? 'schlummert' : 'ruhe',
    quelle: bildQuelle,
    quelleName: !klingelt || klingelt.quelle === 'sender' ? t('telefon.radio') : t('telefon.podcast'),
    sender: senderName,
    senderKurz: kurzName(senderName),
    naechster: naechster ? `${tagKurz(naechster.zeitpunkt)} ${hhmm(naechster.zeitpunkt)}` : null,
    klingelZeit: klingelt?.zeit ?? null,
    schlummerMinuten: klingelt?.schlummern_min || 9,
    schlummerBis: schlummerBis ? hhmm(schlummerBis) : null,
    sonne: sonne && !sonne.polar ? { auf: hhmm(sonne.aufgang), unter: hhmm(sonne.untergang) } : null,
    spielt,
    stoppStattPause: appState.playerMode === 'direct',
    verbindung: waechter.zustand,
    ansage: { an: zeit.an, gesperrt: zeit.an && !ton.laeuft, laeuft: zeit.laeuft },
    nachtWahl,
    tastenSichtbar: knoepfeSichtbar,
    zucken,
  });
  const tun = {
    umschalten,
    ansage: ansageKnopf,
    nacht: () => nachtSetzen(NACHT_FOLGE[nachtWahl]),
    schlummern,
    aus,
    quelle: weckquelle,
  };
  const tt = (schluessel, werte) => t(`telefon.${schluessel}`, werte);
  const Gestaltung = $derived(gestaltung.komponente);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="wa {gestaltung.klasse} {bild.modus}" data-gestaltung={gestaltung.id} onpointerdown={down} onpointerup={up}
  onpointercancel={() => (start = null)} onclickcapture={klickFangen}>
  <Buehne><Gestaltung {bild} {tun} t={tt} /></Buehne>
  <div class="wa-punkte" aria-hidden="true">
    {#each GESTALTUNGEN as g (g.id)}<span class:an={g === gestaltung}></span>{/each}
  </div>
  {#if klingelt}<span class="wa-unsichtbar" role="alert">{t('telefon.klingelt')} {klingelt.zeit}</span>{/if}
</div>
