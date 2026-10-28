<script>
  /** Sparsame Einstellungen am Telefon: wach halten, Darstellung, Ort für Sonnenzeiten, Stand der Ablage. */
  import { appState, actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { api } from '../../lib/api.js';
  import { wach, wachHaltenSetzen } from '../../lib/telefon/wachHalten.svelte.js';
  import { weckerdaten, weckerLaden, ortSpeichern } from '../../lib/telefon/weckerdaten.svelte.js';

  let { onschliessen } = $props();
  let ort = $state({ name: '', breite: '', laenge: '' });
  let ortMeldung = $state('');
  let ablage = $state(null);

  $effect(() => {
    weckerLaden().then(() => {
      const o = weckerdaten.ort;
      ort = { name: o.name || '', breite: o.breite ?? '', laenge: o.laenge ?? '' };
    });
    api.getAblage().then((a) => (ablage = a)).catch(() => (ablage = { verbunden: false, meldung: t('telefon.fehler') }));
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
    <label class="schalter">
      <span>{t('telefon.wachHalten')}</span>
      <input type="checkbox" checked={wach.gewuenscht} disabled={!wach.unterstuetzt}
        onchange={(e) => wachHaltenSetzen(e.currentTarget.checked)} />
    </label>
    <p class="klein">{wach.unterstuetzt ? t('telefon.wachHaltenHinweis') : t('telefon.wachNichtMoeglich')}</p>
  </section>

  <section>
    <h3>{t('telefon.thema')}</h3>
    <div class="wahl">
      <button class:an={appState.theme === 'light'} onclick={() => actions.setTheme('light')}>{t('telefon.hell')}</button>
      <button class:an={appState.theme === 'dark'} onclick={() => actions.setTheme('dark')}>{t('telefon.dunkel')}</button>
    </div>
  </section>

  <section>
    <h3>{t('telefon.ort')}</h3>
    {#if weckerdaten.ort.breite == null}<p class="klein">{t('telefon.ortFehlt')}</p>{/if}
    <form class="suche" onsubmit={(e) => { e.preventDefault(); orteSuchen(); }}>
      <label class="feld"><span>{t('telefon.ortSuchen')}</span><input bind:value={suche} autocomplete="off" enterkeyhint="search" /></label>
      <button class="knopf" type="submit" disabled={sucht}>{t('telefon.suchen')}</button>
    </form>
    {#if fundorte}
      {#if fundorte.length === 0}<p class="klein">{t('telefon.keineOrte')}</p>{/if}
      <ul class="fundorte">
        {#each fundorte as f (`${f.breite},${f.laenge}`)}
          <li><button type="button" onclick={() => ortWaehlen(f)}>{f.name} <span class="klein">{f.breite.toFixed(2)}, {f.laenge.toFixed(2)}</span></button></li>
        {/each}
      </ul>
    {/if}
    <button class="knopf" type="button" onclick={standortUebernehmen}><i class="fa-solid fa-location-crosshairs"></i> {t('telefon.standort')}</button>
    <label class="feld"><span>{t('telefon.ortName')}</span><input bind:value={ort.name} autocomplete="off" /></label>
    <div class="zwei">
      <label class="feld"><span>{t('telefon.breite')}</span><input bind:value={ort.breite} inputmode="decimal" autocomplete="off" /></label>
      <label class="feld"><span>{t('telefon.laenge')}</span><input bind:value={ort.laenge} inputmode="decimal" autocomplete="off" /></label>
    </div>
    <button class="knopf" onclick={ortSichern}>{t('telefon.speichern')}</button>
    {#if ortMeldung}<p class="klein">{ortMeldung}</p>{/if}
  </section>

  {#if ablage}
    <section>
      <h3>{t('telefon.ablage')}</h3>
      <p class="klein"><i class="fa-solid fa-circle punkt" class:gut={ablage.verbunden}></i>
        {ablage.verbunden ? t('telefon.ablageVerbunden') : t('telefon.ablageGetrennt')}{ablage.meldung ? `: ${ablage.meldung}` : ''}</p>
    </section>
  {/if}
</div>

<style>
  .blatt {
    position: fixed;
    inset: 0;
    z-index: 30;
    padding: max(env(safe-area-inset-top, 0px), 1cm) 16px 24px;
    background: var(--t-grund);
    color: var(--t-text);
    overflow-y: auto;
    overflow-x: hidden;
  }
  header { display: flex; align-items: center; margin-bottom: 8px; }
  h2 { flex: 1; margin: 0; font-size: 24px; font-weight: 700; }
  h3 { margin: 0 0 8px; font-size: 17px; font-weight: 600; }
  .zu { width: 48px; height: 48px; border: none; border-radius: 12px; background: transparent; color: var(--t-text); font-size: 22px; }
  section { padding: 14px 0; border-bottom: 1px solid var(--t-linie); }
  .schalter { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; font-size: 17px; }
  .schalter input { width: 28px; height: 28px; accent-color: var(--t-akzent); flex: none; }
  .klein { margin: 6px 0 0; font-size: 15px; color: var(--t-text-2); overflow-wrap: anywhere; }
  .wahl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .wahl button, .knopf {
    min-height: 48px;
    border: 1px solid var(--t-linie);
    border-radius: 12px;
    background: var(--t-flaeche);
    color: var(--t-text);
    font: inherit;
    font-size: 17px;
  }
  .wahl button.an { background: var(--t-akzent); border-color: var(--t-akzent); color: var(--t-akzent-text); font-weight: 600; }
  .knopf { width: 100%; margin-top: 10px; }
  .feld { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; font-size: 15px; color: var(--t-text-2); min-width: 0; }
  .feld input {
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
  .punkt { font-size: 10px; color: var(--t-fehler); margin-right: 4px; }
  .punkt.gut { color: #3fb950; }
  :global([data-theme='light']) .punkt.gut { color: #1a7f37; }
  .suche { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; align-items: end; }
  .fundorte { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .fundorte button { width: 100%; min-height: 44px; text-align: left; padding: 8px 12px; border: 1px solid var(--t-linie); border-radius: 10px; background: transparent; color: var(--t-text); font: inherit; font-size: 17px; }
</style>
