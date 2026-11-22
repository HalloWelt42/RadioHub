<script>
  /**
   * Sparsame Einstellungen am Telefon: wach halten, Zeitansage, Darstellung, Ort für Sonnenzeiten, Stand der Ablage;
   * je Bereich eine Karte, Schalter und Wahlen als Tasten mit Leuchte (RAD-103).
   * Das Angebot sagt, was es gibt (Basic: ohne Backend, also ohne Konto und Ablage, dafür Eigene Daten als Datei);
   * Ortssuche und das Erzeugen der Bausteine zeigen sich nur, wo das Bauziel sie kann ($ziel/telefon).
   */
  import { t } from '../../lib/i18n.svelte.js';
  import { api } from '../../lib/api.js';
  import { wach, wachHaltenSetzen } from '../../lib/telefon/wachHalten.svelte.js';
  import { weckerdaten, weckerLaden, ortSpeichern } from '../../lib/telefon/weckerdaten.svelte.js';
  import { zeit, zeitansageSchalten, planSetzen, nachtsSetzen, stand as zeitStand } from '../../lib/telefon/zeitansage.svelte.js';
  import { ABSTAENDE_MIN, SCHLUMMER_ABSTAND_MIN, zeitraumZeiten } from '../../lib/telefon/zeitplan.js';
  import { Auswahl } from 'appkern-oberflaeche';
  import Darstellung from '../../schale/Darstellung.svelte';
  import Schalter from '../bausteine/Schalter.svelte';
  import Konto from '../../schale/Konto.svelte';
  import DateiReiter from '../radio/einstellungen/DateiReiter.svelte';
  import { senderquelle } from '../../lib/radio';
  import { weckerablage, zeitbausteine } from '$ziel/telefon';
  import { PRO_QUELLCODE } from '../../lib/ausgabe';

  const ZEITEN = zeitraumZeiten();
  /** von und bis als Aufklappliste; leer heißt offen (rund um die Uhr) */
  const zeitOptionen = [{ wert: '', titel: t('telefon.ansageOffen') }, ...ZEITEN.map((z) => ({ wert: z, titel: z }))];
  const WANN = [['wecker', 'ansageNurWecker', 'fa-bell'], ['immer', 'ansageImmer', 'fa-infinity']];
  const NACHTS = [['normal', 'nachtsNormal', 'fa-volume-high'], ['leise', 'nachtsLeise', 'fa-volume-low'], ['aus', 'nachtsAus', 'fa-volume-xmark']];


  let { onschliessen, angebot = { wecker: true, backend: true } } = $props();
  let ort = $state({ name: '', breite: '', laenge: '' });
  let ortMeldung = $state('');
  let ablage = $state(null);
  let bausteine = $state(null);   // Stand der Bausteine der Zeitansage

  function bausteineAbfragen() {
    zeitStand().then((s) => (bausteine = s)).catch(() => (bausteine = null));
  }
  $effect(() => { if (angebot.wecker) bausteineAbfragen(); });

  async function bausteineErzeugen() {
    await zeitbausteine.erzeugen();
    setTimeout(bausteineAbfragen, 1500);
  }

  $effect(() => {
    if (angebot.wecker) weckerLaden().then(() => {
      const o = weckerdaten.ort;
      ort = { name: o.name || '', breite: o.breite ?? '', laenge: o.laenge ?? '' };
    });
    if (angebot.backend) api.getAblage().then((a) => (ablage = a)).catch(() => (ablage = { verbunden: false, meldung: t('telefon.fehler') }));
  });

  const zahl = (w) => (String(w).trim() === '' ? null : Number(String(w).replace(',', '.')));

  let suche = $state('');
  let fundorte = $state(null);
  let sucht = $state(false);

  async function orteSuchen() {
    if (suche.trim().length < 2) return;
    sucht = true;
    try {
      fundorte = await weckerablage.orteSuchen(suche.trim());
    } catch (e) {
      fundorte = [];
      ortMeldung = e.message || t('telefon.fehler');
    } finally {
      sucht = false;
    }
  }

  function ortWaehlen(f) {
    ort = { name: f.name, breite: f.breite.toFixed(5), laenge: f.laenge.toFixed(5) };
    fundorte = null;
    ortSichern();
  }

  function standortUebernehmen() {
    if (!navigator.geolocation) { ortMeldung = t('telefon.standortFehlt'); return; }
    navigator.geolocation.getCurrentPosition(
      (p) => ortWaehlen({ name: t('telefon.standortName'), breite: p.coords.latitude, laenge: p.coords.longitude }),
      () => (ortMeldung = t('telefon.standortFehlt')),
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 3600000 },
    );
  }

  async function ortSichern() {
    try {
      await ortSpeichern({ name: ort.name.trim(), breite: zahl(ort.breite), laenge: zahl(ort.laenge) });
      ortMeldung = t('telefon.gespeichert');
    } catch (e) {
      ortMeldung = e.message || t('telefon.fehler');
    }
  }
