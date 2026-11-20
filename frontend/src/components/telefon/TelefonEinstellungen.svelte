<script>
  /**
   * Sparsame Einstellungen am Telefon: wach halten, Darstellung, Ort für Sonnenzeiten, Stand der Ablage. Das Angebot
   * sagt, was es gibt (Webversion, RAD-4: ohne Wecker und Backend, also ohne Zeitansage, Ort, Konto und Ablage, dafür
   * Eigene Daten als Datei).
   */
  import { t } from '../../lib/i18n.svelte.js';
  import { api } from '../../lib/api.js';
  import { wach, wachHaltenSetzen } from '../../lib/telefon/wachHalten.svelte.js';
  import { weckerdaten, weckerLaden, ortSpeichern } from '../../lib/telefon/weckerdaten.svelte.js';
  import { zeit, zeitansageSchalten, planSetzen, nachtsSetzen, stand as zeitStand } from '../../lib/telefon/zeitansage.svelte.js';
  import { ABSTAENDE_MIN, SCHLUMMER_ABSTAND_MIN, zeitraumZeiten } from '../../lib/telefon/zeitplan.js';
  import Darstellung from '../../schale/Darstellung.svelte';
  import Konto from '../../schale/Konto.svelte';
  import DateiReiter from '../radio/einstellungen/DateiReiter.svelte';
  import { senderquelle } from '../../lib/radio';
  import { PRO_QUELLCODE } from '../../lib/ausgabe';

  const ZEITEN = zeitraumZeiten();

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
    await api.fetch('/api/zeitansage/erzeugen', { method: 'POST' });
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
      fundorte = (await api.searchOrte(suche.trim())).orte;
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

  <section>
    <label class="tf-schalter">
      <span>{t('telefon.wachHalten')}</span>
      <input name="wach-halten" type="checkbox" checked={wach.gewuenscht} disabled={!wach.unterstuetzt}
        onchange={(e) => wachHaltenSetzen(e.currentTarget.checked)} />
    </label>
    <p class="tf-klein">{wach.unterstuetzt ? t(angebot.wecker ? 'telefon.wachHaltenHinweis' : 'telefon.wachHaltenHinweisOhneWecker') : t('telefon.wachNichtMoeglich')}</p>
  </section>

  {#if angebot.wecker}
  <section>
    <label class="tf-schalter">
      <span>{t('telefon.zeitansage')}</span>
      <input name="zeitansage" type="checkbox" checked={zeit.an} onchange={(e) => zeitansageSchalten(e.currentTarget.checked)} />
    </label>
    <p class="tf-klein">{t('telefon.zeitansageHinweis')}</p>
    {#if zeit.an}
      <h3 class="abstand">{t('telefon.ansageAbstand')}</h3>
      <div class="tf-wahl fuenf">
        {#each ABSTAENDE_MIN as n (n)}
          <button class:tf-an={zeit.abstand === n} aria-pressed={zeit.abstand === n} aria-label={t('telefon.minuten', { n })}
            title={t('telefon.minuten', { n })} onclick={() => planSetzen({ abstand: n })}>{n}</button>
        {/each}
      </div>
      <h3 class="abstand">{t('telefon.ansageZeitraum')}</h3>
      <div class="zwei">
        {#each [['von', 'ansageVon'], ['bis', 'ansageBis']] as [feld, text] (feld)}
          <label class="tf-feld"><span>{t('telefon.' + text)}</span>
            <select name="zeitraum-{feld}" value={zeit[feld]} onchange={(e) => planSetzen({ [feld]: e.currentTarget.value })}>
              <option value="">-</option>
              {#each ZEITEN as z (z)}<option value={z}>{z}</option>{/each}
            </select>
          </label>
        {/each}
      </div>
      <p class="tf-klein">{t('telefon.ansageZeitraumHinweis')}</p>
      <h3 class="abstand">{t('telefon.ansageWann')}</h3>
      <div class="tf-wahl">
        {#each [['wecker', 'ansageNurWecker'], ['immer', 'ansageImmer']] as [wert, text] (wert)}
          <button class:tf-an={zeit.bedingung === wert} aria-pressed={zeit.bedingung === wert} onclick={() => planSetzen({ bedingung: wert })}>{t('telefon.' + text)}</button>
        {/each}
      </div>
      <p class="tf-klein">{t('telefon.ansageWecken', { n: SCHLUMMER_ABSTAND_MIN })}</p>
      <h3 class="abstand">{t('telefon.zeitansageNachts')}</h3>
      <div class="tf-wahl drei">
        {#each [['normal', 'nachtsNormal'], ['leise', 'nachtsLeise'], ['aus', 'nachtsAus']] as [wert, text]}
          <button class:tf-an={zeit.nachts === wert} aria-pressed={zeit.nachts === wert} onclick={() => nachtsSetzen(wert)}>{t('telefon.' + text)}</button>
        {/each}
      </div>
    {/if}
    {#if bausteine && bausteine.fehlend.length}
      <p class="tf-klein">{t('telefon.bausteineFehlen', { n: bausteine.fehlend.length })}
        {#if bausteine.erzeugung?.meldung}<br />{bausteine.erzeugung.meldung}{/if}</p>
      <button class="tf-knopf" disabled={bausteine.erzeugung?.laeuft} onclick={bausteineErzeugen}>{t('telefon.bausteineErzeugen')}</button>
    {/if}
  </section>

  {/if}

  <!-- Darstellung und Konto aus der Schale, wie am Rechner in der Tafel des Kopfs -->
  <section class="darstellung"><Darstellung />{#if angebot.backend}<Konto />{/if}</section>
  {#if senderquelle.faehig.datei}<DateiReiter />{/if}
  {#if !angebot.backend}
    <!-- Basic: Verweis auf die volle Version (Nutzer 20.11.2026) -->
    <section class="tf-pro">
      <a class="rh-pro" href={PRO_QUELLCODE} target="_blank" rel="noopener" aria-label={t('schale.proVerweis')}>PRO</a>
      <p class="tf-klein">{t('schale.proVerweis')}</p>
    </section>
  {/if}

  {#if angebot.wecker}
  <section>
    <h3>{t('telefon.ort')}</h3>
    {#if weckerdaten.ort.breite == null}<p class="tf-klein">{t('telefon.ortFehlt')}</p>{/if}
    <form class="tf-suche" onsubmit={(e) => { e.preventDefault(); orteSuchen(); }}>
      <label class="tf-feld"><span>{t('telefon.ortSuchen')}</span><input name="ort-suche" bind:value={suche} autocomplete="off" enterkeyhint="search" /></label>
      <button class="tf-knopf" type="submit" disabled={sucht}>{t('telefon.suchen')}</button>
    </form>
    {#if fundorte}
      {#if fundorte.length === 0}<p class="tf-klein">{t('telefon.keineOrte')}</p>{/if}
      <ul class="fundorte">
        {#each fundorte as f (`${f.breite},${f.laenge}`)}
          <li><button type="button" onclick={() => ortWaehlen(f)}>{f.name} <span class="tf-klein">{f.breite.toFixed(2)}, {f.laenge.toFixed(2)}</span></button></li>
        {/each}
      </ul>
    {/if}
    <button class="tf-knopf" type="button" onclick={standortUebernehmen}><i class="fa-solid fa-location-crosshairs"></i> {t('telefon.standort')}</button>
    <label class="tf-feld"><span>{t('telefon.ortName')}</span><input name="ort-name" bind:value={ort.name} autocomplete="off" /></label>
    <div class="zwei">
      <label class="tf-feld"><span>{t('telefon.breite')}</span><input name="ort-breite" bind:value={ort.breite} inputmode="decimal" autocomplete="off" /></label>
      <label class="tf-feld"><span>{t('telefon.laenge')}</span><input name="ort-laenge" bind:value={ort.laenge} inputmode="decimal" autocomplete="off" /></label>
    </div>
    <button class="tf-knopf" onclick={ortSichern}>{t('telefon.speichern')}</button>
    {#if ortMeldung}<p class="tf-klein">{ortMeldung}</p>{/if}
  </section>
  {/if}

  {#if ablage}
    <section>
      <h3>{t('telefon.ablage')}</h3>
      <p class="tf-klein"><i class="fa-solid fa-circle tf-punkt" class:tf-gut={ablage.verbunden}></i>
        {ablage.verbunden ? t('telefon.ablageVerbunden') : t('telefon.ablageGetrennt')}{ablage.meldung ? `: ${ablage.meldung}` : ''}</p>
    </section>
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
  .tf-schalter { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; font-size: 17px; }
  .tf-schalter input { width: 28px; height: 28px; accent-color: var(--t-akzent); flex: none; }
  .tf-klein { margin: 6px 0 0; font-size: 15px; color: var(--t-text-2); overflow-wrap: anywhere; }
  .tf-wahl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .tf-wahl.drei { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .tf-wahl.fuenf { grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .abstand { margin-top: 12px; }
  .tf-wahl button, .tf-knopf {
    min-height: 48px;
    border: 1px solid var(--t-linie);
    border-radius: 12px;
    background: var(--t-flaeche);
    color: var(--t-text);
    font: inherit;
    font-size: 17px;
  }
  .tf-wahl button.tf-an { background: var(--t-akzent-flaeche); border-color: var(--t-akzent-flaeche); color: var(--t-akzent-text); font-weight: 600; }
  .tf-knopf { width: 100%; margin-top: 10px; }
  .tf-feld { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; font-size: 15px; color: var(--t-text-2); min-width: 0; }
  .tf-feld input, .tf-feld select {
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
  .fundorte { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .fundorte button { width: 100%; min-height: 44px; text-align: left; padding: 8px 12px; border: 1px solid var(--t-linie); border-radius: 10px; background: transparent; color: var(--t-text); font: inherit; font-size: 17px; }
</style>
