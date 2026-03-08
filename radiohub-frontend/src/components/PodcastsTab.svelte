<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import HiFiDisplay from './hifi/HiFiDisplay.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  
  let view = $state('subscriptions');
  let searchQuery = $state('');
  let searchResults = $state([]);
  let subscriptions = $state([]);
  let selectedPodcast = $state(null);
  let episodes = $state([]);
  let isLoading = $state(false);
  
  $effect(() => {
    loadSubscriptions();
  });
  
  async function loadSubscriptions() {
    try {
      const result = await api.getSubscriptions();
      subscriptions = result.subscriptions || [];
    } catch (e) {}
  }
  
  async function search() {
    if (!searchQuery.trim()) return;
    isLoading = true;
    view = 'search';
    try {
      const result = await api.searchPodcasts(searchQuery);
      searchResults = result.results || [];
    } catch (e) {
      actions.showToast('Search failed', 'error');
    }
    isLoading = false;
  }
  
  async function subscribe(podcast) {
    try {
      await api.subscribePodcast(podcast.feed_url);
      actions.showToast('Subscribed', 'success');
      loadSubscriptions();
      view = 'subscriptions';
    } catch (e) {
      actions.showToast('Failed', 'error');
    }
  }
  
  async function unsubscribe(podcast, e) {
    e.stopPropagation();
    try {
      await api.unsubscribePodcast(podcast.id);
      subscriptions = subscriptions.filter(s => s.id !== podcast.id);
      actions.showToast('Unsubscribed', 'success');
    } catch (e) {}
  }
  
  async function openPodcast(podcast) {
    selectedPodcast = podcast;
    isLoading = true;
    view = 'episodes';
    try {
      const result = await api.getEpisodes(podcast.id, 50);
      episodes = result.episodes || [];
    } catch (e) {}
    isLoading = false;
  }
  
  function playEpisode(episode) {
    actions.playEpisode(episode, selectedPodcast);
  }
  
  function handleKeydown(e) {
    if (e.key === 'Enter') search();
  }
  
  function formatDuration(seconds) {
    if (!seconds) return '';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m} min`;
  }
</script>

<div class="podcasts-tab">
  <!-- Control Panel -->
  <div class="hifi-panel" style="margin:16px; margin-bottom:0;">
    <div class="hifi-flex hifi-gap-md" style="align-items:center;">
      <div class="hifi-input-group" style="flex:1;">
        <input 
          type="text" 
          class="hifi-input"
          placeholder="Search podcasts..." 
          bind:value={searchQuery}
          onkeydown={handleKeydown}
        />
      </div>
      <button class="hifi-btn hifi-btn-primary" onclick={search} title="Podcasts suchen">SEARCH</button>
      {#if view !== 'subscriptions'}
        <button class="hifi-btn" onclick={() => { view = 'subscriptions'; selectedPodcast = null; }} title="Zurueck zu meinen abonnierten Podcasts">MY PODCASTS</button>
      {/if}
    </div>
  </div>
  
  <!-- Content -->
  <div class="podcast-content">
    {#if isLoading}
      <div class="hifi-flex" style="justify-content:center; padding:40px;">
        <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
      </div>
    {:else if view === 'search'}
      {#if searchResults.length === 0}
        <div class="hifi-flex" style="justify-content:center; padding:60px;">
          <HiFiDisplay>NO RESULTS</HiFiDisplay>
        </div>
      {:else}
        <div class="hifi-table-wrapper">
          <table class="hifi-table">
            <tbody>
              {#each searchResults as podcast}
                <tr>
                  <td style="width:60px;">
                    {#if podcast.image_url}
                      <img src={podcast.image_url} alt="" style="width:50px;height:50px;border-radius:4px;object-fit:cover;" />
                    {/if}
                  </td>
                  <td>
                    <div style="font-weight:500;">{podcast.title}</div>
                    <div style="font-size:11px;color:var(--hifi-text-secondary);">{podcast.author}</div>
                  </td>
                  <td style="width:100px;">
                    <button class="hifi-btn hifi-btn-success hifi-btn-small" onclick={() => subscribe(podcast)} title="Podcast abonnieren">+ ADD</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    {:else if view === 'episodes'}
      <!-- Episode Header -->
      <div class="hifi-panel" style="margin:16px;">
        <div class="hifi-flex hifi-gap-md" style="align-items:center;">
          <button class="hifi-btn" onclick={() => { view = 'subscriptions'; selectedPodcast = null; }} title="Zurueck zur Podcast-Uebersicht">← BACK</button>
          {#if selectedPodcast?.image_url}
            <img src={selectedPodcast.image_url} alt="" style="width:60px;height:60px;border-radius:4px;" />
          {/if}
          <div>
            <div style="font-weight:600;font-size:16px;">{selectedPodcast?.title}</div>
            <div style="color:var(--hifi-text-secondary);">{selectedPodcast?.author}</div>
          </div>
        </div>
      </div>
      
      <div class="hifi-table-wrapper" style="margin:0 16px;">
        <table class="hifi-table">
          <tbody>
            {#each episodes as episode}
              {@const isPlaying = appState.currentEpisode?.id === episode.id && appState.isPlaying}
              <tr class:playing={isPlaying} onclick={() => playEpisode(episode)}>
                <td style="width:40px;">
                  <HiFiLed color={isPlaying ? 'green' : 'off'} size="small" />
                </td>
                <td>
                  <div class="episode-title">{episode.title}</div>
                  <div class="episode-duration">{formatDuration(episode.duration)}</div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <!-- Subscriptions -->
      {#if subscriptions.length === 0}
        <div class="hifi-flex hifi-flex-col" style="align-items:center; padding:60px;">
          <HiFiDisplay>NO SUBSCRIPTIONS</HiFiDisplay>
          <p style="color:var(--hifi-text-secondary);margin-top:16px;">Search for podcasts to subscribe</p>
        </div>
      {:else}
        <div class="hifi-table-wrapper" style="margin:16px;">
          <table class="hifi-table">
            <tbody>
              {#each subscriptions as podcast}
                <tr onclick={() => openPodcast(podcast)}>
                  <td style="width:60px;">
                    {#if podcast.image_url}
                      <img src={podcast.image_url} alt="" style="width:50px;height:50px;border-radius:4px;object-fit:cover;" />
                    {/if}
                  </td>
                  <td>
                    <div style="font-weight:500;">{podcast.title}</div>
                    <div style="font-size:11px;color:var(--hifi-text-secondary);">{podcast.episode_count || 0} episodes</div>
                  </td>
                  <td style="width:80px;">
                    <button class="hifi-btn hifi-btn-danger hifi-btn-small" onclick={(e) => unsubscribe(podcast, e)} title="Podcast-Abo entfernen">✕</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .podcasts-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
    font-family: var(--hifi-font-values);
  }
  
  .podcast-content {
    flex: 1;
    overflow-y: auto;
  }
  
  .hifi-table tbody tr {
    cursor: pointer;
  }
  
  .episode-title {
    font-family: var(--hifi-font-values);
    font-size: 14px;
    font-weight: 700;
  }
  
  .episode-duration {
    font-family: var(--hifi-font-values);
    font-size: 11px;
    color: var(--hifi-text-secondary);
  }
</style>
