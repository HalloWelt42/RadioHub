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

<li class="tf-zeile" class:tf-laeuft={laeuft}>
  <button class="tf-haupt" onclick={() => actions.playStation(sender)}>
    <Bild src={sender.favicon ? `/api/favicon/${sender.uuid}` : null} symbol="fa-radio" />
    <span class="tf-text">
      <span class="tf-name">{sender.name}</span>
      {#if zusatz}<span class="zusatz">{zusatz}</span>{/if}
    </span>
    {#if laeuft}<i class="fa-solid fa-volume-high spielt" aria-hidden="true"></i>{/if}
  </button>
  <button class="stern" class:tf-an={favorit} onclick={() => actions.toggleFavorite(sender)}
    aria-label={favorit ? t('telefon.favoritAus') : t('telefon.favoritAn')} title={favorit ? t('telefon.favoritAus') : t('telefon.favoritAn')}>
    <i class="fa-solid fa-star"></i>
  </button>
</li>

<style>
  .tf-zeile {
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--rand);
  }
  .tf-haupt {
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
  .tf-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .tf-name { font-size: 17px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .zusatz { font-size: 15px; color: var(--t-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tf-laeuft .tf-name { color: var(--t-akzent); }
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
  .stern.tf-an { color: #e0a526; }
  :global([data-theme='hell']) .stern.tf-an { color: #8a5d00; }
</style>