</script>

<div class="blatt" role="dialog" aria-modal="true" aria-label={t('telefon.einstellungen')}>
  <header>
    <h2>{t('telefon.einstellungen')}</h2>
    <button class="zu" onclick={onschliessen} aria-label={t('telefon.zurueck')}><i class="fa-solid fa-xmark"></i></button>
  </header>

  <!-- Karten wie "Eigene Daten", Schalter und Wahlen als Tasten mit Leuchte wie in der HiFi-Anlage (RAD-103, Wahl B) -->
  <div class="karte rh-karte tf-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-mobile-screen"></i>{t('telefon.bildschirm')}</h2></div>
    {#if wach.unterstuetzt}
      <div class="tf-tasten"><Schalter an={wach.gewuenscht} symbol="fa-sun" text={t('telefon.wachHalten')} onwechsel={(an) => wachHaltenSetzen(an)} /></div>
    {/if}
    <p class="tf-klein">{wach.unterstuetzt ? t(angebot.wecker ? 'telefon.wachHaltenHinweis' : 'telefon.wachHaltenHinweisOhneWecker') : t('telefon.wachNichtMoeglich')}</p>
  </div>

  {#if angebot.wecker}
  <div class="karte rh-karte tf-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-clock"></i>{t('telefon.zeitansage')}</h2></div>
    <div class="tf-tasten"><Schalter an={zeit.an} symbol="fa-bullhorn" text={t('telefon.zeitansage')} onwechsel={(an) => zeitansageSchalten(an)} /></div>
    <p class="tf-klein">{t('telefon.zeitansageHinweis')}</p>
    {#if zeit.an}
      <div class="rh-wahl">
        <h3>{t('telefon.ansageAbstand')}</h3>
        <div class="tf-tasten">{#each ABSTAENDE_MIN as n (n)}<Schalter an={zeit.abstand === n} text={String(n)} hilfe={t('telefon.minuten', { n })}
          onwechsel={() => planSetzen({ abstand: n })} />{/each}</div>
      </div>
      <div class="rh-wahl">
        <h3>{t('telefon.ansageZeitraum')}</h3>
        <div class="zwei">
          {#each [['von', 'ansageVon'], ['bis', 'ansageBis']] as [feld, text] (feld)}
            <div class="tf-zeitfeld"><span>{t('telefon.' + text)}</span>
              <Auswahl wert={zeit[feld] ?? ''} optionen={zeitOptionen} symbol="fa-clock" titel={t('telefon.' + text)}
                       onwahl={(w) => planSetzen({ [feld]: w })} /></div>
          {/each}
        </div>
        <p class="tf-klein">{t('telefon.ansageZeitraumHinweis')}</p>
      </div>
      <div class="rh-wahl">
        <h3>{t('telefon.ansageWann')}</h3>
        <div class="tf-tasten">{#each WANN as [wert, text, zeichen] (wert)}<Schalter an={zeit.bedingung === wert} symbol={zeichen}
          text={t('telefon.' + text)} onwechsel={() => planSetzen({ bedingung: wert })} />{/each}</div>
        <p class="tf-klein">{t('telefon.ansageWecken', { n: SCHLUMMER_ABSTAND_MIN })}</p>
      </div>
      <div class="rh-wahl">
        <h3>{t('telefon.zeitansageNachts')}</h3>
        <div class="tf-tasten">{#each NACHTS as [wert, text, zeichen] (wert)}<Schalter an={zeit.nachts === wert} symbol={zeichen}
          text={t('telefon.' + text)} onwechsel={() => nachtsSetzen(wert)} />{/each}</div>
      </div>
    {/if}
    {#if bausteine && bausteine.fehlend.length && zeitbausteine.faehig.erzeugen}
      <p class="tf-klein">{t('telefon.bausteineFehlen', { n: bausteine.fehlend.length })}
        {#if bausteine.erzeugung?.meldung}<br />{bausteine.erzeugung.meldung}{/if}</p>
      <div class="rh-knoepfe"><button class="knopf" type="button" disabled={bausteine.erzeugung?.laeuft} onclick={bausteineErzeugen}><i
        class="fa-solid fa-wand-magic-sparkles"></i>{t('telefon.bausteineErzeugen')}</button></div>
    {/if}
  </div>
  {/if}

  <!-- Darstellung und Konto aus der Schale, wie am Rechner in der Tafel des Kopfs -->
  <div class="karte rh-karte tf-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-palette"></i>{t('schale.darstellung')}</h2></div>
    <div class="darstellung"><Darstellung /></div>
  </div>
  {#if angebot.backend}<div class="karte rh-karte tf-karte"><Konto /></div>{/if}
  {#if senderquelle.faehig.datei}<DateiReiter />{/if}
  {#if !angebot.backend}
    <!-- Basic: das silberne BASIC verweist selbst auf die volle Version (Nutzer 20.11.2026) -->
    <section class="tf-pro">
      <a class="rh-basic" href={PRO_QUELLCODE} target="_blank" rel="noopener" aria-label={t('schale.basicVerweis')}>BASIC</a>
      <p class="tf-klein">{t('schale.basicVerweis')}</p>
    </section>
  {/if}

  {#if angebot.wecker}
  <div class="karte rh-karte tf-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-location-dot"></i>{t('telefon.ort')}</h2>
      {#if weckerdaten.ort.breite == null}<span class="rh-still">{t('telefon.ortFehlt')}</span>{/if}</div>
    {#if weckerablage.faehig.ortssuche}
      <form class="tf-suche" onsubmit={(e) => { e.preventDefault(); orteSuchen(); }}>
        <label class="tf-feld"><span>{t('telefon.ortSuchen')}</span><input name="ort-suche" bind:value={suche} autocomplete="off" enterkeyhint="search" /></label>
        <button class="knopf" type="submit" disabled={sucht} aria-label={t('telefon.suchen')} title={t('telefon.suchen')}><i class="fa-solid fa-magnifying-glass"></i></button>
      </form>
      {#if fundorte}
        {#if fundorte.length === 0}<p class="tf-klein">{t('telefon.keineOrte')}</p>{/if}
        <div class="tf-fundorte">
          {#each fundorte as f (`${f.breite},${f.laenge}`)}
            <button class="knopf" type="button" onclick={() => ortWaehlen(f)}><i class="fa-solid fa-location-dot"></i>{f.name}
              <span class="rh-still">{f.breite.toFixed(2)}, {f.laenge.toFixed(2)}</span></button>
          {/each}
        </div>
      {/if}
    {/if}
    <div class="rh-knoepfe"><button class="knopf" type="button" onclick={standortUebernehmen}><i class="fa-solid fa-location-crosshairs"></i>{t('telefon.standort')}</button></div>
    <label class="tf-feld"><span>{t('telefon.ortName')}</span><input name="ort-name" bind:value={ort.name} autocomplete="off" /></label>
    <div class="zwei">
      <label class="tf-feld"><span>{t('telefon.breite')}</span><input name="ort-breite" bind:value={ort.breite} inputmode="decimal" autocomplete="off" /></label>
      <label class="tf-feld"><span>{t('telefon.laenge')}</span><input name="ort-laenge" bind:value={ort.laenge} inputmode="decimal" autocomplete="off" /></label>
    </div>
    <div class="rh-knoepfe tf-speichern"><button class="knopf primaer" type="button" onclick={ortSichern}><i class="fa-solid fa-floppy-disk"></i>{t('telefon.speichern')}</button>
      {#if ortMeldung}<span class="rh-still">{ortMeldung}</span>{/if}</div>
  </div>
  {/if}

  {#if ablage}
    <div class="karte rh-karte tf-karte">
      <div class="rh-karte-kopf"><h2><i class="fa-solid fa-cloud"></i>{t('telefon.ablage')}</h2></div>
      <p class="tf-klein"><i class="fa-solid fa-circle tf-punkt" class:tf-gut={ablage.verbunden}></i>
        {ablage.verbunden ? t('telefon.ablageVerbunden') : t('telefon.ablageGetrennt')}{ablage.meldung ? `: ${ablage.meldung}` : ''}</p>
    </div>
  {/if}
</div>

<style>
  .blatt {
    position: fixed;
    inset: 0;
    z-index: 30;
    padding: var(--rahmen-sicher-oben) var(--rahmen-rand) 24px;
    background: var(--t-grund);
    color: var(--t-text);
    overflow-y: auto;
    overflow-x: hidden;
  }
  header { display: flex; align-items: center; margin-bottom: 8px; }
  h2 { flex: 1; margin: 0; font-size: 24px; font-weight: 700; }
  h3 { margin: 0 0 8px; font-size: 17px; font-weight: 600; }
  .zu { width: 48px; height: 48px; border: none; border-radius: 12px; background: transparent; color: var(--t-text); font-size: 22px; }
  section { padding: 14px 0; border-bottom: 1px solid var(--rand); }
  .tf-pro { display: grid; justify-items: start; gap: 6px; }
  .darstellung { display: grid; gap: 14px; }
  .tf-klein { margin: 6px 0 0; font-size: 15px; color: var(--t-text-2); overflow-wrap: anywhere; }
  .tf-feld { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; font-size: 15px; color: var(--t-text-2); min-width: 0; }
  .tf-feld input {
    min-height: 48px;
    padding: 0 12px;
    border: 1px solid var(--t-linie);
    border-radius: 10px;
    background: var(--t-flaeche);
    color: var(--t-text);
    font: inherit;
    font-size: 17px;
    width: 100%;
  }
  .zwei { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .tf-punkt { font-size: 10px; color: var(--t-fehler); margin-right: 4px; }
  .tf-punkt.tf-gut { color: #3fb950; }
  :global([data-theme='hell']) .tf-punkt.tf-gut { color: #1a7f37; }
  .tf-suche { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; align-items: end; }
  /* Karten wie "Eigene Daten" (RAD-103) */
  .tf-karte { margin: 0 0 12px; }
  .tf-karte .rh-wahl { margin-top: 14px; }
  .tf-karte .tf-klein { font-size: var(--klein); color: var(--text-3); }
  .tf-karte .rh-knoepfe { margin-top: 12px; }
  .tf-zeitfeld { display: grid; gap: 4px; min-width: 0; font-size: var(--klein); color: var(--text-3); }
  .tf-tasten { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: 6px; }
  /* Tasten mit Leuchte (RAD-103, Wahl B): gleich breit über die Zeile, der Knopf füllt seine Spalte, die Schrift bleibt
     in einer Zeile */
  .tf-tasten :global(ak-taster) { inline-size: 100%; min-width: 0; }
  .tf-tasten :global(ak-taster .ak-taster-knopf) { inline-size: 100%; min-inline-size: 0; }
  .tf-tasten :global(ak-taster .ak-taster-beschriftung) { white-space: nowrap; }
  .tf-fundorte { display: grid; gap: 6px; margin-top: 8px; }
  .tf-fundorte .knopf { justify-content: flex-start; block-size: auto; min-block-size: 44px; text-align: left; white-space: normal; }
  .tf-speichern { align-items: center; }
  .tf-suche .knopf { block-size: 48px; inline-size: 48px; justify-content: center; }
</style>
