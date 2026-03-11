<script>
  import { t } from '../../lib/i18n.svelte.js';

  let {
    items = [],
    selectedId = null,
    playingId = null,
    onselect,
    onplay,
    renderItem
  } = $props();
</script>

<div class="hifi-table-wrapper">
  <table class="hifi-table">
    <tbody>
      {#each items as item, i}
        <tr 
          class:playing={item.id === playingId || item.uuid === playingId}
          class:selected={item.id === selectedId || item.uuid === selectedId}
          onclick={() => onplay?.(item)}
        >
          {@render renderItem?.(item, i)}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

{#if items.length === 0}
  <div class="hifi-flex hifi-flex-col" style="align-items:center; padding:40px; color:var(--hifi-text-secondary);">
    <span>{t('hifi.keineEintraege')}</span>
  </div>
{/if}
