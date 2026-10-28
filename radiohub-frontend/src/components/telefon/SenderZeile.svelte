<script>
  /** Eine Zeile mit Sender: antippen spielt, Stern merkt oder entfernt den Favoriten. */
  import { appState, actions } from '../../lib/store.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';
  import Bild from './Bild.svelte';

  let { sender } = $props();
  const laeuft = $derived(appState.currentStation?.uuid === sender.uuid && appState.isPlaying);
  const favorit = $derived(appState.favorites.some((f) => f.uuid === sender.uuid));
  const zusatz = $derived([sender.country, (sender.tags || '').split(',').slice(0, 2).join(', ')].filter(Boolean).join(' · '));
</script>

<li class="zeile" class:laeuft>
  <button class="haupt" onclick={() => actions.playStation(sender)}>
    <Bild src={sender.favicon ? `/api/favicon/${sender.uuid}` : null} symbol="fa-radio" />
    <span class="text">
      <span class="name">{sender.name}</span>
      {#if zusatz}<span class="zusatz">{zusatz}</span>{/if}
    </span>
    {#if laeuft}<i class="fa-solid fa-volume-high spielt" aria-hidden="true"></i>{/if}
  </button>
  <button class="stern" class:an={favorit} onclick={() => actions.toggleFavorite(sender)}
    aria-label={favorit ? t('telefon.favoritAus') : t('telefon.favoritAn')} title={favorit ? t('telefon.favoritAus') : t('telefon.favoritAn')}>
    <i class="fa-solid fa-star"></i>
  </button>
</li>

<style>
  .zeile {
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--t-linie);
  }
  .haupt {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 68px;
    padding: 8px 4px 8px 16px;
    border: none;
    background: transparent;
    color: var(--t-text);
    text-align: left;
    font: inherit;
  }
  .text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .name { font-size: 17px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .zusatz { font-size: 15px; color: var(--t-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .laeuft .name { color: var(--t-akzent); }
  .spielt { color: var(--t-akzent); flex: none; }
  .stern {
    width: 56px;
    height: 56px;
    flex: none;
    border: none;
    background: transparent;
    color: var(--t-text-2);
    font-size: 20px;
  }
  .stern.an { color: #e0a526; }
  :global([data-theme='light']) .stern.an { color: #8a5d00; }
</style>
