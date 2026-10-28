<script>
  /** Radio am Telefon: Suche oben, ohne Suche die Favoriten, mit Suche die Treffer; große Zeilen. */
  import { appState } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { api } from '../../lib/api.js';
  import SenderZeile from './SenderZeile.svelte';

  let suche = $state('');
  let treffer = $state([]);
  let laedt = $state(false);
  let fehler = $state(false);
  let zeitgeber;
  let lauf = 0;

  function suchen() {
    clearTimeout(zeitgeber);
    const q = suche.trim();
    if (q.length < 2) { treffer = []; laedt = false; return; }
    laedt = true;
    zeitgeber = setTimeout(async () => {
      const meiner = ++lauf;
      try {
        const r = await api.searchStations({ q, limit: 60, sort_by: 'votes', sort_order: 'desc' });
        if (meiner === lauf) { treffer = r.stations || []; fehler = false; }
      } catch {
        if (meiner === lauf) { treffer = []; fehler = true; }
      } finally {
        if (meiner === lauf) laedt = false;
      }
    }, 300);
  }
</script>

<div class="radio">
  <label class="suche">
    <i class="fa-solid fa-magnifying-glass"></i>
    <input type="search" placeholder={t('telefon.senderSuchen')} bind:value={suche} oninput={suchen}
      enterkeyhint="search" autocomplete="off" />
  </label>

  {#if suche.trim().length >= 2}
    {#if laedt && !treffer.length}
      <p class="hinweis">{t('telefon.laden')}</p>
    {:else if fehler}
      <p class="hinweis">{t('telefon.fehler')}</p>
    {:else if !treffer.length}
      <p class="hinweis">{t('telefon.keineTreffer')}</p>
    {:else}
      <ul class="liste">
        {#each treffer as sender (sender.uuid)}
          <SenderZeile {sender} />
        {/each}
      </ul>
    {/if}
  {:else}
    <h2>{t('telefon.favoriten')}</h2>
    {#if !appState.favorites.length}
      <p class="hinweis">{t('telefon.keineFavoriten')}</p>
    {:else}
      <ul class="liste">
        {#each appState.favorites as sender (sender.uuid)}
          <SenderZeile {sender} />
        {/each}
      </ul>
    {/if}
  {/if}
</div>

<style>
  .radio { padding: 12px 0 16px; }
  .suche {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 12px 12px;
    padding: 0 14px;
    min-height: 48px;
    border-radius: 12px;
    background: var(--t-flaeche-2);
    color: var(--t-text-2);
  }
  .suche input {
    flex: 1;
    min-width: 0;
    border: none;
    background: transparent;
    color: var(--t-text);
    font: inherit;
    font-size: 17px;
    outline: none;
  }
  h2 {
    margin: 4px 16px 6px;
    font-size: 15px;
    font-weight: 600;
    color: var(--t-text-2);
    text-transform: none;
    letter-spacing: 0;
  }
  .hinweis { margin: 16px; color: var(--t-text-2); font-size: 15px; }
  .liste { list-style: none; margin: 0; padding: 0; }
</style>
