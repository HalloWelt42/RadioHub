<script>
  import HiFiLed from './hifi/HiFiLed.svelte';
  import HiFiDisplay from './hifi/HiFiDisplay.svelte';
  import { api } from '../lib/api.js';
  import { appState, actions } from '../lib/store.svelte.js';
  
  let folders = $state([]);
  let files = $state([]);
  let currentPath = $state('');
  let stats = $state({ disk_free_gb: 0, file_count: 0, used_mb: 0 });
  let isLoading = $state(false);
  
  $effect(() => {
    loadStats();
    loadFolders();
    loadFiles('');
  });
  
  async function loadStats() {
    try {
      stats = await api.getRecordingsStats();
    } catch (e) {}
  }
  
  async function loadFolders() {
    try {
      const result = await api.getRecordingsFolders();
      folders = result.folders || [];
    } catch (e) {}
  }
  
  async function loadFiles(path) {
    isLoading = true;
    currentPath = path;
    try {
      const result = await api.getRecordingsFiles(path || '/', 100);
      files = result.files || [];
    } catch (e) {}
    isLoading = false;
  }
  
  function playFile(file) {
    const url = api.getPlayUrl(file.path);
    appState.currentStation = null;
    appState.currentEpisode = {
      title: file.name,
      audio_url: url,
      podcast: { title: 'Recording' }
    };
    appState.isPlaying = true;
  }
  
  async function deleteFile(file, e) {
    e.stopPropagation();
    try {
      await api.fetch(`/api/recordings/file?path=${encodeURIComponent(file.path)}`, { method: 'DELETE' });
      files = files.filter(f => f.path !== file.path);
      actions.showToast('Deleted', 'success');
      loadStats();
    } catch (e) {
      actions.showToast('Error', 'error');
    }
  }
  
  function formatSize(bytes) {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
  
  function formatDate(isoString) {
    const d = new Date(isoString);
    return d.toLocaleDateString('de-DE') + ' ' + d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }
</script>

<div class="recordings-tab">
  <!-- Stats Panel -->
  <div class="hifi-panel" style="margin:16px; margin-bottom:0;">
    <div class="hifi-flex hifi-gap-lg" style="align-items:center;">
      <div class="hifi-display hifi-display-small">{stats.file_count} FILES</div>
      <div class="hifi-display hifi-display-small">{stats.used_mb.toFixed(1)} MB USED</div>
      <div class="hifi-display hifi-display-small">{stats.disk_free_gb.toFixed(1)} GB FREE</div>
      
      <div style="flex:1;"></div>
      
      <!-- Folder buttons -->
      <button 
        class="hifi-btn"
        class:active={currentPath === ''}
        onclick={() => loadFiles('')}
      >ALL</button>
      {#each folders as folder}
        <button 
          class="hifi-btn"
          class:active={currentPath === folder.path}
          onclick={() => loadFiles(folder.path)}
        >{folder.name.toUpperCase()}</button>
      {/each}
    </div>
  </div>
  
  <!-- File List -->
  <div class="file-list">
    {#if isLoading}
      <div class="hifi-flex" style="justify-content:center; padding:40px;">
        <div class="hifi-spinner"><div class="hifi-spinner-ring"></div></div>
      </div>
    {:else if files.length === 0}
      <div class="hifi-flex hifi-flex-col" style="align-items:center; padding:60px;">
        <HiFiDisplay size="medium">NO RECORDINGS</HiFiDisplay>
      </div>
    {:else}
      <div class="hifi-table-wrapper">
        <table class="hifi-table">
          <thead>
            <tr>
              <th>FILE</th>
              <th style="width:100px;">SIZE</th>
              <th style="width:150px;">DATE</th>
              <th style="width:50px;"></th>
            </tr>
          </thead>
          <tbody>
            {#each files as file}
              <tr onclick={() => playFile(file)}>
                <td>{file.name}</td>
                <td>{formatSize(file.size)}</td>
                <td>{formatDate(file.modified)}</td>
                <td>
                  <button class="hifi-btn hifi-btn-small hifi-btn-danger" onclick={(e) => deleteFile(file, e)}>✕</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

<style>
  .recordings-tab {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  .file-list {
    flex: 1;
    overflow-y: auto;
    padding: 0 16px 16px;
  }
  
  .hifi-table tbody tr {
    cursor: pointer;
  }
</style>
